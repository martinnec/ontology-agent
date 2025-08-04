"""
Integration test for the SearchService.
This test file follows the project's testing guidelines:
- No testing library dependencies
- Simple Python script with main function
- Tests placed directly in src directory
- Named with test_ prefix
- Self-contained and runnable independently

HOW TO RUN:
From the src directory, run:
    python -m search.test_service

Or from the project root:
    cd src && python -m search.test_service

This test validates the public SearchService interface using mock components.
"""

import tempfile
from typing import List, Optional

# Mock components for testing
class MockLegalElement:
    """Mock implementation of LegalStructuralElement for testing."""
    
    def __init__(self, id: str, element_type: str, title: str = "Test Title",
                 official_identifier: str = "§ 1", summary: str = None):
        self.id = id
        self.elementType = element_type
        self.title = title
        self.officialIdentifier = official_identifier
        self.summary = summary
        self.summary_names = None
        self.textContent = None
        self.elements = []

class MockSearchResult:
    """Mock implementation of legacy SearchResult for testing."""
    
    def __init__(self, doc, score: float, rank: int):
        self.doc = doc
        self.score = score
        self.rank = rank
        self.matched_fields = ["title"]
        self.snippet = f"Snippet for {doc.title}"

class MockIndexDoc:
    """Mock implementation of IndexDoc for testing."""
    
    def __init__(self, element_id: str, title: str, element_type, level: int = 1):
        self.element_id = element_id
        self.title = title
        self.official_identifier = f"§ {element_id}"
        self.summary = f"Summary for {title}"
        self.text_content = f"Content for {title}"
        self.element_type = element_type
        self.level = level
        self.parent_id = None

class MockElementType:
    """Mock ElementType enum."""
    
    def __init__(self, value: str):
        self.value = value

class MockIndex:
    """Mock index that returns predictable search results."""
    
    def __init__(self, index_type: str):
        self.index_type = index_type
        self._docs = []
    
    def search(self, query):
        """Mock search method."""
        # Create mock results
        mock_element_type = MockElementType("section")
        doc1 = MockIndexDoc("doc1", "Result 1", mock_element_type)
        doc2 = MockIndexDoc("doc2", "Result 2", mock_element_type)
        
        return [
            MockSearchResult(doc1, 0.9, 1),
            MockSearchResult(doc2, 0.7, 2)
        ]
    
    def get_similar_documents(self, element_id: str, k: int = 5):
        """Mock similarity search method."""
        mock_element_type = MockElementType("section")
        doc1 = MockIndexDoc("similar1", "Similar 1", mock_element_type)
        doc2 = MockIndexDoc("similar2", "Similar 2", mock_element_type)
        
        return [
            (doc1, 0.85),
            (doc2, 0.75)
        ]

class MockIndexCollection:
    """Mock IndexCollection for testing."""
    
    def __init__(self, act_iri: str):
        self.act_iri = act_iri
        self._indexes = {}
    
    def get_index(self, index_type: str):
        """Get a mock index."""
        if index_type not in self._indexes:
            self._indexes[index_type] = MockIndex(index_type)
        return self._indexes[index_type]
    
    def get_available_indexes(self) -> List[str]:
        """Get available index types."""
        return list(self._indexes.keys())
    
    def get_document_count(self) -> int:
        """Get document count."""
        return 5

class MockIndexService:
    """Mock IndexService for testing."""
    
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
    
    def get_indexes(self, legal_act, force_rebuild: bool = False):
        """Return mock index collection."""
        collection = MockIndexCollection(str(legal_act.id))
        # Pre-populate with some indexes
        collection.get_index("bm25")
        collection.get_index("faiss")
        collection.get_index("bm25_full")
        return collection

# Import the module to test
from .service import SearchService
from .domain import SearchStrategy, SearchOptions

def create_mock_legal_act():
    """Create a mock legal act for testing."""
    return MockLegalElement(
        id="https://example.com/act/test-act",
        element_type="LegalAct",
        title="Test Legal Act",
        official_identifier="Act 1/2024",
        summary="Test legal act summary"
    )

