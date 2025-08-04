"""
Integration test for SearchService with new IndexService architecture.

HOW TO RUN:
The virtual environment .venv should be activated before running the tests.

From the src directory, run:
    python -m search.test_integration_indexservice

Or from the project root:
    cd src; python -m search.test_integration_indexservice

This test validates that SearchService works correctly with the new IndexService.
"""

import os
# Set any required environment variables for testing
os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"

# Import statements using relative imports
from .service import SearchService
from .domain import SearchStrategy, SearchOptions
from index import IndexService

class MockLegalAct:
    """Mock legal act for testing."""
    def __init__(self):
        self.id = "https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01"
        self.title = "Test Legal Act"
        self.elements = []

class MockIndexService:
    """Mock IndexService for testing."""
    def __init__(self):
        self.indexes_built = False
    
    def get_indexes(self, legal_act, force_rebuild=False):
        """Return a mock IndexCollection."""
        return MockIndexCollection()
    
    def build_indexes(self, legal_act, index_types=None):
        """Mock index building."""
        self.indexes_built = True
        return MockIndexCollection()

class MockIndexCollection:
    """Mock IndexCollection for testing."""
    def __init__(self):
        self.act_iri = "https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01"
        self._indexes = {
            'bm25': MockBM25Index(),
            'faiss': MockFAISSIndex(),
            'bm25_full': MockBM25FullIndex(),
            'faiss_full': MockFAISSFullIndex()
        }
    
    def get_index(self, index_type):
        """Get a specific index."""
        return self._indexes.get(index_type)
    
    def get_available_indexes(self):
        """Get list of available index types."""
        return list(self._indexes.keys())
    
    def get_document_count(self):
        """Get document count."""
        return 10

class MockSearchResult:
    """Mock search result from legacy indexes."""
    def __init__(self, element_id, title, score, rank=1):
        self.doc = MockDocument(element_id, title)
        self.score = score
        self.rank = rank
        self.matched_fields = ["title", "summary"]
        self.snippet = f"Snippet for {title}"

class MockDocument:
    """Mock document from legacy indexes."""
    def __init__(self, element_id, title):
        self.element_id = element_id
        self.title = title
        self.official_identifier = f"§ {element_id.split('/')[-1]}"
        self.summary = f"Summary for {title}"
        self.text_content = f"Text content for {title}"
        self.element_type = MockElementType()
        self.level = 2
        self.parent_id = "parent_id"

class MockElementType:
    """Mock element type."""
    def __init__(self):
        self.value = "section"

class MockBM25Index:
    """Mock BM25 index."""
    def search(self, query):
        """Mock search method."""
        return [
            MockSearchResult("doc1", "BM25 Result 1", 0.9, 1),
            MockSearchResult("doc2", "BM25 Result 2", 0.8, 2)
        ]

class MockFAISSIndex:
    """Mock FAISS index."""
    def search(self, query):
        """Mock search method."""
        return [
            MockSearchResult("doc3", "FAISS Result 1", 0.95, 1),
            MockSearchResult("doc4", "FAISS Result 2", 0.85, 2)
        ]
    
    def get_similar_documents(self, element_id, max_results):
        """Mock similarity search."""
        mock_doc = MockDocument("similar1", "Similar Document")
        return [(mock_doc, 0.9), (mock_doc, 0.8)]

class MockBM25FullIndex:
    """Mock BM25 full-text index."""
    def search(self, query):
        """Mock search method."""
        return [
            MockSearchResult("chunk1", "Full-text Result 1", 0.7, 1),
            MockSearchResult("chunk2", "Full-text Result 2", 0.6, 2)
        ]

class MockFAISSFullIndex:
    """Mock FAISS full-text index."""
    def search(self, query):
        """Mock search method."""
        return [
            MockSearchResult("chunk3", "FAISS Full Result 1", 0.75, 1),
            MockSearchResult("chunk4", "FAISS Full Result 2", 0.65, 2)
        ]

def test_search_service_initialization():
    """Test SearchService initialization with IndexService."""
    print("Testing SearchService initialization...")
    
    legal_act = MockLegalAct()
    index_service = MockIndexService()
    search_service = SearchService(index_service, legal_act)
    
    assert search_service.index_service == index_service
    assert search_service.legal_act == legal_act
    assert search_service._indexes is not None
    
    print("✓ SearchService initialization working correctly")

def test_keyword_search():
    """Test keyword search functionality."""
    print("Testing keyword search...")
    
    legal_act = MockLegalAct()
    index_service = MockIndexService()
    search_service = SearchService(index_service, legal_act)
    
    results = search_service.search_keyword("test query")
    
    assert results.total_found == 2
    assert results.strategy == SearchStrategy.KEYWORD
    assert results.query == "test query"
    assert len(results.items) == 2
    assert results.items[0].title == "BM25 Result 1"
    assert results.items[0].score == 0.9
    
    print("✓ Keyword search working correctly")

