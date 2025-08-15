#!/usr/bin/env python3
"""
Command-line script to load a legal act using the legislation service.

HOW TO RUN:
The virtual environment .venv should be activated before running the script.

From the src directory, run:
    python load_legal_act.py <legal_act_id>

Example:
    python load_legal_act.py https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01

Or from the project root:
    cd src; python load_legal_act.py <legal_act_id>

The script loads the legal act using the legislation service and confirms successful loading.
"""

import sys
import os
from pydantic import AnyUrl

# Add src to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from legislation.service import LegislationService
from legislation.datasource_esel import DataSourceESEL


def main():
    """Main function to load a legal act from command line arguments."""
    
    # Check if legal act ID is provided
    if len(sys.argv) != 2:
        print("Usage: python load_legal_act.py <legal_act_id>")
        print("Example: python load_legal_act.py https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01")
        sys.exit(1)
    
    legal_act_id_str = sys.argv[1]
    
    try:
        # Convert string to AnyUrl for the service
        legal_act_id = AnyUrl(legal_act_id_str)
        
        print(f"Loading legal act: {legal_act_id}")
        print("=" * 60)
        
        # Initialize the datasource and service
        datasource = DataSourceESEL()
        service = LegislationService(datasource, "gpt-4.1")
        
        # Load the legal act
        legal_act = service.get_legal_act(legal_act_id)
        
        # Confirm successful loading
        print("✓ Legal act loaded successfully!")
        print(f"  ID: {legal_act.id}")
        print(f"  Official Identifier: {legal_act.officialIdentifier}")
        print(f"  Title: {legal_act.title}")
        
        if legal_act.summary:
            print(f"  Summary: {legal_act.summary[:100]}{'...' if len(legal_act.summary) > 100 else ''}")
        else:
            print("  Summary: None")
            
        # Count elements
        element_count = len(legal_act.elements) if legal_act.elements else 0
        print(f"  Number of structural elements: {element_count}")
        
        print("=" * 60)
        print("Legal act loading completed successfully!")
        
    except ValueError as e:
        print(f"✗ Invalid legal act ID format: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error loading legal act: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
