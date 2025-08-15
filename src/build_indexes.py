#!/usr/bin/env python3
"""
Command-line script to load a legal act and build all available indexes.

HOW TO RUN:
The virtual environment .venv should be activated before running the script.

From the src directory, run:
    python build_indexes.py <legal_act_id>

Example:
    python build_indexes.py https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01

Or from the project root:
    cd src; python build_indexes.py <legal_act_id>

The script loads the legal act using the legislation service and builds all available 
indexes (bm25, bm25_full, faiss, faiss_full) using the index service.
Indexes are saved to the project root directory under indexes/.
"""

import sys
import os
from pydantic import AnyUrl

# Add src to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from legislation.service import LegislationService
from legislation.datasource_esel import DataSourceESEL
from index.service import IndexService


def main():
    """Main function to load a legal act and build all indexes from command line arguments."""
    
    # Check if legal act ID is provided
    if len(sys.argv) != 2:
        print("Usage: python build_indexes.py <legal_act_id>")
        print("Example: python build_indexes.py https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01")
        sys.exit(1)
    
    legal_act_id_str = sys.argv[1]
    
    try:
        # Convert string to AnyUrl for the service
        legal_act_id = AnyUrl(legal_act_id_str)
        
        print(f"Loading legal act: {legal_act_id}")
        print("=" * 80)
        
        # Initialize the datasource and legislation service
        datasource = DataSourceESEL()
        legislation_service = LegislationService(datasource, "gpt-4.1")
        
        # Load the legal act
        print("Loading legal act...")
        legal_act = legislation_service.get_legal_act(legal_act_id)
        
        # Confirm successful loading
        print("✓ Legal act loaded successfully!")
        print(f"  ID: {legal_act.id}")
        print(f"  Official Identifier: {legal_act.officialIdentifier}")
        print(f"  Title: {legal_act.title}")
        
        # Count elements
        element_count = len(legal_act.elements) if legal_act.elements else 0
        print(f"  Number of structural elements: {element_count}")
        
        print("=" * 80)
        print("Building all indexes...")
        
        # Initialize the index service - use project root for indexes
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        indexes_dir = os.path.join(project_root, "data", "indexes")
        index_service = IndexService(indexes_dir)
        
        # Get available index types
        available_types = index_service.registry.get_available_types()
        print(f"Available index types: {', '.join(available_types)}")
        print()
        
        # Build all indexes
        index_collection = index_service.build_indexes(legal_act)
        
        print("=" * 80)
        print("Index build results:")
        
        # Check and report on each index type
        all_successful = True
        for index_type in available_types:
            if index_collection.has_index(index_type):
                index_instance = index_collection.get_index(index_type)
                if index_instance is not None:
                    print(f"✓ {index_type}: Successfully built")
                else:
                    print(f"✗ {index_type}: Build failed (instance is None)")
                    all_successful = False
            else:
                print(f"✗ {index_type}: Not found in collection")
                all_successful = False
        
        print("=" * 80)
        
        if all_successful:
            print("🎉 All indexes built successfully!")
            print(f"Indexes saved to: {indexes_dir}/{index_service._get_act_identifier(legal_act)}/")
        else:
            print("⚠️  Some indexes failed to build. Check the output above for details.")
            sys.exit(1)
        
    except ValueError as e:
        print(f"✗ Invalid legal act ID format: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error processing legal act: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
