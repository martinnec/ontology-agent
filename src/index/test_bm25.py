"""
Simple test for the BM25 Index.
This test file follows the project's testing guidelines:
- No testing library dependencies
- Simple Python script with main function
- Tests placed directly in src directory
- Named with test_ prefix
- Self-contained and runnable independently

HOW TO RUN:
From the src directory, run:
    python -m index.test_bm25

Or from the project root:
    cd src && python -m index.test_bm25

The test uses mock implementations to avoid external dependencies.
"""

import os
import tempfile
import shutil
from pathlib import Path

# Import statements using relative imports
from .domain import IndexDoc, SearchQuery, ElementType
from .bm25 import BM25SummaryIndex


def create_test_documents() -> list:
    """Create test documents for BM25 indexing."""
    return [
        IndexDoc(
            element_id="act/1",
            title="Zákon o ochraně osobních údajů",
            official_identifier="Zákon č. 110/2019 Sb.",
            summary="Zákon upravuje ochranu osobních údajů fyzických osob a stanoví práva a povinnosti při zpracování osobních údajů.",
            level=0,
            element_type=ElementType.ACT,
            act_iri="http://example.org/act/1"
        ),
        IndexDoc(
            element_id="section/1",
            title="Základní pojmy",
            official_identifier="§ 1",
            summary="Definice základních pojmů používaných v zákoně o ochraně osobních údajů, včetně definice osobních údajů, zpracování a správce.",
            summary_names=["osobní údaje", "zpracování", "správce", "definice"],
            level=1,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/1"
        ),
        IndexDoc(
            element_id="section/2",
            title="Předmět úpravy",
            official_identifier="§ 2",
            summary="Vymezení předmětu úpravy zákona, který se vztahuje na zpracování osobních údajů fyzických osob.",
            summary_names=["předmět úpravy", "fyzická osoba", "zpracování"],
            level=1,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/1"
        ),
        IndexDoc(
            element_id="section/3",
            title="Práva subjektů údajů",
            official_identifier="§ 3",
            summary="Ustanovení o právech fyzických osob, jejichž osobní údaje jsou zpracovávány, včetně práva na informace a opravu.",
            summary_names=["práva subjektů", "informace", "oprava", "fyzická osoba"],
            level=1,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/1"
        ),
        IndexDoc(
            element_id="section/4",
            title="Povinnosti správců",
            official_identifier="§ 4",
            summary="Povinnosti správců osobních údajů při zpracování, včetně zajištění bezpečnosti a oznámení porušení.",
            summary_names=["povinnosti správců", "bezpečnost", "porušení", "oznámení"],
            level=1,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/1"
        ),
        IndexDoc(
            element_id="section/5",
            title="Sankce a pokuty",
            official_identifier="§ 5",
            summary="Sankce a pokuty za porušení povinností při zpracování osobních údajů.",
            level=1,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/1"
        )
    ]


def test_bm25_index_creation():
    """Test BM25 index creation and basic functionality."""
    print("Testing BM25 index creation...")
    
    # Create test documents
    documents = create_test_documents()
    
    # Create and build index
    index = BM25SummaryIndex()
    index.build(documents)
    
    # Verify index was built
    assert index.bm25_model is not None, "BM25 model should be created"
    assert len(index.documents) == len(documents), "All documents should be stored"
    assert len(index.weighted_texts) == len(documents), "Weighted texts should be created"
    
    # Verify metadata
    metadata = index.get_metadata()
    assert metadata.document_count == len(documents)
    assert metadata.index_type == "bm25_summary"
    assert "weighted_fields" in metadata.metadata
    
    print("✓ BM25 index creation working correctly")


