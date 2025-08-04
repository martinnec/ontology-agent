"""
End-to-end integration test for SearchService with real data.

HOW TO RUN:
The virtual environment .venv should be activated before running the tests.

From the src directory, run:
    python -m search.test_e2e_integration

Or from the project root:
    cd src; python -m search.test_e2e_integration

This test validates the complete integration between IndexService and SearchService
using real legal act data.
"""

import os
# Set dummy environment variable for testing
os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"

def test_real_data_integration():
    """Test end-to-end integration with real legal act data."""
    print("=" * 60)
    print("End-to-End Integration Test with Real Data")
    print("=" * 60)
    
    try:
        # Import required modules
        from legislation.service import LegislationService
        from legislation.datasource_esel import DataSourceESEL
        from index import IndexService
        from search.service import SearchService
        from search.domain import SearchStrategy, SearchOptions
        
        print("Loading real legal act 56/2001...")
        
        # Load real legal act
        data_source = DataSourceESEL()
        legislation_service = LegislationService(data_source, llm_model_identifier="gpt-4.1-mini")
        legal_act_id = "https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01"
        legal_act = legislation_service.get_legal_act(legal_act_id)
        
        if not legal_act:
            print("✗ Failed to load legal act")
            return False
        
        print(f"✓ Loaded legal act: {legal_act.title}")
        
        # Initialize IndexService and build indexes
        print("\\nBuilding indexes...")
        index_service = IndexService("./test_indexes")
        
        # Build only BM25 index for faster testing
        collection = index_service.build_indexes(legal_act, ["bm25"])
        print(f"✓ Built indexes: {', '.join(collection.get_available_indexes())}")
        print(f"✓ Processed {collection.get_document_count()} documents")
        
        # Initialize SearchService
        print("\\nInitializing SearchService...")
        search_service = SearchService(index_service, legal_act)
        print("✓ SearchService initialized")
        
        # Test keyword search
        print("\\nTesting keyword search...")
        query = "registrace vozidla"
        results = search_service.search_keyword(query)
        
        print(f"✓ Found {results.total_found} results for '{query}'")
        print(f"✓ Search took {results.search_time_ms:.2f}ms")
        
        if results.items:
            top_result = results.items[0]
            print(f"✓ Top result: {top_result.title} (score: {top_result.score:.3f})")
        
        # Test search with options
        print("\\nTesting search with options...")
        options = SearchOptions(max_results=3, element_types=["section"])
        results_filtered = search_service.search_keyword(query, options)
        
        print(f"✓ Found {results_filtered.total_found} filtered results")
        print(f"✓ Applied filters: {results_filtered.filters_applied}")
        
        # Test index info
        print("\\nTesting index info...")
        info = search_service.get_index_info()
        print(f"✓ Available indexes: {info['available_indexes']}")
        print(f"✓ Document count: {info['document_count']}")
        
        # Clean up
        print("\\nCleaning up...")
        index_service.clear_indexes(legal_act)
        print("✓ Indexes cleared")
        
        print("\\n" + "=" * 60)
        print("✅ END-TO-END INTEGRATION TEST PASSED")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\\n✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run the end-to-end test."""
    success = test_real_data_integration()
    if success:
        print("End-to-end integration test completed successfully!")
        return 0
    else:
        print("End-to-end integration test failed!")
        return 1

if __name__ == "__main__":
    exit(main())
