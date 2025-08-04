"""
Unit test for the ontology similarity engine.

HOW TO RUN:
The virtual environment .venv should be activated before running the tests.

From the src directory, run:
    python -m ontology.test_similarity

Or from the project root:
    cd src; python -m ontology.test_similarity

The test uses mock implementations to avoid external dependencies.
"""

import os
# Set any required environment variables for testing
os.environ["OPENAI_API_KEY"] = "dummy-value-for-testing"

# Import statements using relative imports
from .similarity import SemanticSimilarity
import numpy as np
from typing import Dict, List


class MockSentenceTransformer:
    """Mock implementation of SentenceTransformer for testing."""
    
    def __init__(self):
        self.call_count = 0
        self.last_input = None
    
    def encode(self, texts, normalize_embeddings=True):
        """Mock encoding that returns deterministic embeddings."""
        self.call_count += 1
        
        # Handle both string and list inputs
        was_single_string = isinstance(texts, str)
        if was_single_string:
            texts = [texts]
        
        self.last_input = texts
        
        # Return deterministic embeddings based on text content
        embeddings = []
        for text in texts:
            # Create a simple hash-based embedding
            text_hash = hash(text.lower()) % 1000
            # Create a normalized vector
            vector = np.array([text_hash / 1000.0, (1000 - text_hash) / 1000.0, 0.5])
            
            if normalize_embeddings:
                # Normalize the vector
                norm = np.linalg.norm(vector)
                if norm > 0:
                    vector = vector / norm
            
            embeddings.append(vector)
        
        # Return format based on input type
        embeddings_array = np.array(embeddings)
        if was_single_string:
            return embeddings_array[0]  # Return 1D array for single string
        return embeddings_array  # Return 2D array for multiple strings


def test_semantic_similarity_initialization():
    """Test SemanticSimilarity initialization."""
    print("Testing SemanticSimilarity initialization...")
    
    mock_embedder = MockSentenceTransformer()
    similarity_engine = SemanticSimilarity(mock_embedder)
    
    # Verify embedder is stored
    assert similarity_engine.embedder == mock_embedder
    
    print("✓ SemanticSimilarity initialization working correctly")


def test_compute_class_embedding_with_labels():
    """Test computing class embedding with labels only."""
    print("Testing class embedding computation with labels...")
    
    mock_embedder = MockSentenceTransformer()
    similarity_engine = SemanticSimilarity(mock_embedder)
    
    # Test with labels only
    labels = {"cs": "Vozidlo", "en": "Vehicle"}
    definitions = {}
    comments = {}
    
    embedding = similarity_engine.compute_class_embedding(labels, definitions, comments)
    
    # Verify embedding is computed
    assert embedding is not None
    assert isinstance(embedding, np.ndarray)
    assert len(embedding.shape) == 1  # Should be 1D vector, not 2D
    assert embedding.shape[0] == 3  # Based on our mock implementation
    
    # Verify embedder was called
    assert mock_embedder.call_count == 1
    
    print("✓ Class embedding with labels working correctly")


def test_compute_class_embedding_comprehensive():
    """Test computing class embedding with all text types."""
    print("Testing comprehensive class embedding computation...")
    
    mock_embedder = MockSentenceTransformer()
    similarity_engine = SemanticSimilarity(mock_embedder)
    
    # Test with all text types
    labels = {"cs": "Vozidlo", "en": "Vehicle"}
    definitions = {"cs": "Dopravní prostředek", "en": "Transportation device"}
    comments = {"cs": "Poznámka", "en": "Additional comment"}
    
    embedding = similarity_engine.compute_class_embedding(labels, definitions, comments)
    
    # Verify embedding is computed
    assert embedding is not None
    assert isinstance(embedding, np.ndarray)
    
    # Verify the input includes weighted text (labels repeated 3x, definitions 2x, comments 1x)
    input_text = mock_embedder.last_input[0]
    assert "Vozidlo" in input_text
    assert "Vehicle" in input_text
    assert "Dopravní prostředek" in input_text
    assert "Transportation device" in input_text
    assert "Poznámka" in input_text
    assert "Additional comment" in input_text
    
    # Count occurrences to verify weighting
    vozidlo_count = input_text.count("Vozidlo")
    assert vozidlo_count == 3  # Labels repeated 3 times
    
    print("✓ Comprehensive class embedding working correctly")


