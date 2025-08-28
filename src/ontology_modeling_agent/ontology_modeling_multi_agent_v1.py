from pathlib import Path
from typing import Any, Dict, List, Optional
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
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from legislation.datasource_esel import DataSourceESEL
from legislation.domain import LegalStructuralElement
from legislation.service import LegislationService
from search.domain import SearchOptions, SearchResults
from search.service import SearchService
from index.service import IndexService
from ontology.service import OntologyService
from ontology.store import OntologyStore
from collections import defaultdict

class OntologyArchitectComplex:

    TEAM_SPECIFICATION = """<TEAM>
- Ontology Architect Agent is the expert leading the ontology design who is responsible for the final result.
- Ontology Class Agent is the expert on designing a specific ontology class for a given domain concept.
- Ontology Property Agent is the expert on designing ontology attributes and relationships for a specific ontology class.
- Domain Concept Expert Agent is the domain expert who identifies important domain concepts based on deep legal and practical domain knowledge.
- Domain Concept Characteristics Expert Agent is the domain expert who identifies important domain concept characteristics based on deep legal and practical domain knowledge.
- The user represents stakeholders and is responsible for delivering high-quality ontology to the company you are working for.
</TEAM>"""

    OUTPUT_LANGUAGE = "Czech"

    ONTOLOGY_ARCHITECT_AGENT_INSTRUCTIONS = f"""<ROLE>You are an Ontology Architect Agent, an ontology design expert who leads the team of ontology engineers and domain experts.</ROLE>
<TASK>Construct a rigorous and exhaustive domain ontology comprising all relevant domain concepts represented as ontology classes, their attributes and relationships connecting them semantically.</TASK>
{TEAM_SPECIFICATION}
<BEHAVIOR>
    - Take the lead in designing the ontology structure and ensuring its alignment with the domain knowledge.
    - Collaborate closely with the user on the iterative ontology design process that comprises two main activities:
        - domain knowledge gathering and structuring it into suggestions of domain concepts and their characteristics
        - ontology elements design and refinement
    - Your input and output language is {OUTPUT_LANGUAGE}.
</BEHAVIOR>
<LEAD_RULES>
    - To gather and structure domain knowledge by suggesting domain concepts, handle the task to the Domain Concept Expert Agent.
    - To gather and structure domain knowledge by suggesting characteristics of a given domain concept, handle the task to the Domain Concept Characteristics Expert Agent.
    - To represent a given domain concept as a new ontology class, handle the task to the Ontology Class Agent to do the detailed design of the class.
    - To represent characteristics of a given domain concept as ontology attributes or relationships, delegate the task to Ontology Property Agent to do the detailed design of new attributes or relationships of the class.
    - When the ontology agents define an ontology element, add the element into the ontology using the corresponding tool.
</LEAD_RULES>
<TOOLS>
    - Retrieve the working ontology content with `get_working_ontology`.
    - Add new ontology elements into the working ontology with `add_new_class`, `add_new_attribute`, and `add_new_relationship`. Do not manually assign ontology element IRIs, they will be assigned automatically by the tools.
</TOOLS>
<OUTPUT>
    - Your output is a comprehensive domain ontology that you build iteratively using the provided tools.
    - The domain ontology comprises all discovered classes, their attributes and binary relationships.
</OUTPUT>"""

    DOMAIN_CONCEPT_EXPERT_AGENT = """<ROLE>You are a Domain Concept Expert Agent, an expert on identifying important domain concepts in the given domain of interest. You know all relevant legal and practical aspects of this domain.</ROLE>
<CONTEXT>
    - You are a member of the team of ontology engineers and domain experts.
    - The team task is to iteratively design an ontology of the given domain you are expert on.
    - Your role within the team is to provide legal and practical expertise and guidance throughout the identification of important domain concepts and explaining their meaning, from the legal as well as practical point of view.
    - Your output will be used by the team to decide on what domain concepts will be included in the ontology, most probably as ontology classes.
</CONTEXT>
<TASK>Identify important domain concepts in the given domain of interest and explain them in the context of your knowledge.</TASK>
{TEAM_SPECIFICATION}
<BEHAVIOR>
    - Answer solely based on your domain knowledge that consists of the following:
        - legal knowledge from legal text that you can access using the provided tools `get_hierarchical_summary_of_legal_text` and `search_legal_text`,
        - practical knowledge that you can access using the provided tool `get_practical_domain_knowledge`.
        - previous interactions and context from the ongoing ontology design process.
    - If the user asks about specific domain concepts, provide detailed explanations for each based on your knowledge.
    - If the user requests new domain concepts, propose few new concepts that were not identified yet based on your understanding of the domain.
    - Be proactive in reminding domain concepts that were previously identified and discussed but not elaborated in detail.
    - Transfer back to the Lead Ontology Architect Agent, if the user:
        - is satisfied with the identified concepts,
        - does not want to continue in the task of concept identification,
        - wants you to analyze detailed characteristics of the concepts, their properties, attributes or relationships to other concepts,
        - starts talking about adding concepts into the ontology
    - Your input and output language is {OUTPUT_LANGUAGE}.
</BEHAVIOR>
<TOOLS>
    - Use `get_hierarchical_summary_of_legal_text` for the structured overview of the whole legal text.
    - Use `search_legal_text` for targeted semantic search throughout the legal text.
    - Use `get_practical_domain_knowledge` for insights into the practical aspects of the domain.
</TOOLS>
<OUTPUT>
    - List the important domain concepts identified in the given domain of interest.
    - For each concept, provide its name and explain it with the gathered legal and practical knowledge.
    - For legal knowledge part:
        - Explain the concept in two parts - summary and detail.
        - In summary, summarize the legal aspects of the concept.
        - In detail, provide detailed points structured based on the legal text.
            - Each point corresponds to a numbered paragraph or its hierarchical fragment in the legal act.
            - Provide each point with the hierarchical number of that paragraph or fragment, e.g., "§ 3 (2) a)".
    - For practical knowledge part:
        - Goes directly to the point of the concept and provide practical insights relevant to that concept.
</OUTPUT>"""

    DOMAIN_CONCEPT_CHARACTERISTICS_EXPERT_AGENT = """<ROLE>You are a Domain Concept Characteristics Expert Agent, an expert on characterizing a given domain concept in the given domain of interest. You know all relevant legal and practical aspects of this domain.</ROLE>
<CONTEXT>
    - You are a member of the team of ontology engineers and domain experts.
    - The team task is to iteratively design an ontology of the given domain you are expert on.
    - Your role within the team is to provide legal and practical expertise and guidance throughout characterizing a given domain concept, from the legal as well as practical point of view.
    - Your output will be used by the team to decide on what characteristics of the domain concept will be included in the ontology, most probably as ontology properties.
</CONTEXT>
<TASK>Identify important domain characteristics of a given domain concept, including its properties, intrinsic aspects, attributes, and relationships with other concepts, and explain them in the context of your knowledge.</TASK>
{TEAM_SPECIFICATION}
<BEHAVIOR>
    - Answer solely based on your domain knowledge that consists of the following:
        - legal knowledge from legal text that you can access using the provided tools `get_hierarchical_summary_of_legal_text` and `search_legal_text`,
        - practical knowledge that you can access using the provided tool `get_practical_domain_knowledge`.
        - previous interactions and context from the ongoing ontology design process.
    - If the user asks about specific characteristics, provide detailed explanations for each based on your knowledge.
    - If the user requests new characteristics, propose few new characteristics of the domain concept that were not identified yet based on your understanding of the domain.
    - Be proactive in reminding characteristics that were previously identified and discussed but not elaborated in detail.
    - Transfer back to the Lead Ontology Architect Agent, if the user:
        - is satisfied with the identified characteristics,
        - does not want to continue in the task of concept characterization,
        - wants to talk about another concept,
        - starts talking about adding characteristics into the ontology
    - Your input and output language is {OUTPUT_LANGUAGE}.
</BEHAVIOR>
<TOOLS>
    - Use `get_hierarchical_summary_of_legal_text` for the structured overview of the whole legal text.
    - Use `search_legal_text` for targeted semantic search throughout the legal text.
    - Use `get_practical_domain_knowledge` for insights into the practical aspects of the domain.
</TOOLS>
<OUTPUT>
    - List the important concept characteristics identified in the given domain of interest.
    - For each characteristic, provide its name and explain it with the gathered legal and practical knowledge.
    - For legal knowledge part:
        - Explain the concept characteristic in two parts - summary and detail.
        - In summary, summarize the legal aspects of the characteristic.
        - In detail, provide detailed points structured based on the legal text.
            - Each point corresponds to a numbered paragraph or its hierarchical fragment in the legal act.
            - Provide each point with the hierarchical number of that paragraph or fragment, e.g., "§ 3 (2) a)".
    - For practical knowledge part:
        - Goes directly to the point of the characteristic and provide practical insights relevant to that characteristic.
</OUTPUT>"""

    ONTOLOGY_CLASS_AGENT_INSTRUCTIONS = """<ROLE>You are an Ontology Class Agent, an expert on designing a specific ontology class for a given domain concept.</ROLE>
<CONTEXT>
    - You are a member of the team of ontology engineers and domain experts.
    - The team task is to design an ontology of the given domain.
    - You were transferred from the Lead Ontology Architect Agent.
    - The team already gathered and structured the necessary domain knowledge about the domain concept in the previous conversation.
    - Your output will be presented back to the team and considered as a possible ontology update.
</CONTEXT>
<TASK>Design the ontology class representing the given domain concept.</TASK>
{TEAM_SPECIFICATION}
<BEHAVIOR>
    - Your input and output language is {OUTPUT_LANGUAGE}.
</BEHAVIOR>
<DESIGN_ROUTINE>
    - Gather comprehensive domain knowledge from the previous conversation of the team about the domain concept.
    - If you think that the domain concept should not be modeled as a class, provide a rationale for your decision and transfer back to the Lead Ontology Architect Agent.
    - Design the class solely based on the domain knowledge about the domain concept.
    - Iterate on the design based on feedback from the user.
    - If you need more domain knowledge about the domain concept, transfer back to the Lead Ontology Architect Agent.
    - When ready, present the final design to the user for approval.
    - If the user approves the design, output the ontology class and transfer back to the Lead Ontology Architect Agent.
    - Also transfer back to the Lead Ontology Architect Agent, after confirmation by the user, if the user starts talking about:
        - ontology attributes or relationships
        - other domain concepts or areas
        - any other unrelated topic, problem or task
</DESIGN_ROUTINE>
<TOOLS>
    - Retrieve the working ontology content with `get_working_ontology`.
</TOOLS>
<OUTPUT_DEFINITION>
    - Class represents a domain entity (subject or object).
        - Subject: Entity capable of rights and obligations (e.g., natural/legal persons, functional roles).
        - Object: Entity that is the target or beneficiary of legal relations (e.g., assets, entitlements, official acts) but lacks legal agency.
    - If the domain concept belongs to the blacklist below, you must reject the domain concept to be designed as a class. The blacklist does not list the exact terms, but rather categories or types of concepts.
        <BLACKLIST>
            - "ministerstvo"
            - "informační systém, registr, evidence"
            - "právní předpis"
        </BLACKLIST>
</OUTPUT_DEFINITION>
<OUTPUT_STRUCTURE>
    - prefLabel: Unique, concrete, short label, noun/noun phrase, first letter upper-case (e.g. "Kosmická loď")
    - definition: Concise, non-circular, exact, self-contained, domain-oriented; preferably one or two sentences; preferably quotes legal definition from the legal knowledge with only minor linguistic modifications.
    - comment: explains the class meaning, expanding on semantics without introducing extraneous context; self-contained, domain-oriented; must summarize all important and relevant domain aspects throughout the domain knowledge; preferably a paragraph.
    - references: One or more references to numbered paragraphs and their hierarchical fragment in the legal act with the definitory text of the class. Keeps the hierarchical numbering from the numbered paragraph to the specific hierarchical fragment (e.g., "§ 3 (2) a)").
    - parent: the prefLabel of the parent class, if applicable.
</OUTPUT_STRUCTURE>"""

    ONTOLOGY_PROPERTY_AGENT_INSTRUCTIONS = """<ROLE>You are an Ontology Property Agent, an expert on designing ontology attributes and relationships (properties) of a specific ontology class.</ROLE>
<CONTEXT>
    - You are a member of the team of ontology engineers and domain experts.
    - The team task is to design an ontology of the given domain.
    - You were transferred from the Lead Ontology Architect Agent.
    - The team has already gathered and structured the necessary domain knowledge about the characteristics of the domain concept in the previous conversaton.
    - Your output will be presented to them and considered as a possible ontology update.
</CONTEXT>
<TASK>Design ontology attributes and relationships of the given ontology class.</TASK>
{TEAM_SPECIFICATION}
<BEHAVIOR>
    - Your input and output language is {OUTPUT_LANGUAGE}.
</BEHAVIOR>
<DESIGN_ROUTINE>
    - Gather comprehensive domain knowledge from the previous conversation of the team about the domain concept characteristics.
    - Start by proposing possible attributes and relationships to the user based on the domain knowledge.
    - Cooperate with the user on designing the attributes and relationships, discuss with them their requirements and viewpoints.
    - Iterate on the design based on feedback from the user.
    - If you need more domain knowledge about the domain concept characteristics, transfer back to the Lead Ontology Architect Agent.
    - When ready, present the final design to the user for approval.
    - If the user approves the design, output the ontology attributes and relationships and transfer back to the Lead Ontology Architect Agent.
    - Also transfer back to the Lead Ontology Architect Agent, after confirmation by the user, if the user starts talking about:
        - refining the class,
        - other domain concepts or areas,
        - any other unrelated topic, problem or task
</DESIGN_ROUTINE>
<TOOLS>
    - Retrieve the working ontology content with `get_working_ontology`.
</TOOLS>
<OUTPUT_DEFINITION>
    - Attribute is an intrinsic atomic property of a class, representing a single fact (analogous to one form field).
        - If a candidate attribute represents a generic "data about [concept]" or "údaje o [concept]", it should be split into more specific attributes of the class representing that concept.
    - A binary relationship is a directed semantic connection from a domain class to the range class and represents a property of the domain class.
        - One of the connected classes must be the class for which the relationship is being defined, the other can be a known or a new ontology class.
    - If a candidate property can be split into more properties, split it to more properties.
    - If you are not sure whether a property should be expressed as an attribute or relationship, propose both possibilities to the user with pros/cons and let the user decide.
</OUTPUT_DEFINITION>
<OUTPUT_STRUCTURE>
    - prefLabel: Unique, concrete, short label, lower case, includes the class's prefLabel linguistically incorporated (e.g. "barva kosmické lodi" instead of "barva", "je kapitánem kosmické lodi" instead of "je kapitánem" or "je")
        - attribute: noun/noun phrase
        - relationship: verb/verb phrase
    - definition: Concise, non-circular, exact, self-contained, domain-oriented; preferably one or two sentences; preferably quotes legal definition from the legal knowledge with only minor linguistic modifications.
    - comment: explains the property meaning, expanding on semantics without introducing extraneous context; self-contained, domain-oriented; must summarize all important and relevant domain aspects throughout the domain knowledge.
    - references: One or more references to numbered paragraphs and their hierarchical fragment in the legal act with the definitory text of the property. Keeps the hierarchical numbering from the numbered paragraph to the specific hierarchical fragment (e.g., "§ 3 (2) a)").
    - domain: the prefLabel of the domain class
    - range: the prefLabel of the range class (for relationships only)
</OUTPUT_STRUCTURE>"""

    def __init__(self, legal_act_id: str):
        data_source = DataSourceESEL()
        self.legislation_service = LegislationService(data_source, "gpt-4.1")
        self.legal_act = self.legislation_service.get_legal_act(AnyUrl(legal_act_id))

        project_root = Path(__file__).parent.parent.parent
        index_base_path = project_root / "data" / "indexes"

        self.index_service = IndexService(index_base_path)
        self.search_service = SearchService(self.index_service, self.legal_act)

        ontology_store = OntologyStore()
        self.ontology_service = OntologyService(ontology_store)

        # Extract components from legal_act_id to build filename
        match = re.match(
            r"https://opendata\.eselpoint\.cz/esel-esb/eli/cz/sb/(?P<year>\d{4})/(?P<number>\d+)/(?P<date>\d{4}-\d{2}-\d{2})",
            legal_act_id
        )
        if not match:
            raise ValueError(f"Invalid legal_act_id format: {legal_act_id}")
        short_id = f"{match.group('number')}-{match.group('year')}-{match.group('date')}"
        self.working_ontology_file = Path(__file__).parent.parent.parent / "data" / "output" / f"{short_id}-ontology.ttl"

        @function_tool
        def get_practical_domain_knowledge() -> str:
            """
            Get the practical domain knowledge about the given domain.

            Use this tool to retrieve practical insights and knowledge about the domain.

            Returns:
                str: Text representation of the practical domain knowledge.
            """
            return self._get_practical_domain_knowledge_impl()

        @function_tool
        def get_hierarchical_summary_of_legal_text() -> str:
            """
            Get the legal act summary, comprising hierarchically organized summaries of the legal act, its parts, chapters, and divisions.
            
            Use this tool to retrieve an overview of the domain knowledge in the form of summarized content of the legal act hierarchically structured based on the original structure of the legal act.
            This gives you complete context and understanding of the domain without the need to read the full legal act that can be very long.
            
            Returns:
                str: XML representation of the hierarchical structure
            """
            return self._get_hierarchical_summary_impl()
        
        @function_tool
        def search_legal_text(query: str, k: int) -> list[str]:
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
            return self._search_legal_text_impl(query, k)
        
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

        self.domain_concept_expert_agent = Agent(
            name="DomainConceptExpertAgent",
            handoff_description="An agent that identifies important domain concepts in the given domain of interest.",
            instructions=RECOMMENDED_PROMPT_PREFIX + self.DOMAIN_CONCEPT_EXPERT_AGENT,
            model="gpt-4.1",
            tools=[get_hierarchical_summary_of_legal_text, search_legal_text, get_practical_domain_knowledge]
        )

        self.domain_concept_characteristics_expert_agent = Agent(
            name="DomainConceptCharacteristicsExpertAgent",
            handoff_description="An agent that characterizes a domain concept in the given domain of interest.",
            instructions=RECOMMENDED_PROMPT_PREFIX + self.DOMAIN_CONCEPT_CHARACTERISTICS_EXPERT_AGENT,
            model="gpt-4.1",
            tools=[get_hierarchical_summary_of_legal_text, search_legal_text, get_practical_domain_knowledge]
        )

        self.ontology_class_agent =  Agent(
            name="OntologyClassAgent",
            handoff_description="An agent that can design a specific ontology class to represent a given domain concept based on the domain knowledge.",
            handoffs=[
                self.domain_concept_characteristics_expert_agent
            ],
            instructions=RECOMMENDED_PROMPT_PREFIX + self.ONTOLOGY_CLASS_AGENT_INSTRUCTIONS,
            model="gpt-4.1",
            tools=[get_working_ontology]
        )

        self.ontology_property_agent = Agent(
            name="OntologyPropertyAgent",
            handoff_description="An agent that can design ontology attributes and relationships (properties) of a given ontology class based on the domain knowledge.",
            handoffs=[
                self.domain_concept_characteristics_expert_agent
            ],
            instructions=RECOMMENDED_PROMPT_PREFIX + self.ONTOLOGY_PROPERTY_AGENT_INSTRUCTIONS,
            model="gpt-4.1",
            tools=[get_working_ontology]
        )

        self.ontology_architect_agent = Agent(
            name="OntologyArchitectAgent",
            instructions=RECOMMENDED_PROMPT_PREFIX + self.ONTOLOGY_ARCHITECT_AGENT_INSTRUCTIONS,
            handoffs=[
                self.domain_concept_expert_agent,
                self.domain_concept_characteristics_expert_agent,
                self.ontology_class_agent,
                self.ontology_property_agent
            ],
            model="gpt-5",
            model_settings=ModelSettings(
                reasoning={
                    "effort": "low"
                },
                verbosity="low"
            ),
            tools=[get_working_ontology, add_new_class, add_new_attribute, add_new_relationship]
        )
        self.domain_concept_expert_agent.handoffs.append(self.ontology_architect_agent)
        self.domain_concept_characteristics_expert_agent.handoffs.append(self.ontology_architect_agent)
        self.ontology_class_agent.handoffs.append(self.ontology_architect_agent)
        self.ontology_property_agent.handoffs.append(self.ontology_architect_agent)

    async def build_ontology(self) -> None:
        """
        Build the ontology from the legal act.
        """
        input_items: list[TResponseInputItem] = []

        current_agent = self.ontology_architect_agent

        input_items.append({"content": "Budeme pracovat na doméně silničních vozidel.", "role": "user"})    

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

    def _get_practical_domain_knowledge_impl(self) -> str:
        """
        Implementation method for getting the practical domain knowledge.

        Returns:
            str: Text representation of the practical domain knowledge.
        """
        if not self.practical_domain_knowledge:
            file_path = Path(__file__).parent.parent.parent / "data" / "domains" / "practical_knowledge" / "vehicle_registry.md"
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.practical_domain_knowledge = f.read()
            except Exception as e:
                return f"Error reading practical domain knowledge: {e}"

        return self.practical_domain_knowledge
    
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

    def _search_legal_text_impl(self, query: str, k: int) -> str:
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