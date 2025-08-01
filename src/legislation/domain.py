from pydantic import BaseModel, Field, AnyUrl, field_validator
from typing import Optional, List
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

class LegalAct(LegalStructuralElement):
    # A class representing a legal act, which is a specific type of structural element.
    pass

class LegalPart(LegalStructuralElement):
    # A class representing a part of a legal act, inheriting from LegalStructuralElement.
    pass

class LegalChapter(LegalStructuralElement):
    # A class representing a chapter of a legal act, inheriting from LegalStructuralElement.
    pass

class LegalDivision(LegalStructuralElement):
    # A class representing a division of a legal act, inheriting from LegalStructuralElement.
    pass

class LegalSection(LegalStructuralElement):
    # A class representing a section of a legal act, inheriting from LegalStructuralElement.
    pass