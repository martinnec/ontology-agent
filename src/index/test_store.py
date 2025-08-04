"""
Unit test for the IndexStore.

HOW TO RUN:
From the src directory, run:
    python -m index.test_store

Or from the project root:
    cd src; python -m index.test_store

The test uses mock implementations to avoid external dependencies.
"""

import os
import tempfile
import shutil
from datetime import datetime

# Import the module to test
from .store import IndexStore, IndexMetadata

def test_store_initialization():
    """Test IndexStore initialization."""
    print("Testing store initialization...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        store = IndexStore(temp_dir)
        
        assert store.base_output_dir == temp_dir
        assert os.path.exists(temp_dir), "Base directory should be created"
    
    print("✓ Store initialization working correctly")

def test_act_directory_creation():
    """Test act directory path generation."""
    print("Testing act directory creation...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        store = IndexStore(temp_dir)
        
        # Test safe identifier creation
        act_dir = store.get_act_directory("test-act")
        expected_path = os.path.join(temp_dir, "test-act")
        assert act_dir == expected_path, f"Expected {expected_path}, got {act_dir}"
        
        # Test with unsafe characters
        unsafe_act_dir = store.get_act_directory("https://example.com/act:123")
        expected_safe_path = os.path.join(temp_dir, "https___example.com_act_123")
        assert unsafe_act_dir == expected_safe_path, "Unsafe characters should be replaced"
    
    print("✓ Act directory creation working correctly")

def test_metadata_operations():
    """Test metadata save and load operations."""
    print("Testing metadata operations...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        store = IndexStore(temp_dir)
        
        # Create test metadata
        metadata = IndexMetadata(
            act_iri="test-act-iri",
            snapshot_id="test-snapshot",
            document_count=10,
            index_types=["bm25", "faiss"]
        )
        
        # Save metadata
        store.save_metadata("test-act", metadata)
        
        # Verify file exists
        metadata_path = store.get_metadata_path("test-act")
        assert os.path.exists(metadata_path), "Metadata file should exist"
        
        # Load metadata
        loaded_metadata = store.load_metadata("test-act")
        assert loaded_metadata is not None, "Metadata should be loaded"
        assert loaded_metadata.act_iri == "test-act-iri", "Act IRI should match"
        assert loaded_metadata.snapshot_id == "test-snapshot", "Snapshot ID should match"
        assert loaded_metadata.document_count == 10, "Document count should match"
        assert "bm25" in loaded_metadata.index_types, "BM25 should be in index types"
        assert "faiss" in loaded_metadata.index_types, "FAISS should be in index types"
    
    print("✓ Metadata operations working correctly")

def run_all_tests():
    """Run all test functions."""
    print("=" * 50)
    print("Running IndexStore Tests")
    print("=" * 50)
    
    test_functions = [
        test_store_initialization,
        test_act_directory_creation,
        test_metadata_operations,
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
