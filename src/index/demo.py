"""
Demo script for the Index module - Iteration 1 completion.

This script demonstrates the core functionality implemented in Iteration 1:
- IndexDoc creation from legal elements
- Document extraction from hierarchical structures  
- Filtering and statistics utilities

Run from the src directory:
    python -m index.demo
"""

import sys
from pathlib import Path

# Add the current directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from index.domain import IndexDoc, ElementType
from index.builder import DocumentExtractor


def demo_index_doc_creation():
    """Demonstrate IndexDoc creation and searchable text extraction."""
    print("\n" + "="*50)
    print("DEMO: IndexDoc Creation")
    print("="*50)
    
    # Create a mock legal element (in practice, this comes from legislation.service)
    class MockElement:
        def __init__(self, id, title, officialIdentifier, summary, textContent=None):
            self.id = id
            self.title = title
            self.officialIdentifier = officialIdentifier
            self.summary = summary
            self.textContent = textContent
    
    element = MockElement(
        id="http://example.org/act/1/section/1",
        title="Základní pojmy",
        officialIdentifier="§ 1",
        summary="Tento paragraf definuje základní pojmy používané v tomto zákoně pro účely správného výkladu a aplikace právních norem.",
        textContent="(1) Pro účely tohoto zákona se rozumí: a) fyzickou osobou každá osoba mající..."
    )
    
    # Create IndexDoc
    doc = IndexDoc.from_legal_element(
        legal_element=element,
        level=2,
        element_type=ElementType.SECTION,
        act_iri="http://example.org/act/1"
    )
    
    print(f"Element ID: {doc.element_id}")
    print(f"Title: {doc.title}")
    print(f"Official ID: {doc.official_identifier}")
    print(f"Type: {doc.element_type}")
    print(f"Level: {doc.level}")
    print(f"Summary: {doc.summary[:100]}...")
    
    # Show searchable text extraction
    print(f"\nSearchable text (summary only): {doc.get_searchable_text()[:150]}...")
    print(f"Searchable text (with content): {doc.get_searchable_text(include_content=True)[:150]}...")
    
    # Show weighted fields for BM25
    weighted = doc.get_weighted_fields()
    print(f"\nWeighted fields for BM25:")
    for field, content in weighted.items():
        if content:
            print(f"  {field}: {content[:80]}...")


def demo_hierarchy_extraction():
    """Demonstrate extracting documents from a hierarchical legal structure."""
    print("\n" + "="*50)
    print("DEMO: Hierarchy Extraction")
    print("="*50)
    
    # Create a realistic hierarchical structure
    class MockElement:
        def __init__(self, id, title, officialIdentifier, summary, textContent=None, elements=None):
            self.id = id
            self.title = title
            self.officialIdentifier = officialIdentifier
            self.summary = summary
            self.textContent = textContent
            self.elements = elements or []
    
    # Build the hierarchy: Act > Part > Chapter > Sections
    section1 = MockElement(
        id="http://example.org/act/1/section/1",
        title="Základní pojmy",
        officialIdentifier="§ 1",
        summary="Definice základních pojmů.",
        textContent="Pro účely tohoto zákona se rozumí..."
    )
    
    section2 = MockElement(
        id="http://example.org/act/1/section/2", 
        title="Předmět úpravy",
        officialIdentifier="§ 2",
        summary="Vymezení předmětu úpravy zákona.",
        textContent="Tento zákon upravuje..."
    )
    
    chapter1 = MockElement(
        id="http://example.org/act/1/chapter/1",
        title="Obecná ustanovení",
        officialIdentifier="Hlava I",
        summary="Kapitola obsahující obecná ustanovení zákona.",
        elements=[section1, section2]
    )
    
    part1 = MockElement(
        id="http://example.org/act/1/part/1",
        title="Úvodní ustanovení",
        officialIdentifier="ČÁST PRVNÍ",
        summary="První část obsahuje úvodní a obecná ustanovení.",
        elements=[chapter1]
    )
    
    act = MockElement(
        id="http://example.org/act/1",
        title="Zákon o ochraně osobních údajů",
        officialIdentifier="Zákon č. 110/2019 Sb.",
        summary="Zákon upravuje ochranu osobních údajů fyzických osob.",
        elements=[part1]
    )
    
    # Extract all documents
    documents = DocumentExtractor.extract_from_act(
        legal_act=act,
        act_iri="http://example.org/act/1",
        snapshot_id="2025-08-01"
    )
    
    print(f"Extracted {len(documents)} documents from hierarchical structure:")
    print()
    
    for doc in documents:
        indent = "  " * doc.level
        print(f"{indent}[{doc.element_type.value.upper()}] {doc.official_identifier} - {doc.title}")
        print(f"{indent}  Level {doc.level}, Parent: {doc.parent_id or 'None'}")
        if doc.child_ids:
            print(f"{indent}  Children: {len(doc.child_ids)}")
        print()


