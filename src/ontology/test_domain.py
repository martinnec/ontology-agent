"""
Unit test for the ontology domain models.

HOW TO RUN:
The virtual environment .venv should be activated before running the tests.

From the src directory, run:
    python -m ontology.test_domain

Or from the project root:
    cd src; python -m ontology.test_domain

The test uses mock implementations to avoid external dependencies.
"""

import os
# Set any required environment variables for testing
os.environ["OPENAI_API_KEY"] = "dummy-value-for-testing"

# Import statements using relative imports
from .domain import (
    OntologyClass, OntologyProperty, ClassNeighborhood, 
    SimilarClass, OntologyStats
)
from rdflib import URIRef


def test_ontology_class_creation():
    """Test OntologyClass dataclass creation and properties."""
    print("Testing OntologyClass creation...")
    
    # Create test data
    iri = URIRef("https://example.org/Vehicle")
    labels = {"cs": "Vozidlo", "en": "Vehicle"}
    definitions = {"cs": "Dopravní prostředek", "en": "Transportation device"}
    comments = {"cs": "Poznámka", "en": "Comment"}
    parent_classes = [URIRef("https://example.org/MovableObject")]
    subclasses = [URIRef("https://example.org/Car"), URIRef("https://example.org/Truck")]
    datatype_properties = [URIRef("https://example.org/hasWeight")]
    object_properties_out = [URIRef("https://example.org/hasOwner")]
    object_properties_in = [URIRef("https://example.org/isOwnedBy")]
    source_elements = ["https://example.org/legal/element/1"]
    
    # Create OntologyClass instance
    ontology_class = OntologyClass(
        iri=iri,
        labels=labels,
        definitions=definitions,
        comments=comments,
        parent_classes=parent_classes,
        subclasses=subclasses,
        datatype_properties=datatype_properties,
        object_properties_out=object_properties_out,
        object_properties_in=object_properties_in,
        source_elements=source_elements
    )
    
    # Verify all properties are set correctly
    assert ontology_class.iri == iri
    assert ontology_class.labels == labels
    assert ontology_class.definitions == definitions
    assert ontology_class.comments == comments
    assert ontology_class.parent_classes == parent_classes
    assert ontology_class.subclasses == subclasses
    assert ontology_class.datatype_properties == datatype_properties
    assert ontology_class.object_properties_out == object_properties_out
    assert ontology_class.object_properties_in == object_properties_in
    assert ontology_class.source_elements == source_elements
    
    print("✓ OntologyClass creation working correctly")


def test_ontology_property_creation():
    """Test OntologyProperty dataclass creation and properties."""
    print("Testing OntologyProperty creation...")
    
    # Create test data
    iri = URIRef("https://example.org/hasOwner")
    labels = {"cs": "má vlastníka", "en": "has owner"}
    definitions = {"cs": "Vztah vlastnictví", "en": "Ownership relationship"}
    comments = {"cs": "Poznámka k vlastnictví", "en": "Ownership comment"}
    property_type = "ObjectProperty"
    domain = URIRef("https://example.org/Vehicle")
    range_ = URIRef("https://example.org/Person")
    source_elements = ["https://example.org/legal/element/2"]
    
    # Create OntologyProperty instance
    ontology_property = OntologyProperty(
        iri=iri,
        labels=labels,
        definitions=definitions,
        comments=comments,
        property_type=property_type,
        domain=domain,
        range=range_,
        source_elements=source_elements
    )
    
    # Verify all properties are set correctly
    assert ontology_property.iri == iri
    assert ontology_property.labels == labels
    assert ontology_property.definitions == definitions
    assert ontology_property.comments == comments
    assert ontology_property.property_type == property_type
    assert ontology_property.domain == domain
    assert ontology_property.range == range_
    assert ontology_property.source_elements == source_elements
    
    print("✓ OntologyProperty creation working correctly")


def test_datatype_property_creation():
    """Test OntologyProperty creation for datatype properties."""
    print("Testing OntologyProperty for datatype properties...")
    
    # Create datatype property
    ontology_property = OntologyProperty(
        iri=URIRef("https://example.org/hasWeight"),
        labels={"cs": "má hmotnost", "en": "has weight"},
        definitions={"cs": "Hmotnost objektu", "en": "Weight of object"},
        comments={},
        property_type="DatatypeProperty",
        domain=URIRef("https://example.org/Vehicle"),
        range=URIRef("http://www.w3.org/2001/XMLSchema#decimal"),
        source_elements=[]
    )
    
    # Verify property type and range
    assert ontology_property.property_type == "DatatypeProperty"
    assert ontology_property.range == URIRef("http://www.w3.org/2001/XMLSchema#decimal")
    
    print("✓ OntologyProperty for datatype properties working correctly")