def test_compute_class_embedding_empty():
    """Test computing class embedding with empty inputs."""
    print("Testing class embedding with empty inputs...")
    
    mock_embedder = MockSentenceTransformer()
    similarity_engine = SemanticSimilarity(mock_embedder)
    
    # Test with empty inputs
    embedding = similarity_engine.compute_class_embedding({}, {}, {})
    
    # Verify no embedding is computed
    assert embedding is None
    
    # Test with whitespace-only inputs
    labels = {"cs": "   ", "en": ""}
    definitions = {"cs": "\t\n"}
    comments = {}
    
    embedding = similarity_engine.compute_class_embedding(labels, definitions, comments)
    assert embedding is None
    
    print("✓ Class embedding with empty inputs working correctly")


def test_compute_property_embedding():
    """Test computing property embedding."""
    print("Testing property embedding computation...")
    
    mock_embedder = MockSentenceTransformer()
    similarity_engine = SemanticSimilarity(mock_embedder)
    
    # Test property embedding (should use same logic as class embedding)
    labels = {"cs": "má vlastníka", "en": "has owner"}
    definitions = {"cs": "Vztah vlastnictví"}
    comments = {}
    
    embedding = similarity_engine.compute_property_embedding(labels, definitions, comments)
    
    # Verify embedding is computed
    assert embedding is not None
    assert isinstance(embedding, np.ndarray)
    
    print("✓ Property embedding computation working correctly")


def test_find_similar_embeddings():
    """Test finding similar embeddings."""
    print("Testing similar embeddings search...")
    
    mock_embedder = MockSentenceTransformer()
    similarity_engine = SemanticSimilarity(mock_embedder)
    
    # Create target embedding
    target_embedding = np.array([1.0, 0.0, 0.0])
    
    # Create candidate embeddings
    all_embeddings = {
        "class1": np.array([0.9, 0.1, 0.0]),    # High similarity
        "class2": np.array([0.0, 1.0, 0.0]),    # Low similarity
        "class3": np.array([0.8, 0.2, 0.0]),    # Medium similarity
        "class4": np.array([-1.0, 0.0, 0.0]),   # Negative similarity
    }
    
    # Find similar embeddings
    results = similarity_engine.find_similar_embeddings(target_embedding, all_embeddings, limit=3)
    
    # Verify results
    assert len(results) == 3
    assert isinstance(results, list)
    
    # Verify ordering (highest similarity first)
    assert results[0][1] > results[1][1] > results[2][1]
    
    # Verify first result is most similar
    assert results[0][0] == "class1"
    
    print("✓ Similar embeddings search working correctly")


def test_find_similar_embeddings_limit():
    """Test similar embeddings search with limit."""
    print("Testing similar embeddings search with limit...")
    
    mock_embedder = MockSentenceTransformer()
    similarity_engine = SemanticSimilarity(mock_embedder)
    
    target_embedding = np.array([1.0, 0.0, 0.0])
    
    # Create many candidate embeddings
    all_embeddings = {}
    for i in range(10):
        all_embeddings[f"class{i}"] = np.array([0.5 + i * 0.05, 0.0, 0.0])
    
    # Test with different limits
    results_5 = similarity_engine.find_similar_embeddings(target_embedding, all_embeddings, limit=5)
    results_3 = similarity_engine.find_similar_embeddings(target_embedding, all_embeddings, limit=3)
    
    assert len(results_5) == 5
    assert len(results_3) == 3
    
    print("✓ Similar embeddings search with limit working correctly")


def test_compute_text_similarity():
    """Test direct text similarity computation."""
    print("Testing direct text similarity...")
    
    mock_embedder = MockSentenceTransformer()
    similarity_engine = SemanticSimilarity(mock_embedder)
    
    # Test similar texts
    text1 = "Vehicle transportation"
    text2 = "Transportation vehicle"
    
    similarity = similarity_engine.compute_text_similarity(text1, text2)
    
    # Verify similarity is computed
    assert isinstance(similarity, float)
    assert 0.0 <= similarity <= 1.0
    
    # Verify embedder was called with both texts
    assert mock_embedder.call_count == 1
    assert len(mock_embedder.last_input) == 2
    
    print("✓ Direct text similarity working correctly")


