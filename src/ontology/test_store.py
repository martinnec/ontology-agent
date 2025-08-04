"""
Unit test for the ontology store.

HOW TO RUN:
The virtual environment .venv should be activated before running the tests.

From the src directory, run:
    python -m ontology.test_store

Or from the project root:
    cd src; python -m ontology.test_store

The test uses mock implementations to avoid external dependencies.
"""

import os
# Set any required environment variables for testing
os.environ["OPENAI_API_KEY"] = "dummy-api-key-for-testing"

# Import statements using relative imports
from .store import OntologyStore
from .domain import OntologyClass, OntologyProperty, OntologyStats
from rdflib import URIRef


def test_store_initialization():
    """Test OntologyStore initialization."""
    print("Testing OntologyStore initialization...")
    
    store = OntologyStore()
    
    # Check graphs are created
    assert store.working_graph is not None
    assert store.published_graph is not None
    
    # Check namespaces are bound
    assert str(store.ex) == "https://example.org/ontology/"
    assert store.owl is not None
    assert store.rdfs is not None
    assert store.skos is not None
    assert store.xsd is not None
    
    print("✓ OntologyStore initialization working correctly")


def test_ontology_stats():
    """Test ontology statistics computation."""
    print("Testing ontology statistics...")
    
    store = OntologyStore()
    stats = store._get_ontology_stats()
    
    # Empty ontology should have zero counts
    assert isinstance(stats, OntologyStats)
    assert stats.total_classes == 0
    assert stats.total_object_properties == 0
    assert stats.total_datatype_properties == 0
    assert stats.total_triples == 0
    
    print("✓ Ontology statistics working correctly")


def test_get_whole_ontology():
    """Test getting complete ontology overview."""
    print("Testing get_whole_ontology...")
    
    store = OntologyStore()
    ontology = store.get_whole_ontology()
    
    # Should return dictionary with required keys
    assert isinstance(ontology, dict)
    assert "classes" in ontology
    assert "object_properties" in ontology
    assert "datatype_properties" in ontology
    assert "stats" in ontology
    
    # Empty ontology should have empty lists
    assert ontology["classes"] == []
    assert ontology["object_properties"] == []
    assert ontology["datatype_properties"] == []
    assert isinstance(ontology["stats"], OntologyStats)
    
    print("✓ get_whole_ontology working correctly")


def test_class_operations_placeholder():
    """Test class operations (placeholder for Phase 2)."""
    print("Testing class operations (Phase 2 placeholder)...")
    
    store = OntologyStore()
    test_iri = URIRef("https://example.org/ontology/TestClass")
    
    # These should return None/empty until Phase 2
    result = store.get_class(test_iri)
    assert result is None
    
    surroundings = store.get_class_with_surroundings(test_iri)
    assert surroundings["connected_classes"] == {}
    assert surroundings["connecting_properties"] == {}
    
    hierarchy = store.get_class_hierarchy(test_iri)
    assert hierarchy["parents"] == []
    assert hierarchy["subclasses"] == []
    
    print("✓ Class operations placeholders working correctly")


def test_property_operations_placeholder():
    """Test property operations (placeholder for Phase 2)."""
    print("Testing property operations (Phase 2 placeholder)...")
    
    store = OntologyStore()
    test_iri = URIRef("https://example.org/ontology/testProperty")
    
    # Should return None until Phase 2
    result = store.get_property_details(test_iri)
    assert result is None
    
    print("✓ Property operations placeholders working correctly")


def test_similarity_operations_placeholder():
    """Test similarity operations (placeholder for Phase 3)."""
    print("Testing similarity operations (Phase 3 placeholder)...")
    
    store = OntologyStore()
    test_iri = URIRef("https://example.org/ontology/TestClass")
    
    # Should return empty list until Phase 3
    similar = store.find_similar_classes(test_iri, limit=5)
    assert similar == []
    
    print("✓ Similarity operations placeholders working correctly")


def test_embedding_computation():
    """Test embedding computation for classes."""
    print("Testing embedding computation...")
    
    store = OntologyStore()
    
    # Create a test class with textual content
    test_class = OntologyClass(
        iri=URIRef("https://example.org/ontology/Vehicle"),
        labels={"cs": "Vozidlo", "en": "Vehicle"},
        definitions={"cs": "Dopravní prostředek pro přepravu osob nebo nákladu"},
        comments={"cs": "Silniční motorové vozidlo"},
        parent_classes=[],
        subclasses=[],
        datatype_properties=[],
        object_properties_out=[],
        object_properties_in=[],
        source_elements=[]
    )
    
    # Try to compute embedding (may be None if embedder not available)
    embedding = store._compute_class_embedding(test_class)
    
    if store.embedder is not None:
        assert embedding is not None
        assert len(embedding.shape) == 1  # Should be 1D vector
        print(f"✓ Embedding computed successfully (shape: {embedding.shape})")
    else:
        assert embedding is None
        print("✓ Embedding computation handled gracefully (no embedder available)")


def run_all_tests():
    """Run all test functions."""
    print("=" * 50)
    print("Running OntologyStore Tests")
    print("=" * 50)
    
    test_functions = [
        test_store_initialization,
        test_ontology_stats,
        test_get_whole_ontology,
        test_class_operations_placeholder,
        test_property_operations_placeholder,
        test_similarity_operations_placeholder,
        test_embedding_computation
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
