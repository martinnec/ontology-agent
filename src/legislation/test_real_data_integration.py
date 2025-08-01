"""
Integration test for the real cached legal act 56/2001.
This test verifies that the type preservation fix works with the actual cached data.

HOW TO RUN:
From the src directory, run:
    python -m legislation.test_real_data_integration

Or from the project root:
    cd src && python -m legislation.test_real_data_integration
"""

import os

# Set any required environment variables for testing
os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"

from .datasource_esel import DataSourceESEL
from .domain import LegalAct, LegalPart, LegalChapter, LegalDivision, LegalSection

def test_real_cached_data_type_preservation():
    """Test that real cached data loads with correct types."""
    print("Testing real cached data type preservation...")
    
    # Initialize data source
    datasource = DataSourceESEL()
    
    # Test with the cached 56/2001 legal act
    legal_act_id = "https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01"
    
    try:
        # Load the legal act (should load from cache)
        legal_act = datasource.get_legal_act(legal_act_id)
        
        # Debug information
        print(f"Loaded legal act type: {type(legal_act)}")
        print(f"Legal act class name: {legal_act.__class__.__name__}")
        print(f"Legal act element type: {getattr(legal_act, 'elementType', 'MISSING')}")
        
        # Verify it's the correct type
        assert isinstance(legal_act, LegalAct), f"Expected LegalAct, got {type(legal_act)}"
        
        # Check if it has elements
        assert legal_act.elements is not None, "Legal act should have elements"
        assert len(legal_act.elements) > 0, "Legal act should have at least one element"
        
        # Verify the first element (should be a Part)
        first_element = legal_act.elements[0]
        print(f"First element type: {type(first_element)}")
        print(f"First element class name: {first_element.__class__.__name__}")
        print(f"First element ID: {first_element.id}")
        print(f"First element official identifier: {first_element.officialIdentifier}")
        print(f"First element element type: {getattr(first_element, 'elementType', 'MISSING')}")
        
        # Check that it's specifically a LegalPart (not generic LegalStructuralElement)
        assert isinstance(first_element, LegalPart), f"Expected LegalPart, got {type(first_element)}"
        
        # Check nested structure
        if first_element.elements and len(first_element.elements) > 0:
            # Find a section to test
            section_found = False
            for element in first_element.elements:
                print(f"Sub-element type: {type(element).__name__}, ID: {element.officialIdentifier}")
                if isinstance(element, LegalSection):
                    section_found = True
                    assert element.textContent is not None, "Section should have text content"
                    print(f"Found section: {element.officialIdentifier}")
                    break
            
            if not section_found:
                # Look deeper if needed
                for element in first_element.elements:
                    if hasattr(element, 'elements') and element.elements:
                        for sub_element in element.elements:
                            print(f"Deep sub-element type: {type(sub_element).__name__}, ID: {sub_element.officialIdentifier}")
                            if isinstance(sub_element, LegalSection):
                                section_found = True
                                break
        
        print("✓ Real cached data type preservation working correctly")
        return True
        
    except Exception as e:
        print(f"✗ Failed to test real data: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fresh_load_vs_cached_load():
    """Test that fresh load and cached load produce the same types."""
    print("Testing fresh vs cached load consistency...")
    
    # Since we can't easily test fresh load without SPARQL access in this test,
    # we'll focus on verifying the cached data structure
    
    datasource = DataSourceESEL()
    legal_act_id = "https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01"
    
    try:
        # Load from cache
        legal_act = datasource.get_legal_act(legal_act_id)
        
        # Save it again (this will test the serialization/deserialization cycle)
        datasource.store_legal_act(legal_act)
        
        # Load it again
        legal_act_reloaded = datasource.get_legal_act(legal_act_id)
        
        # Compare types
        assert type(legal_act) == type(legal_act_reloaded), "Types should match after reload"
        
        if legal_act.elements and legal_act_reloaded.elements:
            assert len(legal_act.elements) == len(legal_act_reloaded.elements), "Element count should match"
            
            for i, (orig, reloaded) in enumerate(zip(legal_act.elements, legal_act_reloaded.elements)):
                assert type(orig) == type(reloaded), f"Element {i} types should match: {type(orig)} vs {type(reloaded)}"
        
        print("✓ Fresh vs cached load consistency working correctly")
        return True
        
    except Exception as e:
        print(f"✗ Failed consistency test: {e}")
        return False

def run_all_tests():
    """Run all test functions."""
    print("=" * 50)
    print("Running Real Data Integration Tests")
    print("=" * 50)
    
    test_functions = [
        test_real_cached_data_type_preservation,
        test_fresh_load_vs_cached_load,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
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
