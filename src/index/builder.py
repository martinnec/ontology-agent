"""
Index builder interfaces and utilities.

This module defines the abstract interfaces for building different types of indexes
and utility functions for processing legal act elements.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Iterator, Any
from .domain import IndexDoc, IndexMetadata, ElementType


class IndexBuilder(ABC):
    """Abstract base class for index builders."""
    
    @abstractmethod
    def build(self, documents: List[IndexDoc]) -> None:
        """
        Build an index from a list of documents.
        
        Args:
            documents: List of IndexDoc instances to index
        """
        pass
    
    @abstractmethod
    def save(self, path: str) -> None:
        """
        Save the index to disk.
        
        Args:
            path: Path where to save the index
        """
        pass
    
    @abstractmethod
    def load(self, path: str) -> None:
        """
        Load an index from disk.
        
        Args:
            path: Path to load the index from
        """
        pass
    
    @abstractmethod
    def get_metadata(self) -> IndexMetadata:
        """
        Get metadata about this index.
        
        Returns:
            IndexMetadata instance
        """
        pass


class DocumentExtractor:
    """
    Utility class for extracting IndexDoc instances from legal act elements.
    """
    
    @staticmethod
    def extract_from_act(legal_act: Any, 
                        act_iri: Optional[str] = None,
                        snapshot_id: Optional[str] = None) -> List[IndexDoc]:
        """
        Extract all IndexDoc instances from a legal act and its elements.
        
        Args:
            legal_act: LegalAct instance from legislation.domain
            act_iri: IRI of the legal act
            snapshot_id: Version snapshot identifier
            
        Returns:
            List of IndexDoc instances for all elements in the act
        """
        documents = []
        
        def extract_recursive(element: Any, 
                            level: int = 0, 
                            parent_id: Optional[str] = None,
                            element_type: ElementType = ElementType.UNKNOWN) -> None:
            """Recursively extract documents from element hierarchy."""
            
            # Determine element type based on class name
            element_type = DocumentExtractor._get_element_type(element)
            
            # Create IndexDoc for current element
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
                for child in element.elements:
                    extract_recursive(
                        element=child,
                        level=level + 1,
                        parent_id=str(element.id),
                        element_type=DocumentExtractor._get_element_type(child)
                    )
        
        # Start extraction from the root act
        extract_recursive(legal_act, level=0, element_type=ElementType.ACT)
        
        return documents
    
    @staticmethod
    def _get_element_type(element: Any) -> ElementType:
        """
        Determine the ElementType based on the element's class name.
        
        Args:
            element: Legal structural element instance
            
        Returns:
            Corresponding ElementType
        """
        class_name = element.__class__.__name__.lower()
        
        if 'act' in class_name:
            return ElementType.ACT
        elif 'part' in class_name:
            return ElementType.PART
        elif 'chapter' in class_name:
            return ElementType.CHAPTER
        elif 'division' in class_name:
            return ElementType.DIVISION
        elif 'section' in class_name:
            return ElementType.SECTION
        else:
            return ElementType.UNKNOWN
    
    @staticmethod
    def filter_documents(documents: List[IndexDoc],
                        element_types: Optional[List[ElementType]] = None,
                        min_level: Optional[int] = None,
                        max_level: Optional[int] = None,
                        has_summary: Optional[bool] = None,
                        has_content: Optional[bool] = None) -> List[IndexDoc]:
        """
        Filter documents based on various criteria.
        
        Args:
            documents: List of IndexDoc instances to filter
            element_types: Filter by element types
            min_level: Minimum hierarchical level
            max_level: Maximum hierarchical level
            has_summary: Filter documents that have/don't have summaries
            has_content: Filter documents that have/don't have text content
            
        Returns:
            Filtered list of documents
        """
        filtered = documents
        
        if element_types is not None:
            filtered = [doc for doc in filtered if doc.element_type in element_types]
        
        if min_level is not None:
            filtered = [doc for doc in filtered if doc.level >= min_level]
        
        if max_level is not None:
            filtered = [doc for doc in filtered if doc.level <= max_level]
        
        if has_summary is not None:
            if has_summary:
                filtered = [doc for doc in filtered if doc.summary is not None and doc.summary.strip()]
            else:
                filtered = [doc for doc in filtered if doc.summary is None or not doc.summary.strip()]
        
        if has_content is not None:
            if has_content:
                filtered = [doc for doc in filtered if doc.text_content is not None and doc.text_content.strip()]
            else:
                filtered = [doc for doc in filtered if doc.text_content is None or not doc.text_content.strip()]
        
        return filtered
    
    @staticmethod
    def get_document_stats(documents: List[IndexDoc]) -> dict:
        """
        Get statistics about a collection of documents.
        
        Args:
            documents: List of IndexDoc instances
            
        Returns:
            Dictionary with statistics
        """
        if not documents:
            return {
                'total_count': 0,
                'by_type': {},
                'by_level': {},
                'with_summary': 0,
                'with_content': 0,
                'avg_level': 0
            }
        
        # Count by type
        by_type = {}
        for doc in documents:
            by_type[doc.element_type] = by_type.get(doc.element_type, 0) + 1
        
        # Count by level
        by_level = {}
        for doc in documents:
            by_level[doc.level] = by_level.get(doc.level, 0) + 1
        
        # Count documents with summary/content
        with_summary = sum(1 for doc in documents if doc.summary and doc.summary.strip())
        with_content = sum(1 for doc in documents if doc.text_content and doc.text_content.strip())
        
        # Calculate average level
        avg_level = sum(doc.level for doc in documents) / len(documents)
        
        return {
            'total_count': len(documents),
            'by_type': by_type,
            'by_level': by_level,
            'with_summary': with_summary,
            'with_content': with_content,
            'avg_level': avg_level
        }
