from pathlib import Path
from pydantic import AnyUrl
import re

from agents import (
    Agent,
    Runner,
    TResponseInputItem,
    MessageOutputItem,
    ItemHelpers,
    ModelSettings,
    ToolCallItem,
    ToolCallOutputItem,
    function_tool
)

from legislation.datasource_esel import DataSourceESEL
from legislation.service import LegislationService
from search.domain import SearchOptions, SearchResults
from search.service import SearchService
from index.service import IndexService
from ontology.service import OntologyService
from ontology.store import OntologyStore
from collections import defaultdict

class OntologyModelingAgent:
    """
    Agent for building an ontology from a given legal act text.
    """

    #TODO: modeluje Ministerstvo, registr
    #TODO: zavedl výrobce *silničního* vozidla, ale pak vlastníka vozidla a provozovtele vozidla, byť zákon mluví o vlastníkovi/provozovateli *silničního* vozidla
    #TODO: definice byly na začátku moc odchýlené od textu v zákonu, definice pojmů by měly v maximální možné míře citovat text ze zákona, které je definičním textem.
    #TODO: Komentář komentuje vztah pojmu k zákonu. Je to tedy spíše meta-komentář. Komentáře mají být věcné, vysvětlující doménovou sémantiku, tj. význam, pojmu.
    #TODO: měl by mít explicitně instrukci se zaměřit na to, zda by třída neměla mít nadřídu - obzvlášť pozor při rolích osob
    #TODO: nutno explicitně zakázat ve fázi 1 dělat vlastnosti
    #TODO: vypsal třídy a zeptal se, zda má pracovat na jedné, dostal potvrzení ale pak ji rovnou hodil do ontologie, aniž by ukázal detail uživateli
    AGENT_INSTRUCTIONS = """<ROLE>You are a Conceptual Designer Agent, an ontology engineering expert. </ROLE>
<TASK>
- Construct a rigorous and exhaustive domain ontology from the provided legal act and user input.
- Engage with a user who is a domain authority but lacks ontology engineering experience.
</TASK>
<INPUT>
- Your sole repository of domain knowledge is the text of the relevant legal act and prior dialogue with the user.
</INPUT>
<BEHAVIOR>
- Derive ontology elements strictly from provided domain knowledge sources; prohibit speculative additions.
- Prioritize ontological simplicity: restrict modeling to classes, attributes, and binary relationships.
- Conduct exhaustive analysis for each ontology element, ensuring full coverage of relevant domain knowledge.
</BEHAVIOR>
<OUTPUT_DEFINITION>
- Class: Represents a domain entity (subject or object).
    - Subject: Entity capable of rights and obligations (e.g., natural/legal persons, functional roles).
    - Object: Entity that is the target or beneficiary of legal relations (e.g., assets, entitlements, official acts) but lacks legal agency.
- Attribute: Intrinsic atomic property of a class, representing a single fact (analogous to one form field). Prohibit aggregation; maintain strict atomization.
- Binary Relationship: Directed semantic connection between two classes.
</OUTPUT_DEFINITION>
<OUTPUT_STRUCTURE>
- Each ontology element includes:
    - prefLabel: Unique, concrete, short label
        - Classes: Noun/noun phrase, first letter upper-case (e.g. "Kosmická loď")
        - Attributes: Noun/noun phrase, lower case, includes the class's prefLabel linguistically incorporated (e.g. "barva kosmické lodi" instead of "barva")
        - Relationships: Verb/verb phrase, lower case, includes prefLabel of one of the linked classes, preferably the target (e.g. "je kapitánem kosmické lodi" instead of "je kapitánem" or "je")
    - definition: Concise, non-circular sentence; quotes legal definition from the legal act with only minor linguistic modifications.
    - comment: Explains the element meaning, expanding on semantics without introducing extraneous context.
    - references: One or more references to numbered paragraphs and their hierarchical fragment in the legal act with the definitory text of the ontology element. Keeps the hierarchical numbering from the numbered paragraph to the specific hierarchical fragment (e.g., "§ 3 (2) a)").
- For classes: parent class if applicable.
- For attributes: domain class.
- For relationships: domain class and range class.
- All text (labels, definitions, comments) must remain traceable to source legal knowledge.
</OUTPUT_STRUCTURE>
<TOOLS>
- Utilize `get_hierarchical_summary_of_legal_act` for structured overviews.
- Use `search_legal_act` for targeted semantic search.
- Retrieve or update ontology with `get_working_ontology`, `add_new_class`, `add_new_attribute`, and `add_new_relationship`. Do not manually assign IRIs.
</TOOLS>
<ROUTINE>
**PHASE 1 - Determine class taxonomy**
1. Extract candidate class from the legal act summary (start from the most important); present it to user with concise semantic justification.
2. Collaboratively refine class with user (iterative confirmation/refinement).
3. Synthesize complete legal knowledge pertaining to the class.
4. Validate understanding with user, update with feedback.
5. Continuously cross-validate ontology class with the legal act.
6. Before adding a class to the ontology, ensure that
    6.1. all necessary information (labels, definitions, comments, references) is complete and accurate and present it to the user for confirmation.
    6.2. the parent class, if applicable, is already present in the ontology.
8. Iterate until all relevant classes are extracted and added to the ontology.
**PHASE 2 - Define properties**
1. Determine a class from the ontology.
2. Synthesize complete legal knowledge relevant to the class properties.
3. Identify and systematically classify properties as attributes or relationships, ensuring strict adherence to atomicity and proper semantic modeling.
    3.1. Rigorously distinguish intrinsic vs. relational properties. Model the former as attributes, the other as relationships.
    3.2. Decompose attributes as needed for maximal granularity.
    3.3. For relationships capture and queue referenced classes for further modeling.
4. Present and review properties with user; refine iteratively.
5. Continuously cross-validate properties with the legal act.
6. Upon user confirmation, add properties into the ontology.
    6.1. When adding an attribute, ensure the domain class is already present in the ontology.
    6.2. When adding a relationship, ensure both the domain class and range class are already present in the ontology.
7. Track unaddressed classes and prompt user to revisit skipped classes when appropriate.
8. Iterate until all relevant properties are extracted and added to the ontology.
**PHASE 3 - Validate and finalize ontology**
1. Review the entire ontology with the user, ensuring all elements are accurate and complete.
2. When necessary, return to PHASE 1, e.g. new classes were discovered in PHASE 2 but skipped.
3. Validate the ontology against the legal act, checking for consistency and compliance.
</ROUTINE>
<OUTPUT>
Your output is a comprehensive domain ontology that you build iteratively based on the legal act and the previous conversation with the user.
The domain ontology comprises all discovered classes, their attributes and binary relationships.
</OUTPUT>"""


    def __init__(self, legal_act_id: str):
        """
        Initialize the OntologyModelingAgent.

        Args:
            legal_act_id (str): The IRI identifier of the legal act.
        """
        self.legal_act_id = legal_act_id

        data_source = DataSourceESEL()
        self.legislation_service = LegislationService(data_source, "gpt-4.1")
        self.legal_act = self.legislation_service.get_legal_act(AnyUrl(legal_act_id))

        project_root = Path(__file__).parent.parent.parent
        index_base_path = project_root / "data" / "indexes"

        self.index_service = IndexService(index_base_path)
        self.search_service = SearchService(self.index_service, self.legal_act)

        ontology_store = OntologyStore()
        self.ontology_service = OntologyService(ontology_store)

        self.working_ontology_file = Path(__file__).parent.parent.parent / "data" / "output" / "56-2001-2025-07-01-ontology.ttl"

        # Create the tool function that captures self context
        @function_tool
        def get_hierarchical_summary_of_legal_act() -> str:
            """
            Get the legal act summary, comprising hierarchically organized summaries of the legal act, its parts, chapters, and divisions.
            
            Use this tool to retrieve an overview of the domain knowledge in the form of summarized content of the legal act hierarchically structured based on the original structure of the legal act.
            This gives you complete context and understanding of the domain without the need to read the full legal act that can be very long.
            
            Returns:
                str: XML representation of the hierarchical structure
            """
            return self._get_hierarchical_summary_impl()
        
        @function_tool
        def search_legal_act(query: str, k: int) -> list[str]:
            """
            Search the legal act for relevant passages based on the query.
            
            Use this tool to find semantically relevant passages within the legal act for the given query to get detailed domain knowledge from the legal act.
            The query can be any text.

            Usage tips:
            1) Try to be as specific as possible when formulating your query, e.g.:
            - When needing details about a class, use also different shapes of the class preferred label, its various synonyms, and also keywords from the known description of the class.
            - When needing details about a relationships of a class, use the preferred labels of the class and relationship, and keywords from their known definitions or descriptions.
            
            2) If the query does not return anything relevant, relax the query and try again.

            3) Use the parameter k to determine the number of returned passages. If all returned passages are highly relevant, there may be other passages in the legal text that you did not receive so search again with increased k.

            4) If you need to find a definition text for element use a query in the form "[pref label] se rozumí".

            Args:
                query (str): The search query.
                k (int): The number of relevant passages to retrieve.

            Returns:
                list[str]: A list of relevant passages from the legal act.
            """
            return self._search_legal_act_impl(query, k)
        
        @function_tool
        def get_working_ontology() -> str:
            """
            Get the current working ontology.
            
            Use this tool to retrieve the current working ontology you constructed in the previous steps expressed in RDF Turtle syntax.

            Returns:
                str: The current working ontology.
            """
            return self._get_working_ontology_impl()
        
        @function_tool
        def add_new_class(prefLabel: str, definition: str, comment: str, references: list[str], parent_class_prefLabel: str) -> bool:
            """
            Use this tool to add a new class to the ontology.

            Args:
                prefLabel (str): preferred label of the class.
                definition (str): definition of the class.
                comment (str): comment about the class.
                references (list[str]): references to the legal act.
                parent_class_prefLabel (str): preferred label of the parent class.

            Returns:
                bool: True if successfully added, False otherwise.
            """
            return self._add_new_class_impl(prefLabel, definition, comment, references, parent_class_prefLabel)

        @function_tool
        def add_new_attribute(prefLabel: str, definition: str, comment: str, references: list[str], domain_class_prefLabel: str) -> bool:
            """
            Use this tool to add a new attribute (datatype property) to the ontology.

            Args:
                prefLabel (str): The preferred label of the attribute.
                definition (str): The definition of the attribute.
                comment (str): Additional comment about the attribute.
                references (list[str]): References to the legal act.
                domain_class_prefLabel (str): The preferred label of the class this attribute belongs to.

            Returns:
                bool: True if successfully added, False otherwise.
            """
            return self._add_new_attribute_impl(prefLabel, definition, comment, references, domain_class_prefLabel)

        @function_tool
        def add_new_relationship(prefLabel: str, definition: str, comment: str, references: list[str], domain_class_prefLabel: str, range_class_prefLabel: str) -> bool:
            """
            Use this tool to add a new relationship (object property) to the ontology.

            Args:
                prefLabel (str): The preferred label of the relationship.
                definition (str): The definition of the relationship.
                comment (str): Additional comment about the relationship.
                references (list[str]): References to the legal act.
                domain_class_prefLabel (str): The preferred label of the domain class this relationship belongs to.
                range_class_prefLabel (str): The preferred label of the range class this relationship connects to.

            Returns:
                bool: True if successfully added, False otherwise.
            """
            return self._add_new_relationship_impl(prefLabel, definition, comment, references, domain_class_prefLabel, range_class_prefLabel)

        self.agent = Agent(
            name="OntologyModelingAgent",
            instructions=self.AGENT_INSTRUCTIONS,
            model="gpt-5",
            model_settings=ModelSettings(
                reasoning={
                    "effort": "minimal"
                },
                verbosity="low"
            ),
            tools=[get_hierarchical_summary_of_legal_act, search_legal_act, get_working_ontology, add_new_class, add_new_attribute, add_new_relationship]
        )

    async def build_ontology(self) -> None:
        """
        Build the ontology from the legal act.
        """
        input_items: list[TResponseInputItem] = []

        current_agent = self.agent

        input_items.append({"content": "Budeme pracovat se zákonu o podmínkách provozu vozidel na pozemních komunikacích.", "role": "user"})    

        skip_run = False

        while True:

            if not skip_run:

                result = await Runner.run(current_agent, input_items, max_turns=1000)
                
                for new_item in result.new_items:
                    agent_name = new_item.agent.name
                    if isinstance(new_item, MessageOutputItem):
                        print("=" * 50)
                        print(f"[{agent_name}]: {ItemHelpers.text_message_output(new_item)}")
                        print("=" * 50)
                    elif isinstance(new_item, ToolCallItem):
                        tool_name = getattr(new_item.raw_item, 'name', None) or getattr(new_item.raw_item, 'function', {}).get('name', 'unknown tool')
                        arguments = getattr(new_item.raw_item, 'arguments', None)
                        print(f"[{agent_name}]: Calling a tool {tool_name} with arguments {arguments}")
                    elif isinstance(new_item, ToolCallOutputItem):
                        print(f"[{agent_name}]: Tool output received.")
                    else:
                        print(f"[{agent_name}]: Skipping item: {new_item.__class__.__name__}")

                input_items = result.to_input_list()
                current_agent = result.last_agent

            user_input = input("Co dál? ('exit' pro ukončení, 'write' pro write): ")

            if user_input.lower() == 'exit':
                break
            elif user_input.lower() == 'write':
                self._write_working_ontology_to_file()
                skip_run = True
            else:
                input_items.append({"content": user_input, "role": "user"})
                skip_run = False

    
    # TOOL IMPLEMENTATIONS

    def _get_working_ontology_impl(self) -> str:
        """
        Implementation method for getting the current working ontology.

        Returns:
            str: The current working ontology in OWL/TTL format.
        """
        return self.ontology_service.export_whole_ontology_to_turtle()
    
    def _add_new_class_impl(self, prefLabel: str, definition: str, comment: str, references: list[str], parent_class_prefLabel: str) -> bool:
        """
        Implementation method for adding a new class to the ontology.

        Args:
            prefLabel (str): The preferred label of the class.
            definition (str): The definition of the class.
            comment (str): Additional comment about the class.
            references (list[str]): References to the legal act.
            parent_class_prefLabel (str): The preferred label of the parent class.

        Returns:
            bool: True if successfully added, False otherwise.
        """
        iri = None  # Unspecified IRI, will be generated
        # Use references as source_elements list
        source_elements = references if references else []

        # Find parent class by prefLabel if specified
        if parent_class_prefLabel:
            parent_class = self.ontology_service.get_class_by_prefLabel(parent_class_prefLabel)
            if not parent_class:
                return False
            parent_class_iri = str(parent_class.iri)
        else:
            parent_class_iri = None  # No parent class specified
        
        return self.ontology_service.add_class(
            iri,
            name_cs=prefLabel,
            name_en="",
            definition_cs=definition,
            definition_en="",
            comment_cs=comment,
            comment_en="",
            parent_class_iri=parent_class_iri,
            source_elements=source_elements
        )

    def _add_new_attribute_impl(self, prefLabel: str, definition: str, comment: str, references: list[str], domain_class_prefLabel: str) -> bool:
        """
        Implementation method for adding a new attribute (datatype property) to the ontology.

        Args:
            prefLabel (str): The preferred label of the attribute.
            definition (str): The definition of the attribute.
            comment (str): Additional comment about the attribute.
            references (list[str]): References to the legal act.
            domain_class_prefLabel (str): The preferred label of the domain class this attribute belongs to.

        Returns:
            bool: True if successfully added, False otherwise.
        """
        iri = None  # Unspecified IRI, will be generated

        # Find domain class by prefLabel and check that this class exists
        if not domain_class_prefLabel:
            return False
        domain_class = self.ontology_service.get_class_by_prefLabel(domain_class_prefLabel)
        if not domain_class:
            return False

        # Use references as source_elements list
        source_elements = references if references else []

        return self.ontology_service.add_property(
            iri=iri,
            property_type="DatatypeProperty",
            name_cs=prefLabel,
            name_en="",
            definition_cs=definition,
            definition_en="",
            comment_cs=comment,
            comment_en="",
            domain_iri=str(domain_class.iri),
            range_iri="http://www.w3.org/2001/XMLSchema#string",  # Default to string
            source_elements=source_elements
        )

    def _add_new_relationship_impl(self, prefLabel: str, definition: str, comment: str, references: list[str], domain_class_prefLabel: str, range_class_prefLabel: str) -> bool:
        """
        Implementation method for adding a new relationship (object property) to the ontology.

        Args:
            prefLabel (str): The preferred label of the relationship.
            definition (str): The definition of the relationship.
            comment (str): Additional comment about the relationship.
            references (list[str]): References to the legal act.
            domain_class_prefLabel (str): The preferred label of the domain class this relationship belongs to.
            range_class_prefLabel (str): The preferred label of the range class this relationship connects to.

        Returns:
            bool: True if successfully added, False otherwise.
        """
        iri = None  # Unspecified IRI, will be generated
        
        # Find domain class by prefLabel and check that this class exists
        if not domain_class_prefLabel:
            return False
        domain_class = self.ontology_service.get_class_by_prefLabel(domain_class_prefLabel)
        if not domain_class:
            return False

        # Find range class by prefLabel and check that this class exists
        if not range_class_prefLabel:
            return False
        range_class = self.ontology_service.get_class_by_prefLabel(range_class_prefLabel)
        if not range_class:
            return False

        # Use references as source_elements list
        source_elements = references if references else []

        return self.ontology_service.add_property(
            iri=iri,
            property_type="ObjectProperty",
            name_cs=prefLabel,
            name_en="",
            definition_cs=definition,
            definition_en="",
            comment_cs=comment,
            comment_en="",
            domain_iri=str(domain_class.iri),
            range_iri=str(range_class.iri),
            source_elements=source_elements
        )

    def _get_hierarchical_summary_impl(self) -> str:
        """
        Implementation method for getting the legal act summary.
        
        Returns:
            str: XML representation of the hierarchical structure
        """
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append('<legalAct>')
        
        # Process the root legal act
        self._add_element_to_xml(self.legal_act, xml_lines, indent=1)

        xml_lines.append('</legalAct>')
        output = '\n'.join(xml_lines)

        return output

    def _search_legal_act_impl(self, query: str, k: int) -> str:
        """
        Implementation method for searching the legal act.

        Args:
            query (str): The search query.
            k (int): The number of relevant passages to retrieve.

        Returns:
            list[str]: A list of relevant passages from the legal act.
        """
        options = SearchOptions(
            max_results=k,
            element_types=["section"]
        )

        results: SearchResults = self.search_service.search_semantic_fulltext(query, options)

        # Create a mapping from parent_id to list of search result items
        parent_to_items = defaultdict(list)
        for item in results.items:
            if item.parent_id:
                parent_to_items[item.parent_id].append(item)

        # Generate XML by recursively traversing the legal act
        xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml_lines.append('<searchResults>')
        
        self._add_search_element_to_xml(self.legal_act, parent_to_items, xml_lines, indent=1)

        xml_lines.append('</searchResults>')
        output = '\n'.join(xml_lines)

        return output

    # HELPER METHODS
    
    def _get_short_id(self, element_id: str) -> str:
        """
        Remove the common prefix from element ID to get a shorter identifier.
        
        Args:
            element_id: Full element ID (IRI)
            
        Returns:
            str: Shortened element ID with common prefix removed
        """
        # Common prefix pattern for ESEL legal acts
        prefix_pattern = r"https://opendata\.eselpoint\.cz/esel-esb/eli/cz/sb/[0-9]{4}/[0-9]+/[0-9]{4}-[0-9]{2}-[0-9]{2}/dokument/norma/"
        
        # Remove the prefix if it matches
        shortened = re.sub(prefix_pattern, "", element_id)
        return shortened
    
    def _add_search_element_to_xml(self, element, parent_to_items: dict, xml_lines: list[str], indent: int = 0) -> None:
        """
        Recursively traverse legal act structure and add sections with search results to XML.
        
        Args:
            element: LegalStructuralElement to process
            parent_to_items: Dictionary mapping parent_id to list of SearchResultItems
            xml_lines: List to append XML lines to
            indent: Current indentation level
        """
        element_id = str(element.id)
        
        indent_str = '  ' * indent
        element_tag = self._get_xml_tag(element)

        # Start element tag
        xml_lines.append(f'{indent_str}<{element_tag}>')

        # Check if this is a section and has search results
        if hasattr(element, 'elementType') and element.elementType == 'LegalSection' and element_id in parent_to_items:
            
            # Add section properties
            xml_lines.append(f'{indent_str}  <id>{self._escape_xml(self._get_short_id(element_id))}</id>')
            xml_lines.append(f'{indent_str}  <officialIdentifier>{self._escape_xml(element.officialIdentifier)}</officialIdentifier>')
            xml_lines.append(f'{indent_str}  <title>{self._escape_xml(element.title)}</title>')
            
            if element.summary:
                xml_lines.append(f'{indent_str}  <summary>{self._escape_xml(element.summary)}</summary>')
            
            # Add search result items for this section
            search_items = parent_to_items[element_id]
            if search_items:
                xml_lines.append(f'{indent_str}  <searchResultItems>')
                for item in search_items:
                    xml_lines.append(f'{indent_str}    <item>')
                    xml_lines.append(f'{indent_str}      <elementId>{self._escape_xml(self._get_short_id(item.element_id))}</elementId>')
                    xml_lines.append(f'{indent_str}      <score>{item.score:.4f}</score>')
                    xml_lines.append(f'{indent_str}      <rank>{item.rank}</rank>')
                    if item.text_content:
                        xml_lines.append(f'{indent_str}      <textContent>{self._escape_xml(item.text_content)}</textContent>')
                    xml_lines.append(f'{indent_str}    </item>')
                xml_lines.append(f'{indent_str}  </searchResultItems>')
        
        elif hasattr(element, 'elementType') and element.elementType != 'LegalSection':
            # Add element id
            xml_lines.append(f'{indent_str}  <id>{self._escape_xml(self._get_short_id(element_id))}</id>')
            xml_lines.append(f'{indent_str}  <officialIdentifier>{self._escape_xml(element.officialIdentifier)}</officialIdentifier>')
            xml_lines.append(f'{indent_str}  <title>{self._escape_xml(element.title)}</title>')
        
        # Process child elements recursively
        if element.elements:
            for child in element.elements:
                self._add_search_element_to_xml(child, parent_to_items, xml_lines, indent)

        # End element tag
        xml_lines.append(f'{indent_str}</{element_tag}>')
    
    def _add_element_to_xml(self, element, xml_lines: list[str], indent: int = 0) -> None:
        """
        Recursively add element and its children to XML, excluding sections.
        
        Args:
            element: LegalStructuralElement to process
            xml_lines: List to append XML lines to
            indent: Current indentation level
        """
        # Skip sections entirely
        if hasattr(element, 'elementType') and element.elementType == 'LegalSection':
            return
            
        indent_str = '  ' * indent
        element_tag = self._get_xml_tag(element)
        
        # Start element tag
        xml_lines.append(f'{indent_str}<{element_tag}>')
        
        # Add basic properties
        xml_lines.append(f'{indent_str}  <id>{self._escape_xml(self._get_short_id(str(element.id)))}</id>')
        xml_lines.append(f'{indent_str}  <officialIdentifier>{self._escape_xml(element.officialIdentifier)}</officialIdentifier>')
        xml_lines.append(f'{indent_str}  <title>{self._escape_xml(element.title)}</title>')
        
        if element.summary:
            xml_lines.append(f'{indent_str}  <summary>{self._escape_xml(element.summary)}</summary>')
        
        # Process child elements (excluding sections)
        if element.elements:
            non_section_children = [
                child for child in element.elements 
                if not (hasattr(child, 'elementType') and child.elementType == 'LegalSection')
            ]
            
            if non_section_children:
                xml_lines.append(f'{indent_str}  <childElements>')
                for child in non_section_children:
                    self._add_element_to_xml(child, xml_lines, indent + 2)
                xml_lines.append(f'{indent_str}  </childElements>')
        
        # End element tag
        xml_lines.append(f'{indent_str}</{element_tag}>')
    
    def _get_xml_tag(self, element) -> str:
        """
        Get appropriate XML tag name based on element type.
        
        Args:
            element: LegalStructuralElement
            
        Returns:
            str: XML tag name
        """
        if hasattr(element, 'elementType'):
            type_mapping = {
                'LegalAct': 'legalAct',
                'LegalPart': 'part',
                'LegalChapter': 'chapter',
                'LegalDivision': 'division',
                'LegalSection': 'section'
            }
            return type_mapping.get(element.elementType, 'element')
        return 'element'
    
    def _escape_xml(self, text: str) -> str:
        """
        Escape special XML characters in text content.
        
        Args:
            text: Text to escape
            
        Returns:
            str: XML-escaped text
        """
        if not text:
            return ''
        
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#39;'))
    
    def _write_working_ontology_to_file(self) -> bool:
        """
        Writes the working ontology expressed in Turtle into the working ontology file.
        It rewrites the file with the new Turtle representation of the ontology.
        """
        try:
            ontology_ttl = self.ontology_service.export_whole_ontology_to_turtle()
            self.working_ontology_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.working_ontology_file, "w", encoding="utf-8") as f:
                f.write(ontology_ttl)
            return True
        except Exception as e:
            print(f"Error writing ontology to file: {e}")
            return False


