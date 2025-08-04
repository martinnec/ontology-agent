"""
Integration test for the IndexService.

HOW TO RUN:
The virtual environment .venv should be activated before running the tests.

From the src directory, run:
    python -m index.test_service

Or from the project root:
    cd src; python -m index.test_service

This test validates the public IndexService interface using mock components.
"""

import os
import tempfile
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

# Mock index builders that don't actually build indexes
class MockIndexBuilder:
    """Mock index builder that simulates index building without dependencies."""
    
    def __init__(self, index_type: str):
        self.index_type = index_type
    
    def build(self, documents: List, output_dir: str, act_identifier: str):
        """Mock build method."""
        return f"mock_{self.index_type}_index"
    
    def load(self, index_path: str):
        """Mock load method."""
        return f"loaded_{self.index_type}_index"
    
    def get_index_files(self, output_dir: str, act_identifier: str) -> List[str]:
        """Mock get_index_files method."""
        return [os.path.join(output_dir, self.index_type, f"{self.index_type}_{act_identifier}.mock")]

# Import the module to test
from .service import IndexService

def create_mock_legal_act():
    """Create a mock legal act for testing."""
    section1 = MockLegalElement(
        id="https://example.com/section/1",
        element_type="LegalSection",
        title="Section 1",
        official_identifier="§ 1",
        summary="First section summary",
        text_content="This is the full text content of section 1. It contains detailed provisions about the first topic covered by this legal act. The section establishes fundamental principles and basic requirements."
    )
    
    section2 = MockLegalElement(
        id="https://example.com/section/2",
        element_type="LegalSection",
        title="Section 2",
        official_identifier="§ 2",
        summary="Second section summary",
        text_content="This is the full text content of section 2. It provides comprehensive rules and regulations for the second topic. The section includes specific procedures and implementation guidelines."
    )
    
    chapter = MockLegalElement(
        id="https://example.com/chapter/1",
        element_type="LegalChapter",
        title="Chapter 1",
        official_identifier="Chapter I",
        summary="First chapter summary",
        text_content="This chapter introduces the main topics covered in this legal act. It provides an overview of the regulatory framework and establishes the scope of application.",
        elements=[section1, section2]
    )
    
    legal_act = MockLegalElement(
        id="https://example.com/act/test-act",
        element_type="LegalAct",
        title="Test Legal Act",
        official_identifier="Act 1/2024",
        summary="Test legal act summary",
        text_content="This is a comprehensive legal act that establishes regulations and procedures for various legal matters. The act is divided into chapters and sections that cover different aspects of the subject matter.",
        elements=[chapter]
    )
    
    return legal_act