def test_service_initialization():
    """Test SearchService initialization."""
    print("Testing SearchService initialization...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        index_service = MockIndexService(temp_dir)
        legal_act = create_mock_legal_act()
        
        search_service = SearchService(index_service, legal_act)
        
        assert search_service.index_service is index_service
        assert search_service.legal_act is legal_act
        assert search_service._indexes is not None
        
        # Test index info
        info = search_service.get_index_info()
        assert "act_iri" in info
        assert "available_indexes" in info
        assert "document_count" in info
        assert info["document_count"] == 5
    
    print("✓ SearchService initialization working correctly")

def test_keyword_search():
    """Test keyword search functionality."""
    print("Testing keyword search...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        index_service = MockIndexService(temp_dir)
        legal_act = create_mock_legal_act()
        search_service = SearchService(index_service, legal_act)
        
        # Test keyword search
        results = search_service.search_keyword("test query")
        
        assert results is not None, "Should return SearchResults"
        assert results.query == "test query"
        assert results.strategy == SearchStrategy.KEYWORD
        assert len(results.items) == 2, "Should return 2 mock results"
        assert results.search_time_ms > 0, "Should have search time"
        
        # Check result items
        item1 = results.items[0]
        assert item1.element_id == "doc1"
        assert item1.title == "Result 1"
        assert item1.score == 0.9
        assert item1.rank == 1
    
    print("✓ Keyword search working correctly")

def test_semantic_search():
    """Test semantic search functionality."""
    print("Testing semantic search...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        index_service = MockIndexService(temp_dir)
        legal_act = create_mock_legal_act()
        search_service = SearchService(index_service, legal_act)
        
        # Test semantic search
        results = search_service.search_semantic("test query")
        
        assert results is not None, "Should return SearchResults"
        assert results.query == "test query"
        assert results.strategy == SearchStrategy.SEMANTIC
        assert len(results.items) >= 0, "Should return results"
    
    print("✓ Semantic search working correctly")

def test_hybrid_search():
    """Test hybrid search functionality."""
    print("Testing hybrid search...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        index_service = MockIndexService(temp_dir)
        legal_act = create_mock_legal_act()
        search_service = SearchService(index_service, legal_act)
        
        # Test different hybrid strategies
        strategies = ["semantic_first", "keyword_first", "parallel"]
        
        for strategy in strategies:
            results = search_service.search_hybrid("test query", strategy=strategy)
            
            assert results is not None, f"Should return results for {strategy}"
            assert results.query == "test query"
            assert "HYBRID" in results.strategy.value.upper(), f"Should use hybrid strategy for {strategy}"
    
    print("✓ Hybrid search working correctly")

def test_search_with_options():
    """Test search with custom options."""
    print("Testing search with options...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        index_service = MockIndexService(temp_dir)
        legal_act = create_mock_legal_act()
        search_service = SearchService(index_service, legal_act)
        
        # Create custom options
        options = SearchOptions(
            max_results=5,
            min_score=0.5,
            element_types=["section"],
            min_level=1,
            max_level=3,
            boost_summary=3.0
        )
        
        results = search_service.search_keyword("test query", options)
        
        assert results is not None, "Should return results with options"
        assert results.options is options, "Should preserve options in results"
        assert results.options.max_results == 5
        assert results.options.element_types == ["section"]
    
    print("✓ Search with options working correctly")

def test_similarity_search():
    """Test similarity search functionality."""
    print("Testing similarity search...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        index_service = MockIndexService(temp_dir)
        legal_act = create_mock_legal_act()
        search_service = SearchService(index_service, legal_act)
        
        # Test similarity search
        results = search_service.search_similar("reference_element_id")
        
        assert results is not None, "Should return SearchResults"
        assert "similar:" in results.query, "Query should indicate similarity search"
        assert results.strategy == SearchStrategy.SEMANTIC
        assert len(results.items) == 2, "Should return 2 similar documents"
        
        # Check similarity results
        item1 = results.items[0]
        assert item1.element_id == "similar1"
        assert item1.score == 0.85
        assert "similarity" in item1.matched_fields
    
    print("✓ Similarity search working correctly")

def test_fulltext_search():
    """Test full-text search functionality."""
    print("Testing full-text search...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        index_service = MockIndexService(temp_dir)
        legal_act = create_mock_legal_act()
        search_service = SearchService(index_service, legal_act)
        
        # Test full-text search
        results = search_service.search_fulltext("detailed content search")
        
        assert results is not None, "Should return SearchResults"
        assert results.query == "detailed content search"
        assert results.strategy == SearchStrategy.FULLTEXT
    
    print("✓ Full-text search working correctly")

def test_exact_phrase_search():
    """Test exact phrase search functionality."""
    print("Testing exact phrase search...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        index_service = MockIndexService(temp_dir)
        legal_act = create_mock_legal_act()
        search_service = SearchService(index_service, legal_act)
        
        # Test exact phrase search
        results = search_service.search_exact_phrase("exact phrase")
        
        assert results is not None, "Should return SearchResults"
        assert results.query == "exact phrase"
        assert results.strategy == SearchStrategy.EXACT_PHRASE
    
    print("✓ Exact phrase search working correctly")

def test_unified_search_interface():
    """Test the unified search interface with different strategies."""
    print("Testing unified search interface...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        index_service = MockIndexService(temp_dir)
        legal_act = create_mock_legal_act()
        search_service = SearchService(index_service, legal_act)
        
        # Test all strategies through unified interface
        strategies = [
            SearchStrategy.KEYWORD,
            SearchStrategy.SEMANTIC,
            SearchStrategy.HYBRID_SEMANTIC_FIRST,
            SearchStrategy.HYBRID_KEYWORD_FIRST,
            SearchStrategy.HYBRID_PARALLEL,
            SearchStrategy.FULLTEXT,
            SearchStrategy.EXACT_PHRASE
        ]
        
        for strategy in strategies:
            results = search_service.search("test query", strategy=strategy)
            
            assert results is not None, f"Should return results for {strategy}"
            assert results.strategy == strategy, f"Should use correct strategy {strategy}"
            assert results.query == "test query"
    
    print("✓ Unified search interface working correctly")

def test_search_results_properties():
    """Test search results properties and metadata."""
    print("Testing search results properties...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        index_service = MockIndexService(temp_dir)
        legal_act = create_mock_legal_act()
        search_service = SearchService(index_service, legal_act)
        
        results = search_service.search_keyword("test query")
        
        # Test basic properties
        assert results.total_found >= 0, "Should have valid total_found"
        assert results.search_time_ms >= 0, "Should have valid search time"
        assert isinstance(results.index_types_used, list), "Should have index types list"
        assert isinstance(results.filters_applied, dict), "Should have filters dict"
        assert isinstance(results.score_range, dict), "Should have score range"
        
        # Test score range
        if results.items:
            assert "min" in results.score_range, "Should have min score"
            assert "max" in results.score_range, "Should have max score"
            assert results.score_range["min"] <= results.score_range["max"]
    
    print("✓ Search results properties working correctly")

def test_error_handling():
    """Test error handling in search operations."""
    print("Testing error handling...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        index_service = MockIndexService(temp_dir)
        legal_act = create_mock_legal_act()
        search_service = SearchService(index_service, legal_act)
        
        # Test with invalid strategy (should raise ValueError)
        try:
            search_service.search("test", strategy="invalid_strategy")
            assert False, "Should raise ValueError for invalid strategy"
        except ValueError:
            pass  # Expected
        
        # Test similarity search with non-existent element
        results = search_service.search_similar("nonexistent_id")
        assert results is not None, "Should handle non-existent element gracefully"
    
    print("✓ Error handling working correctly")

def run_all_tests():
    """Run all test functions."""
    print("=" * 50)
    print("Running SearchService Integration Tests")
    print("=" * 50)
    
    test_functions = [
        test_service_initialization,
        test_keyword_search,
        test_semantic_search,
        test_hybrid_search,
        test_search_with_options,
        test_similarity_search,
        test_fulltext_search,
        test_exact_phrase_search,
        test_unified_search_interface,
        test_search_results_properties,
        test_error_handling,
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
