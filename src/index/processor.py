"""
Document processor for converting legal acts to indexable documents.

This module handles the conversion from legislation domain objects to index domain objects,
ensuring consistent element type mapping and hierarchical structure preservation.
"""

from typing import List, Optional
from .domain import IndexDoc, ElementType


class DocumentProcessor:
    """
    Processes legal acts and converts them to IndexDoc objects for indexing.
    
    This processor ensures consistent element type mapping from legislation domain
    to index domain and maintains proper hierarchical relationships.
    """
    
    # Mapping from legislation domain elementType to index domain ElementType
    ELEMENT_TYPE_MAPPING = {
        "LegalAct": ElementType.LEGAL_ACT,
        "LegalPart": ElementType.PART,
        "LegalChapter": ElementType.CHAPTER,
        "LegalDivision": ElementType.DIVISION,
        "LegalSection": ElementType.SECTION,
    }
    
    def __init__(self):
        """Initialize the document processor."""
        pass
    
    def process_legal_act(self, legal_act, act_iri: Optional[str] = None, 
                         snapshot_id: Optional[str] = None) -> List[IndexDoc]:
        """
        Process a legal act and convert it to a list of IndexDoc objects.
        
        Args:
            legal_act: LegalAct domain object from legislation module
            act_iri: IRI identifier for the legal act
            snapshot_id: Snapshot version identifier
            
        Returns:
            List of IndexDoc objects ready for indexing
        """
        documents = []
        
        # Process the root legal act
        self._process_element_recursive(
            element=legal_act,
            level=0,
            parent_id=None,
            documents=documents,
            act_iri=act_iri or str(legal_act.id),
            snapshot_id=snapshot_id
        )
        
        return documents
    
    def _process_element_recursive(self, element, level: int, parent_id: Optional[str],
                                 documents: List[IndexDoc], act_iri: str,
                                 snapshot_id: Optional[str]) -> None:
        """
        Recursively process a legal element and its children.
        
        Args:
            element: LegalStructuralElement to process
            level: Current hierarchical level
            parent_id: ID of parent element
            documents: List to append processed documents to
            act_iri: IRI of the legal act
            snapshot_id: Snapshot version identifier
        """
        # Determine element type from legislation domain elementType
        element_type = self._map_element_type(element.elementType)
        
        # Create IndexDoc for this element
        doc = IndexDoc.from_legal_element(
            legal_element=element,
            level=level,
            element_type=element_type,
            parent_id=parent_id,
            act_iri=act_iri,
            snapshot_id=snapshot_id
        )
        
        documents.append(doc)
        
        # Process child elements if they exist
        if hasattr(element, 'elements') and element.elements:
            for child_element in element.elements:
                self._process_element_recursive(
                    element=child_element,
                    level=level + 1,
                    parent_id=str(element.id),
                    documents=documents,
                    act_iri=act_iri,
                    snapshot_id=snapshot_id
                )
    
    def _map_element_type(self, legislation_element_type: str) -> ElementType:
        """
        Map legislation domain elementType to index domain ElementType.
        
        Args:
            legislation_element_type: elementType from legislation domain
            
        Returns:
            Corresponding ElementType for index domain
        """
        return self.ELEMENT_TYPE_MAPPING.get(
            legislation_element_type, 
            ElementType.UNKNOWN
        )
    
    def get_supported_element_types(self) -> List[str]:
        """
        Get list of supported legislation domain element types.
        
        Returns:
            List of supported elementType values
        """
        return list(self.ELEMENT_TYPE_MAPPING.keys())