def test_weighted_text_creation():
    """Test weighted text creation for BM25."""
    print("Testing weighted text creation...")
    
    index = BM25SummaryIndex()
    
    # Create test document with all fields
    doc = IndexDoc(
        element_id="test/1",
        title="Test Title",
        official_identifier="§ Test",
        summary="Test summary for BM25 weighting",
        summary_names=["test concept", "weighting"],
        text_content="Full text content for testing",
        level=1,
        element_type=ElementType.SECTION
    )
    
    # Create weighted text
    weighted_text = index._create_weighted_text(doc)
    
    # Verify weighting according to new scheme:
    # summary_names: 5x, summary: 3x, title: 2x, text_content: 1x, official_identifier: 1x
    assert weighted_text.count("test concept weighting") == 5, "Summary names should appear 5 times"
    assert weighted_text.count("Test summary for BM25 weighting") == 3, "Summary should appear 3 times"
    assert weighted_text.count("Test Title") == 2, "Title should appear 2 times"
    assert weighted_text.count("Full text content for testing") == 1, "Text content should appear 1 time"
    assert weighted_text.count("§ Test") == 1, "Official ID should appear 1 time"
    
    # Test document without summary_names
    doc_no_names = IndexDoc(
        element_id="test/2",
        title="Test Title",
        official_identifier="§ Test",
        summary="Test summary for BM25 weighting",
        summary_names=None,
        level=1,
        element_type=ElementType.SECTION
    )
    
    weighted_text_no_names = index._create_weighted_text(doc_no_names)
    assert "test concept weighting" not in weighted_text_no_names, "Should not contain summary names when None"
    
    print("✓ Weighted text creation working correctly")


def test_tokenization():
    """Test Czech text tokenization."""
    print("Testing tokenization...")
    
    index = BM25SummaryIndex()
    tokenizer = index._tokenizer
    
    # Test Czech text with diacritics
    text = "Zákon č. 110/2019 Sb., o ochraně osobních údajů"
    tokens = tokenizer(text)
    
    # Should tokenize and normalize
    expected_tokens = ["zákon", "č", "110", "2019", "sb", "o", "ochraně", "osobních", "údajů"]
    
    # Check that basic tokens are present (allowing for some tokenization differences)
    assert "zákon" in tokens, "Should tokenize 'zákon'"
    assert "ochraně" in tokens, "Should preserve Czech diacritics"
    assert "osobních" in tokens, "Should tokenize 'osobních'"
    assert "údajů" in tokens, "Should tokenize 'údajů'"
    
    # Test empty and None handling
    assert tokenizer("") == []
    assert tokenizer("   ") == []
    
    print("✓ Tokenization working correctly")


def test_basic_search():
    """Test basic BM25 search functionality."""
    print("Testing basic search...")
    
    documents = create_test_documents()
    index = BM25SummaryIndex()
    index.build(documents)
    
    # Test search for "základní pojmy"
    query = SearchQuery(query="základní pojmy", max_results=5)
    results = index.search(query)
    
    assert len(results) > 0, "Should find results for 'základní pojmy'"
    
    # First result should be the "Základní pojmy" section
    top_result = results[0]
    assert "základní pojmy" in top_result.doc.title.lower(), "Top result should match title"
    assert top_result.score > 0, "Should have positive relevance score"
    assert top_result.rank == 1, "Top result should have rank 1"
    
    # Test search for "osobních údajů"
    query2 = SearchQuery(query="osobních údajů", max_results=10)
    results2 = index.search(query2)
    
    assert len(results2) > 0, "Should find results for 'osobních údajů'"
    
    # Multiple documents should match this common phrase
    assert len(results2) >= 3, "Multiple documents should contain 'osobních údajů'"
    
    print("✓ Basic search working correctly")


