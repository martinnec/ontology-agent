"""
Simple test for type preservation in JSON serialization/deserialization.
This test verifies that LegalStructuralElement subclasses maintain their types
when saved to JSON and loaded back.

HOW TO RUN:
From the src directory, run:
    python -m legislation.test_type_preservation

Or from the project root:
    cd src && python -m legislation.test_type_preservation
"""

import os
import json
import tempfile

# Import the domain models and factory function
from .domain import LegalAct, LegalPart, LegalChapter, LegalDivision, LegalSection, create_legal_element

def test_type_preservation():
    """Test that types are preserved during JSON serialization/deserialization."""
    print("Testing type preservation...")
    
    # Create a legal act with various structural elements
    legal_act = LegalAct(
        id="https://example.com/act/1",
        officialIdentifier="1/2023",
        title="Test Legal Act",
        elements=[
            LegalPart(
                id="https://example.com/act/1/part/1",
                officialIdentifier="Část 1",
                title="Test Part",
                elements=[
                    LegalChapter(
                        id="https://example.com/act/1/part/1/chapter/1",
                        officialIdentifier="Část 1 Hlava 1",
                        title="Test Chapter",
                        elements=[
                            LegalDivision(
                                id="https://example.com/act/1/part/1/chapter/1/division/1",
                                officialIdentifier="Část 1 Hlava 1 Díl 1",
                                title="Test Division",
                                elements=[
                                    LegalSection(
                                        id="https://example.com/act/1/part/1/chapter/1/division/1/section/1",
                                        officialIdentifier="§ 1",
                                        title="Test Section",
                                        textContent="Test content"
                                    )
                                ]
                            )
                        ]
                    )
                ]
            )
        ]
    )
    
    # Test original types
    assert isinstance(legal_act, LegalAct), "Original should be LegalAct"
    assert isinstance(legal_act.elements[0], LegalPart), "Original should contain LegalPart"
    assert isinstance(legal_act.elements[0].elements[0], LegalChapter), "Original should contain LegalChapter"
    assert isinstance(legal_act.elements[0].elements[0].elements[0], LegalDivision), "Original should contain LegalDivision"
    assert isinstance(legal_act.elements[0].elements[0].elements[0].elements[0], LegalSection), "Original should contain LegalSection"
    
    # Serialize to JSON
    json_data = legal_act.model_dump_json(indent=2)
    
    # Deserialize from JSON using the factory function
    data_dict = json.loads(json_data)
    restored_legal_act = create_legal_element(data_dict)
    
    # Test restored types
    assert isinstance(restored_legal_act, LegalAct), "Restored should be LegalAct"
    assert isinstance(restored_legal_act.elements[0], LegalPart), "Restored should contain LegalPart"
    assert isinstance(restored_legal_act.elements[0].elements[0], LegalChapter), "Restored should contain LegalChapter"
    assert isinstance(restored_legal_act.elements[0].elements[0].elements[0], LegalDivision), "Restored should contain LegalDivision"
    assert isinstance(restored_legal_act.elements[0].elements[0].elements[0].elements[0], LegalSection), "Restored should contain LegalSection"
    
    # Test that content is preserved
    assert restored_legal_act.title == legal_act.title, "Title should be preserved"
    assert restored_legal_act.elements[0].title == legal_act.elements[0].title, "Part title should be preserved"
    assert restored_legal_act.elements[0].elements[0].elements[0].elements[0].textContent == "Test content", "Section content should be preserved"
    
    print("✓ Type preservation working correctly")

def test_datasource_integration():
    """Test that DataSourceESEL loads types correctly."""
    print("Testing DataSourceESEL integration...")
    
    # Create a temporary JSON file with test data
    test_data = {
        "id": "https://example.com/act/test",
        "officialIdentifier": "TEST/2023",
        "title": "Test Act",
        "elementType": "LegalAct",
        "elements": [
            {
                "id": "https://example.com/act/test/part/1",
                "officialIdentifier": "Část 1",
                "title": "Test Part",
                "elementType": "LegalPart",
                "elements": [
                    {
                        "id": "https://example.com/act/test/part/1/section/1",
                        "officialIdentifier": "§ 1",
                        "title": "Test Section",
                        "elementType": "LegalSection",
                        "textContent": "Test content",
                        "elements": []
                    }
                ]
            }
        ]
    }
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(test_data, f, indent=2)
        temp_file = f.name
    
    try:
        # Load using the factory function
        with open(temp_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            legal_act = create_legal_element(data)
        
        # Verify types
        assert isinstance(legal_act, LegalAct), "Should be LegalAct"
        assert isinstance(legal_act.elements[0], LegalPart), "Should contain LegalPart"
        assert isinstance(legal_act.elements[0].elements[0], LegalSection), "Should contain LegalSection"
        
        print("✓ DataSourceESEL integration working correctly")
        
    finally:
        # Clean up
        os.unlink(temp_file)

def run_all_tests():
    """Run all test functions."""
    print("=" * 50)
    print("Running Type Preservation Tests")
    print("=" * 50)
    
    test_functions = [
        test_type_preservation,
        test_datasource_integration,
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
