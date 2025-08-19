from pydantic import BaseModel, Field, AnyUrl, field_validator, model_validator
import os
import re
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

update_class_detail_system_prompt ="""*** ROLE ***
You are an ontology expert specializing on updating details about ontology classes.

*** TASK ***
Your task is to update the details (name, definition, comment) of an existing ontology class based on the supplied domain knowledge expressed as text while keeping the original meaning intact.

*** INPUT_DETAILS ***
1) <CLASS> ... </CLASS> - Existing ontology class structured as follows:
- <name> ... </name> - The name of <CLASS />, must be capitalized and must not use any abbreviations.
- <definition> ... </definition> - The definition of <CLASS />, that explicitly defines the semantics of <CLASS />. It must be a complete sentence in the form corresponding to "<name> is [broader name] that/which/who/... [text clearly distinguishing <name> from <broader name>]."
- <comment> ... </comment> - The comment about <CLASS /> explaining its semantics in a less formal, possibly longer and human-approachable way.
2) <DOMAIN_KNOWLEDGE> ... </DOMAIN_KNOWLEDGE> - New piece of domain knowledge that possibly specifies the context or usage of the ontology class.
- It is a fragment from a larger body of knowledge.
- It is a hierarchy of <CONTEXT_KNOWLEDGE /> elements that can contain other <CONTEXT_KNOWLEDGE /> elements or <DETAILED_KNOWLEDGE /> elements.
- <CONTEXT_KNOWLEDGE /> contains a text summary of a context knowledge in <summary />.
- <DETAILED_KNOWLEDGE /> element contains detailed and hierarchically structured domain knowledge in <text-with-fragments /> you must focus on.

*** INSTRUCTIONS ***
- Analyze the <DOMAIN_KNOWLEDGE /> focusing especially on <DETAILED_KNOWLEDGE /> and using various <CONTEXT_KNOWLEDGE /> for the domain context.
- You can update the <name />, <definition />, and <comment /> fields of <CLASS /> only when there is a clear and justified reason to do so based solely on <DETAILED_KNOWLEDGE />.
- You cannot change the meaning of the original <CLASS />, i.e. its <name />, <definition />, and <comment /> in any way.
- The new values of <name />, <definition />, and <comment /> fields must be in the same language as <DETAILED_KNOWLEDGE />.
- <name /> must be capitalized, and must not use any abbreviations.
- <definition /> can be updated only when <DETAILED_KNOWLEDGE /> contains a clear definitory text for <CLASS /> using wordings such as "... se rozumí ...", "... rozumíme ...", "<name /> je ...". You must keep it unchanged if no such text is present, even it should remain empty. You must keep it as close as possible to the original wording, ideally preserving the original text.
- <comment /> can be updated whenever <DETAILED_KNOWLEDGE /> contains new knowledge related directly to <CLASS />.

*** OUTPUT ***
Output <UPDATED-CLASS>
<name updated="true|false">... possibly updated name ...</name>
<definition updated="true|false">... possibly updated definition ...</definition>
<comment updated="true|false">... possibly updated comment ...</comment>
</UPDATED-CLASS>
where updated="true" if the given property was changed, otherwise "false".
"""
update_class_detail_user_prompt = """<CLASS>
<name>{name}</name>
<definition>{definition}</definition>
<comment>{comment}</comment>
</CLASS>
<DOMAIN_KNOWLEDGE>
{domain_knowledge}
</DOMAIN_KNOWLEDGE>"""

class OntologyClass(BaseModel):
    name: str = Field(..., description="Name of the ontology class")
    definition: str = Field(..., description="Definition of the ontology class")
    comment: str = Field(..., description="Comment about the ontology class")

class OntologyClassDetailUpdateResult(BaseModel):
    updated_class: OntologyClass = Field(..., description="The updated ontology class")
    name_updated: bool = Field(..., description="Whether the name was updated")
    definition_updated: bool = Field(..., description="Whether the definition was updated")
    comment_updated: bool = Field(..., description="Whether the comment was updated")

class ClassDetailSpecialist:
    def __init__(self):
        self.model = "gpt-4.1-mini"
        self.open_api_key = os.getenv("OPENAI_API_KEY")
        if not self.open_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.client = OpenAI(api_key=self.open_api_key)

    def update_class_detail(self, current_class: OntologyClass, domain_knowledge: str) -> OntologyClassDetailUpdateResult:
        """
        Updates details (name, definition, comment) of an existing ontology class based on the supplied domain knowledge expressed as text

        Args:
            current_class (OntologyClass): The current class details.
            domain_knowledge (str): The domain knowledge to update the class with. It should be structured as an XML string.

        Returns:
            ClassDetailUpdateResult: The result containing the updated class and information about what was updated.
        """
        
        messages=[
            {"role": "system", "content": update_class_detail_system_prompt},
            {"role": "user", "content": update_class_detail_user_prompt.format(name=current_class.name, definition=current_class.definition, comment=current_class.comment, domain_knowledge=domain_knowledge)}
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2
        )
        if not response.choices:
            raise ValueError("No ontology class update generated from the domain knowledge")
        
        result_xml = response.choices[0].message.content.strip()
        
        # Validate XML format using regex
        class_pattern = r'<UPDATED-CLASS>\s*<name\s+updated="(true|false)">([^<]*)</name>\s*<definition\s+updated="(true|false)">([^<]*)</definition>\s*<comment\s+updated="(true|false)">([^<]*)</comment>\s*</UPDATED-CLASS>'
        match = re.search(class_pattern, result_xml, re.DOTALL)
        
        if not match:
            raise ValueError("The ontology class update was generated but the model did not provide the result in the required formatting. Expected format: <UPDATED-CLASS><name updated=\"true|false\">...</name><definition updated=\"true|false\">...</definition><comment updated=\"true|false\">...</comment></UPDATED-CLASS>")

        # Parse XML to extract values
        try:
            root = ET.fromstring(result_xml)
            
            name_element = root.find('name')
            definition_element = root.find('definition')
            comment_element = root.find('comment')
            
            if name_element is None or definition_element is None or comment_element is None:
                raise ValueError("Missing required elements in XML response")
            
            # Extract text content and update flags
            name = name_element.text.strip() if name_element.text else ""
            definition = definition_element.text.strip() if definition_element.text else ""
            comment = comment_element.text.strip() if comment_element.text else ""
            
            name_updated = name_element.get('updated', 'false').lower() == 'true'
            definition_updated = definition_element.get('updated', 'false').lower() == 'true'
            comment_updated = comment_element.get('updated', 'false').lower() == 'true'
            
            # Create updated OntologyClass
            updated_class = OntologyClass(
                name=name,
                definition=definition,
                comment=comment
            )
            
            # Return result with update information
            return OntologyClassDetailUpdateResult(
                updated_class=updated_class,
                name_updated=name_updated,
                definition_updated=definition_updated,
                comment_updated=comment_updated
            )
            
        except ET.ParseError as e:
            raise ValueError(f"The ontology class update was generated but the model did not provide the result in the required formatting. XML parsing error: {e}")
        except Exception as e:
            raise ValueError(f"Error processing the ontology class update: {e}")