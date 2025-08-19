from typing import List, Dict, Any, Optional
from pathlib import Path
from collections import defaultdict, deque
from dataclasses import dataclass
from pydantic import AnyUrl

from legislation.datasource_esel import DataSourceESEL
from legislation.service import LegislationService
from legislation.domain import LegalAct, LegalStructuralElement
from search.service import SearchService
from search.domain import SearchOptions, SearchStrategy, SearchResults
from index.service import IndexService
from ontology.service import OntologyService
from ontology.store import OntologyStore
from modeler.specialists.class_detail_specialist import ClassDetailSpecialist, OntologyClass, OntologyClassDetailUpdateResult
import re

DEFAULT_LLM_MODEL = "gpt-4.1-mini"


class ModelerService:
    """
    Service for ontology modeling task.
    """

    def __init__(self, legal_act_id: str, llm_model: str = DEFAULT_LLM_MODEL):
        """
        Initialize the modeler service.

        Args:
            legal_act_id: The ID of the legal act.
            llm_model: The LLM model to use.
        """
        self.legal_act_id = legal_act_id
        self.llm_model = llm_model

        data_source = DataSourceESEL()
        self.legislation_service = LegislationService(data_source, self.llm_model)
        self.legal_act = self.legislation_service.get_legal_act(AnyUrl(legal_act_id))

        project_root = Path(__file__).parent.parent.parent
        index_base_path = project_root / "data" / "indexes"

        self.index_service = IndexService(index_base_path)
        self.search_service = SearchService(self.index_service, self.legal_act)

        ontology_store = OntologyStore()
        self.ontology_service = OntologyService(ontology_store)

        self.class_detail_specialist = ClassDetailSpecialist()

    def model_ontology(self) -> str:
        """
        Model the ontology based on the legal act.

        Returns:
            The OWL representation of the modeled ontology.
        """
        # Initialize FIFO queue with concepts from seed terms
        ontology_class_queue = deque()
        
        # Get seed terms and create concepts
        seed_terms = self._get_top_k_seed_terms(k=10)
        # Some of the terms to exclude from the ontology
        stop_terms = ["ministerstvo"]
        for seed_term_data in seed_terms:
            if seed_term_data["term"] in stop_terms:
                continue
            ontology_class = OntologyClass(name=seed_term_data["term"], definition="", comment="")
            ontology_class_queue.append(ontology_class)

        # Process queue until empty
        while ontology_class_queue:
            current_ontology_class = ontology_class_queue.popleft()

            # Find legal sections in the legal act that are semantically relevant for the current concept
            search_result_for_term = self._find_seed_legal_sections_in_legal_act_for_term(current_ontology_class.name, 10)

            # Extract legal section IDs from the search results
            legal_sections_ids = [result["legal_section_id"] for result in search_result_for_term["results"]]
            
            for legal_section in legal_sections_ids:
                # Get summarized legal act with details for the legal_section and its siblings.
                domain_knowledge = self._get_domain_knowledge_for_legal_section(legal_section)

                updated_ontology_class = self.class_detail_specialist.update_class_detail(current_ontology_class, domain_knowledge)

                print(f"Updated ontology class: {updated_ontology_class}")

            print(f"Finished term: {current_ontology_class.term}"  )

        return ""


    def _get_top_k_seed_terms(self, k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Returns the most frequently appearing terms (seed terms) from a legal act.
        
        Seed terms are terms frequently occurring in the legal act, calculated
        based on term frequency with hierarchical weighting:
        - LegalSection: 1x weight
        - LegalDivision: 2x weight  
        - LegalChapter: 4x weight
        - LegalPart: 8x weight
        - LegalAct: 16x weight
        
        Term frequency TF(t,act) = f(t,act) / sum(f(t',act)) for all terms t'
        
        Args:
            legal_act_id: The IRI identifier of the legal act
            k: Number of top terms to return (optional; if None, returns all terms)
            
        Returns:
            List of dictionaries containing term and frequency information:
            [{"term": str, "frequency": float, "raw_count": int}, ...]
        """

        def get_element_weight(element_type: str) -> int:
            """
            Get the hierarchical weight for an element type.
            
            Args:
                element_type: The type of the legal element
                
            Returns:
                Weight multiplier (1, 2, 4, 8, or 16)
            """
            weight_map = {
                "LegalSection": 1,      # 2^0
                "LegalDivision": 2,     # 2^1  
                "LegalChapter": 4,      # 2^2
                "LegalPart": 8,         # 2^3
                "LegalAct": 16          # 2^4
            }
            
            return weight_map.get(element_type, 1)  # Default to 1 for unknown types

        def calculate_weighted_term_frequencies(element: LegalStructuralElement) -> Dict[str, int]:
            """
            Recursively calculate weighted term frequencies from an element and its children.
            
            Args:
                element: The legal structural element to process
                
            Returns:
                Dictionary mapping terms to their weighted counts
            """
            term_counts = defaultdict(int)
            
            # Get the weight for this element type
            weight = get_element_weight(element.elementType)

            # Add terms from this element's summary_names with appropriate weight
            if element.summary_names:
                for term in element.summary_names:
                    if term and term.strip():  # Only count non-empty terms
                        term_counts[term.strip()] += weight
            
            # Recursively process child elements
            if element.elements:
                for child in element.elements:
                    child_counts = calculate_weighted_term_frequencies(child)
                    for term, count in child_counts.items():
                        term_counts[term] += count
            
            return dict(term_counts)

        # Calculate weighted term frequencies
        term_counts = calculate_weighted_term_frequencies(self.legal_act)
        
        # Calculate total count for normalization
        total_count = sum(term_counts.values())
        
        if total_count == 0:
            return []
        
        # Calculate normalized frequencies and create result list
        term_frequencies = []
        for term, count in term_counts.items():
            frequency = count / total_count
            term_frequencies.append({
                "term": term,
                "frequency": frequency,
                "raw_count": count
            })
        
        # Sort by frequency (descending)
        term_frequencies.sort(key=lambda x: x["frequency"], reverse=True)
        if k is not None:
            return term_frequencies[:k]
        return term_frequencies

    def _find_seed_legal_sections_in_legal_act_for_term(
        self,
        term: str,
        k: int
    ) -> Dict[str, Any]:
        """
        Searches for seed k legal sections relevant for the given term.

        Args:
            term: Search term
            k: Number of seed legal sections to find

        Returns:
            Dictionary containing search results and metadata:
            {
                "term": str,
                "total_found": int,
                "results": [
                    {
                        "legal_section_id": str,
                        "title": str,
                        "official_identifier": str,
                        "text_content": str,
                        "score": float,
                        "rank": int,
                        "parent_id": str
                    }, ...
                ]
            }
            where:
            - term: The search term
            - total_found: The total number of results found
            - results: A list of matching legal sections
            where:
            - legal_section_id: The unique technical identifier of the legal section in the form of a globally unique IRI (Internationalized Resource Identifier)
            - title: The title of the legal section
            - official_identifier: The official identifier of the legal section. It differs from the legal_section_id in that it is a human-readable string. It is unique within the legal act.
            - text_content: The text content of the legal section in XML format which structures the text content into a hiearchy of fragments (<f> elements) each with its fragment id being a globally unique IRI with legal_section_id as prefix followed by a local part identifying the fragment within the legal section hierarchy.
            - score: The relevance score of the legal section within the context of the search query.
            - rank: The rank of the legal section in the search results.
            - parent_id: The ID of the parent element in the form of a globally unique IRI. It can be any higher-level element in the hierarchy of the legal act, i.e. legal division, chapter, part, or the act itself.
        """
        
        # 1. Semantic search that tries to find legal sections with text content similar to the term
        search_options = SearchOptions(
            max_results=k,
            element_types=["section"]
        )
        search_results: SearchResults = self.search_service.search_keyword_summary(
            query=term,
            options=search_options
        )

        # Convert results to dictionary format, combining both search results
        results_data = []

        # Add all results from semantic search
        for item in search_results.items:
            results_data.append({
                "legal_section_id": item.element_id,
                "title": item.title,
                "official_identifier": item.official_identifier,
                "text_content": item.text_content,
                "score": item.score,
                "rank": item.rank,
                "parent_id": item.parent_id
            })
        
        total_found = len(results_data)
        
        return {
            "term": term,
            "total_found": total_found,
            "results": results_data
        }
    
    def _get_domain_knowledge_for_legal_section(self, legal_section_iri: str) -> str:
        """
        Generate a partially summarized XML representation of the legal act with targeted detail of a single 
        legal section and its immediate previous and following sibling sections.
        
        This method finds the specified legal section, identifies its previous and following sibling 
        sections within the same parent, and then calls the detailed targeting method with all three 
        sections to provide context around the target section.

        Args:
            legal_section_iri: IRI (Internationalized Resource Identifier) of the target legal section

        Returns:
            XML string representation of the legal act with the following structure:
            - For the target legal section and its siblings: includes id, officialIdentifier, 
              title, textContent without ids.
            - For ancestor elements containing these legal sections: includes id, officialIdentifier, 
              title, and summary
            - Maintains the hierarchical structure of the original legal act
            - Elements with no target legal sections in their descendants are excluded
            - Returns empty string if the target legal section is not found in the legal act hierarchy
            
            The textContent field contains XML fragments with hierarchical structure using <f> elements,
            where each fragment has a globally unique IRI with the legal_section_id as prefix.
        """
        # Find the target legal section in the legal act
        target_element = self.legislation_service._find_element_by_id(self.legal_act, legal_section_iri)
        if not target_element:
            return ""
        
        # Find the parent element that contains this section
        parent_element = self._find_parent_element(self.legal_act, legal_section_iri)
        if not parent_element or not parent_element.elements:
            # If no parent found or parent has no children, just process the single section
            return self._get_legal_act_hierarchical_summary_targeting_legal_sections_details([legal_section_iri])
        
        # Find the index of the target section in the parent's children
        target_index = -1
        for i, child in enumerate(parent_element.elements):
            if str(child.id) == legal_section_iri:
                target_index = i
                break
        
        if target_index == -1:
            # Target section not found in parent's children, just process the single section
            return self._get_legal_act_hierarchical_summary_targeting_legal_sections_details([legal_section_iri])
        
        # Collect the target section and its siblings
        sections_to_process = []
        
        # Add previous sibling if exists
        if target_index > 0:
            previous_sibling = parent_element.elements[target_index - 1]
            sections_to_process.append(str(previous_sibling.id))
        
        # Add the target section
        sections_to_process.append(legal_section_iri)
        
        # Add following sibling if exists
        if target_index < len(parent_element.elements) - 1:
            following_sibling = parent_element.elements[target_index + 1]
            sections_to_process.append(str(following_sibling.id))
        
        # Generate the XML representation starting from the root legal act
        return self._generate_detail_knowledge_with_hierarchical_context_from_legal_section(self.legal_act, sections_to_process)

    def _find_parent_element(self, element: LegalStructuralElement, target_child_id: str) -> Optional[LegalStructuralElement]:
        """
        Find the parent element that directly contains a child with the specified ID.
        
        Uses the hierarchical IRI structure where the parent ID is the child ID 
        without the last fragment (fragments are separated by '/').
        
        Args:
            element: The root element to search from (not used in current implementation)
            target_child_id: The ID of the child element to find the parent for
            
        Returns:
            The parent element if found, None otherwise
        """
        # Extract parent ID by removing the last fragment from the hierarchical IRI
        if '/' not in target_child_id:
            return None
            
        parent_id = target_child_id.rsplit('/', 1)[0]
        
        # Find the parent element using the legislation service
        return self.legislation_service._find_element_by_id(self.legal_act, parent_id)

    def _generate_detail_knowledge_with_hierarchical_context_from_legal_section(self, legal_structural_element: LegalStructuralElement, legal_sections: set, indent: int = 0) -> str:
        """
        Recursively generate XML content for legal sections and their ancestors.
        
        Args:
            legal_structural_element: The current element being processed
            legal_sections: Set of legal section IRIs that should include full textContent
            indent: Current indentation level for XML formatting
            
        Returns:
            XML string representation based on the rules:
            - Full textContent if element is in legal_sections
            - Summary + children if element has descendants in legal_sections
            - Empty string if element not in legal_sections and no relevant descendants
        """
        element_id = str(legal_structural_element.id)
        ind = "\t" * indent
        
        # Check if this element is one of the target legal sections
        if element_id in legal_sections:
            # Return full details for target legal sections
            return self._generate_detail_knowledge_from_legal_section(legal_structural_element, indent)
        
        # Check if any descendants are in legal_sections
        if not self._has_descendant_in_legal_sections(legal_structural_element, legal_sections):
            # No relevant descendants, return empty string
            return ""
        
        # This element has descendants in legal_sections, so include summary and process children
        lines: List[str] = []
        
        # Start element tag with id attribute
        lines.append(f'{ind}<CONTEXT_KNOWLEDGE>')

        # Include basic information (id, title, summary) for ancestor elements
        lines.append(f'{ind}\t<officialIdentifier>{str(legal_structural_element.officialIdentifier or "")}</officialIdentifier>')
        lines.append(f'{ind}\t<title>{str(legal_structural_element.title or "")}</title>')
        lines.append(f'{ind}\t<summary>{str(legal_structural_element.summary or "")}</summary>')
        
        # Process children recursively
        children = getattr(legal_structural_element, 'elements', None) or []
        for child in children:
            child_content = self._generate_detail_knowledge_with_hierarchical_context_from_legal_section(child, legal_sections, indent + 1)
            if child_content:  # Only include non-empty child content
                lines.append(child_content)
        
        # Close tag
        lines.append(f'{ind}</CONTEXT_KNOWLEDGE>')
        
        return "\n".join(lines)
    
    def _has_descendant_in_legal_sections(self, legal_structural_element: LegalStructuralElement, legal_sections: set) -> bool:
        """
        Check if the given element has any descendant in the legal_sections set.
        
        Args:
            legal_structural_element: The element to check
            legal_sections: Set of legal section IRIs
            
        Returns:
            True if element or any descendant is in legal_sections, False otherwise
        """
        # Check current element
        if str(legal_structural_element.id) in legal_sections:
            return True
        
        # Check children recursively
        children = getattr(legal_structural_element, 'elements', None) or []
        for child in children:
            if self._has_descendant_in_legal_sections(child, legal_sections):
                return True
        
        return False

    def _generate_detail_knowledge_from_legal_section(self, el, indent: int = 0) -> str:
        """Generates the detailed knowledge from the legal section for processing by a large language model.
        """
        ind = "\t" * indent
        lines: List[str] = []
        # Start element tag with id attribute
        lines.append(f'{ind}<DETAILED_KNOWLEDGE>')

        # Basic scalar fields
        lines.append(f'{ind}\t<officialIdentifier>{str(el.officialIdentifier or "")}</officialIdentifier>')
        lines.append(f'{ind}\t<title>{str(el.title or "")}</title>')

        # text content
        text_content = getattr(el, 'textContent', "")
        if (text_content != ""):
            # Remove all 'id' attributes from <f> elements in text_content
            cleaned_text_content = re.sub(r'<f\s+id="[^"]*"', '<f', str(text_content))
            lines.append(f'{ind}\t<text-with-fragments>{cleaned_text_content}</text-with-fragments>')

        # Close tag
        lines.append(f'{ind}</DETAILED_KNOWLEDGE>')
        return "\n".join(lines)