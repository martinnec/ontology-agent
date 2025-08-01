"""
Simple test for the Index Domain.
This test file follows the project's testing guidelines:
- No testing library dependencies
- Simple Python script with main function
- Tests placed directly in src directory
- Named with test_ prefix
- Self-contained and runnable independently

HOW TO RUN:
From the src directory, run:
    python -m index.test_domain

Or from the project root:
    cd src && python -m index.test_domain

The test uses mock implementations to avoid external dependencies.
"""

import os
from typing import List, Optional

# Import statements using relative imports
from .domain import IndexDoc, ElementType, SearchQuery, SearchResult, IndexMetadata
from .builder import DocumentExtractor


class MockLegalElement:
    """Mock implementation of LegalStructuralElement for testing."""
    
    def __init__(self, 
                 id: str,
                 title: str,
                 officialIdentifier: str,
                 summary: Optional[str] = None,
                 textContent: Optional[str] = None,
                 elements: Optional[List['MockLegalElement']] = None):
        self.id = id
        self.title = title
        self.officialIdentifier = officialIdentifier
        self.summary = summary
        self.textContent = textContent
        self.elements = elements or []


class MockLegalAct(MockLegalElement):
    """Mock implementation of LegalAct for testing."""
    pass


def test_index_doc_creation():
    """Test IndexDoc creation from mock legal element."""
    print("Testing IndexDoc creation...")
    
    # Create mock legal element
    mock_element = MockLegalElement(
        id="http://example.org/act/1/section/1",
        title="Základní pojmy",
        officialIdentifier="§ 1",
        summary="Definice základních pojmů používaných v tomto zákoně.",
        textContent="Pro účely tohoto zákona se rozumí: a) osobou..."
    )
    
    # Create IndexDoc
    doc = IndexDoc.from_legal_element(
        legal_element=mock_element,
        level=1,
        element_type=ElementType.SECTION,
        parent_id="http://example.org/act/1",
        act_iri="http://example.org/act/1",
        snapshot_id="2025-08-01"
    )
    
    # Verify fields
    assert doc.element_id == "http://example.org/act/1/section/1"
    assert doc.title == "Základní pojmy"
    assert doc.official_identifier == "§ 1"
    assert doc.summary == "Definice základních pojmů používaných v tomto zákoně."
    assert doc.text_content == "Pro účely tohoto zákona se rozumí: a) osobou..."
    assert doc.level == 1
    assert doc.element_type == ElementType.SECTION
    assert doc.parent_id == "http://example.org/act/1"
    assert doc.act_iri == "http://example.org/act/1"
    assert doc.snapshot_id == "2025-08-01"
    
    print("✓ IndexDoc creation working correctly")


def test_searchable_text_extraction():
    """Test searchable text extraction from IndexDoc."""
    print("Testing searchable text extraction...")
    
    mock_element = MockLegalElement(
        id="http://example.org/act/1/section/2",
        title="Předmět úpravy",
        officialIdentifier="§ 2",
        summary="Tento zákon upravuje podmínky...",
        textContent="Tento zákon stanoví pravidla pro..."
    )
    
    doc = IndexDoc.from_legal_element(mock_element)
    
    # Test searchable text without content
    searchable_text = doc.get_searchable_text(include_content=False)
    expected_parts = ["§ 2", "Předmět úpravy", "Tento zákon upravuje podmínky..."]
    for part in expected_parts:
        assert part in searchable_text, f"Expected '{part}' in searchable text"
    
    # Test searchable text with content
    searchable_text_with_content = doc.get_searchable_text(include_content=True)
    assert "Tento zákon stanoví pravidla pro..." in searchable_text_with_content
    
    print("✓ Searchable text extraction working correctly")


def test_weighted_fields():
    """Test weighted fields extraction."""
    print("Testing weighted fields extraction...")
    
    mock_element = MockLegalElement(
        id="http://example.org/act/1/section/3",
        title="Definice",
        officialIdentifier="§ 3",
        summary="Klíčové definice pojmů.",
        textContent="V tomto zákoně se definují..."
    )
    
    doc = IndexDoc.from_legal_element(mock_element)
    weighted_fields = doc.get_weighted_fields()
    
    assert weighted_fields['official_identifier'] == "§ 3"
    assert weighted_fields['title'] == "Definice"
    assert weighted_fields['summary'] == "Klíčové definice pojmů."
    assert weighted_fields['text_content'] == "V tomto zákoně se definují..."
    
    print("✓ Weighted fields extraction working correctly")


