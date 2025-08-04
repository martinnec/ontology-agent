"""
Index collection container for managing different index types.

This module provides a unified interface for accessing different types of indexes
(BM25, FAISS, full-text) for a given legal act.
"""

from typing import Dict, Optional, Any, List
from .domain import IndexDoc


class IndexCollection:
    """
    Container for different types of indexes built from the same legal act.
    
    Provides a unified interface for accessing BM25, FAISS, and full-text indexes
    while supporting lazy loading and consistent API.
    """
    
    def __init__(self, act_iri: str, snapshot_id: Optional[str] = None):
        """
        Initialize the index collection.
        
        Args:
            act_iri: IRI identifier of the legal act
            snapshot_id: Snapshot version identifier
        """
        self.act_iri = act_iri
        self.snapshot_id = snapshot_id
        self._indexes: Dict[str, Any] = {}
        self._documents: List[IndexDoc] = []
    
    def add_index(self, index_type: str, index_instance: Any) -> None:
        """
        Add an index to the collection.
        
        Args:
            index_type: Type of index (e.g., 'bm25', 'faiss', 'bm25_full', 'faiss_full')
            index_instance: The built index instance
        """
        self._indexes[index_type] = index_instance
    
    def get_index(self, index_type: str) -> Optional[Any]:
        """
        Get an index by type.
        
        Args:
            index_type: Type of index to retrieve
            
        Returns:
            Index instance or None if not found
        """
        return self._indexes.get(index_type)
    
    def has_index(self, index_type: str) -> bool:
        """
        Check if an index type exists in the collection.
        
        Args:
            index_type: Type of index to check
            
        Returns:
            True if index exists, False otherwise
        """
        return index_type in self._indexes
    
    def get_available_indexes(self) -> List[str]:
        """
        Get list of available index types.
        
        Returns:
            List of index type names
        """
        return list(self._indexes.keys())
    
    def set_documents(self, documents: List[IndexDoc]) -> None:
        """
        Set the source documents used to build the indexes.
        
        Args:
            documents: List of IndexDoc objects
        """
        self._documents = documents.copy()
    
    def get_documents(self) -> List[IndexDoc]:
        """
        Get the source documents used to build the indexes.
        
        Returns:
            List of IndexDoc objects
        """
        return self._documents.copy()
    
    def get_document_count(self) -> int:
        """
        Get the number of documents in the collection.
        
        Returns:
            Number of documents
        """
        return len(self._documents)
    
    def get_document_by_id(self, element_id: str) -> Optional[IndexDoc]:
        """
        Get a document by its element ID.
        
        Args:
            element_id: Element ID to search for
            
        Returns:
            IndexDoc or None if not found
        """
        for doc in self._documents:
            if doc.element_id == element_id:
                return doc
        return None
    
    def __repr__(self) -> str:
        """String representation of the collection."""
        return (f"IndexCollection(act_iri='{self.act_iri}', "
                f"indexes={list(self._indexes.keys())}, "
                f"documents={len(self._documents)})")
