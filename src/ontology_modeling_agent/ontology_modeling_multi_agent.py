from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import AnyUrl
import re

from agents import (
    Agent,
    HandoffCallItem,
    HandoffOutputItem,
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

class OntologyArchitect:

    TEAM_SPECIFICATION = """<TEAM>
- OntologyArchitectAgent - the expert leading the ontology design, responsible for the final result
- OntologyIterationManagerAgent - the expert on managing iterations of the ontology design process
</TEAM>"""

    ONTOLOGY_METAMODEL = """<ONTOLOGY_METAMODEL>
    - Class represents a primary entity in the domain, it is the main subject or object of interest.
        - Subject: An entity with legal agency, capable of rights and obligations (e.g., a person, a company, a role).
        - Object: An entity that is the target of an action but has no legal agency (e.g., a document, a physical asset, a legal right).
        - A class can specialize another class in the ontological (IS-A hierarchy) sense.
    - Attribute is a simple, literal property of a single Class (e.g., a name, a date, a number)
        - It represents an intrinsic property of the class.
        - It represents a single fact about the class, like a simple field in a form.
    - Relationship is a binary directed semantic link that describes how one Class is related to another.
        - It is a property of the first class (the domain).
    - No cardinalities.
    - No primary keys.
    - No primitive datatypes.
</ONTOLOGY_METAMODEL>"""

    BEHAVIOR_KNOWLEDGE_SPECIFICATION = """- Do your job solely based on the domain knowledge that can be collected from two sources:
        1) External long-term domain knowledge: legal act 56/2001, practical domain knowledge of a domain professional.
            - Use the provided tools to retrieve the external domain knowledge.
        2) Conversational short-term domain knowledge that you acquire from the conversation with the user throughout the design process."""
    
    BEHAVIOR_ROUTINE = """- Stick strictly to the <ROUTINE> specified below and its ordered steps when doing your job."""

    BEHAVIOR_OUTPUT = """- When <ROUTINE> requires you to provide an output [x], structure it as specified for [x] in <OUTPUT> below.
    - Never output[x] defined in <OUTPUT> when not requested by <ROUTINE> explicitly."""

    LANGUAGE_SPECIFICATION = "- Your input and output language is Czech."

    ONTOLOGY_ARCHITECT_AGENT_INSTRUCTIONS = f"""<ROLE>You are the OntologyArchitectAgent, an ontology design expert.</ROLE>
<TASK>Iterativelly construct a rigorous and exhaustive domain ontology comprising all relevant domain concepts represented as ontology classes, their attributes and relationships connecting them semantically.</TASK>
{TEAM_SPECIFICATION}
<BEHAVIOR>
    {LANGUAGE_SPECIFICATION}
    {BEHAVIOR_KNOWLEDGE_SPECIFICATION}
    {BEHAVIOR_ROUTINE}
    {BEHAVIOR_OUTPUT}
    - Take the lead on ontology design.
    - Never design concrete ontology elements on your own, always use specialized tools for this.

    ** Ontology Architecture **
    - Maintain the ontology architecture of your ontology comprising a small number of domain sub-areas roughly corresponding to key domain concepts and their short description from the sub-area point of view.
        - A key domain concept roughly corresponds to some central or important ontology class and its neighborhood - it is more a cluster that will be later probably modeled as more specific classes.
        - A domain concept can be a key concept in different sub-areas but from different points of view.
    - Drive the ontology design process using the ontology architecture.
    - Continuously monitor the ontology development process and make adjustments to the ontology architecture as needed. When adjusted, discuss the architecture with the user to get approval.
    - Focus the user's attention on the gaps in the coverage of the ontology architecture.
    
    ** Ontology Design Iterations **
    - Think deeply about possible ontology design iterations.
    - Keep the iterations small and focused on particular aspects of the domain sub-areas that you can formulate as the goal of the iteration.
        - An iteration should not aim at designing the detailed ontology of the whole sub-area.
        - An iteration should aim to fill the identified gaps or improve the overall ontology design.
        - Examples include: neighborhood of a key domain concept, detailing ontology attributes or relationships of a specific ontology class, refining relationships between a small number of ontology classes, etc.
    - Start with iterations that build a core simple ontology and then proceed with iterations that refine and expand it.

    ** Iteration Plan **
    - For an iteration chosen by the user, always build a detailed plan of individual steps to execute the iteration.
    - Each step must contribute to the overall iteration goal.
    - A step can focus on designing ontology elements of solely one category, i.e. it can focus on either classes, relationships, or attributes, but not a combination of them.
    - Keep the proposed steps as granular as possible.
    - Consider only steps of the following categories:
        1) class steps
            1.1) discover one or more new ontology classes related to a topic and specify their details
            1.2) discover one or more new ontology classes related to a given existing ontology class and specify their details
            1.3) discover one or more new ontology classes specializing/generalizing existing ontology classes and specify their details
            1.4) specify inheritance/specialization/generalization between existing ontology classes
            1.5) specify the details of a given ontology class
        2) relationship steps
            2.1) discover one or more new ontology relationships of an ontology class or between more ontology classes and specify their details
            2.2) discover one or more new ontology relationships related to a given existing ontology relationship and specify their details
            2.3) specify the details of a given ontology relationship
        3) attribute steps
            3.1) discover one or more ontology attributes for a given ontology class and specify their details
            3.2) break down a given ontology attribute to more atomic/granular ontology attributes (choose with/without keeping the original) and specify their details
            3.3) merge two or more ontology attributes into a new ontology attribute (choose with/without keeping the originals) and specify its details
            3.4) specify the details of a given ontology attribute

    ** Iteration Plan Execution **
    - Always execute the iteration plan step-by-step using the specialized tools for each step type.
    - After each step, review the plan and update it based on the step results, if necessary.
    - Always use the specialized tool for each specific step - do not attempt to implement the step on your own.
    - Never skip any steps in the plan execution.
    - The plan execution must be an atomic transaction, i.e. either all steps are executed successfully, or none are applied.
    - To ensure atomicity, do not write any changes to the working ontology until the entire plan is successfully executed.
    - The iteration plan must lead to a consistent ontology state:
        - If a new ontology class is proposed that specializes an ontology class, this class must already exist in the ontology or be created as part of the same iteration.
        - If a new ontology attribute is proposed, its class must already exist in the ontology or be created as part of the same iteration.
        - If a new ontology relationship is proposed, its classes must already exist in the ontology or be created as part of the same iteration.

    ** Continuous Communication with User **
    - If the user asks about the coverage of the domain by the working ontology, provide a summary structured by the domain sub-areas and informing about what is covered and where are the gaps.

    ** DON'T DO **
    - Never proceed to the plan execution without user approval.
    - Never write changes to the working ontology until the entire plan of the whole iteration is successfully executed and the user has approved the changes.
</BEHAVIOR>
{ONTOLOGY_METAMODEL}
<ROUTINE>
    1) Initialize the ontology architecture and list the sub-areas of the ontology architecture to the user as [subareas-list].
    2) Propose the next few ontology design iterations in the chosen sub-area and show them to the user as [proposed-iterations-list].
        - If previous iterations have been executed, review the previously proposed iterations that were not executed based on the communication with the user and show them to the user as [proposed-iterations-list].
    3) Let the user choose the next iteration from the proposals.
    4) Plan the detailed steps of the iteration.
    5) Execute the plan step-by-step. For each step:
        5.1) Execute each step by calling a specialized tool.
            - `ontology_class_tool` for class steps
            - `ontology_attribute_tool` for attribute steps
            - `ontology_relationship_tool` for relationship steps
        5.2) Review the plan and update it based on the step results, if necessary.
    6) Integrate the partial results from all steps into the coherent and consistent iteration result.
    7) Check the consistency of the iteration result.
    8) Show the complete result to the user as [iteration_result].
        6.1) If the user approves, write the result into the working ontology using the provided tools `add_ontology_class`, `add_ontology_relationship`, `add_ontology_attribute`.
        6.2) If the user does not approve, ask for their feedback and incorporate it into the iteration result.
            - If the user wants structural or semantic changes to the iteration result, you must repeat the whole iteration: prepare better iteration specification and go back to step 4.
            - If the user wants only a minor change to the iteration result, e.g., renaming ontology elements, you must incorporate this change into the iteration result and go back to step 8.
    9) Review the ontology architecture based on the iteration result. If necessary, update the ontology architecture accordingly and communicate the changes to the user as [subareas-list].
    10) Repeat 2-7 until the working ontology is complete.
</ROUTINE>
<OUTPUT>
    - [subareas-list]: list of sub-area, each with its name, brief description and key domain concepts.
    - [proposed-iterations-list]:  list of next few proposed iterations, each denoted with a letter A-Z, with a short title, and a longer specification so that the user can choose one to implement.
    - [iteration-plan]: current numbered list of steps to be taken during the iteration, each with a clear description of the task or tasks to be performed in the step.
    - [iteration-result]: complete list of proposed ontology updates as a list of all XML elements returned by the requested agents nested inside a root XML element <IterationResult>
</OUTPUT>"""
    
    ONTOLOGY_CLASS_AGENT_INSTRUCTIONS = f"""<ROLE>You are the OntologyClassAgent, an expert on discovering, designing or refining ontology classes.</ROLE>
<TASK>Do a discovery, design or refinement step required by the OntologyIterationManagerAgent.</TASK>
{TEAM_SPECIFICATION}
<BEHAVIOR>
    {LANGUAGE_SPECIFICATION}
    {BEHAVIOR_KNOWLEDGE_SPECIFICATION}
    {BEHAVIOR_ROUTINE}
    {BEHAVIOR_OUTPUT}
    - You never output any information that is not directly related to the task at hand.
    - You never output a class for a domain concept that belongs to the category on the blacklist.
    - For each class, ensure that you specify the following details based on the domain knowledge:
        - prefLabel: Unique, concrete, short label, noun/noun phrase, first letter upper-case (e.g. "Kosmická loď")
        - definition: Concise, non-circular, exact, self-contained, domain-oriented; preferably one or two sentences; preferably quotes legal definition from the legal knowledge with only minor linguistic modifications.
        - comment: explains the class meaning, expanding on semantics without introducing extraneous context; self-contained, domain-oriented; must summarize all important and relevant domain aspects throughout the domain knowledge; preferably a paragraph.
        - references: One or more references to numbered paragraphs and their hierarchical fragment in the legal act with the definitory text of the class. Keeps the hierarchical numbering from the numbered paragraph to the specific hierarchical fragment (e.g., "§ 3 (2) a)").
        - parent: (only if applicable) the prefLabel of the parent class in the IS-A (specialization) hierarchy - use when the parent class is a more generic than the current class and the current class represents a subset of the parent class.
    - If the step requires designing a concrete class and proposes its prefLabel, you do not have to keep it unchanged. If the domain knowledge requires a different prefLabel, you must update it accordingly.
</BEHAVIOR>
{ONTOLOGY_METAMODEL}
<BLACKLIST>
    - ministerstvo
    - informační systém
    - registr
    - evidence
    - právní předpis
</BLACKLIST>
<ROUTINE>
    1) Gather comprehensive domain knowledge needed to complete the step.
    2) Do the step by adding new classes, and updating or deleting existing ones.
        - If you are required to discover new ontology classes, you are free to discover them and give them preferred labels within the scope of the step.
        - If you are required to design or refine a concrete ontology class, you should not change its preferred label unless necessary.
    3) After finishing the step, inform the user about this with [short step summary] [list of proposed operations], and ask the user if they want to change anything or if they are satisfied with the results.
        - If the user requests to change anything, repeat the step considering the request.
        - If the user is satisfied, return [list of proposed operations].
</ROUTINE>
<OUTPUT>
    - [list of proposed operations]: Complete list of proposed additions, updates, or deletions of ontology classes, each as an XML element <ClassOperation> nested inside a root XML element <OntologyOperationsStep>. XML element <ClassOperation> strucured as follows:
        <ClassOperation>
            <Action>Add/Update/Delete</Action>
            <Detail>
                <prefLabel>...</prefLabel>
                <definition>...</definition>
                <comment>...</comment>
                <references>...</references>
                <parent>...</parent>
            </Detail>
        </ClassOperation>
</OUTPUT>"""

    ONTOLOGY_ATTRIBUTE_AGENT_INSTRUCTIONS = """<ROLE>You are the OntologyAttributeAgent, an expert on discovering, designing or refining ontology attributes of a specific ontology class.</ROLE>
<TASK>Do a discovery, design or refinement step required by the OntologyIterationManagerAgent.</TASK>
{TEAM_SPECIFICATION}
<BEHAVIOR>
    {LANGUAGE_SPECIFICATION}
    {BEHAVIOR_KNOWLEDGE_SPECIFICATION}
    {BEHAVIOR_ROUTINE}
    {BEHAVIOR_OUTPUT}
    - You never output any information that is not directly related to the task at hand.
    - You never output an attribute that belongs to the category on the blacklist.
    - You must keep attributes atomic, specific and focused on a single atomic fact.
        - If a candidate attribute aggregates more facts, split it.
        - If a candidate attribute is too broad, split it to more specific attributes.
        - If a candidate attribute refers to a complex structured value, split it but comment for each resulting attribute that it should be relocated to a separate ontology class representing this complex structured value.
    - For each attribute, ensure that you specify the following details based on the domain knowledge:
        - prefLabel: Unique, concrete, short label, noun/noun phrase lower case, includes the ontology class's prefLabel linguistically incorporated (e.g. "barva kosmické lodi" instead of "barva")
        - definition: Concise, non-circular, exact, self-contained, domain-oriented; preferably one or two sentences; preferably quotes legal definition from the legal knowledge with only minor linguistic modifications.
        - comment: explains the attribute meaning, expanding on semantics without introducing extraneous context; self-contained, domain-oriented; must summarize all important and relevant domain aspects throughout the domain knowledge.
        - references: One or more references to numbered paragraphs and their hierarchical fragment in the legal act with the definitory text of the attribute. Keeps the hierarchical numbering from the numbered paragraph to the specific hierarchical fragment (e.g., "§ 3 (2) a)").
        - domain: the prefLabel of the ontology class
    - If the step requires designing a concrete attribute and proposes its prefLabel, you do not have to keep it unchanged. If the domain knowledge requires a different prefLabel, you must update it accordingly.
</BEHAVIOR>
{ONTOLOGY_METAMODEL}
<BLACKLIST>
    - údaje o ...
    - informace o ...
    - vlastnosti ...
</BLACKLIST>
<ROUTINE>
    1) Gather comprehensive domain knowledge needed to complete the step.
    2) Do the step by adding new attributes, and updating or deleting existing ones.
        - If you are required to discover new ontology attributes, you are free to discover them within the scope of the given ontology class and give them preferred labels within the scope of the step.
        - If you are required to design or refine a concrete ontology attribute, you should not change its preferred label unless necessary.
    3) After finishing the step, inform the user about this with [short step summary] [list of proposed operations], and ask the user if they want to change anything or if they are satisfied with the results.
        - If the user requests to change anything, repeat the step considering the request.
        - If the user is satisfied, return [list of proposed operations].
</ROUTINE>
<OUTPUT>
    - [list of proposed operations]: Complete list of proposed additions, updates, or deletions of ontology attributes, each as an XML element <AttributeOperation> nested inside a root XML element <OntologyOperationsStep>. XML element <AttributeOperation> strucured as follows:
        <AttributeOperation>
            <Action>Add/Update/Delete</Action>
            <Detail>
                <prefLabel>...</prefLabel>
                <definition>...</definition>
                <comment>...</comment>
                <references>...</references>
                <domain>...</domain>
            </Detail>
        </AttributeOperation>
</OUTPUT>"""

    ONTOLOGY_RELATIONSHIP_AGENT_INSTRUCTIONS = """<ROLE>You are the OntologyRelationshipAgent, an expert on discovering, designing or refining ontology relationships of a specific ontology class or connecting specific ontology classes.</ROLE>
<TASK>Do a discovery, design or refinement step required by the OntologyIterationManagerAgent.</TASK>
{TEAM_SPECIFICATION}
<BEHAVIOR>
    {LANGUAGE_SPECIFICATION}
    {BEHAVIOR_KNOWLEDGE_SPECIFICATION}
    {BEHAVIOR_ROUTINE}
    {BEHAVIOR_OUTPUT}
    - You never output any information that is not directly related to the task at hand.
    - You never output a relationship that belongs to the category on the blacklist.
    - You must keep relationships atomic, specific and focused on a single atomic fact.
        - If a candidate relationship aggregates more semantic connections, split it.
        - If a candidate relationship is too broad, split it to more specific relationships.
        - If a candidate relationship refers to a primitive unstructured value, comment that it could be redesigned as an attribute.
    - For each relationship, ensure that you specify the following details based on the domain knowledge:
        - prefLabel: Unique, concrete, short label, verb/verb phrase lower case, includes the ontology class's linguistically incorporated (e.g. "je kapitánem kosmické lodi" instead of "je kapitánem" or "je")
        - definition: Concise, non-circular, exact, self-contained, domain-oriented; preferably one or two sentences; preferably quotes legal definition from the legal knowledge with only minor linguistic modifications.
        - comment: explains the relationship meaning, expanding on semantics without introducing extraneous context; self-contained, domain-oriented; must summarize all important and relevant domain aspects throughout the domain knowledge.
        - references: One or more references to numbered paragraphs and their hierarchical fragment in the legal act with the definitory text of the relationship. Keeps the hierarchical numbering from the numbered paragraph to the specific hierarchical fragment (e.g., "§ 3 (2) a)").
        - domain: the prefLabel of the ontology class
    - If the step requires designing a concrete relationship and proposes its prefLabel, you do not have to keep it unchanged. If the domain knowledge requires a different prefLabel, you must update it accordingly.
</BEHAVIOR>
{ONTOLOGY_METAMODEL}
<BLACKLIST>
    - "je" without any further specification
    - "má" without any further specification
    - vztahuje se k
    - souvisí s
</BLACKLIST>
<ROUTINE>
    1) Gather comprehensive domain knowledge needed to complete the step.
    2) Do the step by adding new relationships, and updating or deleting existing ones.
        - If you are required to discover new ontology relationships, you are free to discover them within the scope of the given ontology classes and give them preferred labels within the scope of the step.
        - If you are required to design or refine a concrete ontology relationship, you should not change its preferred label unless necessary.
    3) After finishing the step, inform the user about this with [short step summary] [list of proposed operations], and ask the user if they want to change anything or if they are satisfied with the results.
        - If the user requests to change anything, repeat the step considering the request.
        - If the user is satisfied, return [list of proposed operations].
</ROUTINE>
<OUTPUT>
    - [list of proposed operations]: Complete list of proposed additions, updates, or deletions of ontology relationships, each as an XML element <RelationshipOperation> nested inside a root XML element <OntologyOperationsStep>. XML element <RelationshipOperation> strucured as follows:
        <RelationshipOperation>
            <Action>Add/Update/Delete</Action>
            <Detail>
                <prefLabel>...</prefLabel>
                <definition>...</definition>
                <comment>...</comment>
                <references>...</references>
                <domain>...</domain>
                <range>...</range>
            </Detail>
        </RelationshipOperation>
</OUTPUT>"""
    
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

        practical_knowledge_file_path = Path(__file__).parent.parent.parent / "data" / "domains" / "practical_knowledge" / "vehicle_registry.md"
        self.practical_domain_knowledge = None
        try:
            with open(practical_knowledge_file_path, "r", encoding="utf-8") as f:
                self.practical_domain_knowledge = f.read()
        except Exception as e:
            return f"Error reading practical domain knowledge: {e}"

        @function_tool
        def get_practical_domain_knowledge() -> str:
            """
            Get the practical domain knowledge about the given domain.

            Use this tool to retrieve practical insights and knowledge about the domain.

            Returns:
                str: Text representation of the practical domain knowledge.
            """
            print("[tool get_practical_domain_knowledge]")
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
            print("[tool get_hierarchical_summary_of_legal_text]")
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
            print(f"[tool search_legal_text]: query: {query}, k: {k}")
            return self._search_legal_text_impl(query, k)
        
        @function_tool
        def get_working_ontology() -> str:
            """
            Get the current working ontology.
            
            Use this tool to retrieve the current working ontology you constructed in the previous steps expressed in RDF Turtle syntax.

            Returns:
                str: The current working ontology.
            """
            print("[tool get_working_ontology]")
            return self._get_working_ontology_impl()
        
        @function_tool
        def add_new_class(prefLabel: str, definition: str, comment: str, references: list[str], parent_class_prefLabel: str) -> bool:
            """
            Use this tool to add a new class to the working ontology.

            Args:
                prefLabel (str): preferred label of the class.
                definition (str): definition of the class.
                comment (str): comment about the class.
                references (list[str]): references to the legal act.
                parent_class_prefLabel (str): preferred label of the parent class.

            Returns:
                bool: True if successfully added, False otherwise.
            """
            print(f"[tool add_new_class]: prefLabel: {prefLabel}")
            return self._add_new_class_impl(prefLabel, definition, comment, references, parent_class_prefLabel)

        @function_tool
        def add_new_attribute(prefLabel: str, definition: str, comment: str, references: list[str], domain_class_prefLabel: str) -> bool:
            """
            Use this tool to add a new attribute (datatype property) to the working ontology.

            Args:
                prefLabel (str): The preferred label of the attribute.
                definition (str): The definition of the attribute.
                comment (str): Additional comment about the attribute.
                references (list[str]): References to the legal act.
                domain_class_prefLabel (str): The preferred label of the class this attribute belongs to.

            Returns:
                bool: True if successfully added, False otherwise.
            """
            print(f"[tool add_new_attribute]: prefLabel: {prefLabel}")
            return self._add_new_attribute_impl(prefLabel, definition, comment, references, domain_class_prefLabel)

        @function_tool
        def add_new_relationship(prefLabel: str, definition: str, comment: str, references: list[str], domain_class_prefLabel: str, range_class_prefLabel: str) -> bool:
            """
            Use this tool to add a new relationship (object property) to the working ontology.

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
            print(f"[tool add_new_relationship]: prefLabel: {prefLabel}")
            return self._add_new_relationship_impl(prefLabel, definition, comment, references, domain_class_prefLabel, range_class_prefLabel)

        self.ontology_class_agent =  Agent(
            name="OntologyClassAgent",
            handoff_description="An agent that can fulfill the autonomous task of discovering new ontology classes, designing the detail of a given ontology class, or refining an existing ontology class based solely on the available domain knowledge and the current state of the working ontology. It provides its output as a set of proposed ontology add/update/delete class changes.",
            instructions=RECOMMENDED_PROMPT_PREFIX + self.ONTOLOGY_CLASS_AGENT_INSTRUCTIONS,
            model="gpt-4.1",
            tools=[get_working_ontology, get_hierarchical_summary_of_legal_text, search_legal_text, get_practical_domain_knowledge]
        )

        self.ontology_attribute_agent = Agent(
            name="OntologyAttributeAgent",
            handoff_description="An agent that can fulfill the autonomous task of discovering new ontology attributes of a given ontology class, designing the detail of a given ontology attribute, or refining an existing ontology attribute based solely on the available domain knowledge and the current state of the working ontology. It provides its output as a set of proposed ontology add/update/delete attribute changes.",
            instructions=RECOMMENDED_PROMPT_PREFIX + self.ONTOLOGY_ATTRIBUTE_AGENT_INSTRUCTIONS,
            model="gpt-4.1",
            tools=[get_working_ontology, get_hierarchical_summary_of_legal_text, search_legal_text, get_practical_domain_knowledge]
        )

        self.ontology_relationship_agent = Agent(
            name="OntologyRelationshipAgent",
            handoff_description="An agent that can fulfill the autonomous task of discovering new ontology relationships of a given ontology class or between given ontology classes, designing the detail of a given ontology relationship, or refining an existing ontology relationship based solely on the available domain knowledge and the current state of the working ontology. It provides its output as a set of proposed ontology add/update/delete relationship changes.",
            instructions=RECOMMENDED_PROMPT_PREFIX + self.ONTOLOGY_RELATIONSHIP_AGENT_INSTRUCTIONS,
            model="gpt-4.1",
            tools=[get_working_ontology, get_hierarchical_summary_of_legal_text, search_legal_text, get_practical_domain_knowledge]
        )

        self.ontology_architect_agent = Agent(
            name="OntologyArchitectAgent",
            handoff_description="The lead agent responsible for the overall ontology design and architecture. It communicates with the user, oversees the iterative ontology design process by proposing and coordinating iterations to fulfill the user's requirements, and ensures that the results of the iterations are integrated and stored in the working ontology.",
            instructions=RECOMMENDED_PROMPT_PREFIX + self.ONTOLOGY_ARCHITECT_AGENT_INSTRUCTIONS,
            model="gpt-4.1",
#            model_settings=ModelSettings(
#                reasoning={
#                    "effort": "medium"
#                },
#                verbosity="low"
#            ),
            tools=[
                get_working_ontology,
                get_hierarchical_summary_of_legal_text,
                search_legal_text,
                get_practical_domain_knowledge,
                self.ontology_class_agent.as_tool(
                    tool_name="ontology_class_tool",
                    tool_description="Perform a class step of an ontology design iteration."
                ),
                self.ontology_relationship_agent.as_tool(
                    tool_name="ontology_relationship_tool",
                    tool_description="Perform a relationship step of an ontology design iteration."
                ),
                self.ontology_attribute_agent.as_tool(
                    tool_name="ontology_attribute_tool",
                    tool_description="Perform an attribute step of an ontology design iteration."
                ),
                add_new_class,
                add_new_attribute,
                add_new_relationship
            ]
        )
        
    async def build_ontology(self) -> None:
        """
        Build the ontology from the legal act.
        """
        input_items: list[TResponseInputItem] = []

        current_agent = self.ontology_architect_agent

        input_items.append({"content": "Budeme pracovat na doméně silničních vozidel.", "role": "user"})    

        skip_agentic_run = False

        while True:

            if not skip_agentic_run:

                result = await Runner.run(current_agent, input_items, max_turns=1000)

                for new_item in result.new_items:
                    agent_name = new_item.agent.name

                    if isinstance(new_item, MessageOutputItem):
                        print("\n<" + agent_name + " SPEAKING" + ">")
                        agent_output_message = ItemHelpers.text_message_output(new_item)
                        print(f"{agent_output_message}")
                        print("</" + agent_name + " SPEAKING" + ">\n")
                    elif isinstance(new_item, HandoffCallItem):
                        print(f"[{agent_name}]: Handing off through {new_item.raw_item.name}")
                    elif isinstance(new_item, HandoffOutputItem):
                        print(f"[{agent_name}]: Handed off to {new_item.target_agent.name}")
                    elif isinstance(new_item, ToolCallItem):
                        tool_name = getattr(new_item.raw_item, 'name', None) or getattr(new_item.raw_item, 'function', {}).get('name', 'unknown tool')
                        arguments = getattr(new_item.raw_item, 'arguments', None)
                        print(f"[{agent_name}]: Calling a tool {tool_name} with arguments {arguments}")

                input_items = result.to_input_list()

            skip_agentic_run = False

            user_input = input("Vstup uživatele ('exit' pro ukončení, 'write' pro zápis): ")
            if user_input.lower() == 'exit':
                break
            elif user_input.lower() == 'write':
                self._write_working_ontology_to_file()
                skip_agentic_run = True
            else:
                input_items.append({"content": user_input, "role": "user"})
    
    # TOOL IMPLEMENTATIONS

    def _get_working_ontology_impl(self) -> str:
        """
        Implementation method for getting the current working ontology.

        Returns:
            str: The current working ontology in OWL/TTL format.
        """
        return self.ontology_service.export_whole_ontology_to_turtle()

    def _get_practical_domain_knowledge_impl(self) -> str:
        """
        Implementation method for getting the practical domain knowledge.

        Returns:
            str: Text representation of the practical domain knowledge.
        """
        if self.practical_domain_knowledge:
            return self.practical_domain_knowledge
        else:
            return "Practical domain knowledge is empty."
    
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