def test_search_filters():
    """Test search filtering functionality."""
    print("Testing search filters...")
    
    documents = create_test_documents()
    index = BM25SummaryIndex()
    index.build(documents)
    
    # Test element type filter - only sections
    query = SearchQuery(
        query="údajů",
        element_types=[ElementType.SECTION],
        max_results=10
    )
    results = index.search(query)
    
    for result in results:
        assert result.doc.element_type == ElementType.SECTION, "Should only return sections"
    
    # Test element type filter - only acts
    query_acts = SearchQuery(
        query="zákon",
        element_types=[ElementType.ACT],
        max_results=10
    )
    results_acts = index.search(query_acts)
    
    for result in results_acts:
        assert result.doc.element_type == ElementType.ACT, "Should only return acts"
    
    # Test level filter
    query_level = SearchQuery(
        query="údajů",
        min_level=1,
        max_level=1,
        max_results=10
    )
    results_level = index.search(query_level)
    
    for result in results_level:
        assert result.doc.level == 1, "Should only return level 1 documents"
    
    # Test official identifier pattern
    query_pattern = SearchQuery(
        query="údajů",
        official_identifier_pattern="^§",
        max_results=10
    )
    results_pattern = index.search(query_pattern)
    
    for result in results_pattern:
        assert result.doc.official_identifier.startswith("§"), "Should only return documents with § identifier"
    
    print("✓ Search filters working correctly")


def test_search_scoring():
    """Test that search results are properly scored and ranked."""
    print("Testing search scoring...")
    
    documents = create_test_documents()
    index = BM25SummaryIndex()
    index.build(documents)
    
    # Search for "osobních údajů" - should appear in multiple documents
    query = SearchQuery(query="osobních údajů", max_results=10)
    results = index.search(query)
    
    assert len(results) > 1, "Should find multiple results"
    
    # Check that results are ranked by score (descending)
    for i in range(len(results) - 1):
        current_score = results[i].score
        next_score = results[i + 1].score
        assert current_score >= next_score, f"Results should be ranked by score: {current_score} >= {next_score}"
    
    # Check that ranks are consecutive
    for i, result in enumerate(results):
        assert result.rank == i + 1, f"Rank should be consecutive: expected {i + 1}, got {result.rank}"
    
    # Check matched fields detection
    for result in results:
        assert len(result.matched_fields) > 0, "Should identify matched fields"
        assert isinstance(result.snippet, str), "Should provide snippet"
    
    print("✓ Search scoring working correctly")


def test_index_persistence():
    """Test saving and loading index to/from disk."""
    print("Testing index persistence...")
    
    documents = create_test_documents()
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        index_path = os.path.join(temp_dir, "test_index")
        
        # Build and save index
        index1 = BM25SummaryIndex()
        index1.build(documents)
        index1.save(index_path)
        
        # Verify files were created
        path_obj = Path(index_path)
        assert (path_obj / "bm25_model.pkl").exists(), "BM25 model file should exist"
        assert (path_obj / "documents.pkl").exists(), "Documents file should exist"
        assert (path_obj / "weighted_texts.pkl").exists(), "Weighted texts file should exist"
        assert (path_obj / "metadata.json").exists(), "Metadata file should exist"
        
        # Load index and verify
        index2 = BM25SummaryIndex()
        index2.load(index_path)
        
        # Check that loaded index has same content
        assert len(index2.documents) == len(documents), "Loaded index should have same number of documents"
        assert index2.bm25_model is not None, "Loaded index should have BM25 model"
        
        # Test that loaded index can search
        query = SearchQuery(query="základní pojmy", max_results=5)
        results = index2.search(query)
        assert len(results) > 0, "Loaded index should be able to search"
        
        # Compare metadata
        metadata1 = index1.get_metadata()
        metadata2 = index2.get_metadata()
        assert metadata1.document_count == metadata2.document_count, "Metadata should match"
        assert metadata1.index_type == metadata2.index_type, "Index type should match"
    
    print("✓ Index persistence working correctly")


def test_index_statistics():
    """Test index statistics calculation."""
    print("Testing index statistics...")
    
    documents = create_test_documents()
    index = BM25SummaryIndex()
    index.build(documents)
    
    stats = index.get_stats()
    
    # Check basic statistics
    assert stats["document_count"] == len(documents), "Document count should match"
    assert stats["vocabulary_size"] > 0, "Should have vocabulary"
    assert stats["total_tokens"] > 0, "Should have tokens"
    assert stats["average_document_length"] > 0, "Should have average document length"
    
    # Check BM25 parameters
    assert "bm25_params" in stats, "Should include BM25 parameters"
    assert "k1" in stats["bm25_params"], "Should include k1 parameter"
    assert "b" in stats["bm25_params"], "Should include b parameter"
    
    print("✓ Index statistics working correctly")