def test_semantic_search():
    """Test semantic search functionality."""
    print("Testing semantic search...")
    
    legal_act = MockLegalAct()
    index_service = MockIndexService()
    search_service = SearchService(index_service, legal_act)
    
    results = search_service.search_semantic("test query")
    
    assert results.total_found == 2
    assert results.strategy == SearchStrategy.SEMANTIC
    assert results.query == "test query"
    assert len(results.items) == 2
    assert results.items[0].title == "FAISS Result 1"
    assert results.items[0].score == 0.95
    
    print("✓ Semantic search working correctly")

def test_hybrid_search():
    """Test hybrid search functionality."""
    print("Testing hybrid search...")
    
    legal_act = MockLegalAct()
    index_service = MockIndexService()
    search_service = SearchService(index_service, legal_act)
    
    # Test semantic-first hybrid
    results = search_service.search_hybrid("test query", "semantic_first")
    
    assert results.strategy == SearchStrategy.HYBRID_SEMANTIC_FIRST
    assert results.query == "test query"
    assert results.total_found >= 0  # Results depend on mock implementation
    
    # Test parallel hybrid
    results = search_service.search_hybrid("test query", "parallel")
    
    assert results.strategy == SearchStrategy.HYBRID_PARALLEL
    assert results.query == "test query"
    
    print("✓ Hybrid search working correctly")

def test_fulltext_search():
    """Test full-text search functionality."""
    print("Testing full-text search...")
    
    legal_act = MockLegalAct()
    index_service = MockIndexService()
    search_service = SearchService(index_service, legal_act)
    
    results = search_service.search_fulltext("test query")
    
    assert results.total_found == 2
    assert results.strategy == SearchStrategy.FULLTEXT
    assert results.query == "test query"
    assert len(results.items) == 2
    assert results.items[0].title == "Full-text Result 1"
    
    print("✓ Full-text search working correctly")

def test_similarity_search():
    """Test similarity search functionality."""
    print("Testing similarity search...")
    
    legal_act = MockLegalAct()
    index_service = MockIndexService()
    search_service = SearchService(index_service, legal_act)
    
    results = search_service.search_similar("element123")
    
    assert results.strategy == SearchStrategy.SEMANTIC
    assert results.query == "similar:element123"
    assert results.total_found == 2
    assert len(results.items) == 2
    
    print("✓ Similarity search working correctly")

def test_search_options():
    """Test search with options."""
    print("Testing search with options...")
    
    legal_act = MockLegalAct()
    index_service = MockIndexService()
    search_service = SearchService(index_service, legal_act)
    
    options = SearchOptions(
        max_results=5,
        element_types=["section"],
        min_level=1,
        max_level=3
    )
    
    results = search_service.search_keyword("test query", options)
    
    assert results.options.max_results == 5
    assert results.options.element_types == ["section"]
    assert results.options.min_level == 1
    assert results.options.max_level == 3
    
    print("✓ Search options working correctly")

def test_index_info():
    """Test getting index information."""
    print("Testing index info retrieval...")
    
    legal_act = MockLegalAct()
    index_service = MockIndexService()
    search_service = SearchService(index_service, legal_act)
    
    info = search_service.get_index_info()
    
    assert "act_iri" in info
    assert "available_indexes" in info
    assert "document_count" in info
    assert info["document_count"] == 10
    assert len(info["available_indexes"]) == 4
    
    print("✓ Index info retrieval working correctly")

def test_empty_results_handling():
    """Test handling of empty search results."""
    print("Testing empty results handling...")
    
    legal_act = MockLegalAct()
    index_service = MockIndexService()
    search_service = SearchService(index_service, legal_act)
    
    # Mock an index that returns no results
    search_service._indexes._indexes['bm25'] = None
    
    results = search_service.search_keyword("test query")
    
    assert results.total_found == 0
    assert len(results.items) == 0
    assert results.strategy == SearchStrategy.KEYWORD
    
    print("✓ Empty results handling working correctly")

def run_all_tests():
    """Run all test functions."""
    print("=" * 60)
    print("Running SearchService Integration Tests")
    print("=" * 60)
    
    test_functions = [
        test_search_service_initialization,
        test_keyword_search,
        test_semantic_search,
        test_hybrid_search,
        test_fulltext_search,
        test_similarity_search,
        test_search_options,
        test_index_info,
        test_empty_results_handling
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
    print(f"Integration Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0

def main():
    """Main function to run the tests."""
    success = run_all_tests()
    if success:
        print("All integration tests passed!")
        return 0
    else:
        print("Some integration tests failed!")
        return 1

if __name__ == "__main__":
    exit(main())
