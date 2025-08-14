"""
Simple test for the FAISS semantic index implementation.
This test file follows the project's testing guidelines:
- No testing library dependencies
- Simple Python script with main function
- Tests placed directly in src directory
- Named with test_ prefix
- Self-contained and runnable independently

HOW TO RUN:
From the src directory, run:
    python -m index.test_faiss

Or from the project root:
    cd src && python -m index.test_faiss

The test uses mock implementations to avoid external dependencies.
"""

import os
import tempfile
import numpy as np
from pathlib import Path

# Set any required environment variables for testing
os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"

# Import statements using relative imports
from .faiss import FAISSSummaryIndex
from .domain import IndexDoc, SearchQuery, ElementType


class MockSentenceTransformer:
    """Mock implementation of SentenceTransformer for testing."""
    
    def __init__(self, model_name):
        self.model_name = model_name
        self.embedding_dim = 384
    
    def encode(self, texts, convert_to_numpy=True, show_progress_bar=False):
        """Mock encoding that returns random embeddings."""
        if isinstance(texts, str):
            texts = [texts]
        
        # Return consistent random embeddings for reproducible tests
        np.random.seed(42)
        embeddings = np.random.rand(len(texts), self.embedding_dim).astype(np.float32)
        return embeddings


class MockFAISSIndex:
    """Mock implementation of FAISS Index for testing."""
    
    def __init__(self, dimension):
        self.dimension = dimension
        self.embeddings = None
        self.search_calls = []
    
    def add(self, embeddings):
        """Mock add method."""
        self.embeddings = embeddings
    
    def search(self, query_embedding, k):
        """Mock search method."""
        self.search_calls.append((query_embedding, k))
        
        # Return mock results - indices and scores
        n_docs = len(self.embeddings) if self.embeddings is not None else 3
        indices = np.arange(min(k, n_docs)).reshape(1, -1)
        scores = np.linspace(0.9, 0.1, min(k, n_docs)).reshape(1, -1)
        return scores, indices


def mock_faiss_normalize_l2(embeddings):
    """Mock FAISS normalize function."""
    pass


def create_sample_documents():
    """Create sample documents for testing."""
    return [
        IndexDoc(
            element_id="doc1",
            title="Základní pojmy",
            official_identifier="§ 1",
            summary="Definice základních pojmů v oblasti ochrany osobních údajů, včetně definice osobních údajů a zpracování.",
            summary_names=["osobní údaje", "zpracování", "správce"],
            level=1,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/1"
        ),
        IndexDoc(
            element_id="doc2", 
            title="Práva subjektů údajů",
            official_identifier="§ 2",
            summary="Ustanovení o právech fyzických osob při zpracování osobních údajů, právo na informace a opravu.",
            summary_names=["práva subjektů", "právo na informace", "právo na opravu"],
            level=1,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/1"
        ),
        IndexDoc(
            element_id="doc3",
            title="Povinnosti správce",
            official_identifier="§ 3",
            summary="Povinnosti správce osobních údajů při zpracování, včetně zajištění bezpečnosti a vedení záznamu.",
            summary_names=["povinnosti správce", "bezpečnost", "vedení záznamu"],
            level=1,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/1"
        )
    ]


def test_index_initialization():
    """Test FAISS index initialization."""
    print("Testing FAISS index initialization...")
    
    # Test default initialization
    index = FAISSSummaryIndex()
    assert index.model_name == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    assert index.model is None
    assert index.faiss_index is None
    assert index.documents == []
    assert index.embeddings is None
    assert index.metadata is None
    
    # Test custom model initialization
    custom_model = "sentence-transformers/all-MiniLM-L6-v2"
    index2 = FAISSSummaryIndex(model_name=custom_model)
    assert index2.model_name == custom_model
    
    print("✓ Index initialization working correctly")


def test_embedding_text_creation():
    """Test embedding text creation from documents."""
    print("Testing embedding text creation...")
    
    index = FAISSSummaryIndex()
    docs = create_sample_documents()
    
    # Test with title and summary
    text = index._create_embedding_text(docs[0])
    expected = "Základní pojmy Definice základních pojmů v oblasti ochrany osobních údajů, včetně definice osobních údajů a zpracování."
    assert text == expected
    
    # Test with summary only
    doc_no_title = IndexDoc(
        element_id="test",
        title="",
        official_identifier="§ 1",
        summary="Test summary",
        level=1,
        element_type=ElementType.SECTION
    )
    text = index._create_embedding_text(doc_no_title)
    assert text == "Test summary"
    
    # Test with identifier only
    doc_minimal = IndexDoc(
        element_id="test",
        title="",
        official_identifier="§ 1",
        summary="",
        level=1,
        element_type=ElementType.SECTION
    )
    text = index._create_embedding_text(doc_minimal)
    assert text == "§ 1"
    
    print("✓ Embedding text creation working correctly")


