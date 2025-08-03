"""
BM25-based full-text search index implementation.

This module provides BM25 indexing and search capabilities for full text content
of legal act elements, with support for exact phrase searches and text chunking.
"""

import json
import pickle
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from rank_bm25 import BM25Okapi
import numpy as np

from .domain import IndexDoc, TextChunk, SearchResult, SearchQuery, IndexMetadata, ElementType
from .builder import IndexBuilder


class BM25FullIndex(IndexBuilder):
    """
    BM25-based full-text search index for legal document content.
    
    Implements full-text search over chunked text content with support for:
    - Exact phrase searches (e.g., "rozumí se", "musí", "je povinen")
    - Text chunking with overlaps to preserve semantic coherence
    - Keyword matching within text chunks
    """
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Initialize BM25 full-text index.
        
        Args:
            chunk_size: Maximum number of words per chunk
            chunk_overlap: Number of words to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        self.bm25_model: Optional[BM25Okapi] = None
        self.text_chunks: List[TextChunk] = []
        self.chunk_texts: List[str] = []
        self.metadata: Optional[IndexMetadata] = None
        self._tokenizer = self._create_tokenizer()
    
    def _create_tokenizer(self):
        """Create a simple tokenizer for Czech legal text."""
        def tokenize(text: str) -> List[str]:
            # Convert to lowercase and split on whitespace and punctuation
            text = text.lower()
            # Keep letters, numbers, and some Czech characters
            text = re.sub(r'[^\w\sáčďéěíňóřšťúůýž]', ' ', text)
            # Split on whitespace and filter empty strings
            tokens = [token for token in text.split() if token.strip()]
            return tokens
        return tokenize
    
    def build(self, documents: List[IndexDoc]) -> None:
        """
        Build BM25 full-text index from documents.
        
        Args:
            documents: List of IndexDoc instances to index
        """
        if not documents:
            raise ValueError("Cannot build index from empty document list")
        
        # Extract text chunks from documents
        self.text_chunks = []
        self.chunk_texts = []
        
        for doc in documents:
            if doc.text_content:  # Only process documents with text content
                chunk_data_list = doc.get_text_chunks(
                    chunk_size=self.chunk_size, 
                    overlap=self.chunk_overlap
                )
                
                for chunk_data in chunk_data_list:
                    text_chunk = TextChunk.from_chunk_data(chunk_data, doc)
                    self.text_chunks.append(text_chunk)
                    self.chunk_texts.append(text_chunk.text)
        
        if not self.chunk_texts:
            raise ValueError("No text content found in documents for full-text indexing")
        
        # Tokenize chunk texts
        tokenized_chunks = [self._tokenizer(text) for text in self.chunk_texts]
        
        # Build BM25 model
        self.bm25_model = BM25Okapi(tokenized_chunks)
        
        # Create metadata
        self.metadata = IndexMetadata(
            act_iri=documents[0].act_iri or "unknown",
            snapshot_id=documents[0].snapshot_id or "unknown",
            created_at=datetime.now().isoformat(),
            document_count=len(self.text_chunks),
            index_type="bm25_full",
            metadata={
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "source_documents": len(documents),
                "total_chunks": len(self.text_chunks)
            }
        )
    
    def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Search the full-text index for the query.
        
        Args:
            query: SearchQuery instance with search parameters
            
        Returns:
            List of SearchResult instances ranked by relevance
        """
        if not self.bm25_model or not self.text_chunks:
            return []
        
        # Tokenize query
        query_tokens = self._tokenizer(query.query)
        if not query_tokens:
            return []
        
        # Get BM25 scores
        scores = self.bm25_model.get_scores(query_tokens)
        
        # Create results with scores
        results = []
        for i, (chunk, score) in enumerate(zip(self.text_chunks, scores)):
            if score > 0:  # Only include chunks with non-zero scores
                # Apply filters if specified
                if self._passes_filters(chunk, query):
                    # Create snippet showing the match
                    snippet = self._create_snippet(chunk.text, query.query)
                    
                    # Create an IndexDoc-like object for the chunk
                    chunk_doc = IndexDoc(
                        element_id=chunk.chunk_id,
                        title=f"{chunk.title} (chunk {chunk.chunk_id.split('_')[-1]})",
                        summary=chunk.summary,
                        official_identifier=chunk.official_identifier,
                        text_content=chunk.text,
                        level=chunk.level,
                        element_type=chunk.element_type,
                        parent_id=chunk.element_id
                    )
                    
                    result = SearchResult(
                        doc=chunk_doc,
                        score=float(score),
                        rank=0,  # Will be set after sorting
                        matched_fields=["text_content"],
                        snippet=snippet
                    )
                    results.append(result)
        
        # Sort by score (descending)
        results.sort(key=lambda x: x.score, reverse=True)
        
        # Set ranks and limit results
        for i, result in enumerate(results[:query.max_results]):
            result.rank = i + 1
        
        return results[:query.max_results]
    
    def search_exact_phrase(self, phrase: str, max_results: int = 10) -> List[SearchResult]:
        """
        Search for exact phrase occurrences in the text.
        
        Args:
            phrase: Exact phrase to search for
            max_results: Maximum number of results to return
            
        Returns:
            List of SearchResult instances containing the exact phrase
        """
        if not self.text_chunks:
            return []
        
        phrase_lower = phrase.lower()
        results = []
        
        for i, chunk in enumerate(self.text_chunks):
            chunk_text_lower = chunk.text.lower()
            if phrase_lower in chunk_text_lower:
                # Calculate a simple relevance score based on phrase frequency and position
                phrase_count = chunk_text_lower.count(phrase_lower)
                # Higher score for more occurrences and earlier positions
                first_position = chunk_text_lower.find(phrase_lower)
                position_score = 1.0 / (1.0 + first_position / len(chunk_text_lower))
                score = phrase_count * position_score
                
                # Create snippet showing the phrase match
                snippet = self._create_phrase_snippet(chunk.text, phrase)
                
                # Create IndexDoc-like object for the chunk
                chunk_doc = IndexDoc(
                    element_id=chunk.chunk_id,
                    title=f"{chunk.title} (chunk {chunk.chunk_id.split('_')[-1]})",
                    summary=chunk.summary,
                    official_identifier=chunk.official_identifier,
                    text_content=chunk.text,
                    level=chunk.level,
                    element_type=chunk.element_type,
                    parent_id=chunk.element_id
                )
                
                result = SearchResult(
                    doc=chunk_doc,
                    score=score,
                    rank=0,  # Will be set after sorting
                    matched_fields=["text_content"],
                    snippet=snippet
                )
                results.append(result)
        
        # Sort by score (descending)
        results.sort(key=lambda x: x.score, reverse=True)
        
        # Set ranks and limit results
        for i, result in enumerate(results[:max_results]):
            result.rank = i + 1
        
        return results[:max_results]
    
    def _passes_filters(self, chunk: TextChunk, query: SearchQuery) -> bool:
        """Check if a chunk passes the query filters."""
        if query.element_types and chunk.element_type not in query.element_types:
            return False
        
        if query.min_level is not None and chunk.level < query.min_level:
            return False
        
        if query.max_level is not None and chunk.level > query.max_level:
            return False
        
        if query.official_identifier_pattern:
            if not re.search(query.official_identifier_pattern, chunk.official_identifier):
                return False
        
        return True
    
    def _create_snippet(self, text: str, query: str, max_length: int = 200) -> str:
        """Create a text snippet showing the query match."""
        query_lower = query.lower()
        text_lower = text.lower()
        
        # Find the first occurrence of any query word
        query_words = query_lower.split()
        best_position = len(text)
        
        for word in query_words:
            pos = text_lower.find(word)
            if pos != -1 and pos < best_position:
                best_position = pos
        
        if best_position == len(text):
            # No match found, return beginning of text
            return text[:max_length] + ("..." if len(text) > max_length else "")
        
        # Create snippet around the match
        start = max(0, best_position - max_length // 2)
        end = min(len(text), start + max_length)
        
        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        
        return snippet
    
    def _create_phrase_snippet(self, text: str, phrase: str, max_length: int = 200) -> str:
        """Create a text snippet showing the exact phrase match."""
        phrase_lower = phrase.lower()
        text_lower = text.lower()
        
        pos = text_lower.find(phrase_lower)
        if pos == -1:
            return text[:max_length] + ("..." if len(text) > max_length else "")
        
        # Create snippet around the phrase
        start = max(0, pos - (max_length - len(phrase)) // 2)
        end = min(len(text), start + max_length)
        
        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        
        return snippet
    
    def save(self, path: Path) -> None:
        """
        Save the index to disk.
        
        Args:
            path: Directory path where to save the index files
        """
        if not self.bm25_model or not self.text_chunks:
            raise ValueError("Cannot save empty index")
        
        path.mkdir(parents=True, exist_ok=True)
        
        # Save BM25 model
        with open(path / "bm25_full_model.pkl", "wb") as f:
            pickle.dump(self.bm25_model, f)
        
        # Save text chunks
        with open(path / "text_chunks.pkl", "wb") as f:
            pickle.dump(self.text_chunks, f)
        
        # Save chunk texts (for reference)
        with open(path / "chunk_texts.pkl", "wb") as f:
            pickle.dump(self.chunk_texts, f)
        
        # Save metadata
        if self.metadata:
            with open(path / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(self.metadata.model_dump(), f, indent=2, ensure_ascii=False)
    
    def load(self, path: Path) -> None:
        """
        Load the index from disk.
        
        Args:
            path: Directory path where the index files are stored
        """
        if not path.exists():
            raise FileNotFoundError(f"Index path {path} does not exist")
        
        # Load BM25 model
        with open(path / "bm25_full_model.pkl", "rb") as f:
            self.bm25_model = pickle.load(f)
        
        # Load text chunks
        with open(path / "text_chunks.pkl", "rb") as f:
            self.text_chunks = pickle.load(f)
        
        # Load chunk texts
        with open(path / "chunk_texts.pkl", "rb") as f:
            self.chunk_texts = pickle.load(f)
        
        # Load metadata
        metadata_path = path / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata_dict = json.load(f)
                self.metadata = IndexMetadata(**metadata_dict)
    
    def get_metadata(self) -> IndexMetadata:
        """
        Get metadata about this index.
        
        Returns:
            IndexMetadata instance
        """
        if self.metadata is None:
            raise ValueError("Index metadata not available. Build the index first.")
        return self.metadata
