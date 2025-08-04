"""
Demo script for IndexService - demonstrating unified index management.

This demo shows how to use the IndexService to build and manage indexes
for legal acts in a consistent way.

HOW TO RUN:
From the src directory, run:
    python -m index.demo_index_service

Or from the project root:
    cd src && python -m index.demo_index_service

The demo uses a real legal act if available, or creates mock data for demonstration.
"""

import os
import sys
from pathlib import Path

def get_legal_act():
    """Get a legal act for demonstration."""
    try:
        # Try to load a real legal act if legislation module is available
        from legislation.service import LegislationService
        from legislation.datasource_esel import DataSourceESEL
        
        print("Loading real legal act 56/2001...")
        
        # Initialize service with real data source and LLM model
        data_source = DataSourceESEL()
        service = LegislationService(data_source, llm_model_identifier="gpt-4.1-mini")
        
        # Load the legal act using the correct ELI identifier
        legal_act_id = "https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01"
        legal_act = service.get_legal_act(legal_act_id)
        if legal_act:
            print(f"✓ Loaded real legal act: {legal_act.title}")
            return legal_act
        else:
            print("! Could not load real legal act, using mock data")
            return create_mock_legal_act()
            
    except Exception as e:
        print(f"! Could not load real legal act ({e}), using mock data")
        return create_mock_legal_act()

def create_mock_legal_act():
    """Create a mock legal act for demonstration."""
    print("Creating mock legal act for demonstration...")
    
    class MockLegalElement:
        def __init__(self, id: str, element_type: str, title: str, 
                     official_identifier: str, summary: str = None, 
                     text_content: str = None, elements: list = None):
            self.id = id
            self.elementType = element_type
            self.title = title
            self.officialIdentifier = official_identifier
            self.summary = summary
            self.summary_names = None
            self.textContent = text_content
            self.elements = elements or []
    
    # Create a hierarchical structure
    section1 = MockLegalElement(
        id="https://example.com/section/1",
        element_type="LegalSection",
        title="Základní pojmy",
        official_identifier="§ 1",
        summary="Definice základních pojmů používaných v tomto zákoně",
        text_content="V tomto zákoně se rozumí základními pojmy..."
    )
    
    section2 = MockLegalElement(
        id="https://example.com/section/2", 
        element_type="LegalSection",
        title="Registrace vozidel",
        official_identifier="§ 2",
        summary="Postupy a požadavky pro registraci motorových vozidel",
        text_content="Motorová vozidla musí být registrována před uvedením do provozu..."
    )
    
    section3 = MockLegalElement(
        id="https://example.com/section/3",
        element_type="LegalSection", 
        title="Technická kontrola",
        official_identifier="§ 3",
        summary="Pravidla a postupy pro provádění technické kontroly vozidel",
        text_content="Technická kontrola se provádí v pravidelných intervalech..."
    )
    
    chapter1 = MockLegalElement(
        id="https://example.com/chapter/1",
        element_type="LegalChapter",
        title="Obecná ustanovení",
        official_identifier="Hlava I",
        summary="Základní ustanovení a definice",
        elements=[section1, section2]
    )
    
    chapter2 = MockLegalElement(
        id="https://example.com/chapter/2", 
        element_type="LegalChapter",
        title="Technické požadavky",
        official_identifier="Hlava II",
        summary="Technické požadavky na vozidla",
        elements=[section3]
    )
    
    legal_act = MockLegalElement(
        id="https://example.com/act/demo-act",
        element_type="LegalAct",
        title="Demo zákon o silničním provozu",
        official_identifier="Zákon č. 123/2024 Sb.",
        summary="Demonstrační zákon upravující pravidla silničního provozu",
        elements=[chapter1, chapter2]
    )
    
    print(f"✓ Created mock legal act: {legal_act.title}")
    return legal_act

def demo_index_building():
    """Demonstrate building indexes for a legal act."""
    print("\n" + "="*60)
    print("DEMO: Building Indexes")
    print("="*60)
    
    # Import IndexService
    from index import IndexService
    
    # Initialize IndexService
    output_dir = "./demo_indexes"
    print(f"Initializing IndexService with output directory: {output_dir}")
    index_service = IndexService(output_dir=output_dir)
    
    # Get legal act
    legal_act = get_legal_act()
    
    # Show available index types
    available_types = index_service.get_available_index_types()
    print(f"\nAvailable index types: {', '.join(available_types)}")
    
    # Build specific index types (using mock builders to avoid dependencies)
    print(f"\nBuilding BM25 index for: {legal_act.title}")
    try:
        collection = index_service.build_indexes(legal_act, index_types=["bm25"])
        print(f"✓ Successfully built BM25 index")
        print(f"  - Documents processed: {collection.get_document_count()}")
        print(f"  - Available indexes: {', '.join(collection.get_available_indexes())}")
    except Exception as e:
        print(f"✗ Failed to build BM25 index: {e}")
        print("  (This is expected if index builders have external dependencies)")
    
    # Try building all indexes
    print(f"\nBuilding all available indexes...")
    try:
        collection = index_service.build_indexes(legal_act)
        print(f"✓ Successfully built all indexes")
        print(f"  - Documents processed: {collection.get_document_count()}")
        print(f"  - Available indexes: {', '.join(collection.get_available_indexes())}")
        
        # Show some document details
        documents = collection.get_documents()
        print(f"\nDocument structure:")
        for doc in documents[:5]:  # Show first 5 documents
            print(f"  - {doc.element_type.value}: {doc.title} (Level {doc.level})")
            
    except Exception as e:
        print(f"✗ Failed to build all indexes: {e}")
        print("  (This is expected if index builders have external dependencies)")