def test_build_index_with_mocks():
    """Test building FAISS index with mock dependencies."""
    print("Testing FAISS index building...")
    
    # Patch the dependencies to use our mocks
    import sys
    import index.faiss as faiss_module
    
    original_sentence_transformer = getattr(faiss_module, 'SentenceTransformer', None)
    original_faiss = getattr(faiss_module, 'faiss', None)
    
    try:
        # Mock SentenceTransformer
        faiss_module.SentenceTransformer = MockSentenceTransformer
        
        # Mock FAISS module
        class MockFAISS:
            IndexFlatIP = MockFAISSIndex
            normalize_L2 = staticmethod(mock_faiss_normalize_l2)
        
        faiss_module.faiss = MockFAISS()
        
        # Create index and build
        index = FAISSSummaryIndex()
        documents = create_sample_documents()
        
        # Test empty documents
        try:
            index.build([])
            assert False, "Should raise ValueError for empty documents"
        except ValueError as e:
            assert "empty document list" in str(e)
        
        # Build with real documents
        index.build(documents)
        
        # Verify state
        assert len(index.documents) == 3
        assert index.embeddings is not None
        assert index.embeddings.shape == (3, 384)
        assert index.metadata is not None
        assert index.metadata.index_type == "faiss_summary"
        assert index.metadata.document_count == 3
        
    finally:
        # Restore original modules
        if original_sentence_transformer:
            faiss_module.SentenceTransformer = original_sentence_transformer
        if original_faiss:
            faiss_module.faiss = original_faiss
    
    print("✓ Index building working correctly")


def test_search_functionality():
    """Test search functionality with mocks."""
    print("Testing FAISS search functionality...")
    
    import index.faiss as faiss_module
    
    original_sentence_transformer = getattr(faiss_module, 'SentenceTransformer', None)
    original_faiss = getattr(faiss_module, 'faiss', None)
    
    try:
        # Setup mocks
        faiss_module.SentenceTransformer = MockSentenceTransformer
        
        class MockFAISS:
            IndexFlatIP = MockFAISSIndex
            normalize_L2 = staticmethod(mock_faiss_normalize_l2)
        
        faiss_module.faiss = MockFAISS()
        
        # Create and build index
        index = FAISSSummaryIndex()
        documents = create_sample_documents()
        index.build(documents)
        
        # Test search before building (create new index)
        empty_index = FAISSSummaryIndex()
        query = SearchQuery(query="test query")
        
        try:
            empty_index.search(query)
            assert False, "Should raise ValueError for unbuilt index"
        except ValueError as e:
            assert "not built" in str(e)
        
        # Test successful search
        query = SearchQuery(query="osobní údaje", max_results=2)
        results = index.search(query)
        
        assert len(results) <= 2
        if results:
            assert results[0].doc.element_id in ["doc1", "doc2", "doc3"]
            assert results[0].rank == 0
            assert isinstance(results[0].score, float)
        
    finally:
        # Restore original modules
        if original_sentence_transformer:
            faiss_module.SentenceTransformer = original_sentence_transformer
        if original_faiss:
            faiss_module.faiss = original_faiss
    
    print("✓ Search functionality working correctly")


def test_filter_functionality():
    """Test search filtering."""
    print("Testing search filters...")
    
    index = FAISSSummaryIndex()
    docs = create_sample_documents()
    doc = docs[0]
    
    # No filters - should pass
    query = SearchQuery(query="test")
    assert index._passes_filters(doc, query)
    
    # Element type filter - should pass
    query = SearchQuery(query="test", element_types=[ElementType.SECTION])
    assert index._passes_filters(doc, query)
    
    # Element type filter - should fail
    query = SearchQuery(query="test", element_types=[ElementType.ACT])
    assert not index._passes_filters(doc, query)
    
    # Level filter - should pass
    query = SearchQuery(query="test", min_level=1, max_level=2)
    assert index._passes_filters(doc, query)
    
    # Level filter - should fail
    query = SearchQuery(query="test", min_level=2)
    assert not index._passes_filters(doc, query)
    
    print("✓ Search filters working correctly")


def test_document_retrieval():
    """Test document retrieval by ID."""
    print("Testing document retrieval...")
    
    index = FAISSSummaryIndex()
    documents = create_sample_documents()
    
    # Before building
    doc = index.get_document_by_id("doc1")
    assert doc is None
    
    # After setting documents
    index.documents = documents
    
    doc = index.get_document_by_id("doc1")
    assert doc is not None
    assert doc.element_id == "doc1"
    
    doc = index.get_document_by_id("nonexistent")
    assert doc is None
    
    print("✓ Document retrieval working correctly")


