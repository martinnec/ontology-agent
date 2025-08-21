"""
Integration test for the ontology service.

HOW TO RUN:
The virtual environment .venv should be activated before running the tests.

From the src directory, run:
    python -m ontology.test_service

Or from the project root:
    cd src; python -m ontology.test_service

The test uses mock implementations to avoid external dependencies.
"""

import os
# Set any required environment variables for testing
os.environ["OPENAI_API_KEY"] = "dummy-api-key-for-testing"

# Import statements using relative imports
from .service import OntologyService
from .store import OntologyStore
from .domain import ClassNeighborhood, SimilarClass, OntologyProperty
from rdflib import URIRef


class MockOntologyStore:
    """Mock implementation of OntologyStore for testing."""
    
    def __init__(self):
        self.classes = {}
        self.properties = {}
        # Pre-populate with test data
        self.setup_test_data()
    
    def setup_test_data(self):
        """Setup test data for comprehensive testing."""
        from .domain import OntologyClass, OntologyProperty
        
        # Test class
        test_class = OntologyClass(
            iri=URIRef("https://example.org/Vehicle"),
            prefLabels={"cs": "Vozidlo", "en": "Vehicle"},
            definitions={"cs": "Dopravní prostředek", "en": "Transportation device"},
            comments={"cs": "Poznámka", "en": "Comment"},
            parent_classes=[URIRef("https://example.org/MovableObject")],
            subclasses=[URIRef("https://example.org/Car")],
            datatype_properties=[URIRef("https://example.org/hasWeight")],
            object_properties_out=[URIRef("https://example.org/hasOwner")],
            object_properties_in=[URIRef("https://example.org/isOwnedBy")],
            source_elements=["legal_element_1"]
        )
        self.classes[URIRef("https://example.org/Vehicle")] = test_class
        
        # Test property
        test_property = OntologyProperty(
            iri=URIRef("https://example.org/hasOwner"),
            prefLabels={"cs": "má vlastníka", "en": "has owner"},
            definitions={"cs": "Vztah vlastnictví", "en": "Ownership relationship"},
            comments={},
            property_type="ObjectProperty",
            domain=URIRef("https://example.org/Vehicle"),
            range=URIRef("https://example.org/Person"),
            source_elements=["legal_element_2"]
        )
        self.properties[URIRef("https://example.org/hasOwner")] = test_property
    
    def get_whole_ontology(self):
        return {
            "classes": [
                {
                    "iri": "https://example.org/Vehicle",
                    "labels": {"cs": "Vozidlo", "en": "Vehicle"}
                }
            ],
            "object_properties": [
                {
                    "iri": "https://example.org/hasOwner",
                    "labels": {"cs": "má vlastníka", "en": "has owner"}
                }
            ],
            "datatype_properties": [],
            "stats": {"total_classes": 1, "total_properties": 1}
        }
    
    def get_class(self, class_iri):
        return self.classes.get(class_iri)
    
    def get_class_with_surroundings(self, class_iri):
        if class_iri in self.classes:
            return {
                "connected_classes": {"https://example.org/Person": self.classes.get(URIRef("https://example.org/Person"))},
                "connecting_properties": {"https://example.org/hasOwner": self.properties.get(URIRef("https://example.org/hasOwner"))}
            }
        return {"connected_classes": {}, "connecting_properties": {}}
    
    def get_property_details(self, property_iri):
        return self.properties.get(property_iri)
    
    def get_class_hierarchy(self, class_iri):
        if class_iri in self.classes:
            return {
                "parents": [URIRef("https://example.org/MovableObject")],
                "subclasses": [URIRef("https://example.org/Car")]
            }
        return {"parents": [], "subclasses": []}
    
    def find_similar_classes(self, class_iri, limit=10):
        if class_iri in self.classes:
            return [(URIRef("https://example.org/Car"), 0.85), (URIRef("https://example.org/Truck"), 0.75)]
        return []
    
    def add_class(self, ontology_class):
        self.classes[ontology_class.iri] = ontology_class
        return True
    
    def add_property(self, ontology_property):
        self.properties[ontology_property.iri] = ontology_property
        return True
    
    def update_class(self, ontology_class):
        if ontology_class.iri in self.classes:
            self.classes[ontology_class.iri] = ontology_class
            return True
        return False
    
    def update_property(self, ontology_property):
        if ontology_property.iri in self.properties:
            self.properties[ontology_property.iri] = ontology_property
            return True
        return False
    
    def remove_class(self, class_iri):
        if class_iri in self.classes:
            del self.classes[class_iri]
            return True
        return False
    
    def remove_property(self, property_iri):
        if property_iri in self.properties:
            del self.properties[property_iri]
            return True
        return False


