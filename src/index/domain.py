"""
Domain models for indexing and retrieval.

This module defines the core data structures used for indexing legal act elements
and managing search operations.
"""

from pydantic import BaseModel, Field, AnyUrl
from typing import Optional, List, Dict, Any
from enum import Enum


class ElementType(str, Enum):
    """Types of legal structural elements."""
    ACT = "act"
    PART = "part"
    CHAPTER = "chapter"
    DIVISION = "division"
    SECTION = "section"
    UNKNOWN = "unknown"


class IndexDoc(BaseModel):
    """
    A searchable document representing a legal act element.
    
    This class extracts and structures the searchable content from legal act elements
    for use in BM25 and FAISS indexes.
    """
    
    element_id: str = Field(..., description="Unique identifier for the element")
    title: str = Field(..., description="Title/heading of the element")
    summary: Optional[str] = Field(None, description="AI-generated summary of the element")
    official_identifier: str = Field(..., description="Official legal identifier (e.g., '§ 2', 'čl. 15')")
    text_content: Optional[str] = Field(None, description="Full text content of the element")
    
    # Metadata for filtering and ranking
    level: int = Field(0, description="Hierarchical level in the document structure")
    element_type: ElementType = Field(ElementType.UNKNOWN, description="Type of legal element")
    parent_id: Optional[str] = Field(None, description="ID of parent element")
    child_ids: List[str] = Field(default_factory=list, description="IDs of child elements")
    
    # Additional metadata
    act_iri: Optional[str] = Field(None, description="IRI of the legal act this element belongs to")
    snapshot_id: Optional[str] = Field(None, description="Snapshot version of the source data")
    
    @classmethod
    def from_legal_element(cls, 
                          legal_element: Any,  # LegalStructuralElement from legislation.domain
                          level: int = 0,
                          element_type: ElementType = ElementType.UNKNOWN,
                          parent_id: Optional[str] = None,
                          act_iri: Optional[str] = None,
                          snapshot_id: Optional[str] = None) -> 'IndexDoc':
        """
        Extract searchable content from a legal act element.
        
        Args:
            legal_element: A LegalStructuralElement instance
            level: Hierarchical level in the document
            element_type: Type of the legal element
            parent_id: ID of the parent element
            act_iri: IRI of the legal act
            snapshot_id: Version snapshot identifier
            
        Returns:
            IndexDoc instance ready for indexing
        """
        # Extract child IDs if elements exist
        child_ids = []
        if hasattr(legal_element, 'elements') and legal_element.elements:
            child_ids = [str(child.id) for child in legal_element.elements]
        
        return cls(
            element_id=str(legal_element.id),
            title=legal_element.title,
            summary=legal_element.summary,
            official_identifier=legal_element.officialIdentifier,
            text_content=legal_element.textContent,
            level=level,
            element_type=element_type,
            parent_id=parent_id,
            child_ids=child_ids,
            act_iri=act_iri,
            snapshot_id=snapshot_id
        )
    
    def get_searchable_text(self, include_content: bool = False) -> str:
        """
        Get the combined searchable text for this document.
        
        Args:
            include_content: Whether to include full text content
            
        Returns:
            Combined searchable text
        """
        parts = []
        
        # Add official identifier
        if self.official_identifier:
            parts.append(self.official_identifier)
        
        # Add title (weighted higher in search)
        if self.title:
            parts.append(self.title)
        
        # Add summary (weighted highest in search)
        if self.summary:
            parts.append(self.summary)
        
        # Optionally add full text content
        if include_content and self.text_content:
            parts.append(self.text_content)
        
        return " ".join(parts)
    
    def get_weighted_fields(self) -> Dict[str, str]:
        """
        Get fields with their intended search weights.
        
        Returns:
            Dictionary mapping field names to their content
        """
        return {
            'official_identifier': self.official_identifier or "",
            'title': self.title or "",
            'summary': self.summary or "",
            'text_content': self.text_content or ""
        }


class SearchResult(BaseModel):
    """Result from a search operation."""
    
    doc: IndexDoc = Field(..., description="The matched document")
    score: float = Field(..., description="Relevance score")
    rank: int = Field(..., description="Rank in the result list")
    
    # Additional search metadata
    matched_fields: List[str] = Field(default_factory=list, description="Fields that matched the query")
    snippet: Optional[str] = Field(None, description="Text snippet showing the match")


class SearchQuery(BaseModel):
    """A search query with parameters."""
    
    query: str = Field(..., description="The search query text")
    max_results: int = Field(10, description="Maximum number of results to return")
    
    # Filtering options
    element_types: Optional[List[ElementType]] = Field(None, description="Filter by element types")
    min_level: Optional[int] = Field(None, description="Minimum hierarchical level")
    max_level: Optional[int] = Field(None, description="Maximum hierarchical level")
    official_identifier_pattern: Optional[str] = Field(None, description="Regex pattern for official identifier")
    
    # Search strategy options
    use_semantic: bool = Field(True, description="Use semantic (FAISS) search")
    use_keyword: bool = Field(True, description="Use keyword (BM25) search")
    semantic_weight: float = Field(0.6, description="Weight for semantic search (0-1)")
    keyword_weight: float = Field(0.4, description="Weight for keyword search (0-1)")


class IndexMetadata(BaseModel):
    """Metadata about an index."""
    
    act_iri: str = Field(..., description="IRI of the indexed legal act")
    snapshot_id: str = Field(..., description="Snapshot version of the source data")
    created_at: str = Field(..., description="ISO timestamp when index was created")
    document_count: int = Field(..., description="Number of documents in the index")
    index_type: str = Field(..., description="Type of index (bm25, faiss, hybrid)")
    
    # Index-specific metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional index-specific metadata")
