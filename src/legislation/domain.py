from pydantic import BaseModel, Field, AnyUrl, field_validator, model_validator
from typing import Optional, List, Union, Literal, Dict, Any
import re
from datetime import datetime

# This code defines the data models for legal acts and their structural elements using Pydantic.
    
class LegalStructuralElement(BaseModel):
    # A class representing a structural element of a legal act with its unique identifier, official identifier, title, summary, text content, and parts.
    # A structural element can be any logical part of a legal act, such as a part, chapter, division, or section.
    id: AnyUrl = Field(..., description="Unique identifier for the structural element as IRI")
    officialIdentifier: str = Field(..., description="Official identifier of the structural element")
    title: str = Field(..., description="Title of the structural element")
    summary: Optional[str] = Field(None, description="Summary of the structural element")
    textContent: Optional[str] = Field(None, description="Text content of the structural element")
    elements: Optional[List['LegalStructuralElement']] = Field(None, description="List of parts of the structural element")
    elementType: str = Field(default="LegalStructuralElement", description="Type discriminator for proper deserialization")

class LegalAct(LegalStructuralElement):
    # A class representing a legal act, which is a specific type of structural element.
    elementType: Literal["LegalAct"] = Field(default="LegalAct", description="Type discriminator")

class LegalPart(LegalStructuralElement):
    # A class representing a part of a legal act, inheriting from LegalStructuralElement.
    elementType: Literal["LegalPart"] = Field(default="LegalPart", description="Type discriminator")

class LegalChapter(LegalStructuralElement):
    # A class representing a chapter of a legal act, inheriting from LegalStructuralElement.
    elementType: Literal["LegalChapter"] = Field(default="LegalChapter", description="Type discriminator")

class LegalDivision(LegalStructuralElement):
    # A class representing a division of a legal act, inheriting from LegalStructuralElement.
    elementType: Literal["LegalDivision"] = Field(default="LegalDivision", description="Type discriminator")

class LegalSection(LegalStructuralElement):
    # A class representing a section of a legal act, inheriting from LegalStructuralElement.
    elementType: Literal["LegalSection"] = Field(default="LegalSection", description="Type discriminator")

# Rebuild model to handle forward references
LegalStructuralElement.model_rebuild()

def create_legal_element(data: Dict[str, Any]) -> 'LegalStructuralElement':
    """
    Factory function to create the appropriate LegalStructuralElement subclass
    based on the elementType field in the data, or infer from other fields if missing.
    """
    element_type = data.get('elementType')
    
    # If elementType is missing, try to infer from other fields
    if not element_type:
        official_identifier = data.get('officialIdentifier', '')
        element_id = str(data.get('id', ''))
        
        # Infer type based on officialIdentifier patterns
        if official_identifier.startswith('§'):
            element_type = 'LegalSection'
        elif official_identifier.startswith('Část') and 'Hlava' in official_identifier and 'Díl' in official_identifier:
            element_type = 'LegalDivision'
        elif official_identifier.startswith('Část') and 'Hlava' in official_identifier:
            element_type = 'LegalChapter'
        elif official_identifier.startswith('Část'):
            element_type = 'LegalPart'
        else:
            # Check ID patterns for more specific inference
            if '/eli/cz/sb/' in element_id and element_id.count('/') <= 6:
                # Root legal act pattern (e.g., .../eli/cz/sb/2001/56/2025-07-01)
                element_type = 'LegalAct'
            elif '/cast_' in element_id:
                element_type = 'LegalPart'
            elif '/hlava_' in element_id:
                element_type = 'LegalChapter'
            elif '/dil_' in element_id:
                element_type = 'LegalDivision'
            elif '/par_' in element_id:
                element_type = 'LegalSection'
            else:
                # Default fallback: check if it seems like a root element
                if ('elements' in data and isinstance(data['elements'], list) and 
                    len(data['elements']) > 0 and 
                    any('Část' in str(elem.get('officialIdentifier', '')) for elem in data['elements'] if isinstance(elem, dict))):
                    element_type = 'LegalAct'
                else:
                    element_type = 'LegalStructuralElement'
    
    # Handle nested elements recursively
    if 'elements' in data and data['elements']:
        data['elements'] = [create_legal_element(elem) if isinstance(elem, dict) else elem for elem in data['elements']]
    
    if element_type == 'LegalAct':
        return LegalAct.model_validate(data)
    elif element_type == 'LegalPart':
        return LegalPart.model_validate(data)
    elif element_type == 'LegalChapter':
        return LegalChapter.model_validate(data)
    elif element_type == 'LegalDivision':
        return LegalDivision.model_validate(data)
    elif element_type == 'LegalSection':
        return LegalSection.model_validate(data)
    else:
        return LegalStructuralElement.model_validate(data)