ORIGINAL_AGENT_INSTRUCTIONS = """<ROLE>You are a Conceptual Designer Agent, a helpful ontology engineer.</ROLE>
<TASK>
- Your task is to build a precise and comprehensive domain ontology based on provided domain knowledge.
- You cooperate with a user who is a domain expert but has no prior experience in building ontologies.
</TASK>
<INPUT>
- Your primary and the only resource of domain knowledge is the legal act that describes the domain and the previous conversation with the user.
</INPUT>
<BEHAVIOR>
- Build the domain ontology solely based on the domain knowledge.
- Never invent your own ontology elements that are not supported by the domain knowledge.
- Keep the ontology simple, comprising only these kinds of elements: classes, attributes, binary relationships.
- When determining required ontology element details, keep going until you analyze all domain knowledge relevant to the element.
</BEHAVIOR>
<OUTPUT_DEFINITION>
- A class represents a domain concept that is either a subject or object.
    - A subject is an entity that has legal personality or is treated by law as a bearer of rights and duties and can perform legal acts toward others (natural persons, legal persons, functional roles).
    - An object is anything that is the focus or benefit of a legal relationship but lacks its own will; subjects direct their rights or duties toward it (tangible and intangible assets, rights and obligations, registrations, decisions, establishments, cancellations, official acts).
- An attribute of a class represents an intrinsic property of the class.
    - It captures a single, atomic, further indivisible piece of information, potentially analogous to one form field.
    - It never bundles or aggregates multiple elementary data points that can be split to more attributes.
    - It does not express a semantic connection with another class but is inherent exclusively to the class.
- A binary relationship represents a connection between two classes that expresses a semantic relation.
    - It is directed from the source class to the target class.
    - One of the classes should be already known and specified in the ontology. The other class can be a new class that you will need to specify as well.
</OUTPUT_DEFINITION>
<OUTPUT_STRUCTURE>
- Each ontology element must have:
    - prefLabel (in Czech, unique in the ontology, element name)
      - for classes: noun or noun phrase
      - for attributes: noun or noun phrase including the prefLabel of the class it belongs to
      - for relationships: verb or verb phrase including the prefLabel of one or both connected classes
    - definition (one sentence, no circularity, quoting legal act as much as possible with minimal necessary edits)
    - comment (one or more sentences up to short paragraph, semantically corresponds to the definition but explains it verbosely capturing the full semantics)
    - references (the hierarchical numbers of the structural elements of the legal act, e.g. "§ 3 (2) a)")
- Each class in addition to the previous:
    - the parent class it inherits from (optional)
- Each attribute must have in addition to the previous:
    - the domain class it belongs to
- Each relationship must have in addition to the previous:
    - the domain class it belongs to
    - the range class it connects to
- All texts (prefLables, definitions, comments) must be strictly grounded in the domain knowledge.
</OUTPUT_STRUCTURE>
<TOOLS>
- Use `get_hierarchical_summary_of_legal_act` tool to retrieve an overview of the domain knowledge writtedn in the legal act.
- Use `search_legal_act` tool to find semantically relevant passages within the legal act for the given query.
- Use `get_working_ontology` tool to retrieve the current working ontology.
- Use `add_new_class`, `add_new_attribute`, `add_new_relationship` tool to manipulate with the current working ontology. These tools create new elements in the ontology with their IRIs. You do not determine the IRIs yourself.
</TOOLS>
<ROUTINE>
1. Identify key classes based on the legal act summary and show them to the user, each with a short explanation of its semantics and importance.
2. Discuss with the user about the list of key classes and refine their list if necessary. This gives you the initial list of classes.
3. Focus on each class in the list individually. Let the user decide what class you will work on next.
4. For each class on the list:
    4.1. Gather detailed and complete knowledge related to the class from the legal act.
    4.2. Always discuss with the user about the gathered knowledge relevant for the class and refine it based on the user feedback.
    4.3. Organize the gathered and refined knowledge about the class to the full list of class properties.
        4.3.1. Think hard about each property whether it is an intrinsic characteristic of the class itself that should be modeled as an attribute or it is a relationship to another class.
        4.3.2. Think hard about each attribute whether it is an intrinsic characteristic of the class itself or it is an intrinsic characteristic of some other class that should be identified and connected through a relationship.
        4.3.3. Think hard about each attribute whether it should not be further decomposed to more atomic attributes. If so, always decompose it before revealing to the user.
        4.3.4. If a relationship with a new class is identified, put this class onto the list of key classes in the subject area and get back to it later.
    4.4. Always check the list of attributes and relationships with the user and refine it based on the user feedback by looping through 4.3.*.
5. Validate the identified classes, attributes and relationships against the legal act again and do corrections if needed.
6. Whenever during the process the user confirms an ontology class, attribute or relationship, you add it into the ontology and you inform the user shortly with the preferred label of each added element  .
7. Whenever during the process the user decides to update or remove an existing ontology element, you deny it because you do not support this yet.
8. Ensure that each class discovered during the process is discussed with the user. It may happen that the user skips a class you proposed, wants to return to it later but forgets.
9. Iterate the ontology until it is complete (i.e. it covers 100 percent of the legal act and the knowledge gathered from the user).
</ROUTINE>
<OUTPUT>
Your output is a comprehensive domain ontology that you build iteratively based on the legal act and the previous conversation with the user.
The domain ontology comprises all discovered classes, their attributes and binary relationships.
</OUTPUT>"""