def test_empty_query_handling():
    """Test handling of empty queries and edge cases."""
    print("Testing empty query handling...")
    
    documents = create_test_documents()
    index = BM25SummaryIndex()
    index.build(documents)
    
    # Test empty query
    query = SearchQuery(query="", max_results=5)
    results = index.search(query)
    assert len(results) == 0, "Empty query should return no results"
    
    # Test query with only whitespace
    query_whitespace = SearchQuery(query="   ", max_results=5)
    results_whitespace = index.search(query_whitespace)
    assert len(results_whitespace) == 0, "Whitespace-only query should return no results"
    
    # Test query with no matches
    query_nomatch = SearchQuery(query="xyzabc123nonexistent", max_results=5)
    results_nomatch = index.search(query_nomatch)
    assert len(results_nomatch) == 0, "Query with no matches should return no results"
    
    print("✓ Empty query handling working correctly")


def test_summary_names_functionality():
    """Test that summary_names are properly indexed and weighted."""
    print("Testing summary_names functionality...")
    
    # Create test documents with and without summary_names
    doc_with_names = IndexDoc(
        element_id="test/with_names",
        title="Document with concept names",
        official_identifier="§ 1",
        summary="This document defines legal obligations and compliance requirements.",
        summary_names=["legal obligation", "compliance requirement", "penalty", "enforcement"],
        level=1,
        element_type=ElementType.SECTION,
        act_iri="http://example.org/act/1"
    )
    
    doc_without_names = IndexDoc(
        element_id="test/without_names",
        title="Document without concept names",
        official_identifier="§ 2",
        summary="This document also discusses legal obligations and compliance requirements.",
        summary_names=None,
        level=1,
        element_type=ElementType.SECTION,
        act_iri="http://example.org/act/1"
    )
    
    # Build index
    index = BM25SummaryIndex()
    index.build([doc_with_names, doc_without_names])
    
    # Test weighted text creation with summary_names
    weighted_text_with_names = index._create_weighted_text(doc_with_names)
    weighted_text_without_names = index._create_weighted_text(doc_without_names)
    
    # Verify that summary_names appear with weight 5
    summary_names_text = "legal obligation compliance requirement penalty enforcement"
    assert weighted_text_with_names.count(summary_names_text) == 5, "Summary names should appear 5 times"
    
    # Verify that document without summary_names doesn't contain the weighted concept names
    assert summary_names_text not in weighted_text_without_names, "Document without summary_names should not contain weighted concept names"
    
    # Test search - document with summary_names should rank higher for concept queries
    query = SearchQuery(query="legal obligation", max_results=10)
    results = index.search(query)
    
    assert len(results) >= 1, "Should find at least one result"
    
    # The document with summary_names should rank higher due to higher weight
    if len(results) == 2:
        # Both documents should be found, but the one with summary_names should rank higher
        assert results[0].doc.element_id == "test/with_names", "Document with summary_names should rank higher"
        assert results[0].score > results[1].score, "Document with summary_names should have higher score"
    
    # Test that summary_names appear in matched fields
    for result in results:
        if result.doc.element_id == "test/with_names":
            assert "summary_names" in result.matched_fields, "summary_names should be in matched fields"
    
    print(f"Search results for 'legal obligation': {len(results)} documents found")
    for i, result in enumerate(results):
        print(f"  {i+1}. {result.doc.element_id} (score: {result.score:.3f}, fields: {result.matched_fields})")
    
    print("✓ Summary names functionality working correctly")


def run_all_tests():
    """Run all test functions."""
    print("=" * 50)
    print("Running BM25 Index Tests")
    print("=" * 50)
    
    test_functions = [
        test_bm25_index_creation,
        test_weighted_text_creation,
        test_tokenization,
        test_basic_search,
        test_search_filters,
        test_search_scoring,
        test_index_persistence,
        test_index_statistics,
        test_empty_query_handling,
        test_summary_names_functionality
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