def test_document_extractor_hierarchy():
    """Test extracting documents from hierarchical legal act structure."""
    print("Testing document extraction from hierarchy...")
    
    # Create hierarchical structure
    section1 = MockLegalElement(
        id="http://example.org/act/1/section/1",
        title="Základní pojmy",
        officialIdentifier="§ 1",
        summary="Definice základních pojmů."
    )
    
    section2 = MockLegalElement(
        id="http://example.org/act/1/section/2",
        title="Předmět úpravy",
        officialIdentifier="§ 2",
        summary="Předmět úpravy zákona."
    )
    
    chapter1 = MockLegalElement(
        id="http://example.org/act/1/chapter/1",
        title="Obecná ustanovení",
        officialIdentifier="Hlava I",
        summary="Obecná ustanovení zákona.",
        elements=[section1, section2]
    )
    
    mock_act = MockLegalAct(
        id="http://example.org/act/1",
        title="Testovací zákon",
        officialIdentifier="Zákon č. 1/2025 Sb.",
        summary="Testovací zákon pro ověření funkcionality.",
        elements=[chapter1]
    )
    
    # Extract documents
    documents = DocumentExtractor.extract_from_act(
        legal_act=mock_act,
        act_iri="http://example.org/act/1",
        snapshot_id="2025-08-01"
    )
    
    # Verify extraction
    assert len(documents) == 4  # act + chapter + 2 sections
    
    # Check act document
    act_doc = documents[0]
    assert act_doc.element_type == ElementType.ACT
    assert act_doc.level == 0
    assert act_doc.parent_id is None
    assert len(act_doc.child_ids) == 1
    
    # Check chapter document
    chapter_doc = documents[1]
    assert chapter_doc.element_type == ElementType.UNKNOWN  # MockLegalElement doesn't have specific type
    assert chapter_doc.level == 1
    assert chapter_doc.parent_id == "http://example.org/act/1"
    assert len(chapter_doc.child_ids) == 2
    
    # Check section documents
    section_docs = documents[2:]
    for section_doc in section_docs:
        assert section_doc.element_type == ElementType.UNKNOWN
        assert section_doc.level == 2
        assert section_doc.parent_id == "http://example.org/act/1/chapter/1"
        assert len(section_doc.child_ids) == 0
    
    print("✓ Document extraction from hierarchy working correctly")


def test_document_filtering():
    """Test document filtering functionality."""
    print("Testing document filtering...")
    
    # Create test documents
    docs = [
        IndexDoc(
            element_id="1",
            title="Title 1",
            official_identifier="§ 1",
            level=0,
            element_type=ElementType.ACT,
            summary="Summary 1"
        ),
        IndexDoc(
            element_id="2",
            title="Title 2",
            official_identifier="§ 2",
            level=1,
            element_type=ElementType.SECTION,
            summary=None
        ),
        IndexDoc(
            element_id="3",
            title="Title 3",
            official_identifier="§ 3",
            level=2,
            element_type=ElementType.SECTION,
            summary="Summary 3",
            text_content="Content 3"
        )
    ]
    
    # Test filtering by element type
    act_docs = DocumentExtractor.filter_documents(docs, element_types=[ElementType.ACT])
    assert len(act_docs) == 1
    assert act_docs[0].element_id == "1"
    
    # Test filtering by level
    level_1_plus = DocumentExtractor.filter_documents(docs, min_level=1)
    assert len(level_1_plus) == 2
    
    # Test filtering by summary presence
    with_summary = DocumentExtractor.filter_documents(docs, has_summary=True)
    assert len(with_summary) == 2
    
    # Test filtering by content presence
    with_content = DocumentExtractor.filter_documents(docs, has_content=True)
    assert len(with_content) == 1
    assert with_content[0].element_id == "3"
    
    print("✓ Document filtering working correctly")


def test_document_stats():
    """Test document statistics calculation."""
    print("Testing document statistics...")
    
    # Create test documents
    docs = [
        IndexDoc(element_id="1", title="T1", official_identifier="§1", 
                level=0, element_type=ElementType.ACT, summary="S1"),
        IndexDoc(element_id="2", title="T2", official_identifier="§2", 
                level=1, element_type=ElementType.SECTION, summary="S2"),
        IndexDoc(element_id="3", title="T3", official_identifier="§3", 
                level=1, element_type=ElementType.SECTION, text_content="C3"),
        IndexDoc(element_id="4", title="T4", official_identifier="§4", 
                level=2, element_type=ElementType.SECTION, summary="S4", text_content="C4")
    ]
    
    stats = DocumentExtractor.get_document_stats(docs)
    
    assert stats['total_count'] == 4
    assert stats['by_type'][ElementType.ACT] == 1
    assert stats['by_type'][ElementType.SECTION] == 3
    assert stats['by_level'][0] == 1
    assert stats['by_level'][1] == 2
    assert stats['by_level'][2] == 1
    assert stats['with_summary'] == 3
    assert stats['with_content'] == 2
    assert stats['avg_level'] == 1.0
    
    print("✓ Document statistics working correctly")


def test_search_query_model():
    """Test SearchQuery model functionality."""
    print("Testing SearchQuery model...")
    
    # Test basic query
    query = SearchQuery(query="základní pojmy")
    assert query.query == "základní pojmy"
    assert query.max_results == 10
    assert query.use_semantic == True
    assert query.use_keyword == True
    assert query.semantic_weight == 0.6
    assert query.keyword_weight == 0.4
    
    # Test query with filters
    filtered_query = SearchQuery(
        query="definice",
        max_results=5,
        element_types=[ElementType.SECTION],
        min_level=1,
        max_level=2,
        official_identifier_pattern="^§"
    )
    assert filtered_query.element_types == [ElementType.SECTION]
    assert filtered_query.min_level == 1
    assert filtered_query.max_level == 2
    assert filtered_query.official_identifier_pattern == "^§"
    
    print("✓ SearchQuery model working correctly")


def run_all_tests():
    """Run all test functions."""
    print("=" * 50)
    print("Running Index Domain Tests")
    print("=" * 50)
    
    test_functions = [
        test_index_doc_creation,
        test_searchable_text_extraction,
        test_weighted_fields,
        test_document_extractor_hierarchy,
        test_document_filtering,
        test_document_stats,
        test_search_query_model
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