def test_service_initialization():
    """Test IndexService initialization."""
    print("Testing IndexService initialization...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        service = IndexService(output_dir=temp_dir)
        
        assert service.output_dir == temp_dir
        assert service.processor is not None
        assert service.registry is not None
        assert service.store is not None
        
        # Test available index types
        available_types = service.get_available_index_types()
        expected_types = ['bm25', 'bm25_full', 'faiss', 'faiss_full']
        for expected_type in expected_types:
            assert expected_type in available_types, f"Expected {expected_type} in available types"
    
    print("✓ IndexService initialization working correctly")

def test_build_indexes():
    """Test building indexes for a legal act."""
    print("Testing index building...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        service = IndexService(output_dir=temp_dir)
        legal_act = create_mock_legal_act()
        
        # Replace builders with mock ones to avoid external dependencies
        service.registry.register_builder("bm25", MockIndexBuilder("bm25"))
        service.registry.register_builder("faiss", MockIndexBuilder("faiss"))
        
        # Build specific index types
        collection = service.build_indexes(legal_act, index_types=["bm25", "faiss"])
        
        assert collection is not None, "Should return IndexCollection"
        assert collection.act_iri == "https://example.com/act/test-act"
        assert len(collection.get_available_indexes()) == 2, "Should have 2 built indexes"
        assert collection.has_index("bm25"), "Should have BM25 index"
        assert collection.has_index("faiss"), "Should have FAISS index"
        
        # Check documents were processed
        assert collection.get_document_count() == 4, "Should have 4 documents (act + chapter + 2 sections)"
        
        documents = collection.get_documents()
        assert len(documents) == 4, "Should return 4 documents"
        
        # Verify document hierarchy
        act_doc = documents[0]
        assert act_doc.element_type.value == "legal_act"
        assert act_doc.level == 0
        assert act_doc.parent_id is None
        
        chapter_doc = documents[1]
        assert chapter_doc.element_type.value == "chapter"
        assert chapter_doc.level == 1
        assert chapter_doc.parent_id == "https://example.com/act/test-act"
        
        section_docs = documents[2:4]
        for section_doc in section_docs:
            assert section_doc.element_type.value == "section"
            assert section_doc.level == 2
            assert section_doc.parent_id == "https://example.com/chapter/1"
    
    print("✓ Index building working correctly")

def test_get_indexes_force_rebuild():
    """Test getting indexes with force rebuild."""
    print("Testing get indexes with force rebuild...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        service = IndexService(output_dir=temp_dir)
        legal_act = create_mock_legal_act()
        
        # Replace builders with mock ones
        service.registry.register_builder("bm25", MockIndexBuilder("bm25"))
        service.registry.register_builder("faiss", MockIndexBuilder("faiss"))
        
        # First call - should build all indexes
        collection1 = service.get_indexes(legal_act, force_rebuild=True)
        assert len(collection1.get_available_indexes()) >= 2, "Should build indexes"
        
        # Second call - force rebuild should build again
        collection2 = service.get_indexes(legal_act, force_rebuild=True)
        assert len(collection2.get_available_indexes()) >= 2, "Should rebuild indexes"
    
    print("✓ Get indexes with force rebuild working correctly")

def test_index_exists():
    """Test checking if specific indexes exist."""
    print("Testing index existence checking...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        service = IndexService(output_dir=temp_dir)
        legal_act = create_mock_legal_act()
        
        # Initially no indexes should exist
        assert not service.index_exists(legal_act, "bm25"), "BM25 index should not exist initially"
        assert not service.index_exists(legal_act, "faiss"), "FAISS index should not exist initially"
        
        # Replace builders with mock ones
        mock_builder = MockIndexBuilder("bm25")
        service.registry.register_builder("bm25", mock_builder)
        
        # Create the mock index file that the builder expects
        act_identifier = service._get_act_identifier(legal_act)
        required_files = mock_builder.get_index_files(temp_dir, act_identifier)
        
        # Ensure directory exists and create the mock file
        for file_path in required_files:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                f.write("mock")
        
        # Now BM25 should exist
        assert service.index_exists(legal_act, "bm25"), "BM25 index should exist after building"
        assert not service.index_exists(legal_act, "faiss"), "FAISS index should still not exist"
    
    print("✓ Index existence checking working correctly")

def test_clear_indexes():
    """Test clearing all indexes for a legal act."""
    print("Testing clear indexes...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        service = IndexService(output_dir=temp_dir)
        legal_act = create_mock_legal_act()
        
        # Replace builders with mock ones
        service.registry.register_builder("bm25", MockIndexBuilder("bm25"))
        
        # Build some indexes
        service.build_indexes(legal_act, index_types=["bm25"])
        
        # Verify directory exists
        act_identifier = service._get_act_identifier(legal_act)
        act_dir = service.store.get_act_directory(act_identifier)
        
        # Create a metadata file to simulate index existence
        metadata_path = service.store.get_metadata_path(act_identifier)
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
        with open(metadata_path, 'w') as f:
            f.write('{"act_iri": "test"}')
        
        assert os.path.exists(act_dir), "Act directory should exist before clearing"
        
        # Clear indexes
        service.clear_indexes(legal_act)
        
        # Verify directory is removed
        assert not os.path.exists(act_dir), "Act directory should be removed after clearing"
    
    print("✓ Clear indexes working correctly")

def test_act_identifier_extraction():
    """Test extraction of safe act identifiers."""
    print("Testing act identifier extraction...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        service = IndexService(output_dir=temp_dir)
        
        # Test various identifier formats
        test_cases = [
            ("https://example.com/act/56-2001", "56-2001"),
            ("simple-act", "simple-act"),
            ("act:with:colons", "act_with_colons"),
            ("https://example.com/path/to/act/123", "123"),
        ]
        
        for input_iri, expected_id in test_cases:
            legal_act = MockLegalElement(id=input_iri, element_type="LegalAct")
            result = service._get_act_identifier(legal_act)
            assert result == expected_id, f"Expected {expected_id}, got {result} for {input_iri}"
    
    print("✓ Act identifier extraction working correctly")

def test_document_processing_consistency():
    """Test that document processing is consistent across operations."""
    print("Testing document processing consistency...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        service = IndexService(output_dir=temp_dir)
        legal_act = create_mock_legal_act()
        
        # Replace builders with mock ones
        service.registry.register_builder("bm25", MockIndexBuilder("bm25"))
        service.registry.register_builder("faiss", MockIndexBuilder("faiss"))
        
        # Build indexes multiple times
        collection1 = service.build_indexes(legal_act, index_types=["bm25"])
        collection2 = service.build_indexes(legal_act, index_types=["faiss"])
        
        # Documents should be consistent
        docs1 = collection1.get_documents()
        docs2 = collection2.get_documents()
        
        assert len(docs1) == len(docs2), "Document count should be consistent"
        
        # Check that documents have same structure
        for doc1, doc2 in zip(docs1, docs2):
            assert doc1.element_id == doc2.element_id, "Element IDs should match"
            assert doc1.element_type == doc2.element_type, "Element types should match"
            assert doc1.level == doc2.level, "Levels should match"
            assert doc1.parent_id == doc2.parent_id, "Parent IDs should match"
    
    print("✓ Document processing consistency working correctly")

def run_all_tests():
    """Run all test functions."""
    print("=" * 50)
    print("Running IndexService Integration Tests")
    print("=" * 50)
    
    test_functions = [
        test_service_initialization,
        test_build_indexes,
        test_get_indexes_force_rebuild,
        test_index_exists,
        test_clear_indexes,
        test_act_identifier_extraction,
        test_document_processing_consistency,
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
