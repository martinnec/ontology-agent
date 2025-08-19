from pathlib import Path
from pydantic import AnyUrl

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
from search.service import SearchService
from index.service import IndexService
from ontology.service import OntologyService
from ontology.store import OntologyStore

class OntologyModelingAgent:
    """
    Agent for building an ontology from a given legal act text.
    """

    AGENT_INSTRUCTIONS = """<ROLE>You are a Conceptual Designer Agent, a helpful ontology expert.</ROLE>
<TASK>Your task is to build a precise domain ontology based on the domain knowledge.</TASK>
<INPUT>Your primary resource of domain knowledge is the legal act that describes the domain in detail and the previous conversation with the domain expert.</INPUT>
<BEHAVIOR>
- Be proactive in asking for clarification and additional details from the user.
- The user speaks Czech, you answer in Czech.
- Build the domain ontology solely based on the domain knowledge. Never invent your own ontology elements that are not supported by the legal act or the user's input.
- Keep the ontology simple, comprising only these kinds of elements: classes, attributes, binary relationships.
</BEHAVIOR>
<TOOLS>
- Use `get_hierarchical_summary_of_legal_act` tool to retrieve the domain knowledge in the form of summarized content of the legal act hierarchically structured based on the original structure of the legal act.
</TOOLS>
<ROUTINE>
1. Split the domain to smaller subdomains.
2. Explain the purpose and scope of each subdomain to the user.
3. Ask the user what subdomain they want to focus on.
4. Identify key concepts, discuss with the user about them to refine their list. If the user leaves the subdomain, stop them.
5. Organize the gathered knowledge about the subdomain into a structured format.
6. Ask the user for clarification or additional details if needed.
7. Validate the structured information with the user.
8. Repeat until all subdomains are processed.
9. Generate the ontology elements (classes, attributes, relationships) based on the previous conversations for the whole domain.
</ROUTINE>
<OUTPUT>
The domain ontology comprises all discovered classes, their attributes and binary relationships.
Each of these elements must have:
- name (Class: CamelCase; attribute: lowerCamelCase; relationship: verbPhrase)
- definition (one sentence, no circularity, quoting legal act)
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
            tools=[get_hierarchical_summary_of_legal_act]
        )

    async def build_ontology(self) -> None:
        """
        Build the ontology from the legal act.
        """
        input_items: list[TResponseInputItem] = []

        current_agent = self.agent

        while True:
            user_input = input("Explain your domain (or type 'exit' to finish): ")
            if user_input.lower() == 'exit':
                break
            input_items.append({"content": user_input, "role": "user"})
            
            result = await Runner.run(current_agent, input_items)
            
            for new_item in result.new_items:
                agent_name = new_item.agent.name
                if isinstance(new_item, MessageOutputItem):
                    print(f"[{agent_name}]: {ItemHelpers.text_message_output(new_item)}")
                elif isinstance(new_item, ToolCallItem):
                    tool_name = getattr(new_item.raw_item, 'name', None) or getattr(new_item.raw_item, 'function', {}).get('name', 'unknown tool')
                    print(f"[{agent_name}]: Calling a tool {tool_name}")
                elif isinstance(new_item, ToolCallOutputItem):
                    print(f"[{agent_name}]: Tool output received.")
                else:
                    print(f"[{agent_name}]: Skipping item: {new_item.__class__.__name__}")

            input_items = result.to_input_list()
            current_agent = result.last_agent

    
    # TOOLS

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

        print(output)

        return output
    
    # HELPER METHODS
    
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
        xml_lines.append(f'{indent_str}  <id>{self._escape_xml(str(element.id))}</id>')
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
                'LegalDivision': 'division'
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