def test_service_initialization():
    """Test OntologyService initialization."""
    print("Testing OntologyService initialization...")
    
    # Test with default store
    service = OntologyService()
    assert service.store is not None
    assert isinstance(service.store, OntologyStore)
    
    # Test with custom store
    mock_store = MockOntologyStore()
    service_with_mock = OntologyService(store=mock_store)
    assert service_with_mock.store is mock_store
    
    print("✓ OntologyService initialization working correctly")


def test_get_working_ontology():
    """Test getting complete working ontology."""
    print("Testing get_working_ontology...")
    
    service = OntologyService()
    ontology = service.get_working_ontology()
    
    # Should return dictionary with required structure
    assert isinstance(ontology, dict)
    assert "classes" in ontology
    assert "object_properties" in ontology
    assert "datatype_properties" in ontology
    assert "stats" in ontology
    
    print("✓ get_working_ontology working correctly")


def test_get_working_ontology_with_mock_data():
    """Test getting working ontology with populated mock data."""
    print("Testing get_working_ontology with mock data...")
    
    mock_store = MockOntologyStore()
    service = OntologyService(store=mock_store)
    ontology = service.get_working_ontology()
    
    # Verify structure and content
    assert isinstance(ontology, dict)
    assert len(ontology["classes"]) == 1
    assert len(ontology["object_properties"]) == 1
    assert ontology["classes"][0]["iri"] == "https://example.org/Vehicle"
    assert ontology["stats"]["total_classes"] == 1
    
    print("✓ get_working_ontology with mock data working correctly")


def test_get_class_neighborhood_success():
    """Test successful class neighborhood retrieval."""
    print("Testing get_class_neighborhood success case...")
    
    mock_store = MockOntologyStore()
    service = OntologyService(store=mock_store)
    
    neighborhood = service.get_class_neighborhood("https://example.org/Vehicle")
    
    # Verify structure
    assert isinstance(neighborhood, ClassNeighborhood)
    assert neighborhood.target_class is not None
    assert neighborhood.target_class.iri == URIRef("https://example.org/Vehicle")
    assert isinstance(neighborhood.connected_classes, dict)
    assert isinstance(neighborhood.connecting_properties, dict)
    
    print("✓ get_class_neighborhood success case working correctly")


def test_class_neighborhood_not_found():
    """Test get_class_neighborhood with non-existent class."""
    print("Testing get_class_neighborhood with non-existent class...")
    
    service = OntologyService()
    
    try:
        result = service.get_class_neighborhood("https://example.org/NonExistent")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Class not found" in str(e)
        print("✓ get_class_neighborhood correctly handles non-existent class")


def test_get_similar_classes_success():
    """Test successful similar classes retrieval."""
    print("Testing get_similar_classes success case...")
    
    mock_store = MockOntologyStore()
    service = OntologyService(store=mock_store)
    
    # Add a Car class to mock for similar classes test
    from .domain import OntologyClass
    car_class = OntologyClass(
        iri=URIRef("https://example.org/Car"),
        prefLabels={"cs": "Auto", "en": "Car"},
        definitions={"cs": "Osobní automobil"},
        comments={},
        parent_classes=[URIRef("https://example.org/Vehicle")],
        subclasses=[],
        datatype_properties=[],
        object_properties_out=[],
        object_properties_in=[],
        source_elements=[]
    )
    mock_store.classes[URIRef("https://example.org/Car")] = car_class
    
    similar_classes = service.get_similar_classes("https://example.org/Vehicle")
    
    # Verify structure  
    assert isinstance(similar_classes, list)
    assert len(similar_classes) == 1  # Only one class exists in mock
    assert isinstance(similar_classes[0], SimilarClass)
    assert similar_classes[0].similarity_score == 0.85
    assert similar_classes[0].similarity_basis == "combined"
    
    print("✓ get_similar_classes success case working correctly")


