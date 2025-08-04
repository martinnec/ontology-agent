"""
Unit test for the search domain models.

HOW TO RUN:
From the src directory, run:
    python -m search.test_domain

Or from the project root:
    cd src; python -m search.test_domain

The test validates search domain models functionality.
"""

# Import the module to test
from .domain import (
    SearchStrategy, SearchOptions, SearchResultItem, SearchResults
)

def test_search_strategy_enum():
    """Test SearchStrategy enumeration."""
    print("Testing SearchStrategy enum...")
    
    # Test all enum values
    strategies = [
        SearchStrategy.KEYWORD,
        SearchStrategy.SEMANTIC,
        SearchStrategy.HYBRID_SEMANTIC_FIRST,
        SearchStrategy.HYBRID_KEYWORD_FIRST,
        SearchStrategy.HYBRID_PARALLEL,
        SearchStrategy.FULLTEXT,
        SearchStrategy.EXACT_PHRASE
    ]
    
    expected_values = [
        "keyword",
        "semantic", 
        "hybrid_semantic_first",
        "hybrid_keyword_first",
        "hybrid_parallel",
        "fulltext",
        "exact_phrase"
    ]
    
    for strategy, expected in zip(strategies, expected_values):
        assert strategy.value == expected, f"Expected {expected}, got {strategy.value}"
    
    print("✓ SearchStrategy enum working correctly")

def test_search_options_defaults():
    """Test SearchOptions default values."""
    print("Testing SearchOptions defaults...")
    
    options = SearchOptions()
    
    # Test default values
    assert options.max_results == 10, f"Expected max_results=10, got {options.max_results}"
    assert options.min_score == 0.0, f"Expected min_score=0.0, got {options.min_score}"
    assert options.element_types is None, f"Expected element_types=None, got {options.element_types}"
    assert options.min_level is None, f"Expected min_level=None, got {options.min_level}"
    assert options.max_level is None, f"Expected max_level=None, got {options.max_level}"
    assert options.parent_id is None, f"Expected parent_id=None, got {options.parent_id}"
    assert options.include_content is True, f"Expected include_content=True, got {options.include_content}"
    assert options.boost_summary == 2.0, f"Expected boost_summary=2.0, got {options.boost_summary}"
    assert options.boost_title == 1.5, f"Expected boost_title=1.5, got {options.boost_title}"
    assert options.hybrid_alpha == 0.5, f"Expected hybrid_alpha=0.5, got {options.hybrid_alpha}"
    assert options.rerank_count == 50, f"Expected rerank_count=50, got {options.rerank_count}"
    assert options.chunk_overlap is True, f"Expected chunk_overlap=True, got {options.chunk_overlap}"
    assert options.chunk_size == 500, f"Expected chunk_size=500, got {options.chunk_size}"
    
    print("✓ SearchOptions defaults working correctly")

def test_search_options_custom():
    """Test SearchOptions with custom values."""
    print("Testing SearchOptions with custom values...")
    
    options = SearchOptions(
        max_results=20,
        min_score=0.5,
        element_types=["section", "chapter"],
        min_level=1,
        max_level=3,
        parent_id="parent123",
        include_content=False,
        boost_summary=3.0,
        boost_title=2.0,
        hybrid_alpha=0.7,
        rerank_count=100,
        chunk_overlap=False,
        chunk_size=1000
    )
    
    # Verify custom values
    assert options.max_results == 20
    assert options.min_score == 0.5
    assert options.element_types == ["section", "chapter"]
    assert options.min_level == 1
    assert options.max_level == 3
    assert options.parent_id == "parent123"
    assert options.include_content is False
    assert options.boost_summary == 3.0
    assert options.boost_title == 2.0
    assert options.hybrid_alpha == 0.7
    assert options.rerank_count == 100
    assert options.chunk_overlap is False
    assert options.chunk_size == 1000
    
    print("✓ SearchOptions with custom values working correctly")

def test_search_result_item():
    """Test SearchResultItem creation and properties."""
    print("Testing SearchResultItem...")
    
    item = SearchResultItem(
        element_id="elem123",
        title="Test Title",
        official_identifier="§ 1",
        summary="Test summary",
        text_content="Test content",
        score=0.85,
        rank=1,
        element_type="section",
        level=2,
        parent_id="parent123",
        matched_fields=["title", "summary"],
        highlighted_text="Test <mark>highlighted</mark> text",
        chunk_info={"start": 0, "end": 100}
    )
    
    # Verify all properties
    assert item.element_id == "elem123"
    assert item.title == "Test Title"
    assert item.official_identifier == "§ 1"
    assert item.summary == "Test summary"
    assert item.text_content == "Test content"
    assert item.score == 0.85
    assert item.rank == 1
    assert item.element_type == "section"
    assert item.level == 2
    assert item.parent_id == "parent123"
    assert item.matched_fields == ["title", "summary"]
    assert item.highlighted_text == "Test <mark>highlighted</mark> text"
    assert item.chunk_info == {"start": 0, "end": 100}
    
    print("✓ SearchResultItem working correctly")