def test_class_neighborhood_creation():
    """Test ClassNeighborhood dataclass creation."""
    print("Testing ClassNeighborhood creation...")
    
    # Create target class
    target_class = OntologyClass(
        iri=URIRef("https://example.org/Vehicle"),
        labels={"cs": "Vozidlo"},
        definitions={},
        comments={},
        parent_classes=[],
        subclasses=[],
        datatype_properties=[],
        object_properties_out=[],
        object_properties_in=[],
        source_elements=[]
    )
    
    # Create connected classes
    connected_class = OntologyClass(
        iri=URIRef("https://example.org/Person"),
        labels={"cs": "Osoba"},
        definitions={},
        comments={},
        parent_classes=[],
        subclasses=[],
        datatype_properties=[],
        object_properties_out=[],
        object_properties_in=[],
        source_elements=[]
    )
    
    # Create connecting property
    connecting_property = OntologyProperty(
        iri=URIRef("https://example.org/hasOwner"),
        labels={"cs": "má vlastníka"},
        definitions={},
        comments={},
        property_type="ObjectProperty",
        domain=URIRef("https://example.org/Vehicle"),
        range=URIRef("https://example.org/Person"),
        source_elements=[]
    )
    
    # Create ClassNeighborhood
    neighborhood = ClassNeighborhood(
        target_class=target_class,
        connected_classes={"https://example.org/Person": connected_class},
        connecting_properties={"https://example.org/hasOwner": connecting_property}
    )
    
    # Verify structure
    assert neighborhood.target_class == target_class
    assert len(neighborhood.connected_classes) == 1
    assert len(neighborhood.connecting_properties) == 1
    assert "https://example.org/Person" in neighborhood.connected_classes
    assert "https://example.org/hasOwner" in neighborhood.connecting_properties
    
    print("✓ ClassNeighborhood creation working correctly")


def test_similar_class_creation():
    """Test SimilarClass dataclass creation."""
    print("Testing SimilarClass creation...")
    
    # Create class info
    class_info = OntologyClass(
        iri=URIRef("https://example.org/Car"),
        labels={"cs": "Auto", "en": "Car"},
        definitions={"cs": "Osobní automobil"},
        comments={},
        parent_classes=[URIRef("https://example.org/Vehicle")],
        subclasses=[],
        datatype_properties=[],
        object_properties_out=[],
        object_properties_in=[],
        source_elements=[]
    )
    
    # Create SimilarClass
    similar_class = SimilarClass(
        class_info=class_info,
        similarity_score=0.85,
        similarity_basis="labels"
    )
    
    # Verify properties
    assert similar_class.class_info == class_info
    assert similar_class.similarity_score == 0.85
    assert similar_class.similarity_basis == "labels"
    
    print("✓ SimilarClass creation working correctly")


def test_ontology_stats_creation():
    """Test OntologyStats dataclass creation."""
    print("Testing OntologyStats creation...")
    
    # Create OntologyStats
    stats = OntologyStats(
        total_classes=150,
        total_object_properties=75,
        total_datatype_properties=25,
        total_triples=2000,
        classes_with_definitions=120,
        properties_with_domain_range=80
    )
    
    # Verify all properties
    assert stats.total_classes == 150
    assert stats.total_object_properties == 75
    assert stats.total_datatype_properties == 25
    assert stats.total_triples == 2000
    assert stats.classes_with_definitions == 120
    assert stats.properties_with_domain_range == 80
    
    print("✓ OntologyStats creation working correctly")


def test_empty_collections():
    """Test domain models with empty collections."""
    print("Testing domain models with empty collections...")
    
    # Test with empty collections
    minimal_class = OntologyClass(
        iri=URIRef("https://example.org/MinimalClass"),
        labels={},
        definitions={},
        comments={},
        parent_classes=[],
        subclasses=[],
        datatype_properties=[],
        object_properties_out=[],
        object_properties_in=[],
        source_elements=[]
    )
    
    # Verify empty collections are handled properly
    assert len(minimal_class.labels) == 0
    assert len(minimal_class.parent_classes) == 0
    assert len(minimal_class.source_elements) == 0
    
    minimal_property = OntologyProperty(
        iri=URIRef("https://example.org/MinimalProperty"),
        labels={},
        definitions={},
        comments={},
        property_type="ObjectProperty",
        domain=None,
        range=None,
        source_elements=[]
    )
    
    # Verify None values are handled
    assert minimal_property.domain is None
    assert minimal_property.range is None
    assert len(minimal_property.source_elements) == 0
    
    print("✓ Domain models with empty collections working correctly")


def test_uri_ref_handling():
    """Test proper URIRef handling in domain models."""
    print("Testing URIRef handling...")
    
    # Test with various URI formats
    base_uri = "https://example.org/ontology/"
    class_iri = URIRef(base_uri + "TestClass")
    property_iri = URIRef(base_uri + "testProperty")
    
    test_class = OntologyClass(
        iri=class_iri,
        labels={"en": "Test Class"},
        definitions={},
        comments={},
        parent_classes=[URIRef(base_uri + "ParentClass")],
        subclasses=[URIRef(base_uri + "ChildClass")],
        datatype_properties=[URIRef(base_uri + "dataProperty")],
        object_properties_out=[property_iri],
        object_properties_in=[URIRef(base_uri + "incomingProperty")],
        source_elements=[]
    )
    
    # Verify URIRef types are preserved
    assert isinstance(test_class.iri, URIRef)
    assert isinstance(test_class.parent_classes[0], URIRef)
    assert isinstance(test_class.subclasses[0], URIRef)
    assert isinstance(test_class.datatype_properties[0], URIRef)
    assert isinstance(test_class.object_properties_out[0], URIRef)
    assert isinstance(test_class.object_properties_in[0], URIRef)
    
    # Verify URIs are correct
    assert str(test_class.iri) == base_uri + "TestClass"
    assert str(test_class.object_properties_out[0]) == base_uri + "testProperty"
    
    print("✓ URIRef handling working correctly")


def run_all_tests():
    """Run all test functions."""
    print("=" * 50)
    print("Running Ontology Domain Tests")
    print("=" * 50)
    
    test_functions = [
        test_ontology_class_creation,
        test_ontology_property_creation,
        test_datatype_property_creation,
        test_class_neighborhood_creation,
        test_similar_class_creation,
        test_ontology_stats_creation,
        test_empty_collections,
        test_uri_ref_handling
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
