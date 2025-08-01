"""
FAISS-based semantic search index implementation.

This module provides semantic search capabilities using multilingual embeddings
for legal act elements, focusing on summaries and titles for conceptual matching.
"""

import json
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

import faiss
from sentence_transformers import SentenceTransformer

from .domain import IndexDoc, SearchResult, SearchQuery, IndexMetadata, ElementType
from .builder import IndexBuilder


class FAISSSummaryIndex(IndexBuilder):
    """
    FAISS-based semantic search index for legal document summaries.
    
    Uses multilingual sentence transformers to generate embeddings for:
    - summary (primary semantic content)
    - title (structural semantic information)
    
    Provides semantic similarity search that can find conceptually related
    documents even when they don't share exact keywords.
    """
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        """
        Initialize FAISS semantic index.
        
        Args:
            model_name: Name of the sentence transformer model to use
        """
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self.faiss_index: Optional[faiss.Index] = None
        self.documents: List[IndexDoc] = []
        self.embeddings: Optional[np.ndarray] = None
        self.metadata: Optional[IndexMetadata] = None
        
    def _load_model(self) -> SentenceTransformer:
        """Load the sentence transformer model."""
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)
        return self.model
    
    def _create_embedding_text(self, doc: IndexDoc) -> str:
        """
        Create text for embedding generation.
        
        Combines title and summary to capture both structural and semantic content.
        
        Args:
            doc: IndexDoc to process
            
        Returns:
            Text string for embedding generation
        """
        parts = []
        
        # Add title for structural context
        if doc.title:
            parts.append(doc.title)
        
        # Add summary for semantic content (primary source)
        if doc.summary:
            parts.append(doc.summary)
        else:
            # Fallback to official identifier if no summary
            if doc.official_identifier:
                parts.append(doc.official_identifier)
        
        return " ".join(parts) if parts else doc.official_identifier or ""
    
    def build(self, documents: List[IndexDoc]) -> None:
        """
        Build FAISS index from documents.
        
        Args:
            documents: List of IndexDoc instances to index
        """
        if not documents:
            raise ValueError("Cannot build index from empty document list")
        
        self.documents = documents.copy()
        
        # Load model
        model = self._load_model()
        
        # Create embedding texts
        embedding_texts = [self._create_embedding_text(doc) for doc in documents]
        
        # Filter out empty texts
        valid_texts = [(i, text) for i, text in enumerate(embedding_texts) if text.strip()]
        if not valid_texts:
            raise ValueError("No valid texts found for embedding generation")
        
        # Generate embeddings
        print(f"Generating embeddings for {len(valid_texts)} documents...")
        texts_only = [text for _, text in valid_texts]
        embeddings = model.encode(texts_only, convert_to_numpy=True, show_progress_bar=True)
        
        # Create full embeddings array (with zeros for invalid texts)
        embedding_dim = embeddings.shape[1]
        full_embeddings = np.zeros((len(documents), embedding_dim), dtype=np.float32)
        
        for idx, (orig_idx, _) in enumerate(valid_texts):
            full_embeddings[orig_idx] = embeddings[idx]
        
        self.embeddings = full_embeddings
        
        # Build FAISS index
        print("Building FAISS index...")
        index = faiss.IndexFlatIP(embedding_dim)  # Inner product for cosine similarity
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(self.embeddings)
        index.add(self.embeddings)
        self.faiss_index = index
        
        # Create metadata
        self.metadata = IndexMetadata(
            act_iri=documents[0].act_iri or "unknown",
            snapshot_id=documents[0].snapshot_id or datetime.now().isoformat(),
            created_at=datetime.now().isoformat(),
            document_count=len(documents),
            index_type="faiss_summary",
            metadata={
                "model_name": self.model_name,
                "embedding_dimension": int(embedding_dim),
                "similarity_metric": "cosine",
                "embedding_texts": "title + summary",
                "valid_embeddings": len(valid_texts)
            }
        )
        
        print(f"FAISS index built successfully with {len(documents)} documents")
    
    def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Search the index using semantic similarity.
        
        Args:
            query: SearchQuery with search parameters
            
        Returns:
            List of SearchResult instances ranked by semantic similarity
        """
        if self.faiss_index is None or self.embeddings is None:
            raise ValueError("Index not built. Call build() first.")
        
        # Generate query embedding
        model = self._load_model()
        query_embedding = model.encode([query.query], convert_to_numpy=True)
        
        # Normalize for cosine similarity
        faiss.normalize_L2(query_embedding)
        
        # Search FAISS index
        # Get more candidates than needed for filtering
        search_k = min(query.max_results * 3, len(self.documents))
        scores, indices = self.faiss_index.search(query_embedding, search_k)
        
        # Create results
        results = []
        rank = 0
        
        for i in range(len(indices[0])):
            doc_idx = indices[0][i]
            score = float(scores[0][i])
            
            # Skip invalid indices or very low scores
            if doc_idx < 0 or score < 0.1:
                continue
            
            doc = self.documents[doc_idx]
            
            # Apply filters
            if not self._passes_filters(doc, query):
                continue
            
            # Create result
            matched_fields = self._find_semantic_matched_fields(doc, query.query)
            snippet = self._create_snippet(doc, query.query)
            
            result = SearchResult(
                doc=doc,
                score=score,
                rank=rank,
                matched_fields=matched_fields,
                snippet=snippet
            )
            results.append(result)
            rank += 1
            
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
            import re
            if not re.search(query.official_identifier_pattern, doc.official_identifier or ""):
                return False
        
        return True
    
    def _find_semantic_matched_fields(self, doc: IndexDoc, query: str) -> List[str]:
        """
        Find which fields are semantically related to the query.
        
        For semantic search, we consider the fields used in embedding generation.
        """
        matched_fields = []
        
        # Since we use title + summary for embeddings, these are the relevant fields
        if doc.title:
            matched_fields.append('title')
        if doc.summary:
            matched_fields.append('summary')
        
        # Also include summary_names if they exist (conceptually related)
        if doc.summary_names:
            matched_fields.append('summary_names')
        
        return matched_fields
    
    def _create_snippet(self, doc: IndexDoc, query: str) -> str:
        """Create a text snippet for semantic matches."""
        # For semantic search, prefer summary as it's the primary semantic content
        text_sources = [
            (doc.summary, "summary"),
            (doc.title, "title"),
            (" ".join(doc.summary_names) if doc.summary_names else "", "summary_names"),
            (doc.official_identifier, "identifier")
        ]
        
        for text, source in text_sources:
            if text and text.strip():
                # Return first 200 characters with ellipsis
                snippet = text[:200]
                if len(text) > 200:
                    snippet += "..."
                return snippet
        
        # Fallback to title
        return doc.title[:100] + ("..." if len(doc.title) > 100 else "")
    
    def get_document_by_id(self, element_id: str) -> Optional[IndexDoc]:
        """Get a document by its element ID."""
        for doc in self.documents:
            if doc.element_id == element_id:
                return doc
        return None
    
    def get_similar_documents(self, doc_id: str, k: int = 5) -> List[Tuple[IndexDoc, float]]:
        """
        Find documents similar to the given document.
        
        Args:
            doc_id: Element ID of the reference document
            k: Number of similar documents to return
            
        Returns:
            List of (document, similarity_score) tuples
        """
        if self.faiss_index is None or self.embeddings is None:
            raise ValueError("Index not built. Call build() first.")
        
        # Find the document
        doc_idx = None
        for i, doc in enumerate(self.documents):
            if doc.element_id == doc_id:
                doc_idx = i
                break
        
        if doc_idx is None:
            return []
        
        # Get the document's embedding
        doc_embedding = self.embeddings[doc_idx:doc_idx+1]
        
        # Search for similar documents (k+1 to exclude the document itself)
        scores, indices = self.faiss_index.search(doc_embedding, k + 1)
        
        results = []
        for i in range(len(indices[0])):
            idx = indices[0][i]
            score = float(scores[0][i])
            
            # Skip the document itself
            if idx == doc_idx:
                continue
            
            if idx >= 0 and score > 0.1:
                results.append((self.documents[idx], score))
        
        return results[:k]
    
    def save(self, path: str) -> None:
        """
        Save the index to disk.
        
        Args:
            path: Directory path to save the index files
        """
        if self.faiss_index is None or self.embeddings is None:
            raise ValueError("Index not built. Call build() first.")
        
        path_obj = Path(path)
        path_obj.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.faiss_index, str(path_obj / "faiss_index.bin"))
        
        # Save embeddings
        np.save(path_obj / "embeddings.npy", self.embeddings)
        
        # Save documents
        with open(path_obj / "documents.pkl", "wb") as f:
            pickle.dump(self.documents, f)
        
        # Save metadata (including model name for loading)
        with open(path_obj / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(self.metadata.model_dump(), f, ensure_ascii=False, indent=2)
        
        print(f"FAISS index saved to {path}")
    
    def load(self, path: str) -> None:
        """
        Load the index from disk.
        
        Args:
            path: Directory path to load the index from
        """
        path_obj = Path(path)
        
        if not path_obj.exists():
            raise FileNotFoundError(f"Index path does not exist: {path}")
        
        # Load metadata first to get model name
        with open(path_obj / "metadata.json", "r", encoding="utf-8") as f:
            metadata_dict = json.load(f)
            self.metadata = IndexMetadata(**metadata_dict)
        
        # Update model name from metadata
        if "model_name" in self.metadata.metadata:
            self.model_name = self.metadata.metadata["model_name"]
        
        # Load FAISS index
        self.faiss_index = faiss.read_index(str(path_obj / "faiss_index.bin"))
        
        # Load embeddings
        self.embeddings = np.load(path_obj / "embeddings.npy")
        
        # Load documents
        with open(path_obj / "documents.pkl", "rb") as f:
            self.documents = pickle.load(f)
        
        print(f"FAISS index loaded from {path}")
    
    def get_metadata(self) -> IndexMetadata:
        """Get metadata about this index."""
        if self.metadata is None:
            raise ValueError("Index not built. Call build() first.")
        return self.metadata
    
    def get_stats(self) -> Dict:
        """Get detailed statistics about the index."""
        if self.faiss_index is None or self.embeddings is None:
            return {}
        
        # Calculate embedding statistics
        embedding_norms = np.linalg.norm(self.embeddings, axis=1)
        non_zero_embeddings = np.sum(embedding_norms > 0)
        
        return {
            "document_count": len(self.documents),
            "embedding_dimension": self.embeddings.shape[1],
            "valid_embeddings": int(non_zero_embeddings),
            "model_name": self.model_name,
            "similarity_metric": "cosine",
            "faiss_index_type": type(self.faiss_index).__name__,
            "embedding_stats": {
                "mean_norm": float(np.mean(embedding_norms)),
                "std_norm": float(np.std(embedding_norms)),
                "min_norm": float(np.min(embedding_norms)),
                "max_norm": float(np.max(embedding_norms))
            }
        }
