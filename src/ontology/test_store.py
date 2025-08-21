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


def test_update_class():
    """Test updating existing class."""
    print("Testing update_class...")
    
    store = OntologyStore()
    
    # Create and add a test class
    test_class = OntologyClass(
        iri=URIRef("https://example.org/UpdateTest"),
        labels={"en": "Original Test Class"},
        definitions={"en": "Original definition"},
        comments={},
        parent_classes=[],
        subclasses=[],
        datatype_properties=[],
        object_properties_out=[],
        object_properties_in=[],
        source_elements=["original_source"]
    )
    
    # Add the class
    result = store.add_class(test_class)
    assert result is True
    
    # Update the class
    updated_class = OntologyClass(
        iri=URIRef("https://example.org/UpdateTest"),
        labels={"en": "Updated Test Class", "cs": "Aktualizovaná testovací třída"},
        definitions={"en": "Updated definition", "cs": "Aktualizovaná definice"},
        comments={"en": "Updated comment"},
        parent_classes=[],
        subclasses=[],
        datatype_properties=[],
        object_properties_out=[],
        object_properties_in=[],
        source_elements=["updated_source"]
    )
    
    result = store.update_class(updated_class)
    assert result is True
    
    # Verify the update
    retrieved_class = store.get_class(URIRef("https://example.org/UpdateTest"))
    assert retrieved_class is not None
    assert retrieved_class.labels["en"] == "Updated Test Class"
    assert retrieved_class.labels.get("cs") == "Aktualizovaná testovací třída"
    assert retrieved_class.definitions["en"] == "Updated definition"
    assert retrieved_class.comments.get("en") == "Updated comment"
    
    print("✓ update_class working correctly")


def test_update_property():
    """Test updating existing property."""
    print("Testing update_property...")
    
    store = OntologyStore()
    
    # Create and add a test property
    test_property = OntologyProperty(
        iri=URIRef("https://example.org/updateTestProperty"),
        labels={"en": "original test property"},
        definitions={"en": "Original property definition"},
        comments={},
        property_type="ObjectProperty",
        domain=URIRef("https://example.org/OriginalDomain"),
        range=URIRef("https://example.org/OriginalRange"),
        source_elements=["original_source"]
    )
    
    # Add the property
    result = store.add_property(test_property)
    assert result is True
    
    # Update the property
    updated_property = OntologyProperty(
        iri=URIRef("https://example.org/updateTestProperty"),
        labels={"en": "updated test property", "cs": "aktualizovaná testovací vlastnost"},
        definitions={"en": "Updated property definition", "cs": "Aktualizovaná definice vlastnosti"},
        comments={"en": "Updated comment"},
        property_type="ObjectProperty",
        domain=URIRef("https://example.org/UpdatedDomain"),
        range=URIRef("https://example.org/UpdatedRange"),
        source_elements=["updated_source"]
    )
    
    result = store.update_property(updated_property)
    assert result is True
    
    # Verify the update
    retrieved_property = store.get_property_details(URIRef("https://example.org/updateTestProperty"))
    assert retrieved_property is not None
    assert retrieved_property.labels["en"] == "updated test property"
    assert retrieved_property.labels.get("cs") == "aktualizovaná testovací vlastnost"
    assert retrieved_property.definitions["en"] == "Updated property definition"
    assert retrieved_property.domain == URIRef("https://example.org/UpdatedDomain")
    assert retrieved_property.range == URIRef("https://example.org/UpdatedRange")
    
    print("✓ update_property working correctly")


def test_remove_class():
    """Test removing existing class."""
    print("Testing remove_class...")
    
    store = OntologyStore()
    
    # Create and add a test class
    test_class = OntologyClass(
        iri=URIRef("https://example.org/RemoveTest"),
        labels={"en": "Remove Test Class"},
        definitions={"en": "Class to be removed"},
        comments={},
        parent_classes=[],
        subclasses=[],
        datatype_properties=[],
        object_properties_out=[],
        object_properties_in=[],
        source_elements=["test_source"]
    )
    
    # Add the class
    result = store.add_class(test_class)
    assert result is True
    
    # Verify it exists
    retrieved_class = store.get_class(URIRef("https://example.org/RemoveTest"))
    assert retrieved_class is not None
    
    # Remove the class
    result = store.remove_class(URIRef("https://example.org/RemoveTest"))
    assert result is True
    
    # Verify it's removed
    removed_class = store.get_class(URIRef("https://example.org/RemoveTest"))
    assert removed_class is None
    
    print("✓ remove_class working correctly")


def test_remove_property():
    """Test removing existing property."""
    print("Testing remove_property...")
    
    store = OntologyStore()
    
    # Create and add a test property
    test_property = OntologyProperty(
        iri=URIRef("https://example.org/removeTestProperty"),
        labels={"en": "remove test property"},
        definitions={"en": "Property to be removed"},
        comments={},
        property_type="DatatypeProperty",
        domain=URIRef("https://example.org/TestDomain"),
        range=URIRef("http://www.w3.org/2001/XMLSchema#string"),
        source_elements=["test_source"]
    )
    
    # Add the property
    result = store.add_property(test_property)
    assert result is True
    
    # Verify it exists
    retrieved_property = store.get_property_details(URIRef("https://example.org/removeTestProperty"))
    assert retrieved_property is not None
    
    # Remove the property
    result = store.remove_property(URIRef("https://example.org/removeTestProperty"))
    assert result is True
    
    # Verify it's removed
    removed_property = store.get_property_details(URIRef("https://example.org/removeTestProperty"))
    assert removed_property is None
    
    print("✓ remove_property working correctly")


def test_update_nonexistent_class():
    """Test updating a class that doesn't exist."""
    print("Testing update of nonexistent class...")
    
    store = OntologyStore()
    
    # Try to update a class that doesn't exist
    nonexistent_class = OntologyClass(
        iri=URIRef("https://example.org/NonexistentClass"),
        labels={"en": "Nonexistent Class"},
        definitions={"en": "This class doesn't exist"},
        comments={},
        parent_classes=[],
        subclasses=[],
        datatype_properties=[],
        object_properties_out=[],
        object_properties_in=[],
        source_elements=["test_source"]
    )
    
    result = store.update_class(nonexistent_class)
    assert result is False
    
    print("✓ Update of nonexistent class handled correctly")


def test_remove_nonexistent_elements():
    """Test removing elements that don't exist."""
    print("Testing remove of nonexistent elements...")
    
    store = OntologyStore()
    
    # Try to remove a class that doesn't exist
    result = store.remove_class(URIRef("https://example.org/NonexistentClass"))
    assert result is True  # Should succeed silently
    
    # Try to remove a property that doesn't exist
    result = store.remove_property(URIRef("https://example.org/nonexistentProperty"))
    assert result is True  # Should succeed silently
    
    print("✓ Remove of nonexistent elements handled correctly")


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
        test_embedding_computation,
        test_update_class,
        test_update_property,
        test_remove_class,
        test_remove_property,
        test_update_nonexistent_class,
        test_remove_nonexistent_elements
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