def test_compute_text_similarity_empty():
    """Test text similarity with empty inputs."""
    print("Testing text similarity with empty inputs...")
    
    mock_embedder = MockSentenceTransformer()
    similarity_engine = SemanticSimilarity(mock_embedder)
    
    # Test with empty texts
    similarity = similarity_engine.compute_text_similarity("", "some text")
    assert similarity == 0.0
    
    similarity = similarity_engine.compute_text_similarity("some text", "")
    assert similarity == 0.0
    
    similarity = similarity_engine.compute_text_similarity("   ", "\t\n")
    assert similarity == 0.0
    
    print("✓ Text similarity with empty inputs working correctly")


def test_compute_text_embedding():
    """Test single text embedding computation."""
    print("Testing single text embedding...")
    
    mock_embedder = MockSentenceTransformer()
    similarity_engine = SemanticSimilarity(mock_embedder)
    
    text = "Test text for embedding"
    embedding = similarity_engine.compute_text_embedding(text)
    
    # Verify embedding is computed
    assert embedding is not None
    assert isinstance(embedding, np.ndarray)
    
    # Test with empty text
    empty_embedding = similarity_engine.compute_text_embedding("")
    assert empty_embedding is None
    
    print("✓ Single text embedding working correctly")


def test_compute_similarity():
    """Test direct similarity computation between embeddings."""
    print("Testing direct embedding similarity...")
    
    mock_embedder = MockSentenceTransformer()
    similarity_engine = SemanticSimilarity(mock_embedder)
    
    # Test with normalized embeddings
    embedding1 = np.array([1.0, 0.0, 0.0])
    embedding2 = np.array([0.8, 0.6, 0.0])
    
    similarity = similarity_engine.compute_similarity(embedding1, embedding2)
    
    # Verify similarity is computed and clipped to [0, 1]
    assert isinstance(similarity, float)
    assert 0.0 <= similarity <= 1.0
    
    # Test identical embeddings
    similarity_identical = similarity_engine.compute_similarity(embedding1, embedding1)
    assert similarity_identical == 1.0
    
    # Test orthogonal embeddings
    embedding3 = np.array([0.0, 1.0, 0.0])
    similarity_orthogonal = similarity_engine.compute_similarity(embedding1, embedding3)
    assert similarity_orthogonal == 0.0
    
    print("✓ Direct embedding similarity working correctly")


def test_weighting_strategy():
    """Test text weighting strategy in embedding computation."""
    print("Testing text weighting strategy...")
    
    mock_embedder = MockSentenceTransformer()
    similarity_engine = SemanticSimilarity(mock_embedder)
    
    # Test that labels have higher weight than definitions and comments
    labels = {"en": "LABEL"}
    definitions = {"en": "DEFINITION"}
    comments = {"en": "COMMENT"}
    
    similarity_engine.compute_class_embedding(labels, definitions, comments)
    
    # Check that labels appear more frequently in the input
    input_text = mock_embedder.last_input[0]
    
    label_count = input_text.count("LABEL")
    definition_count = input_text.count("DEFINITION")
    comment_count = input_text.count("COMMENT")
    
    # Verify weighting: labels (3x) > definitions (2x) > comments (1x)
    assert label_count == 3
    assert definition_count == 2
    assert comment_count == 1
    
    print("✓ Text weighting strategy working correctly")


def run_all_tests():
    """Run all test functions."""
    print("=" * 50)
    print("Running Ontology Similarity Tests")
    print("=" * 50)
    
    test_functions = [
        test_semantic_similarity_initialization,
        test_compute_class_embedding_with_labels,
        test_compute_class_embedding_comprehensive,
        test_compute_class_embedding_empty,
        test_compute_property_embedding,
        test_find_similar_embeddings,
        test_find_similar_embeddings_limit,
        test_compute_text_similarity,
        test_compute_text_similarity_empty,
        test_compute_text_embedding,
        test_compute_similarity,
        test_weighting_strategy
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} FAILED: {e}")
            failed += 1
    
    print("=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 50)
    
    return failed == 0


def main():
    """Main function to run the tests."""
    success = run_all_tests()
    if success:
        print("All tests passed!")
        return 0
    else:
        print("Some tests failed!")
        return 1


if __name__ == "__main__":
    exit(main())
