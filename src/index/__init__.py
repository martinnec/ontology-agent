"""
Index module for building and searching legal act indexes.

This module provides indexing and retrieval capabilities for legal acts,
supporting both keyword-based (BM25) and semantic (FAISS) search over 
summaries and full-text content.
"""

# Core domain models
from .domain import IndexDoc, TextChunk, SearchResult, SearchQuery, IndexMetadata, ElementType

# Summary-based indexes  
from .bm25 import BM25SummaryIndex
from .faiss_index import FAISSSummaryIndex

# Full-text indexes
from .bm25_full import BM25FullIndex
from .faiss_full import FAISSFullIndex

# Hybrid search engine
from .hybrid import HybridSearchEngine, HybridConfig

# Index builder interface
from .builder import IndexBuilder, DocumentExtractor

__all__ = [
    # Domain models
    'IndexDoc',
    'TextChunk', 
    'SearchResult',
    'SearchQuery',
    'IndexMetadata',
    'ElementType',
    
    # Summary indexes
    'BM25SummaryIndex',
    'FAISSSummaryIndex',
    
    # Full-text indexes
    'BM25FullIndex',
    'FAISSFullIndex',
    
    # Hybrid search
    'HybridSearchEngine',
    'HybridConfig',
    
    # Builder interface
    'IndexBuilder',
    'DocumentExtractor'
]
