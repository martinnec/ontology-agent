"""
Search domain models for defining search operations and results.

This module contains the data structures for search queries, options, strategies,
and results used throughout the search functionality.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from enum import Enum


class SearchStrategy(str, Enum):
    """Available search strategies."""
    KEYWORD = "keyword"           # BM25-based keyword search
    SEMANTIC = "semantic"         # FAISS-based semantic search
    HYBRID_SEMANTIC_FIRST = "hybrid_semantic_first"  # Semantic → Keyword reranking
    HYBRID_KEYWORD_FIRST = "hybrid_keyword_first"    # Keyword → Semantic reranking
    HYBRID_PARALLEL = "hybrid_parallel"              # Parallel execution + fusion
    FULLTEXT = "fulltext"         # Full-text chunk search
    EXACT_PHRASE = "exact_phrase" # Exact phrase matching


class SearchOptions(BaseModel):
    """Configuration options for search operations."""
    
    # Result limits
    max_results: int = Field(default=10, description="Maximum number of results to return")
    min_score: float = Field(default=0.0, description="Minimum relevance score threshold")
    
    # Filtering options
    element_types: Optional[List[str]] = Field(default=None, description="Filter by element types")
    min_level: Optional[int] = Field(default=None, description="Minimum hierarchical level")
    max_level: Optional[int] = Field(default=None, description="Maximum hierarchical level")
    parent_id: Optional[str] = Field(default=None, description="Filter by parent element ID")
    
    # Search behavior
    include_content: bool = Field(default=True, description="Include full text content in search")
    boost_summary: float = Field(default=2.0, description="Score boost for summary matches")
    boost_title: float = Field(default=1.5, description="Score boost for title matches")
    
    # Hybrid search specific
    hybrid_alpha: float = Field(default=0.5, description="Weight for combining scores (0=keyword, 1=semantic)")
    rerank_count: int = Field(default=50, description="Number of candidates for reranking")
    
    # Full-text search specific
    chunk_overlap: bool = Field(default=True, description="Allow overlapping text chunks")
    chunk_size: int = Field(default=500, description="Size of text chunks for full-text search")


class SearchResultItem(BaseModel):
    """A single search result item."""
    
    element_id: str = Field(..., description="Element ID from the index")
    title: str = Field(..., description="Element title")
    official_identifier: str = Field(..., description="Official legal identifier")
    summary: Optional[str] = Field(None, description="Element summary")
    text_content: Optional[str] = Field(None, description="Full text content")
    
    # Result metadata
    score: float = Field(..., description="Relevance score")
    rank: int = Field(..., description="Result ranking position")
    element_type: str = Field(..., description="Type of legal element")
    level: int = Field(..., description="Hierarchical level")
    parent_id: Optional[str] = Field(None, description="Parent element ID")
    
    # Search-specific metadata
    matched_fields: List[str] = Field(default_factory=list, description="Fields that matched the query")
    highlighted_text: Optional[str] = Field(None, description="Text with query terms highlighted")
    chunk_info: Optional[Dict[str, Any]] = Field(None, description="Text chunk information for full-text results")


class SearchResults(BaseModel):
    """Container for search results and metadata."""
    
    query: str = Field(..., description="Original search query")
    strategy: SearchStrategy = Field(..., description="Search strategy used")
    options: SearchOptions = Field(..., description="Search options used")
    
    # Results
    items: List[SearchResultItem] = Field(default_factory=list, description="Search result items")
    total_found: int = Field(..., description="Total number of matching documents")
    
    # Performance metadata
    search_time_ms: float = Field(..., description="Search execution time in milliseconds")
    index_types_used: List[str] = Field(default_factory=list, description="Index types used for search")
    
    # Additional metadata
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Filters that were applied")
    score_range: Dict[str, float] = Field(default_factory=dict, description="Min/max scores in results")
    
    def get_top_results(self, n: int = 5) -> List[SearchResultItem]:
        """Get the top N results."""
        return self.items[:n]
    
    def filter_by_element_type(self, element_type: str) -> 'SearchResults':
        """Filter results by element type."""
        filtered_items = [item for item in self.items if item.element_type == element_type]
        
        # Create new SearchResults with filtered items
        return SearchResults(
            query=self.query,
            strategy=self.strategy,
            options=self.options,
            items=filtered_items,
            total_found=len(filtered_items),
            search_time_ms=self.search_time_ms,
            index_types_used=self.index_types_used,
            filters_applied={**self.filters_applied, "element_type": element_type},
            score_range=self._calculate_score_range(filtered_items)
        )
    
    def filter_by_score(self, min_score: float) -> 'SearchResults':
        """Filter results by minimum score."""
        filtered_items = [item for item in self.items if item.score >= min_score]
        
        return SearchResults(
            query=self.query,
            strategy=self.strategy,
            options=self.options,
            items=filtered_items,
            total_found=len(filtered_items),
            search_time_ms=self.search_time_ms,
            index_types_used=self.index_types_used,
            filters_applied={**self.filters_applied, "min_score": min_score},
            score_range=self._calculate_score_range(filtered_items)
        )
    
    def _calculate_score_range(self, items: List[SearchResultItem]) -> Dict[str, float]:
        """Calculate score range for a list of items."""
        if not items:
            return {"min": 0.0, "max": 0.0}
        
        scores = [item.score for item in items]
        return {"min": min(scores), "max": max(scores)}
    
    def __len__(self) -> int:
        """Return number of results."""
        return len(self.items)
    
    def __bool__(self) -> bool:
        """Return True if there are any results."""
        return len(self.items) > 0