def demo_index_retrieval():
    """Demonstrate retrieving existing indexes."""
    print("\n" + "="*60)
    print("DEMO: Retrieving Indexes")
    print("="*60)
    
    from index import IndexService
    
    # Initialize IndexService
    index_service = IndexService(output_dir="./demo_indexes")
    legal_act = get_legal_act()
    
    # Check if indexes exist
    print("Checking index existence:")
    for index_type in index_service.get_available_index_types():
        exists = index_service.index_exists(legal_act, index_type)
        status = "✓ EXISTS" if exists else "✗ MISSING"
        print(f"  - {index_type}: {status}")
    
    # Try to get indexes (will build if not exists, load if exists)
    print(f"\nGetting indexes for: {legal_act.title}")
    try:
        collection = index_service.get_indexes(legal_act, force_rebuild=False)
        print(f"✓ Successfully retrieved indexes")
        print(f"  - Available indexes: {', '.join(collection.get_available_indexes())}")
        print(f"  - Documents: {collection.get_document_count()}")
        
        # Try to get specific index
        bm25_index = collection.get_index('bm25')
        if bm25_index:
            print(f"  - BM25 index: Available")
        else:
            print(f"  - BM25 index: Not available")
            
    except Exception as e:
        print(f"✗ Failed to retrieve indexes: {e}")

def demo_force_rebuild():
    """Demonstrate force rebuilding indexes."""
    print("\n" + "="*60)
    print("DEMO: Force Rebuilding Indexes")
    print("="*60)
    
    from index import IndexService
    
    index_service = IndexService(output_dir="./demo_indexes")
    legal_act = get_legal_act()
    
    print("Force rebuilding all indexes...")
    try:
        collection = index_service.get_indexes(legal_act, force_rebuild=True)
        print(f"✓ Successfully force rebuilt indexes")
        print(f"  - Available indexes: {', '.join(collection.get_available_indexes())}")
        
    except Exception as e:
        print(f"✗ Failed to force rebuild: {e}")

def demo_index_management():
    """Demonstrate index management operations."""
    print("\n" + "="*60)
    print("DEMO: Index Management")
    print("="*60)
    
    from index import IndexService
    
    index_service = IndexService(output_dir="./demo_indexes")
    legal_act = get_legal_act()
    
    # Show index information
    print("Index Service Information:")
    print(f"  - Output directory: {index_service.output_dir}")
    print(f"  - Available index types: {', '.join(index_service.get_available_index_types())}")
    
    # Demonstrate clearing indexes
    print(f"\nClearing all indexes for: {legal_act.title}")
    try:
        # Debug: Show what identifier will be used
        act_identifier = index_service._get_act_identifier(legal_act)
        print(f"Debug: Act identifier for clearing: {act_identifier}")
        
        # Debug: Show what directory will be cleared
        act_dir = index_service.store.get_act_directory(act_identifier)
        print(f"Debug: Directory to clear: {act_dir}")
        print(f"Debug: Directory exists: {os.path.exists(act_dir)}")
        
        # List current directories in demo_indexes
        if os.path.exists("./demo_indexes"):
            print(f"Debug: Current directories in ./demo_indexes:")
            for item in os.listdir("./demo_indexes"):
                item_path = os.path.join("./demo_indexes", item)
                if os.path.isdir(item_path):
                    print(f"  - {item}/")
        
        index_service.clear_indexes(legal_act)
        print("✓ Successfully cleared indexes")
        
        # Verify they're gone
        print("Verifying indexes are cleared:")
        for index_type in index_service.get_available_index_types():
            exists = index_service.index_exists(legal_act, index_type)
            status = "✓ EXISTS" if exists else "✗ CLEARED"
            print(f"  - {index_type}: {status}")
            
    except Exception as e:
        print(f"✗ Failed to clear indexes: {e}")

def demo_document_processing():
    """Demonstrate document processing capabilities."""
    print("\n" + "="*60)
    print("DEMO: Document Processing")
    print("="*60)
    
    from index import IndexService
    
    index_service = IndexService(output_dir="./demo_indexes")
    legal_act = get_legal_act()
    
    # Show document processor capabilities
    processor = index_service.processor
    print("Document Processor Information:")
    print(f"  - Supported element types: {', '.join(processor.get_supported_element_types())}")
    
    # Process the legal act to show document structure
    print(f"\nProcessing legal act: {legal_act.title}")
    try:
        documents = processor.process_legal_act(legal_act)
        print(f"✓ Successfully processed {len(documents)} documents")
        
        # Show document hierarchy
        print("\nDocument hierarchy:")
        for doc in documents:
            indent = "  " * doc.level
            parent_info = f" (parent: {doc.parent_id})" if doc.parent_id else ""
            print(f"{indent}- {doc.element_type.value}: {doc.title}{parent_info}")
            
        # Show element type distribution
        type_counts = {}
        for doc in documents:
            type_name = doc.element_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        print("\nElement type distribution:")
        for element_type, count in type_counts.items():
            print(f"  - {element_type}: {count}")
            
    except Exception as e:
        print(f"✗ Failed to process documents: {e}")

def main():
    """Main demo function."""
    print("IndexService Demo")
    print("This demo showcases the unified index management capabilities")
    print("of the IndexService.")
    
    try:
        # Run all demo sections
        demo_document_processing()
        demo_index_building() 
        demo_index_retrieval()
        demo_force_rebuild()
        demo_index_management()
        
        print("\n" + "="*60)
        print("DEMO COMPLETED")
        print("="*60)
        print("This demo showed:")
        print("✓ Document processing with correct element type mapping")
        print("✓ Building indexes for different types")
        print("✓ Retrieving and caching indexes")
        print("✓ Force rebuilding indexes")
        print("✓ Index management operations")
        print("\nThe IndexService provides a unified interface for all")
        print("index operations, ensuring consistency across the application.")
        
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
