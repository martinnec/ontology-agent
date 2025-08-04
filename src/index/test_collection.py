"""
Test for the IndexCollection.

HOW TO RUN:
The virtual environment .venv should be activated before running the tests.

From the src directory, run:
    python -m index.test_collection

Or from the project root:
    cd src; python -m index.test_collection

The test uses mock implementations to avoid external dependencies.
"""

# Mock index classes for testing
class MockIndex:
    """Mock implementation of an index for testing."""
    
    def __init__(self, index_type: str):
        self.index_type = index_type
        self.data = f"mock_{index_type}_data"

# Mock document for testing
class MockIndexDoc:
    """Mock implementation of IndexDoc for testing."""
    
    def __init__(self, element_id: str, title: str = "Mock Title"):
        self.element_id = element_id
        self.title = title

# Import the module to test
from .collection import IndexCollection

def test_collection_initialization():
    """Test IndexCollection initialization."""
    print("Testing collection initialization...")
    
    collection = IndexCollection(act_iri="test-act", snapshot_id="test-snapshot")
    
    assert collection.act_iri == "test-act"
    assert collection.snapshot_id == "test-snapshot"
    assert len(collection.get_available_indexes()) == 0
    assert collection.get_document_count() == 0
    
    print("✓ Collection initialization working correctly")

def test_add_and_get_indexes():
    """Test adding and retrieving indexes."""
    print("Testing add and get indexes...")
    
    collection = IndexCollection(act_iri="test-act")
    
    # Add some mock indexes
    bm25_index = MockIndex("bm25")
    faiss_index = MockIndex("faiss")
    
    collection.add_index("bm25", bm25_index)
    collection.add_index("faiss", faiss_index)
    
    # Test retrieval
    retrieved_bm25 = collection.get_index("bm25")
    retrieved_faiss = collection.get_index("faiss")
    
    assert retrieved_bm25 is bm25_index, "BM25 index not retrieved correctly"
    assert retrieved_faiss is faiss_index, "FAISS index not retrieved correctly"
    
    # Test non-existent index
    nonexistent = collection.get_index("nonexistent")
    assert nonexistent is None, "Non-existent index should return None"
    
    print("✓ Add and get indexes working correctly")

def test_has_index():
    """Test checking index existence."""
    print("Testing has_index functionality...")
    
    collection = IndexCollection(act_iri="test-act")
    
    # Initially no indexes
    assert not collection.has_index("bm25"), "Should not have BM25 index initially"
    assert not collection.has_index("faiss"), "Should not have FAISS index initially"
    
    # Add an index
    bm25_index = MockIndex("bm25")
    collection.add_index("bm25", bm25_index)
    
    # Test existence
    assert collection.has_index("bm25"), "Should have BM25 index after adding"
    assert not collection.has_index("faiss"), "Should not have FAISS index"
    
    print("✓ Has_index functionality working correctly")

def test_available_indexes():
    """Test getting available indexes list."""
    print("Testing available indexes list...")
    
    collection = IndexCollection(act_iri="test-act")
    
    # Initially empty
    available = collection.get_available_indexes()
    assert len(available) == 0, "Should have no available indexes initially"
    
    # Add indexes
    collection.add_index("bm25", MockIndex("bm25"))
    collection.add_index("faiss", MockIndex("faiss"))
    collection.add_index("bm25_full", MockIndex("bm25_full"))
    
    # Test available list
    available = collection.get_available_indexes()
    assert len(available) == 3, "Should have 3 available indexes"
    assert "bm25" in available, "BM25 should be available"
    assert "faiss" in available, "FAISS should be available"
    assert "bm25_full" in available, "BM25 full should be available"
    
    print("✓ Available indexes list working correctly")

def test_documents_management():
    """Test setting and getting documents."""
    print("Testing documents management...")
    
    collection = IndexCollection(act_iri="test-act")
    
    # Initially no documents
    assert collection.get_document_count() == 0, "Should have no documents initially"
    assert len(collection.get_documents()) == 0, "Should return empty documents list"
    
    # Create mock documents
    doc1 = MockIndexDoc("doc1", "Title 1")
    doc2 = MockIndexDoc("doc2", "Title 2")
    doc3 = MockIndexDoc("doc3", "Title 3")
    
    documents = [doc1, doc2, doc3]
    collection.set_documents(documents)
    
    # Test document count
    assert collection.get_document_count() == 3, "Should have 3 documents"
    
    # Test document retrieval
    retrieved_docs = collection.get_documents()
    assert len(retrieved_docs) == 3, "Should retrieve 3 documents"
    
    # Test that it's a copy (modifying original shouldn't affect collection)
    documents.append(MockIndexDoc("doc4", "Title 4"))
    assert collection.get_document_count() == 3, "Collection should still have 3 documents"
    
    print("✓ Documents management working correctly")

def test_get_document_by_id():
    """Test getting document by ID."""
    print("Testing get document by ID...")
    
    collection = IndexCollection(act_iri="test-act")
    
    # Create and set documents
    doc1 = MockIndexDoc("doc1", "Title 1")
    doc2 = MockIndexDoc("doc2", "Title 2")
    doc3 = MockIndexDoc("doc3", "Title 3")
    
    collection.set_documents([doc1, doc2, doc3])
    
    # Test retrieval by ID
    retrieved_doc1 = collection.get_document_by_id("doc1")
    retrieved_doc2 = collection.get_document_by_id("doc2")
    nonexistent = collection.get_document_by_id("nonexistent")
    
    assert retrieved_doc1 is doc1, "Should retrieve correct document by ID"
    assert retrieved_doc2 is doc2, "Should retrieve correct document by ID"
    assert nonexistent is None, "Non-existent document should return None"
    
    print("✓ Get document by ID working correctly")

def test_collection_repr():
    """Test string representation of collection."""
    print("Testing collection string representation...")
    
    collection = IndexCollection(act_iri="test-act")
    
    # Add some indexes and documents
    collection.add_index("bm25", MockIndex("bm25"))
    collection.add_index("faiss", MockIndex("faiss"))
    collection.set_documents([MockIndexDoc("doc1"), MockIndexDoc("doc2")])
    
    # Test string representation
    repr_str = repr(collection)
    assert "test-act" in repr_str, "Act IRI should be in representation"
    assert "bm25" in repr_str, "Index types should be in representation"
    assert "faiss" in repr_str, "Index types should be in representation"
    assert "2" in repr_str, "Document count should be in representation"
    
    print("✓ Collection string representation working correctly")

def run_all_tests():
    """Run all test functions."""
    print("=" * 50)
    print("Running IndexCollection Tests")
    print("=" * 50)
    
    test_functions = [
        test_collection_initialization,
        test_add_and_get_indexes,
        test_has_index,
        test_available_indexes,
        test_documents_management,
        test_get_document_by_id,
        test_collection_repr,
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