def test_get_similar_classes_with_limit():
    """Test similar classes retrieval with custom limit."""
    print("Testing get_similar_classes with limit...")
    
    mock_store = MockOntologyStore()
    service = OntologyService(store=mock_store)
    
    # Test with different limits
    similar_classes_5 = service.get_similar_classes("https://example.org/Vehicle", limit=5)
    similar_classes_1 = service.get_similar_classes("https://example.org/Vehicle", limit=1)
    
    # Mock returns 2 similar classes, but only one exists in store
    assert isinstance(similar_classes_5, list)
    assert isinstance(similar_classes_1, list)
    assert len(similar_classes_1) <= 1
    
    print("✓ get_similar_classes with limit working correctly")


def test_similar_classes_not_found():
    """Test get_similar_classes with non-existent class."""
    print("Testing get_similar_classes with non-existent class...")
    
    service = OntologyService()
    
    try:
        result = service.get_similar_classes("https://example.org/NonExistent")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Class not found" in str(e)
        print("✓ get_similar_classes correctly handles non-existent class")


def test_get_property_details_success():
    """Test successful property details retrieval."""
    print("Testing get_property_details success case...")
    
    mock_store = MockOntologyStore()
    service = OntologyService(store=mock_store)
    
    property_details = service.get_property_details("https://example.org/hasOwner")
    
    # Verify structure
    assert isinstance(property_details, OntologyProperty)
    assert property_details.iri == URIRef("https://example.org/hasOwner")
    assert property_details.property_type == "ObjectProperty"
    assert property_details.domain == URIRef("https://example.org/Vehicle")
    assert property_details.range == URIRef("https://example.org/Person")
    
    print("✓ get_property_details success case working correctly")


def test_property_details_not_found():
    """Test get_property_details with non-existent property."""
    print("Testing get_property_details with non-existent property...")
    
    service = OntologyService()
    
    try:
        result = service.get_property_details("https://example.org/nonExistentProperty")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Property not found" in str(e)
        print("✓ get_property_details correctly handles non-existent property")


def test_get_class_hierarchy_success():
    """Test successful class hierarchy retrieval."""
    print("Testing get_class_hierarchy success case...")
    
    mock_store = MockOntologyStore()
    service = OntologyService(store=mock_store)
    
    hierarchy = service.get_class_hierarchy("https://example.org/Vehicle")
    
    # Verify structure
    assert isinstance(hierarchy, dict)
    assert "parents" in hierarchy
    assert "subclasses" in hierarchy
    assert len(hierarchy["parents"]) == 1
    assert len(hierarchy["subclasses"]) == 1
    assert hierarchy["parents"][0] == URIRef("https://example.org/MovableObject")
    assert hierarchy["subclasses"][0] == URIRef("https://example.org/Car")
    
    print("✓ get_class_hierarchy success case working correctly")


def test_search_by_concept_empty_input():
    """Test search_by_concept with empty input."""
    print("Testing search_by_concept with empty input...")
    
    service = OntologyService()
    
    # Test with empty string
    results_empty = service.search_by_concept("")
    assert results_empty == []
    
    # Test with whitespace only
    results_whitespace = service.search_by_concept("   \t\n   ")
    assert results_whitespace == []
    
    print("✓ search_by_concept with empty input working correctly")


def test_add_extraction_results_invalid_data():
    """Test add_extraction_results with invalid data."""
    print("Testing add_extraction_results with invalid data...")
    
    service = OntologyService()
    
    # Test with invalid concept type
    invalid_concepts = [
        {"type": "invalid_type", "name_en": "Test"}
    ]
    result = service.add_extraction_results(invalid_concepts)
    assert result is False
    
    # Test with missing required fields
    incomplete_concepts = [
        {"type": "class"}  # Missing name
    ]
    result = service.add_extraction_results(incomplete_concepts)
    assert result is False
    
    print("✓ add_extraction_results with invalid data working correctly")


