"""
FAISS-based full-text semantic search index implementation.

This module provides semantic search capabilities using multilingual embeddings
for text chunks from legal act elements, enabling semantic search over full content.
"""

import json
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

import faiss
from sentence_transformers import SentenceTransformer

from .domain import IndexDoc, TextChunk, SearchResult, SearchQuery, IndexMetadata, ElementType
from .builder import IndexBuilder


class FAISSFullIndex(IndexBuilder):
    """
    FAISS-based semantic search index for full-text legal document content.
    
    Uses multilingual sentence transformers to generate embeddings for text chunks,
    enabling semantic similarity search over full document content that can find
    conceptually related passages even when they don't share exact keywords.
    """
    
    def __init__(self, 
                 model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                 chunk_size: int = 500, 
                 chunk_overlap: int = 50):
        """
        Initialize FAISS full-text semantic index.
        
        Args:
            model_name: Name of the sentence transformer model to use
            chunk_size: Maximum number of words per chunk
            chunk_overlap: Number of words to overlap between chunks
        """
        self.model_name = model_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        self.model: Optional[SentenceTransformer] = None
        self.faiss_index: Optional[faiss.Index] = None
        self.text_chunks: List[TextChunk] = []
        self.embeddings: Optional[np.ndarray] = None
        self.metadata: Optional[IndexMetadata] = None
        
    def _load_model(self) -> SentenceTransformer:
        """Load the sentence transformer model."""
        if self.model is None:
            print(f"Loading sentence transformer model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
        return self.model
    
    def build(self, documents: List[IndexDoc]) -> None:
        """
        Build FAISS full-text semantic index from documents.
        
        Args:
            documents: List of IndexDoc instances to index
        """
        if not documents:
            raise ValueError("Cannot build index from empty document list")
        
        # Load the sentence transformer model
        model = self._load_model()
        
        # Extract text chunks from documents
        self.text_chunks = []
        chunk_texts = []
        
        for doc in documents:
            if doc.text_content:  # Only process documents with text content
                chunk_data_list = doc.get_text_chunks(
                    chunk_size=self.chunk_size, 
                    overlap=self.chunk_overlap
                )
                
                for chunk_data in chunk_data_list:
                    text_chunk = TextChunk.from_chunk_data(chunk_data, doc)
                    self.text_chunks.append(text_chunk)
                    
                    # Combine chunk text with some context for better embeddings
                    combined_text = self._create_combined_text(text_chunk)
                    chunk_texts.append(combined_text)
        
        if not chunk_texts:
            raise ValueError("No text content found in documents for full-text indexing")
        
        print(f"Generating embeddings for {len(chunk_texts)} text chunks...")
        
        # Generate embeddings for all chunk texts
        embeddings = model.encode(chunk_texts, 
                                 convert_to_numpy=True,
                                 show_progress_bar=True)
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        self.embeddings = embeddings
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        # Use IndexFlatIP for inner product (cosine similarity with normalized vectors)
        self.faiss_index = faiss.IndexFlatIP(dimension)
        self.faiss_index.add(embeddings)
        
        print(f"Built FAISS full-text index with {len(chunk_texts)} chunks, dimension: {dimension}")
        
        # Create metadata
        self.metadata = IndexMetadata(
            act_iri=documents[0].act_iri or "unknown",
            snapshot_id=documents[0].snapshot_id or "unknown",
            created_at=datetime.now().isoformat(),
            document_count=len(self.text_chunks),
            index_type="faiss_full",
            metadata={
                "model_name": self.model_name,
                "embedding_dimension": dimension,
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "source_documents": len(documents),
                "total_chunks": len(self.text_chunks)
            }
        )
    
    def _create_combined_text(self, chunk: TextChunk) -> str:
        """
        Create combined text for embedding generation.
        
        Combines chunk text with element context for better semantic understanding.
        
        Args:
            chunk: TextChunk to process
            
        Returns:
            Combined text for embedding
        """
        parts = []
        
        # Add element context first
        if chunk.official_identifier:
            parts.append(f"Oddíl {chunk.official_identifier}")
        
        if chunk.title:
            parts.append(chunk.title)
        
        # Add the chunk text
        parts.append(chunk.text)
        
        return " ".join(parts)
    
    def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Search the full-text semantic index for the query.
        
        Args:
            query: SearchQuery instance with search parameters
            
        Returns:
            List of SearchResult instances ranked by semantic similarity
        """
        if not self.faiss_index or not self.text_chunks:
            return []
        
        # Load model and encode query
        model = self._load_model()
        query_embedding = model.encode([query.query], convert_to_numpy=True)
        
        # Normalize query embedding
        faiss.normalize_L2(query_embedding)
        
        # Search FAISS index
        k = min(query.max_results * 2, len(self.text_chunks))  # Get more candidates for filtering
        scores, indices = self.faiss_index.search(query_embedding, k)
        
        # Create results
        results = []
        for i, (idx, score) in enumerate(zip(indices[0], scores[0])):
            if idx == -1:  # FAISS uses -1 for invalid results
                continue
            
            chunk = self.text_chunks[idx]
            
            # Apply filters if specified
            if self._passes_filters(chunk, query):
                # Create snippet (for full-text, we can show more context)
                snippet = self._create_snippet(chunk.text, query.query)
                
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
                    score=float(score),
                    rank=i + 1,
                    matched_fields=["text_content"],
                    snippet=snippet
                )
                results.append(result)
        
        # Limit to max_results
        return results[:query.max_results]
    
    def _passes_filters(self, chunk: TextChunk, query: SearchQuery) -> bool:
        """Check if a chunk passes the query filters."""
        if query.element_types and chunk.element_type not in query.element_types:
            return False
        
        if query.min_level is not None and chunk.level < query.min_level:
            return False
        
        if query.max_level is not None and chunk.level > query.max_level:
            return False
        
        if query.official_identifier_pattern:
            import re
            if not re.search(query.official_identifier_pattern, chunk.official_identifier):
                return False
        
        return True
    
    def _create_snippet(self, text: str, query: str, max_length: int = 300) -> str:
        """
        Create a text snippet for display.
        
        For semantic search, we show more context since the match might be conceptual.
        """
        if len(text) <= max_length:
            return text
        
        # For semantic search, just return the beginning of the chunk
        # as the entire chunk is semantically relevant
        return text[:max_length] + "..."
    
    def save(self, path: Path) -> None:
        """
        Save the index to disk.
        
        Args:
            path: Directory path where to save the index files
        """
        if not self.faiss_index or not self.text_chunks:
            raise ValueError("Cannot save empty index")
        
        path.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.faiss_index, str(path / "faiss_full_index.bin"))
        
        # Save text chunks
        with open(path / "text_chunks.pkl", "wb") as f:
            pickle.dump(self.text_chunks, f)
        
        # Save embeddings
        if self.embeddings is not None:
            np.save(path / "embeddings.npy", self.embeddings)
        
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
        
        # Load FAISS index
        self.faiss_index = faiss.read_index(str(path / "faiss_full_index.bin"))
        
        # Load text chunks
        with open(path / "text_chunks.pkl", "rb") as f:
            self.text_chunks = pickle.load(f)
        
        # Load embeddings
        embeddings_path = path / "embeddings.npy"
        if embeddings_path.exists():
            self.embeddings = np.load(embeddings_path)
        
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
    
    def get_similar_chunks(self, chunk_id: str, k: int = 5) -> List[Tuple[TextChunk, float]]:
        """
        Find chunks similar to the given chunk.
        
        Args:
            chunk_id: ID of the chunk to find similar chunks for
            k: Number of similar chunks to return
            
        Returns:
            List of (TextChunk, similarity_score) tuples
        """
        if not self.faiss_index or not self.text_chunks:
            return []
        
        # Find the chunk index
        chunk_idx = None
        for i, chunk in enumerate(self.text_chunks):
            if chunk.chunk_id == chunk_id:
                chunk_idx = i
                break
        
        if chunk_idx is None:
            return []
        
        # Get the chunk's embedding
        if self.embeddings is None:
            return []
        
        chunk_embedding = self.embeddings[chunk_idx:chunk_idx+1]
        
        # Search for similar chunks
        scores, indices = self.faiss_index.search(chunk_embedding, k + 1)  # +1 to exclude self
        
        # Return similar chunks (excluding the chunk itself)
        similar_chunks = []
        for idx, score in zip(indices[0], scores[0]):
            if idx != chunk_idx and idx < len(self.text_chunks):
                similar_chunks.append((self.text_chunks[idx], float(score)))
        
        return similar_chunks[:k]