def test_search_results_creation():
    """Test SearchResults creation and basic properties."""
    print("Testing SearchResults creation...")
    
    options = SearchOptions(max_results=10)
    
    # Create some result items
    items = [
        SearchResultItem(
            element_id=f"elem{i}",
            title=f"Title {i}",
            official_identifier=f"§ {i}",
            score=1.0 - i * 0.1,
            rank=i + 1,
            element_type="section",
            level=1
        )
        for i in range(3)
    ]
    
    results = SearchResults(
        query="test query",
        strategy=SearchStrategy.KEYWORD,
        options=options,
        items=items,
        total_found=3,
        search_time_ms=50.5,
        index_types_used=["bm25"],
        filters_applied={"element_types": ["section"]},
        score_range={"min": 0.8, "max": 1.0}
    )
    
    # Verify properties
    assert results.query == "test query"
    assert results.strategy == SearchStrategy.KEYWORD
    assert results.options is options
    assert len(results.items) == 3
    assert results.total_found == 3
    assert results.search_time_ms == 50.5
    assert results.index_types_used == ["bm25"]
    assert results.filters_applied == {"element_types": ["section"]}
    assert results.score_range == {"min": 0.8, "max": 1.0}
    
    print("✓ SearchResults creation working correctly")

def test_search_results_methods():
    """Test SearchResults utility methods."""
    print("Testing SearchResults methods...")
    
    options = SearchOptions()
    
    # Create test items
    items = [
        SearchResultItem(
            element_id=f"elem{i}",
            title=f"Title {i}",
            official_identifier=f"§ {i}",
            score=1.0 - i * 0.1,
            rank=i + 1,
            element_type="section" if i < 2 else "chapter",
            level=1
        )
        for i in range(5)
    ]
    
    results = SearchResults(
        query="test query",
        strategy=SearchStrategy.KEYWORD,
        options=options,
        items=items,
        total_found=5,
        search_time_ms=50.5
    )
    
    # Test get_top_results
    top_3 = results.get_top_results(3)
    assert len(top_3) == 3, "Should return top 3 results"
    assert top_3[0].rank == 1, "First item should have rank 1"
    assert top_3[2].rank == 3, "Third item should have rank 3"
    
    # Test filter_by_element_type
    section_results = results.filter_by_element_type("section")
    assert len(section_results.items) == 2, "Should have 2 section results"
    for item in section_results.items:
        assert item.element_type == "section", "All items should be sections"
    
    # Test filter_by_score
    high_score_results = results.filter_by_score(0.85)
    assert len(high_score_results.items) == 2, "Should have 2 high-score results"
    for item in high_score_results.items:
        assert item.score >= 0.85, "All items should have score >= 0.85"
    
    # Test len and bool
    assert len(results) == 5, "Length should be 5"
    assert bool(results) is True, "Should be truthy with results"
    
    empty_results = SearchResults(
        query="empty",
        strategy=SearchStrategy.KEYWORD,
        options=options,
        items=[],
        total_found=0,
        search_time_ms=10.0
    )
    assert len(empty_results) == 0, "Empty results length should be 0"
    assert bool(empty_results) is False, "Empty results should be falsy"
    
    print("✓ SearchResults methods working correctly")

def test_search_results_score_range_calculation():
    """Test score range calculation in SearchResults methods."""
    print("Testing score range calculation...")
    
    options = SearchOptions()
    
    # Create items with varying scores
    items = [
        SearchResultItem(
            element_id="elem1",
            title="Title 1",
            official_identifier="§ 1",
            score=0.9,
            rank=1,
            element_type="section",
            level=1
        ),
        SearchResultItem(
            element_id="elem2",
            title="Title 2", 
            official_identifier="§ 2",
            score=0.3,
            rank=2,
            element_type="section",
            level=1
        ),
        SearchResultItem(
            element_id="elem3",
            title="Title 3",
            official_identifier="§ 3",
            score=0.6,
            rank=3,
            element_type="chapter",
            level=1
        )
    ]
    
    results = SearchResults(
        query="test",
        strategy=SearchStrategy.KEYWORD,
        options=options,
        items=items,
        total_found=3,
        search_time_ms=50.0
    )
    
    # Test filter by score updates score range
    filtered = results.filter_by_score(0.5)
    assert len(filtered.items) == 2, "Should have 2 items with score >= 0.5"
    assert filtered.score_range["min"] == 0.6, "Min score should be 0.6"
    assert filtered.score_range["max"] == 0.9, "Max score should be 0.9"
    
    # Test empty filter
    empty_filtered = results.filter_by_score(1.5)
    assert len(empty_filtered.items) == 0, "Should have no items with score >= 1.5"
    assert empty_filtered.score_range["min"] == 0.0, "Empty min score should be 0.0"
    assert empty_filtered.score_range["max"] == 0.0, "Empty max score should be 0.0"
    
    print("✓ Score range calculation working correctly")

def run_all_tests():
    """Run all test functions."""
    print("=" * 50)
    print("Running Search Domain Tests")
    print("=" * 50)
    
    test_functions = [
        test_search_strategy_enum,
        test_search_options_defaults,
        test_search_options_custom,
        test_search_result_item,
        test_search_results_creation,
        test_search_results_methods,
        test_search_results_score_range_calculation,
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
