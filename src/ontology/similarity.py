"""
Semantic similarity engine for ontology classes and properties.

This module handles semantic similarity computations using sentence transformers
for discovering related concepts in the ontology.
"""

from typing import Dict, List, Tuple, Optional
import numpy as np
from sentence_transformers import SentenceTransformer

from .domain import OntologyClass, OntologyProperty


class SemanticSimilarity:
    """Handles semantic similarity computations for ontology elements."""
    
    def __init__(self, embedder: SentenceTransformer):
        """Initialize the semantic similarity engine.
        
        Args:
            embedder: Pre-initialized sentence transformer model
        """
        self.embedder = embedder
    
    def compute_class_embedding(self, 
                               labels: Dict[str, str], 
                               definitions: Dict[str, str],
                               comments: Dict[str, str]) -> Optional[np.ndarray]:
        """Combine text from labels, definitions, comments into embedding.
        
        Args:
            labels: Language -> label mapping
            definitions: Language -> definition mapping  
            comments: Language -> comment mapping
            
        Returns:
            Normalized embedding vector or None if no text available
        """
        # Combine all textual content
        text_parts = []
        
        # Add labels (highest priority)
        for label in labels.values():
            if label.strip():
                text_parts.append(label)
        
        # Add definitions (high priority)
        for definition in definitions.values():
            if definition.strip():
                text_parts.append(definition)
        
        # Add comments (lower priority)
        for comment in comments.values():
            if comment.strip():
                text_parts.append(comment)
        
        if not text_parts:
            return None
        
        # Combine all text with priority weighting
        # Labels get repeated for higher weight
        weighted_text_parts = []
        
        # Add labels multiple times for higher weight
        for label in labels.values():
            if label.strip():
                weighted_text_parts.extend([label] * 3)  # 3x weight for labels
        
        # Add definitions twice for medium weight
        for definition in definitions.values():
            if definition.strip():
                weighted_text_parts.extend([definition] * 2)  # 2x weight for definitions
        
        # Add comments once for base weight
        for comment in comments.values():
            if comment.strip():
                weighted_text_parts.append(comment)  # 1x weight for comments
        
        combined_text = " ".join(weighted_text_parts)
        
        try:
            embedding = self.embedder.encode(combined_text, normalize_embeddings=True)
            return embedding
        except Exception as e:
            print(f"Warning: Could not compute embedding: {e}")
            return None
    
    def compute_property_embedding(self,
                                 labels: Dict[str, str],
                                 definitions: Dict[str, str],
                                 comments: Dict[str, str]) -> Optional[np.ndarray]:
        """Compute embedding for a property (same logic as class for now).
        
        Args:
            labels: Language -> label mapping
            definitions: Language -> definition mapping
            comments: Language -> comment mapping
            
        Returns:
            Normalized embedding vector or None if no text available
        """
        return self.compute_class_embedding(labels, definitions, comments)
    
    def find_similar_embeddings(self, 
                               target_embedding: np.ndarray,
                               all_embeddings: Dict[str, np.ndarray],
                               limit: int = 10) -> List[Tuple[str, float]]:
        """Find most similar embeddings using cosine similarity.
        
        Args:
            target_embedding: The embedding to find similarities for
            all_embeddings: Dict of IRI -> embedding for all candidates
            limit: Maximum number of results to return
            
        Returns:
            List of (IRI, similarity_score) tuples ordered by similarity (descending)
        """
        similarities = []
        
        for iri, embedding in all_embeddings.items():
            try:
                # Compute cosine similarity
                similarity = np.dot(target_embedding, embedding)
                similarities.append((iri, float(similarity)))
            except Exception as e:
                print(f"Warning: Could not compute similarity for {iri}: {e}")
                continue
        
        # Sort by similarity score (descending) and limit results
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:limit]
    
    def compute_text_similarity(self, text1: str, text2: str) -> float:
        """Compute direct similarity between two text strings.
        
        Args:
            text1: First text string
            text2: Second text string
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not text1.strip() or not text2.strip():
            return 0.0
        
        try:
            embeddings = self.embedder.encode([text1, text2], normalize_embeddings=True)
            similarity = np.dot(embeddings[0], embeddings[1])
            return float(similarity)
        except Exception as e:
            print(f"Warning: Could not compute text similarity: {e}")
            return 0.0

    def compute_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """Compute embedding for a single text string.
        
        Args:
            text: Text to embed
            
        Returns:
            Normalized embedding vector or None if failed
        """
        if not text.strip():
            return None
        
        try:
            embedding = self.embedder.encode([text], normalize_embeddings=True)
            return embedding[0]
        except Exception as e:
            print(f"Warning: Could not compute text embedding: {e}")
            return None

    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        try:
            # Assume embeddings are already normalized
            similarity = np.dot(embedding1, embedding2)
            return float(np.clip(similarity, 0.0, 1.0))
        except Exception as e:
            print(f"Warning: Could not compute similarity: {e}")
            return 0.0