def test_add_extraction_results_valid_class():
    """Test add_extraction_results with valid class data."""
    print("Testing add_extraction_results with valid class...")
    
    mock_store = MockOntologyStore()
    service = OntologyService(store=mock_store)
    
    valid_class_concepts = [
        {
            "type": "class",
            "name_cs": "Testovací vozidlo",
            "name_en": "Test Vehicle",
            "definition_cs": "Vozidlo pro testování",
            "definition_en": "Vehicle for testing",
            "source_element": "test_element"
        }
    ]
    
    result = service.add_extraction_results(valid_class_concepts)
    assert result is True
    
    print("✓ add_extraction_results with valid class working correctly")


def test_add_class():
    """Test add_class functionality."""
    print("Testing add_class basic functionality...")
    
    mock_store = MockOntologyStore()
    service = OntologyService(store=mock_store)
    
    # Test adding a class with generated IRI
    result = service.add_class(
        iri="",
        name_en="TestClass",
        name_cs="TestTrida",
        definition_en="Test definition",
        definition_cs="Test definice",
        comment_en="Test comment",
        comment_cs="Test komentar",
        parent_class_iri="https://example.org/ParentClass",
        source_element="test_element"
    )
    assert result is True
    
    # Test adding a class with provided IRI
    result = service.add_class(
        iri="https://example.org/ontology/CustomClass",
        name_en="CustomClass",
        definition_en="Custom definition"
    )
    assert result is True
    
    print("✓ add_class basic functionality working correctly")


def test_add_class_invalid_data():
    """Test add_class with invalid data."""
    print("Testing add_class with invalid data...")
    
    mock_store = MockOntologyStore()
    service = OntologyService(store=mock_store)
    
    # Test with no IRI and no names
    result = service.add_class(iri="")
    assert result is False
    
    print("✓ add_class with invalid data working correctly")


def test_update_class():
    """Test update_class functionality."""
    print("Testing update_class...")
    
    mock_store = MockOntologyStore()
    service = OntologyService(store=mock_store)
    
    # First add a class
    iri = "https://example.org/ontology/UpdateTestClass"
    result = service.add_class(
        iri=iri,
        name_en="UpdateTestClass",
        definition_en="Original definition"
    )
    assert result is True
    
    # Now update it
    result = service.update_class(
        iri=iri,
        name_en="UpdatedTestClass",
        definition_en="Updated definition",
        comment_en="New comment"
    )
    assert result is True
    
    print("✓ update_class working correctly")


def test_remove_class():
    """Test remove_class functionality."""
    print("Testing remove_class...")
    
    mock_store = MockOntologyStore()
    service = OntologyService(store=mock_store)
    
    # First add a class
    iri = "https://example.org/ontology/RemoveTestClass"
    result = service.add_class(
        iri=iri,
        name_en="RemoveTestClass",
        definition_en="Test definition"
    )
    assert result is True
    
    # Now remove it
    result = service.remove_class(iri)
    assert result is True
    
    print("✓ remove_class working correctly")


def test_add_property():
    """Test add_property functionality."""
    print("Testing add_property...")
    
    mock_store = MockOntologyStore()
    service = OntologyService(store=mock_store)
    
    # Test adding an object property
    result = service.add_property(
        iri="https://example.org/ontology/testProperty",
        property_type="ObjectProperty",
        name_en="testProperty",
        name_cs="testVlastnost",
        definition_en="Test property definition",
        definition_cs="Test definice vlastnosti",
        domain_iri="https://example.org/TestClass",
        range_iri="https://example.org/TestRange",
        source_element="test_element"
    )
    assert result is True
    
    # Test adding a datatype property
    result = service.add_property(
        iri="https://example.org/ontology/testDataProperty",
        property_type="DatatypeProperty",
        name_en="testDataProperty",
        definition_en="Test data property",
        domain_iri="https://example.org/TestClass",
        range_iri="string"
    )
    assert result is True
    
    print("✓ add_property working correctly")


