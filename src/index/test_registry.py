"""
Unit test for the IndexRegistry.

HOW TO RUN:
The virtual environment .venv should be activated before running the tests.

From the src directory, run:
    python -m index.test_registry

Or from the project root:
    cd src; python -m index.test_registry

The test uses mock implementations to avoid external dependencies.
"""

import os
from typing import List, Any

# Mock index builder for testing
class MockIndexBuilder:
    """Mock implementation of IndexBuilder for testing."""
    
    def __init__(self, name: str):
        self.name = name
        self.build_called = False
        self.load_called = False
    
    def build(self, documents: List, output_dir: str, act_identifier: str) -> Any:
        """Mock build method."""
        self.build_called = True
        return f"mock_{self.name}_index"
    
    def load(self, index_path: str) -> Any:
        """Mock load method."""
        self.load_called = True
        return f"loaded_{self.name}_index"
    
    def get_index_files(self, output_dir: str, act_identifier: str) -> List[str]:
        """Mock get_index_files method."""
        return [f"{output_dir}/{self.name}/{self.name}_{act_identifier}.mock"]

# Import the module to test
from .registry import IndexRegistry, IndexBuilder

def test_default_builders():
    """Test that default builders are registered."""
    print("Testing default builders registration...")
    
    registry = IndexRegistry()
    
    # Check that default builders are registered
    expected_types = ['bm25', 'bm25_full', 'faiss', 'faiss_full']
    available_types = registry.get_available_types()
    
    for expected_type in expected_types:
        assert expected_type in available_types, f"Expected builder {expected_type} not found"
        assert registry.has_builder(expected_type), f"Builder {expected_type} not available"
        builder = registry.get_builder(expected_type)
        assert builder is not None, f"Builder for {expected_type} is None"
    
    print("✓ Default builders registered correctly")

def test_register_custom_builder():
    """Test registering a custom builder."""
    print("Testing custom builder registration...")
    
    registry = IndexRegistry()
    
    # Register a custom builder
    custom_builder = MockIndexBuilder("custom")
    registry.register_builder("custom", custom_builder)
    
    # Verify registration
    assert registry.has_builder("custom"), "Custom builder not registered"
    assert "custom" in registry.get_available_types(), "Custom type not in available types"
    
    retrieved_builder = registry.get_builder("custom")
    assert retrieved_builder is custom_builder, "Retrieved builder is not the same as registered"
    
    print("✓ Custom builder registration working correctly")

def test_get_nonexistent_builder():
    """Test getting a non-existent builder."""
    print("Testing non-existent builder retrieval...")
    
    registry = IndexRegistry()
    
    # Try to get a non-existent builder
    builder = registry.get_builder("nonexistent")
    assert builder is None, "Non-existent builder should return None"
    
    # Test has_builder with non-existent type
    assert not registry.has_builder("nonexistent"), "Non-existent builder should return False"
    
    print("✓ Non-existent builder handling working correctly")

def test_builder_override():
    """Test overriding an existing builder."""
    print("Testing builder override...")
    
    registry = IndexRegistry()
    
    # Get original builder
    original_builder = registry.get_builder("bm25")
    assert original_builder is not None, "Original BM25 builder should exist"
    
    # Override with custom builder
    custom_builder = MockIndexBuilder("custom_bm25")
    registry.register_builder("bm25", custom_builder)
    
    # Verify override
    retrieved_builder = registry.get_builder("bm25")
    assert retrieved_builder is custom_builder, "Builder should be overridden"
    assert retrieved_builder is not original_builder, "Should not be the original builder"
    
    print("✓ Builder override working correctly")

def test_available_types_list():
    """Test getting available types list."""
    print("Testing available types list...")
    
    registry = IndexRegistry()
    
    # Get initial types
    initial_types = registry.get_available_types()
    initial_count = len(initial_types)
    
    # Add a custom type
    custom_builder = MockIndexBuilder("test_type")
    registry.register_builder("test_type", custom_builder)
    
    # Verify types list updated
    updated_types = registry.get_available_types()
    assert len(updated_types) == initial_count + 1, "Types count should increase by 1"
    assert "test_type" in updated_types, "New type should be in the list"
    
    print("✓ Available types list working correctly")

def run_all_tests():
    """Run all test functions."""
    print("=" * 50)
    print("Running IndexRegistry Tests")
    print("=" * 50)
    
    test_functions = [
        test_default_builders,
        test_register_custom_builder,
        test_get_nonexistent_builder,
        test_builder_override,
        test_available_types_list,
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
