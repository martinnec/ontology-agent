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

    AGENT_INSTRUCTIONS = """<ROLE>You are a Conceptual Designer Agent, a helpful ontology expert and guide through the ontology building process.</ROLE>
<TASK>Your task is to build a precise domain ontology based on the domain knowledge. You cooperate with a user who is a domain expert but has no prior experience in building ontologies. You guide the user through the domain, domain concepts and the process.</TASK>
<INPUT>
- Your primary and the only resource of domain knowledge is the legal act that describes the domain in detail and the previous conversation with the user.
</INPUT>
<BEHAVIOR>
- Be proactive in asking for clarification and additional details from the user.
- The user speaks Czech, you answer in Czech.
- Build the domain ontology solely based on the domain knowledge. Never invent your own ontology elements that are not supported by the legal act or the user's input.
- Keep the ontology simple, comprising only these kinds of elements: classes, attributes, binary relationships.
    - A class represents a real-world concept in the domain that can have instances.
    - An attribute of a class represents a real-world property of the concept modeled by the class. It must be as atomic property as possible. If a candidate can be split to more specific properties, you must split it to more specific properties.
    - A binary relationship represents a real-world semantic connection between two concepts in the domain.
- When determining element details, keep going until all domain knowledge relevant to the element is analyzed and considered.
- Use the tools specified below.
</BEHAVIOR>
<OUTPUT_STRUCTURE>
- Each ontology element must have:
    - prefLabel (in Czech, unique in the ontology, element name)
      - class: noun or noun phrase
      - attribute: noun or noun phrase including the prefLabel of the class it belongs to
      - relationship: verb or verb phrase including the prefLabel of one or both connected classes
    - definition (one sentence, no circularity, quoting legal act)
    - definition_citation (in Czech, the source of the definition in the form of a reference into the legal act)
    - comment (one or more sentences up to short paragraph, semantically corresponds to the definition but explains it verbosely capturing the full semantics)
    - comment_citations (in Czech, the sources of the comment in the form of one or more references into the legal act)
- Each attribute must have in addition to the previous:
    - the class it belongs to
- Each relationship must have in addition to the previous:
    - domain class it belongs to
    - range class it connects to
- Do not create IRIs of new ontology elements - they are constructed by the tools for adding elements into the ontology.
</OUTPUT_STRUCTURE>
<TOOLS>
- Use `get_hierarchical_summary_of_legal_act` tool to retrieve an overview of the domain knowledge in the form of summarized content of the legal act hierarchically structured based on the original structure of the legal act. This gives you complete context and understanding of the domain without the need to read the full legal act that can be very long.
- Use `search_legal_act` tool to find semantically relevant passages within the legal act for the given query to get detailed domain knowledge from the legal act. The query can be any text. Try to be as specific as possible, i.e. when needing details from the legal act about a relationships of a class, create the query using the names of the class, relationship and keywords from their known definitions or descriptions. If the query does not return anything relevant, relax the query and try again.
- Use `get_working_ontology` tool to retrieve the current working ontology you constructed in the previous steps.
- Use `add_new_class`, `update_existing_class`, `remove_existing_class`, `add_new_attribute`, `update_existing_attribute`, `remove_existing_attribute`, `add_new_relationship`, `update_existing_relationship`, `remove_existing_relationship` tool to manipulate with the current working ontology.
</TOOLS>
<ROUTINE>
1. Split the domain to smaller subject areas (not legal act parts, but real-world areas based on the domain specification in the legal act).
2. Explain the purpose and scope of each subject area to the user.
3. Work separately in each subject area. Let the user decide what subject area you will work at next.
4. For each subject area build the ontology iterativelly:
    4.1. Identify key classes in the chosen subject area and show them to the user, each with a short explanation of its semantics and its relationship to the subject area.
    4.2. Discuss with the user about the list of key classes and refine their list if necessary. This gives you the initial list of classes in the subject area.
    4.3. Focus on each class in the list individually. Let the user decide what class you will work on next.
    4.4. For each class on the list:
        4.4.1. Gather detailed knowledge related to the class from the legal act.
        4.4.2. Discuss with the user about the gathered knowledge and refine it if necessary.
        4.4.3. Organize the gathered and refined knowledge about the class to the full list of class attributes and relationships.
        4.4.4. If a relationship with a new class is identified, put this class onto the list of key classes in the subject area and get back to it later.
    4.5. Validate the identified classes, attributes and relationships against the legal act and with the user to ensure accuracy and completeness.
    4.6. Whenever during the process the user confirms an ontology element, you add it or update it in the ontology.
    4.7. Whenever during the process the user decides that an existing ontology element does not belong to the ontology, you remove it.
    4.7. Ensure that each discovered class is discussed with the user.
4. Repeat the process until the ontology is complete. Completness = 100 percent coverage of the legal act and the knowledge gathered from the user.
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

        # Create the tool function that captures self context
        @function_tool
        def get_hierarchical_summary_of_legal_act() -> str:
            """
            Get the legal act summary, comprising hierarchically organized summaries of the legal act, its parts, chapters, and divisions.
            Excludes sections.
            
            Returns:
                str: XML representation of the hierarchical structure
            """
            return self._get_hierarchical_summary_impl()
        
        @function_tool
        def search_legal_act(query: str, k: int) -> list[str]:
            """
            Search the legal act for relevant passages based on the query.

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

            Returns:
                str: The current working ontology.
            """
            return self._get_working_ontology_impl()
        
        @function_tool
        def add_new_class(prefLabel: str, definition: str, definition_citation: str, comment: str, comment_citations: list[str], parent_name: str) -> bool:
            """
            Add a new class to the ontology.

            Args:
                prefLabel (str): The preferred label of the class.
                definition (str): The definition of the class.
                definition_citation (str): The citation for the definition.
                comment (str): Additional comment about the class.
                comment_citations (list[str]): Citations for the comment.
                parent_name (str): The name of the parent class.

            Returns:
                bool: True if successfully added, False otherwise.
            """
            return self._add_new_class_impl(prefLabel, definition, definition_citation, comment, comment_citations, parent_name)

        @function_tool
        def update_existing_class(local_name: str, prefLabel: str = None, definition: str = None, definition_citation: str = None, comment: str = None, comment_citations: list[str] = None, parent_name: str = None) -> bool:
            """
            Update an existing class in the ontology.

            Args:
                local_name (str): The local name part of the IRI of the class to update (e.g., "Vehicle" for "https://example.org/ontology/Vehicle").
                prefLabel (str, optional): The new preferred label of the class.
                definition (str, optional): The new definition of the class.
                definition_citation (str, optional): The new citation for the definition.
                comment (str, optional): The new comment about the class.
                comment_citations (list[str], optional): The new citations for the comment.
                parent_name (str, optional): The new name of the parent class.

            Returns:
                bool: True if successfully updated, False otherwise.
            """
            return self._update_existing_class_impl(local_name, prefLabel, definition, definition_citation, comment, comment_citations, parent_name)

        @function_tool
        def remove_existing_class(local_name: str) -> bool:
            """
            Remove an existing class from the ontology.

            Args:
                local_name (str): The local name part of the IRI of the class to remove (e.g., "Vehicle" for "https://example.org/ontology/Vehicle").

            Returns:
                bool: True if successfully removed, False otherwise.
            """
            return self._remove_existing_class_impl(local_name)

        @function_tool
        def add_new_attribute(prefLabel: str, definition: str, definition_citation: str, comment: str, comment_citations: list[str], class_name: str, range_type: str) -> bool:
            """
            Add a new attribute (datatype property) to the ontology.

            Args:
                prefLabel (str): The preferred label of the attribute.
                definition (str): The definition of the attribute.
                definition_citation (str): The citation for the definition.
                comment (str): Additional comment about the attribute.
                comment_citations (list[str]): Citations for the comment.
                class_name (str): The name of the class this attribute belongs to.
                range_type (str): The datatype range of the attribute (e.g., "string", "int", "date").

            Returns:
                bool: True if successfully added, False otherwise.
            """
            return self._add_new_attribute_impl(prefLabel, definition, definition_citation, comment, comment_citations, class_name, range_type)

        @function_tool
        def update_existing_attribute(local_name: str, prefLabel: str = None, definition: str = None, definition_citation: str = None, comment: str = None, comment_citations: list[str] = None, class_name: str = None, range_type: str = None) -> bool:
            """
            Update an existing attribute (datatype property) in the ontology.

            Args:
                local_name (str): The local name part of the IRI of the attribute to update (e.g., "vehicleColor" for "https://example.org/ontology/vehicleColor").
                prefLabel (str, optional): The new preferred label of the attribute.
                definition (str, optional): The new definition of the attribute.
                definition_citation (str, optional): The new citation for the definition.
                comment (str, optional): The new comment about the attribute.
                comment_citations (list[str], optional): The new citations for the comment.
                class_name (str, optional): The new name of the class this attribute belongs to.
                range_type (str, optional): The new datatype range of the attribute.

            Returns:
                bool: True if successfully updated, False otherwise.
            """
            return self._update_existing_attribute_impl(local_name, prefLabel, definition, definition_citation, comment, comment_citations, class_name, range_type)

        @function_tool
        def remove_existing_attribute(local_name: str) -> bool:
            """
            Remove an existing attribute (datatype property) from the ontology.

            Args:
                local_name (str): The local name part of the IRI of the attribute to remove (e.g., "vehicleColor" for "https://example.org/ontology/vehicleColor").

            Returns:
                bool: True if successfully removed, False otherwise.
            """
            return self._remove_existing_attribute_impl(local_name)

        @function_tool
        def add_new_relationship(prefLabel: str, definition: str, definition_citation: str, comment: str, comment_citations: list[str], domain_class: str, range_class: str) -> bool:
            """
            Add a new relationship (object property) to the ontology.

            Args:
                prefLabel (str): The preferred label of the relationship.
                definition (str): The definition of the relationship.
                definition_citation (str): The citation for the definition.
                comment (str): Additional comment about the relationship.
                comment_citations (list[str]): Citations for the comment.
                domain_class (str): The name of the domain class.
                range_class (str): The name of the range class.

            Returns:
                bool: True if successfully added, False otherwise.
            """
            return self._add_new_relationship_impl(prefLabel, definition, definition_citation, comment, comment_citations, domain_class, range_class)

        @function_tool
        def update_existing_relationship(local_name: str, prefLabel: str = None, definition: str = None, definition_citation: str = None, comment: str = None, comment_citations: list[str] = None, domain_class: str = None, range_class: str = None) -> bool:
            """
            Update an existing relationship (object property) in the ontology.

            Args:
                local_name (str): The local name part of the IRI of the relationship to update (e.g., "ownedBy" for "https://example.org/ontology/ownedBy").
                prefLabel (str, optional): The new preferred label of the relationship.
                definition (str, optional): The new definition of the relationship.
                definition_citation (str, optional): The new citation for the definition.
                comment (str, optional): The new comment about the relationship.
                comment_citations (list[str], optional): The new citations for the comment.
                domain_class (str, optional): The new name of the domain class.
                range_class (str, optional): The new name of the range class.

            Returns:
                bool: True if successfully updated, False otherwise.
            """
            return self._update_existing_relationship_impl(local_name, prefLabel, definition, definition_citation, comment, comment_citations, domain_class, range_class)

        @function_tool
        def remove_existing_relationship(local_name: str) -> bool:
            """
            Remove an existing relationship (object property) from the ontology.

            Args:
                local_name (str): The local name part of the IRI of the relationship to remove (e.g., "ownedBy" for "https://example.org/ontology/ownedBy").

            Returns:
                bool: True if successfully removed, False otherwise.
            """
            return self._remove_existing_relationship_impl(local_name)

        self.agent = Agent(
            name="OntologyModelingAgent",
            instructions=self.AGENT_INSTRUCTIONS,
            model="gpt-5-mini",
            model_settings=ModelSettings(
                reasoning={
                    "effort": "low"
                },
                verbosity="low"
            ),
            tools=[get_hierarchical_summary_of_legal_act, search_legal_act, get_working_ontology, add_new_class, update_existing_class, remove_existing_class, add_new_attribute, update_existing_attribute, remove_existing_attribute, add_new_relationship, update_existing_relationship, remove_existing_relationship]
        )

    async def build_ontology(self) -> None:
        """
        Build the ontology from the legal act.
        """
        input_items: list[TResponseInputItem] = []

        current_agent = self.agent

        input_items.append({"content": "Budeme pracovat se zákonem o podmínkách provozu vozidel na pozemních komunikacích.", "role": "user"})    

        while True:

            result = await Runner.run(current_agent, input_items)
            
            for new_item in result.new_items:
                agent_name = new_item.agent.name
                if isinstance(new_item, MessageOutputItem):
                    print(f"[{agent_name}]: {ItemHelpers.text_message_output(new_item)}")
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

            user_input = input("Co dál? ('exit' pro ukončení): ")
            if user_input.lower() == 'exit':
                break
            input_items.append({"content": user_input, "role": "user"})

    
    # TOOL IMPLEMENTATIONS

    def _get_working_ontology_impl(self) -> str:
        """
        Implementation method for getting the current working ontology.

        Returns:
            str: The current working ontology in OWL/TTL format.
        """
        ontology_data = self.ontology_service.get_working_ontology()
        return self._convert_to_ttl(ontology_data)
    
    def _add_new_class_impl(self, prefLabel: str, definition: str, definition_citation: str, comment: str, comment_citations: list[str], parent_name: str) -> bool:
            """
            Implementation method for adding a new class to the ontology.

            Args:
                prefLabel (str): The preferred label of the class.
                definition (str): The definition of the class.
                definition_citation (str): The citation for the definition.
                comment (str): Additional comment about the class.
                comment_citations (list[str]): Citations for the comment.
                parent_name (str): The name of the parent class.

            Returns:
                bool: True if successfully added, False otherwise.
            """
            iri = None  # Unspecified IRI, so "not iri" will be False
            return self.ontology_service.add_class(
                iri,
                name_cs=prefLabel,
                name_en="",
                definition_cs=definition,
                definition_en="",
                comment_cs=comment,
                comment_en="",
                parent_class_iri=parent_name,
                source_element=definition_citation
            )

    def _update_existing_class_impl(self, local_name: str, prefLabel: str = None, definition: str = None, definition_citation: str = None, comment: str = None, comment_citations: list[str] = None, parent_name: str = None) -> bool:
        """
        Implementation method for updating an existing class in the ontology.

        Args:
            local_name (str): The local name of the class to update.
            prefLabel (str, optional): The new preferred label of the class.
            definition (str, optional): The new definition of the class.
            definition_citation (str, optional): The new citation for the definition.
            comment (str, optional): The new comment about the class.
            comment_citations (list[str], optional): The new citations for the comment.
            parent_name (str, optional): The new name of the parent class.

        Returns:
            bool: True if successfully updated, False otherwise.
        """
        # Convert local name to full IRI
        iri = self._local_name_to_iri(local_name)
        
        return self.ontology_service.update_class(
            iri=iri,
            name_cs=prefLabel,
            name_en=None,
            definition_cs=definition,
            definition_en=None,
            comment_cs=comment,
            comment_en=None,
            parent_class_iri=parent_name,
            source_element=definition_citation
        )

    def _remove_existing_class_impl(self, local_name: str) -> bool:
        """
        Implementation method for removing an existing class from the ontology.

        Args:
            local_name (str): The local name of the class to remove.

        Returns:
            bool: True if successfully removed, False otherwise.
        """
        # Convert local name to full IRI
        iri = self._local_name_to_iri(local_name)
        
        return self.ontology_service.remove_class(iri)

    def _add_new_attribute_impl(self, prefLabel: str, definition: str, definition_citation: str, comment: str, comment_citations: list[str], class_name: str, range_type: str) -> bool:
        """
        Implementation method for adding a new attribute (datatype property) to the ontology.

        Args:
            prefLabel (str): The preferred label of the attribute.
            definition (str): The definition of the attribute.
            definition_citation (str): The citation for the definition.
            comment (str): Additional comment about the attribute.
            comment_citations (list[str]): Citations for the comment.
            class_name (str): The name of the class this attribute belongs to.
            range_type (str): The datatype range of the attribute.

        Returns:
            bool: True if successfully added, False otherwise.
        """
        iri = None  # Unspecified IRI, will be generated
        return self.ontology_service.add_property(
            iri=iri,
            property_type="DatatypeProperty",
            name_cs=prefLabel,
            name_en="",
            definition_cs=definition,
            definition_en="",
            comment_cs=comment,
            comment_en="",
            domain_iri=class_name,
            range_iri=range_type,
            source_element=definition_citation
        )

    def _update_existing_attribute_impl(self, local_name: str, prefLabel: str = None, definition: str = None, definition_citation: str = None, comment: str = None, comment_citations: list[str] = None, class_name: str = None, range_type: str = None) -> bool:
        """
        Implementation method for updating an existing attribute (datatype property) in the ontology.

        Args:
            local_name (str): The local name of the attribute to update.
            prefLabel (str, optional): The new preferred label of the attribute.
            definition (str, optional): The new definition of the attribute.
            definition_citation (str, optional): The new citation for the definition.
            comment (str, optional): The new comment about the attribute.
            comment_citations (list[str], optional): The new citations for the comment.
            class_name (str, optional): The new name of the class this attribute belongs to.
            range_type (str, optional): The new datatype range of the attribute.

        Returns:
            bool: True if successfully updated, False otherwise.
        """
        # Convert local name to full IRI
        iri = self._local_name_to_iri(local_name)
        
        return self.ontology_service.update_property(
            iri=iri,
            property_type="DatatypeProperty",
            name_cs=prefLabel,
            name_en=None,
            definition_cs=definition,
            definition_en=None,
            comment_cs=comment,
            comment_en=None,
            domain_iri=class_name,
            range_iri=range_type,
            source_element=definition_citation
        )

    def _remove_existing_attribute_impl(self, local_name: str) -> bool:
        """
        Implementation method for removing an existing attribute (datatype property) from the ontology.

        Args:
            local_name (str): The local name of the attribute to remove.

        Returns:
            bool: True if successfully removed, False otherwise.
        """
        # Convert local name to full IRI
        iri = self._local_name_to_iri(local_name)
        
        return self.ontology_service.remove_property(iri)

    def _add_new_relationship_impl(self, prefLabel: str, definition: str, definition_citation: str, comment: str, comment_citations: list[str], domain_class: str, range_class: str) -> bool:
        """
        Implementation method for adding a new relationship (object property) to the ontology.

        Args:
            prefLabel (str): The preferred label of the relationship.
            definition (str): The definition of the relationship.
            definition_citation (str): The citation for the definition.
            comment (str): Additional comment about the relationship.
            comment_citations (list[str]): Citations for the comment.
            domain_class (str): The name of the domain class.
            range_class (str): The name of the range class.

        Returns:
            bool: True if successfully added, False otherwise.
        """
        iri = None  # Unspecified IRI, will be generated
        return self.ontology_service.add_property(
            iri=iri,
            property_type="ObjectProperty",
            name_cs=prefLabel,
            name_en="",
            definition_cs=definition,
            definition_en="",
            comment_cs=comment,
            comment_en="",
            domain_iri=domain_class,
            range_iri=range_class,
            source_element=definition_citation
        )

    def _update_existing_relationship_impl(self, local_name: str, prefLabel: str = None, definition: str = None, definition_citation: str = None, comment: str = None, comment_citations: list[str] = None, domain_class: str = None, range_class: str = None) -> bool:
        """
        Implementation method for updating an existing relationship (object property) in the ontology.

        Args:
            local_name (str): The local name of the relationship to update.
            prefLabel (str, optional): The new preferred label of the relationship.
            definition (str, optional): The new definition of the relationship.
            definition_citation (str, optional): The new citation for the definition.
            comment (str, optional): The new comment about the relationship.
            comment_citations (list[str], optional): The new citations for the comment.
            domain_class (str, optional): The new name of the domain class.
            range_class (str, optional): The new name of the range class.

        Returns:
            bool: True if successfully updated, False otherwise.
        """
        # Convert local name to full IRI
        iri = self._local_name_to_iri(local_name)
        
        return self.ontology_service.update_property(
            iri=iri,
            property_type="ObjectProperty",
            name_cs=prefLabel,
            name_en=None,
            definition_cs=definition,
            definition_en=None,
            comment_cs=comment,
            comment_en=None,
            domain_iri=domain_class,
            range_iri=range_class,
            source_element=definition_citation
        )

    def _remove_existing_relationship_impl(self, local_name: str) -> bool:
        """
        Implementation method for removing an existing relationship (object property) from the ontology.

        Args:
            local_name (str): The local name of the relationship to remove.

        Returns:
            bool: True if successfully removed, False otherwise.
        """
        # Convert local name to full IRI
        iri = self._local_name_to_iri(local_name)
        
        return self.ontology_service.remove_property(iri)

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

    def _convert_to_ttl(self, ontology_data: dict) -> str:
        """
        Convert ontology data to TTL (Turtle) format.
        
        Args:
            ontology_data: Dictionary containing classes, properties and stats from ontology service
            
        Returns:
            str: TTL representation of the ontology
        """
        ttl_lines = []
        
        # Add prefixes
        ttl_lines.extend([
            "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
            "@prefix ex: <https://example.org/ontology/> .",
            "",
            "# Ontology declaration",
            "ex: a owl:Ontology .",
            ""
        ])
        
        # Add classes
        if ontology_data.get("classes"):
            ttl_lines.append("# Classes")
            for class_data in ontology_data["classes"]:
                ttl_lines.extend(self._class_to_ttl(class_data))
            ttl_lines.append("")
        
        # Add object properties
        if ontology_data.get("object_properties"):
            ttl_lines.append("# Object Properties")
            for prop_data in ontology_data["object_properties"]:
                ttl_lines.extend(self._property_to_ttl(prop_data))
            ttl_lines.append("")
        
        # Add datatype properties
        if ontology_data.get("datatype_properties"):
            ttl_lines.append("# Datatype Properties")
            for prop_data in ontology_data["datatype_properties"]:
                ttl_lines.extend(self._property_to_ttl(prop_data))
            ttl_lines.append("")
        
        # Add statistics as comment
        stats = ontology_data.get("stats", {})
        if stats:
            ttl_lines.extend([
                "# Ontology Statistics:",
                f"# - Total classes: {stats.get('total_classes', 0)}",
                f"# - Total object properties: {stats.get('total_object_properties', 0)}",
                f"# - Total datatype properties: {stats.get('total_datatype_properties', 0)}",
                f"# - Total triples: {stats.get('total_triples', 0)}",
                f"# - Classes with definitions: {stats.get('classes_with_definitions', 0)}",
                f"# - Properties with domain/range: {stats.get('properties_with_domain_range', 0)}"
            ])
        
        return "\n".join(ttl_lines)
    
    def _class_to_ttl(self, class_data: dict) -> list[str]:
        """
        Convert class data to TTL format.
        
        Args:
            class_data: Dictionary with class information
            
        Returns:
            list[str]: TTL lines for the class
        """
        lines = []
        iri = class_data["iri"]
        
        # Use short IRI if it's in our namespace, otherwise use full IRI
        class_iri = self._get_short_iri(iri)
        
        lines.append(f"{class_iri}")
        lines.append("    a owl:Class ;")
        
        # Add labels
        labels = class_data.get("labels", {})
        for lang, label in labels.items():
            lines.append(f'    skos:prefLabel "{self._escape_ttl_string(label)}"@{lang} ;')
        
        # Add definitions
        definitions = class_data.get("definitions", {})
        for lang, definition in definitions.items():
            lines.append(f'    skos:definition "{self._escape_ttl_string(definition)}"@{lang} ;')
        
        # Add comments
        comments = class_data.get("comments", {})
        for lang, comment in comments.items():
            lines.append(f'    rdfs:comment "{self._escape_ttl_string(comment)}"@{lang} ;')
        
        # Add parent classes
        parent_classes = class_data.get("parent_classes", [])
        for parent_iri in parent_classes:
            parent_short = self._get_short_iri(parent_iri)
            lines.append(f"    rdfs:subClassOf {parent_short} ;")
        
        # Remove trailing semicolon and add period
        if lines and lines[-1].endswith(" ;"):
            lines[-1] = lines[-1][:-2] + " ."
        
        lines.append("")
        return lines
    
    def _property_to_ttl(self, property_data: dict) -> list[str]:
        """
        Convert property data to TTL format.
        
        Args:
            property_data: Dictionary with property information
            
        Returns:
            list[str]: TTL lines for the property
        """
        lines = []
        iri = property_data["iri"]
        property_type = property_data.get("property_type", "ObjectProperty")
        
        # Use short IRI if it's in our namespace, otherwise use full IRI
        prop_iri = self._get_short_iri(iri)
        
        lines.append(f"{prop_iri}")
        
        if property_type == "ObjectProperty":
            lines.append("    a owl:ObjectProperty ;")
        else:  # DatatypeProperty
            lines.append("    a owl:DatatypeProperty ;")
        
        # Add labels
        labels = property_data.get("labels", {})
        for lang, label in labels.items():
            lines.append(f'    skos:prefLabel "{self._escape_ttl_string(label)}"@{lang} ;')
        
        # Add definitions
        definitions = property_data.get("definitions", {})
        for lang, definition in definitions.items():
            lines.append(f'    skos:definition "{self._escape_ttl_string(definition)}"@{lang} ;')
        
        # Add comments
        comments = property_data.get("comments", {})
        for lang, comment in comments.items():
            lines.append(f'    rdfs:comment "{self._escape_ttl_string(comment)}"@{lang} ;')
        
        # Add domain
        domain = property_data.get("domain")
        if domain:
            domain_short = self._get_short_iri(domain)
            lines.append(f"    rdfs:domain {domain_short} ;")
        
        # Add range
        range_iri = property_data.get("range")
        if range_iri:
            range_short = self._get_short_iri(range_iri)
            lines.append(f"    rdfs:range {range_short} ;")
        
        # Remove trailing semicolon and add period
        if lines and lines[-1].endswith(" ;"):
            lines[-1] = lines[-1][:-2] + " ."
        
        lines.append("")
        return lines
    
    def _get_short_iri(self, iri: str) -> str:
        """
        Convert full IRI to short form using defined prefixes.
        
        Args:
            iri: Full IRI string
            
        Returns:
            str: Short IRI or full IRI in angle brackets
        """
        if iri.startswith("https://example.org/ontology/"):
            return f"ex:{iri[29:]}"  # Remove prefix
        elif iri.startswith("http://www.w3.org/2002/07/owl#"):
            return f"owl:{iri[31:]}"
        elif iri.startswith("http://www.w3.org/2000/01/rdf-schema#"):
            return f"rdfs:{iri[38:]}"
        elif iri.startswith("http://www.w3.org/2004/02/skos/core#"):
            return f"skos:{iri[37:]}"
        elif iri.startswith("http://www.w3.org/2001/XMLSchema#"):
            return f"xsd:{iri[33:]}"  # Fixed: was 34, should be 33
        else:
            return f"<{iri}>"
    
    def _escape_ttl_string(self, text: str) -> str:
        """
        Escape special characters in TTL string literals.
        
        Args:
            text: Text to escape
            
        Returns:
            str: TTL-escaped text
        """
        if not text:
            return ''
        
        return (text.replace('\\', '\\\\')
                   .replace('"', '\\"')
                   .replace('\n', '\\n')
                   .replace('\r', '\\r')
                   .replace('\t', '\\t'))

    def _local_name_to_iri(self, local_name: str) -> str:
        """
        Convert a local name to a full IRI using the ontology namespace.
        
        Args:
            local_name: The local name of the ontology element (e.g., "Vehicle")
            
        Returns:
            str: Full IRI (e.g., "https://example.org/ontology/Vehicle")
        """
        if not local_name:
            return local_name
        
        # Base namespace for the ontology
        base_namespace = "https://example.org/ontology/"
        
        # Return full IRI
        return f"{base_namespace}{local_name}"