def demo_filtering_and_stats():
    """Demonstrate document filtering and statistics."""
    print("\n" + "="*50)
    print("DEMO: Filtering and Statistics")
    print("="*50)
    
    # Create a variety of documents for filtering
    documents = [
        IndexDoc(
            element_id="act/1", title="Zákon o testování", official_identifier="Zákon č. 1/2025",
            level=0, element_type=ElementType.ACT, summary="Hlavní zákon"
        ),
        IndexDoc(
            element_id="part/1", title="Obecná část", official_identifier="ČÁST PRVNÍ", 
            level=1, element_type=ElementType.PART, summary="Obecná ustanovení"
        ),
        IndexDoc(
            element_id="section/1", title="Definice", official_identifier="§ 1",
            level=2, element_type=ElementType.SECTION, 
            summary="Definice základních pojmů", text_content="Pro účely tohoto zákona..."
        ),
        IndexDoc(
            element_id="section/2", title="Předmět", official_identifier="§ 2",
            level=2, element_type=ElementType.SECTION,
            summary="Předmět úpravy zákona"
        ),
        IndexDoc(
            element_id="section/3", title="Rozsah", official_identifier="§ 3",
            level=2, element_type=ElementType.SECTION,
            text_content="Text bez shrnutí..."
        )
    ]
    
    # Show overall statistics
    stats = DocumentExtractor.get_document_stats(documents)
    print("Document Statistics:")
    print(f"  Total documents: {stats['total_count']}")
    print(f"  By type: {dict(stats['by_type'])}")
    print(f"  By level: {dict(stats['by_level'])}")
    print(f"  With summaries: {stats['with_summary']}")
    print(f"  With content: {stats['with_content']}")
    print(f"  Average level: {stats['avg_level']:.1f}")
    
    # Demo filtering scenarios
    print(f"\nFiltering Examples:")
    
    # Find sections for indexing
    sections = DocumentExtractor.filter_documents(
        documents, element_types=[ElementType.SECTION]
    )
    print(f"  Sections only: {len(sections)} documents")
    
    # Find documents suitable for definition extraction (have both summary and content)
    definition_candidates = DocumentExtractor.filter_documents(
        documents, has_summary=True, has_content=True
    )
    print(f"  Definition candidates (summary + content): {len(definition_candidates)} documents")
    
    # Find high-level structure
    structural = DocumentExtractor.filter_documents(
        documents, max_level=1
    )
    print(f"  High-level structure (level ≤ 1): {len(structural)} documents")
    
    # Find sections that might need summarization
    needs_summary = DocumentExtractor.filter_documents(
        documents, element_types=[ElementType.SECTION], has_summary=False
    )
    print(f"  Sections needing summary: {len(needs_summary)} documents")


def main():
    """Run all demos."""
    print("Index Module - Iteration 1 Demo")
    print("This demonstrates the core data model and extraction capabilities")
    
    demo_index_doc_creation()
    demo_hierarchy_extraction() 
    demo_filtering_and_stats()
    
    print("\n" + "="*50)
    print("Demo completed!")
    print("Next iterations will add:")
    print("  - BM25 keyword search indexes")
    print("  - FAISS semantic search indexes")
    print("  - Hybrid retrieval strategies")
    print("  - CLI tools for building and searching")
    print("="*50)


if __name__ == "__main__":
    main()