def test_snippet_creation():
    """Test snippet creation."""
    print("Testing snippet creation...")
    
    index = FAISSSummaryIndex()
    docs = create_sample_documents()
    doc = docs[0]
    
    snippet = index._create_snippet(doc, "test query")
    expected = doc.summary[:200]
    assert snippet == expected
    
    # Test with long text
    doc_long = IndexDoc(
        element_id="test",
        title="Short title",
        official_identifier="§ 1",
        summary="A" * 300,  # Long summary
        level=1,
        element_type=ElementType.SECTION
    )
    
    snippet = index._create_snippet(doc_long, "test")
    assert len(snippet) == 203  # 200 + "..."
    assert snippet.endswith("...")
    
    print("✓ Snippet creation working correctly")


def test_save_and_load():
    """Test saving and loading index."""
    print("Testing save and load functionality...")
    
    import index.faiss as faiss_module
    
    original_sentence_transformer = getattr(faiss_module, 'SentenceTransformer', None)
    original_faiss = getattr(faiss_module, 'faiss', None)
    
    try:
        # Setup mocks
        faiss_module.SentenceTransformer = MockSentenceTransformer
        
        class MockFAISS:
            IndexFlatIP = MockFAISSIndex
            normalize_L2 = staticmethod(mock_faiss_normalize_l2)
            
            @staticmethod
            def write_index(index, path):
                # Mock write - create empty file
                Path(path).touch()
            
            @staticmethod
            def read_index(path):
                # Mock read - return mock index
                return MockFAISSIndex(384)
        
        faiss_module.faiss = MockFAISS()
        
        # Build index
        index = FAISSSummaryIndex()
        documents = create_sample_documents()
        index.build(documents)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test save before building on new index
            empty_index = FAISSSummaryIndex()
            try:
                empty_index.save(temp_dir)
                assert False, "Should raise ValueError for unbuilt index"
            except ValueError as e:
                assert "not built" in str(e)
            
            # Save built index
            index.save(temp_dir)
            
            # Verify files were created
            assert (Path(temp_dir) / "faiss_index.bin").exists()
            assert (Path(temp_dir) / "embeddings.npy").exists()
            assert (Path(temp_dir) / "documents.pkl").exists()
            assert (Path(temp_dir) / "metadata.json").exists()
            
            # Test load from nonexistent path
            try:
                new_index = FAISSSummaryIndex()
                new_index.load("/nonexistent/path")
                assert False, "Should raise FileNotFoundError"
            except FileNotFoundError:
                pass
            
            # Load from valid path
            new_index = FAISSSummaryIndex()
            new_index.load(temp_dir)
            
            # Verify loaded state
            assert len(new_index.documents) == 3
            assert new_index.embeddings is not None
            assert new_index.metadata is not None
            assert new_index.metadata.index_type == "faiss_summary"
    
    finally:
        # Restore original modules
        if original_sentence_transformer:
            faiss_module.SentenceTransformer = original_sentence_transformer
        if original_faiss:
            faiss_module.faiss = original_faiss
    
    print("✓ Save and load functionality working correctly")


def test_metadata_and_stats():
    """Test metadata and statistics."""
    print("Testing metadata and statistics...")
    
    import index.faiss as faiss_module
    
    original_sentence_transformer = getattr(faiss_module, 'SentenceTransformer', None)
    original_faiss = getattr(faiss_module, 'faiss', None)
    
    try:
        # Setup mocks
        faiss_module.SentenceTransformer = MockSentenceTransformer
        
        class MockFAISS:
            IndexFlatIP = MockFAISSIndex
            normalize_L2 = staticmethod(mock_faiss_normalize_l2)
        
        faiss_module.faiss = MockFAISS()
        
        index = FAISSSummaryIndex()
        
        # Before building
        try:
            index.get_metadata()
            assert False, "Should raise ValueError for unbuilt index"
        except ValueError as e:
            assert "not built" in str(e)
        
        stats = index.get_stats()
        assert stats == {}
        
        # After building
        documents = create_sample_documents()
        index.build(documents)
        
        metadata = index.get_metadata()
        assert metadata.index_type == "faiss_summary"
        assert metadata.document_count == 3
        assert "model_name" in metadata.metadata
        
        stats = index.get_stats()
        assert stats["document_count"] == 3
        assert stats["embedding_dimension"] == 384
        assert stats["valid_embeddings"] == 3
        assert "embedding_stats" in stats
    
    finally:
        # Restore original modules
        if original_sentence_transformer:
            faiss_module.SentenceTransformer = original_sentence_transformer
        if original_faiss:
            faiss_module.faiss = original_faiss
    
    print("✓ Metadata and statistics working correctly")


def run_all_tests():
    """Run all test functions."""
    print("=" * 60)
    print("Running FAISS Semantic Index Tests")
    print("=" * 60)
    
    test_functions = [
        test_index_initialization,
        test_embedding_text_creation,
        test_build_index_with_mocks,
        test_search_functionality,
        test_filter_functionality,
        test_document_retrieval,
        test_snippet_creation,
        test_save_and_load,
        test_metadata_and_stats
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
    
    print("=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
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