def test_add_property_invalid_data():
    """Test add_property with invalid data."""
    print("Testing add_property with invalid data...")
    
    mock_store = MockOntologyStore()
    service = OntologyService(store=mock_store)
    
    # Test with invalid property type
    result = service.add_property(
        iri="https://example.org/ontology/invalidProperty",
        property_type="InvalidType",
        name_en="invalidProperty"
    )
    assert result is False
    
    # Test with no IRI and no names
    result = service.add_property(
        iri="",
        property_type="ObjectProperty"
    )
    assert result is False
    
    print("✓ add_property with invalid data working correctly")


def test_update_property():
    """Test update_property functionality."""
    print("Testing update_property...")
    
    mock_store = MockOntologyStore()
    service = OntologyService(store=mock_store)
    
    # First add a property
    iri = "https://example.org/ontology/updateTestProperty"
    result = service.add_property(
        iri=iri,
        property_type="ObjectProperty",
        name_en="updateTestProperty",
        definition_en="Original definition"
    )
    assert result is True
    
    # Now update it
    result = service.update_property(
        iri=iri,
        name_en="updatedTestProperty",
        definition_en="Updated definition",
        comment_en="New comment"
    )
    assert result is True
    
    print("✓ update_property working correctly")


def test_remove_property():
    """Test remove_property functionality."""
    print("Testing remove_property...")
    
    mock_store = MockOntologyStore()
    service = OntologyService(store=mock_store)
    
    # First add a property
    iri = "https://example.org/ontology/removeTestProperty"
    result = service.add_property(
        iri=iri,
        property_type="ObjectProperty",
        name_en="removeTestProperty",
        definition_en="Test definition"
    )
    assert result is True
    
    # Now remove it
    result = service.remove_property(iri)
    assert result is True
    
    print("✓ remove_property working correctly")


def test_update_nonexistent_class():
    """Test updating a class that doesn't exist."""
    print("Testing update of nonexistent class...")
    
    mock_store = MockOntologyStore()
    service = OntologyService(store=mock_store)
    
    result = service.update_class(
        iri="https://example.org/ontology/NonexistentClass",
        definition_en="Updated definition"
    )
    assert result is False
    
    print("✓ Update of nonexistent class handled correctly")


def test_remove_nonexistent_class():
    """Test removing a class that doesn't exist."""
    print("Testing remove of nonexistent class...")
    
    mock_store = MockOntologyStore()
    service = OntologyService(store=mock_store)
    
    result = service.remove_class("https://example.org/ontology/NonexistentClass")
    assert result is False
    
    print("✓ Remove of nonexistent class handled correctly")


def test_update_nonexistent_property():
    """Test updating a property that doesn't exist."""
    print("Testing update of nonexistent property...")
    
    mock_store = MockOntologyStore()
    service = OntologyService(store=mock_store)
    
    result = service.update_property(
        iri="https://example.org/ontology/NonexistentProperty",
        definition_en="Updated definition"
    )
    assert result is False
    
    print("✓ Update of nonexistent property handled correctly")


def test_remove_nonexistent_property():
    """Test removing a property that doesn't exist."""
    print("Testing remove of nonexistent property...")
    
    mock_store = MockOntologyStore()
    service = OntologyService(store=mock_store)
    
    result = service.remove_property("https://example.org/ontology/NonexistentProperty")
    assert result is False
    
    print("✓ Remove of nonexistent property handled correctly")


def run_all_tests():
    """Run all test functions."""
    print("=" * 50)
    print("Running OntologyService Tests")
    print("=" * 50)
    
    test_functions = [
        test_service_initialization,
        test_get_working_ontology,
        test_get_working_ontology_with_mock_data,
        test_get_class_neighborhood_success,
        test_get_similar_classes_success,
        test_get_similar_classes_with_limit,
        test_similar_classes_not_found,
        test_get_property_details_success,
        test_get_class_hierarchy_success,
        test_search_by_concept_empty_input,
        test_add_class,
        test_add_class_invalid_data,
        test_update_class,
        test_remove_class,
        test_add_property,
        test_add_property_invalid_data,
        test_update_property,
        test_remove_property,
        test_update_nonexistent_class,
        test_remove_nonexistent_class,
        test_update_nonexistent_property,
        test_remove_nonexistent_property
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
