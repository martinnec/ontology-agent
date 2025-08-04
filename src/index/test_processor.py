"""
Unit test for the DocumentProcessor.

HOW TO RUN:
The virtual environment .venv should be activated before running the tests.

From the src directory, run:
    python -m index.test_processor

Or from the project root:
    cd src; python -m index.test_processor

The test uses mock implementations to avoid external dependencies.
"""

import os
import sys
from typing import List, Optional

# Mock legislation domain objects for testing
class MockLegalElement:
    """Mock implementation of LegalStructuralElement for testing."""
    
    def __init__(self, id: str, element_type: str, title: str = "Test Title",
                 official_identifier: str = "§ 1", summary: str = None,
                 text_content: str = None, elements: List = None):
        self.id = id
        self.elementType = element_type
        self.title = title
        self.officialIdentifier = official_identifier
        self.summary = summary
        self.summary_names = None
        self.textContent = text_content
        self.elements = elements or []

# Import the module to test
from .processor import DocumentProcessor
from .domain import ElementType

def test_element_type_mapping():
    """Test element type mapping from legislation to index domain."""
    print("Testing element type mapping...")
    
    processor = DocumentProcessor()
    
    # Test each mapping
    test_cases = [
        ("LegalAct", ElementType.LEGAL_ACT),
        ("LegalPart", ElementType.PART),
        ("LegalChapter", ElementType.CHAPTER),
        ("LegalDivision", ElementType.DIVISION),
        ("LegalSection", ElementType.SECTION),
        ("UnknownType", ElementType.UNKNOWN),
    ]
    
    for input_type, expected_output in test_cases:
        result = processor._map_element_type(input_type)
        assert result == expected_output, f"Expected {expected_output}, got {result} for {input_type}"
    
    print("✓ Element type mapping working correctly")

def test_process_single_element():
    """Test processing a single legal element."""
    print("Testing single element processing...")
    
    processor = DocumentProcessor()
    
    # Create a mock legal act
    legal_act = MockLegalElement(
        id="https://example.com/act/1",
        element_type="LegalAct",
        title="Test Legal Act",
        official_identifier="Act 1/2024",
        summary="Test summary",
        text_content="Test content"
    )
    
    # Process the legal act
    documents = processor.process_legal_act(legal_act, act_iri="test-act", snapshot_id="test-snapshot")
    
    # Verify results
    assert len(documents) == 1, f"Expected 1 document, got {len(documents)}"
    
    doc = documents[0]
    assert doc.element_id == "https://example.com/act/1"
    assert doc.title == "Test Legal Act"
    assert doc.official_identifier == "Act 1/2024"
    assert doc.summary == "Test summary"
    assert doc.text_content == "Test content"
    assert doc.element_type == ElementType.LEGAL_ACT
    assert doc.level == 0
    assert doc.parent_id is None
    assert doc.act_iri == "test-act"
    assert doc.snapshot_id == "test-snapshot"
    
    print("✓ Single element processing working correctly")

def test_process_hierarchical_structure():
    """Test processing a hierarchical legal structure."""
    print("Testing hierarchical structure processing...")
    
    processor = DocumentProcessor()
    
    # Create a mock hierarchical structure
    section1 = MockLegalElement(
        id="https://example.com/section/1",
        element_type="LegalSection",
        title="Section 1",
        official_identifier="§ 1"
    )
    
    section2 = MockLegalElement(
        id="https://example.com/section/2",
        element_type="LegalSection",
        title="Section 2",
        official_identifier="§ 2"
    )
    
    chapter = MockLegalElement(
        id="https://example.com/chapter/1",
        element_type="LegalChapter",
        title="Chapter 1",
        official_identifier="Chap. 1",
        elements=[section1, section2]
    )
    
    legal_act = MockLegalElement(
        id="https://example.com/act/1",
        element_type="LegalAct",
        title="Test Legal Act",
        official_identifier="Act 1/2024",
        elements=[chapter]
    )
    
    # Process the legal act
    documents = processor.process_legal_act(legal_act)
    
    # Verify results
    assert len(documents) == 4, f"Expected 4 documents, got {len(documents)}"
    
    # Verify root act
    act_doc = documents[0]
    assert act_doc.element_type == ElementType.LEGAL_ACT
    assert act_doc.level == 0
    assert act_doc.parent_id is None
    assert len(act_doc.child_ids) == 1
    assert "https://example.com/chapter/1" in act_doc.child_ids
    
    # Verify chapter
    chapter_doc = documents[1]
    assert chapter_doc.element_type == ElementType.CHAPTER
    assert chapter_doc.level == 1
    assert chapter_doc.parent_id == "https://example.com/act/1"
    assert len(chapter_doc.child_ids) == 2
    
    # Verify sections
    section1_doc = documents[2]
    assert section1_doc.element_type == ElementType.SECTION
    assert section1_doc.level == 2
    assert section1_doc.parent_id == "https://example.com/chapter/1"
    assert len(section1_doc.child_ids) == 0
    
    section2_doc = documents[3]
    assert section2_doc.element_type == ElementType.SECTION
    assert section2_doc.level == 2
    assert section2_doc.parent_id == "https://example.com/chapter/1"
    assert len(section2_doc.child_ids) == 0
    
    print("✓ Hierarchical structure processing working correctly")

def test_supported_element_types():
    """Test getting supported element types."""
    print("Testing supported element types...")
    
    processor = DocumentProcessor()
    supported_types = processor.get_supported_element_types()
    
    expected_types = ["LegalAct", "LegalPart", "LegalChapter", "LegalDivision", "LegalSection"]
    
    for expected_type in expected_types:
        assert expected_type in supported_types, f"Expected type {expected_type} not in supported types"
    
    print("✓ Supported element types working correctly")

def run_all_tests():
    """Run all test functions."""
    print("=" * 50)
    print("Running DocumentProcessor Tests")
    print("=" * 50)
    
    test_functions = [
        test_element_type_mapping,
        test_process_single_element,
        test_process_hierarchical_structure,
        test_supported_element_types,
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
