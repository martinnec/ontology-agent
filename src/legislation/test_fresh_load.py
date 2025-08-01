"""
Fresh load test for LegislationService to regenerate cached data with correct types.
This test removes any existing cached data and performs a fresh load from SPARQL,
which will create new cached files with proper type information.

HOW TO RUN:
From the src directory, run:
    python -m legislation.test_fresh_load

Or from the project root:
    cd src && python -m legislation.test_fresh_load

This test requires:
- Internet connection for SPARQL queries
- Valid Anthropic API key for summarization
"""

import os
import tempfile

# Set required environment variables for testing
# Note: For real testing, you'll need a valid API key
if not os.environ.get("OPENAI_API_KEY"):
    print("Warning: OPENAI_API_KEY not set. Using dummy key - summarization will fail.")
    os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"

from .service import LegislationService
from .datasource_esel import DataSourceESEL
from .domain import LegalAct, LegalPart, LegalChapter, LegalDivision, LegalSection

def test_fresh_load_with_type_preservation():
    """Test fresh load from SPARQL with type preservation."""
    print("Testing fresh load with type preservation...")
    
    # Remove existing cached file if it exists
    cache_file = os.path.join("..", "data", "legal_acts", "56-2001-2025-07-01.json")
    if os.path.exists(cache_file):
        os.remove(cache_file)
        print(f"Removed existing cache file: {cache_file}")
    
    # Initialize the service
    datasource = DataSourceESEL()
    service = LegislationService(datasource, "gpt-4.1-mini")
    
    # Test legal act ID
    legal_act_id = "https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01"
    
    try:
        print("Starting fresh load from SPARQL endpoint...")
        print("This may take several minutes as it includes:")
        print("- SPARQL data retrieval")
        print("- Structure parsing")
        print("- AI summarization of all elements")
        
        # Perform fresh load - this will:
        # 1. Fetch from SPARQL (since cache was removed)
        # 2. Create proper typed objects 
        # 3. Generate summaries with LLM
        # 4. Save to cache with correct types
        legal_act = service.get_legal_act(legal_act_id)
        
        # Verify the returned object has correct types
        assert isinstance(legal_act, LegalAct), f"Expected LegalAct, got {type(legal_act)}"
        print(f"✓ Root legal act is correct type: {type(legal_act)}")
        
        # Check that cache file was created
        assert os.path.exists(cache_file), "Cache file should have been created"
        print(f"✓ Cache file created: {cache_file}")
        
        # Verify structure and types
        if legal_act.elements:
            print(f"Legal act has {len(legal_act.elements)} top-level elements")
            
            for i, element in enumerate(legal_act.elements):
                print(f"Element {i+1}: {type(element).__name__} - {element.officialIdentifier}")
                
                # Verify specific types
                if element.officialIdentifier.startswith("Část"):
                    assert isinstance(element, LegalPart), f"Part should be LegalPart, got {type(element)}"
                    
                    # Check nested elements
                    if element.elements:
                        for sub_element in element.elements:
                            if sub_element.officialIdentifier.startswith("§"):
                                assert isinstance(sub_element, LegalSection), f"Section should be LegalSection, got {type(sub_element)}"
                            elif "Hlava" in sub_element.officialIdentifier and "Díl" in sub_element.officialIdentifier:
                                assert isinstance(sub_element, LegalDivision), f"Division should be LegalDivision, got {type(sub_element)}"
                            elif "Hlava" in sub_element.officialIdentifier:
                                assert isinstance(sub_element, LegalChapter), f"Chapter should be LegalChapter, got {type(sub_element)}"
        
        print("✓ Fresh load completed successfully with correct types")
        return True
        
    except Exception as e:
        print(f"✗ Fresh load failed: {e}")
        # Print more details for debugging
        import traceback
        traceback.print_exc()
        return False

def test_reload_from_cache_with_types():
    """Test that reloading from cache preserves types."""
    print("Testing reload from cache with preserved types...")
    
    # Initialize the service
    datasource = DataSourceESEL()
    service = LegislationService(datasource, "gpt-4.1-mini")
    
    # Test legal act ID
    legal_act_id = "https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01"
    
    try:
        # Load from cache (should exist from previous test)
        legal_act = service.get_legal_act(legal_act_id)
        
        # Verify types are preserved
        assert isinstance(legal_act, LegalAct), f"Expected LegalAct, got {type(legal_act)}"
        
        # Check nested types
        if legal_act.elements:
            first_element = legal_act.elements[0]
            if first_element.officialIdentifier.startswith("Část"):
                assert isinstance(first_element, LegalPart), f"Expected LegalPart, got {type(first_element)}"
                print(f"✓ First element is correct type: {type(first_element)}")
        
        print("✓ Reload from cache preserved types correctly")
        return True
        
    except Exception as e:
        print(f"✗ Cache reload failed: {e}")
        return False

def run_all_tests():
    """Run all test functions."""
    print("=" * 60)
    print("Running Fresh Load Tests for Type Preservation")
    print("=" * 60)
    print("NOTE: This test requires internet connection and API key")
    print("      It may take several minutes to complete")
    print("=" * 60)
    
    test_functions = [
        test_fresh_load_with_type_preservation,
        test_reload_from_cache_with_types,
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
    
    print("=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
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
