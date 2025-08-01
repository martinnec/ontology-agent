"""
BM25-based keyword search index implementation.

This module provides BM25 indexing and search capabilities for legal act elements,
with weighted fields (summary_names^5 + summary^3 + title^2 + officialIdentifier^1).
"""

import json
import pickle
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from rank_bm25 import BM25Okapi
import numpy as np

from .domain import IndexDoc, SearchResult, SearchQuery, IndexMetadata, ElementType
from .builder import IndexBuilder


class BM25SummaryIndex(IndexBuilder):
    """
    BM25-based keyword search index for legal document summaries.
    
    Implements weighted search over:
    - summary_names^5 (highest weight - key concepts and relationships)
    - summary^3 (high weight - comprehensive text summary)
    - title^2 (medium weight) 
    - officialIdentifier^1 (baseline weight)
    """
    
    def __init__(self):
        self.bm25_model: Optional[BM25Okapi] = None
        self.documents: List[IndexDoc] = []
        self.weighted_texts: List[str] = []
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
    
    def _create_weighted_text(self, doc: IndexDoc) -> str:
        """
        Create weighted text for BM25 indexing.
        
        Applies weights by repeating text:
        - summary_names: 5x (highest priority - key concepts)
        - summary: 3x (high priority - comprehensive summary)
        - title: 2x (medium priority)
        - officialIdentifier: 1x (baseline)
        
        Args:
            doc: IndexDoc to process
            
        Returns:
            Weighted text string for indexing
        """
        parts = []
        
        # Add official identifier (weight 1)
        if doc.official_identifier:
            parts.append(doc.official_identifier)
        
        # Add title (weight 2)
        if doc.title:
            parts.extend([doc.title] * 2)
        
        # Add summary (weight 3)
        if doc.summary:
            parts.extend([doc.summary] * 3)
        
        # Add summary_names (weight 5 - highest priority)
        if doc.summary_names:
            summary_names_text = " ".join(doc.summary_names)
            parts.extend([summary_names_text] * 5)
        
        return " ".join(parts)
    
    def build(self, documents: List[IndexDoc]) -> None:
        """
        Build BM25 index from documents.
        
        Args:
            documents: List of IndexDoc instances to index
        """
        if not documents:
            raise ValueError("Cannot build index from empty document list")
        
        self.documents = documents.copy()
        
        # Create weighted texts for each document
        self.weighted_texts = [self._create_weighted_text(doc) for doc in documents]
        
        # Tokenize all texts
        tokenized_texts = [self._tokenizer(text) for text in self.weighted_texts]
        
        # Build BM25 model
        self.bm25_model = BM25Okapi(tokenized_texts)
        
        # Create metadata
        self.metadata = IndexMetadata(
            act_iri=documents[0].act_iri or "unknown",
            snapshot_id=documents[0].snapshot_id or datetime.now().isoformat(),
            created_at=datetime.now().isoformat(),
            document_count=len(documents),
            index_type="bm25_summary",
            metadata={
                "weighted_fields": ["summary_names^5", "summary^3", "title^2", "officialIdentifier^1"],
                "tokenizer": "simple_czech",
                "model_params": {
                    "k1": self.bm25_model.k1,
                    "b": self.bm25_model.b
                }
            }
        )
    
    def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Search the index using BM25 scoring.
        
        Args:
            query: SearchQuery with search parameters
            
        Returns:
            List of SearchResult instances ranked by relevance
        """
        if self.bm25_model is None:
            raise ValueError("Index not built. Call build() first.")
        
        # Tokenize query
        query_tokens = self._tokenizer(query.query)
        if not query_tokens:
            return []
        
        # Get BM25 scores
        scores = self.bm25_model.get_scores(query_tokens)
        
        # Create (score, index) pairs and sort by score descending
        scored_docs = [(scores[i], i) for i in range(len(scores))]
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        # Apply filters and create results
        results = []
        for rank, (score, doc_idx) in enumerate(scored_docs[:query.max_results * 2]):  # Get more candidates for filtering
            doc = self.documents[doc_idx]
            
            # Skip documents with very low scores (likely no real match)
            if score <= 0.001:
                continue
            
            # Apply filters
            if not self._passes_filters(doc, query):
                continue
            
            # Find which fields matched - additional verification
            matched_fields = self._find_matched_fields(doc, query_tokens)
            
            # Skip if no fields actually matched (safety check)
            if not matched_fields:
                continue
            
            # Create snippet
            snippet = self._create_snippet(doc, query_tokens)
            
            result = SearchResult(
                doc=doc,
                score=float(score),
                rank=len(results) + 1,  # Use actual result count for ranking
                matched_fields=matched_fields,
                snippet=snippet
            )
            results.append(result)
            
            # Stop when we have enough results
            if len(results) >= query.max_results:
                break
        
        return results
    
    def _passes_filters(self, doc: IndexDoc, query: SearchQuery) -> bool:
        """Check if document passes query filters."""
        
        # Element type filter
        if query.element_types and doc.element_type not in query.element_types:
            return False
        
        # Level filters
        if query.min_level is not None and doc.level < query.min_level:
            return False
        if query.max_level is not None and doc.level > query.max_level:
            return False
        
        # Official identifier pattern
        if query.official_identifier_pattern:
            if not re.search(query.official_identifier_pattern, doc.official_identifier or ""):
                return False
        
        return True
    
    def _find_matched_fields(self, doc: IndexDoc, query_tokens: List[str]) -> List[str]:
        """Find which fields contain query tokens."""
        matched_fields = []
        query_tokens_lower = [token.lower() for token in query_tokens]
        
        fields_to_check = {
            'official_identifier': doc.official_identifier or "",
            'title': doc.title or "",
            'summary': doc.summary or "",
            'summary_names': " ".join(doc.summary_names) if doc.summary_names else ""
        }
        
        for field_name, field_value in fields_to_check.items():
            field_tokens = self._tokenizer(field_value)
            if any(token in field_tokens for token in query_tokens_lower):
                matched_fields.append(field_name)
        
        return matched_fields
    
    def _create_snippet(self, doc: IndexDoc, query_tokens: List[str]) -> str:
        """Create a text snippet showing query matches."""
        # Prefer summary_names, then summary, then title, then official identifier
        text_sources = [
            (" ".join(doc.summary_names) if doc.summary_names else "", "summary_names"),
            (doc.summary, "summary"),
            (doc.title, "title"), 
            (doc.official_identifier, "identifier")
        ]
        
        for text, source in text_sources:
            if not text:
                continue
                
            # Check if any query tokens appear in this text
            text_tokens = self._tokenizer(text)
            query_tokens_lower = [token.lower() for token in query_tokens]
            
            if any(token in text_tokens for token in query_tokens_lower):
                # Return first 200 characters with ellipsis
                snippet = text[:200]
                if len(text) > 200:
                    snippet += "..."
                return snippet
        
        # Fallback to title if no matches found
        return doc.title[:100] + ("..." if len(doc.title) > 100 else "")
    
    def get_document_by_id(self, element_id: str) -> Optional[IndexDoc]:
        """Get a document by its element ID."""
        for doc in self.documents:
            if doc.element_id == element_id:
                return doc
        return None
    
    def get_top_terms(self, doc_idx: int, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Get the top terms for a document by TF-IDF-like scoring.
        
        Args:
            doc_idx: Index of document in the collection
            top_k: Number of top terms to return
            
        Returns:
            List of (term, score) tuples
        """
        if self.bm25_model is None or doc_idx >= len(self.documents):
            return []
        
        # Get document tokens
        doc_tokens = self._tokenizer(self.weighted_texts[doc_idx])
        if not doc_tokens:
            return []
        
        # Calculate term frequencies
        term_freq = {}
        for token in doc_tokens:
            term_freq[token] = term_freq.get(token, 0) + 1
        
        # Calculate IDF-like scores using BM25 model's IDF
        vocab = self.bm25_model.corpus_size
        term_scores = []
        
        for term, freq in term_freq.items():
            if term in self.bm25_model.idf:
                idf = self.bm25_model.idf[term]
                score = freq * idf  # Simple TF * IDF
                term_scores.append((term, score))
        
        # Sort by score and return top k
        term_scores.sort(key=lambda x: x[1], reverse=True)
        return term_scores[:top_k]
    
    def save(self, path: str) -> None:
        """
        Save the index to disk.
        
        Args:
            path: Directory path to save the index files
        """
        if self.bm25_model is None:
            raise ValueError("Index not built. Call build() first.")
        
        path_obj = Path(path)
        path_obj.mkdir(parents=True, exist_ok=True)
        
        # Save BM25 model
        with open(path_obj / "bm25_model.pkl", "wb") as f:
            pickle.dump(self.bm25_model, f)
        
        # Save documents
        with open(path_obj / "documents.pkl", "wb") as f:
            pickle.dump(self.documents, f)
        
        # Save weighted texts
        with open(path_obj / "weighted_texts.pkl", "wb") as f:
            pickle.dump(self.weighted_texts, f)
        
        # Save metadata
        with open(path_obj / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(self.metadata.model_dump(), f, ensure_ascii=False, indent=2)
    
    def load(self, path: str) -> None:
        """
        Load the index from disk.
        
        Args:
            path: Directory path to load the index from
        """
        path_obj = Path(path)
        
        if not path_obj.exists():
            raise FileNotFoundError(f"Index path does not exist: {path}")
        
        # Load BM25 model
        with open(path_obj / "bm25_model.pkl", "rb") as f:
            self.bm25_model = pickle.load(f)
        
        # Load documents
        with open(path_obj / "documents.pkl", "rb") as f:
            self.documents = pickle.load(f)
        
        # Load weighted texts
        with open(path_obj / "weighted_texts.pkl", "rb") as f:
            self.weighted_texts = pickle.load(f)
        
        # Load metadata
        with open(path_obj / "metadata.json", "r", encoding="utf-8") as f:
            metadata_dict = json.load(f)
            self.metadata = IndexMetadata(**metadata_dict)
    
    def get_metadata(self) -> IndexMetadata:
        """Get metadata about this index."""
        if self.metadata is None:
            raise ValueError("Index not built. Call build() first.")
        return self.metadata
    
    def get_stats(self) -> Dict:
        """Get detailed statistics about the index."""
        if self.bm25_model is None:
            return {}
        
        # Calculate vocabulary statistics
        all_tokens = []
        for tokens in [self._tokenizer(text) for text in self.weighted_texts]:
            all_tokens.extend(tokens)
        
        vocab_size = len(set(all_tokens))
        total_tokens = len(all_tokens)
        avg_doc_length = total_tokens / len(self.documents) if self.documents else 0
        
        return {
            "document_count": len(self.documents),
            "vocabulary_size": vocab_size,
            "total_tokens": total_tokens,
            "average_document_length": avg_doc_length,
            "bm25_params": {
                "k1": self.bm25_model.k1,
                "b": self.bm25_model.b
            }
        }
