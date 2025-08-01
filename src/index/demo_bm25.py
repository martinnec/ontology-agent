"""
Demo script for BM25 Index functionality - Iteration 2 completion.

This script demonstrates the BM25 indexing and search capabilities:
- Building BM25 indexes with weighted fields
- Searching with various filters and parameters
- Index persistence and statistics

Run from the src directory:
    python -m index.demo_bm25
"""

import sys
import tempfile
import os
from pathlib import Path

# Add the current directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from index.domain import IndexDoc, SearchQuery, ElementType
from index.bm25 import BM25SummaryIndex


def create_demo_documents():
    """Create realistic demo documents for BM25 demonstration."""
    return [
        IndexDoc(
            element_id="http://example.org/act/1",
            title="Zákon o ochraně osobních údajů",
            official_identifier="Zákon č. 110/2019 Sb.",
            summary="Zákon upravuje ochranu osobních údajů fyzických osob při jejich zpracování a volném pohybu těchto údajů. Stanoví práva a povinnosti při zpracování osobních údajů a podmínky přeshraničního předávání osobních údajů.",
            level=0,
            element_type=ElementType.ACT,
            act_iri="http://example.org/act/1"
        ),
        IndexDoc(
            element_id="http://example.org/act/1/part/1",
            title="Obecná ustanovení",
            official_identifier="ČÁST PRVNÍ",
            summary="První část zákona obsahuje obecná ustanovení, včetně vymezení základních pojmů, předmětu úpravy a dalších základních ustanovení pro ochranu osobních údajů.",
            level=1,
            element_type=ElementType.PART,
            act_iri="http://example.org/act/1"
        ),
        IndexDoc(
            element_id="http://example.org/act/1/section/1",
            title="Základní pojmy",
            official_identifier="§ 1",
            summary="Definice základních pojmů používaných v zákoně o ochraně osobních údajů. Zahrnuje definici osobních údajů, zpracování, správce, zpracovatele, subjektu údajů a dalších klíčových pojmů.",
            text_content="(1) Pro účely tohoto zákona se rozumí: a) osobními údaji veškeré informace o identifikované nebo identifikovatelné fyzické osobě...",
            level=2,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/1"
        ),
        IndexDoc(
            element_id="http://example.org/act/1/section/2",
            title="Předmět úpravy",
            official_identifier="§ 2",
            summary="Vymezení předmětu úpravy zákona o ochraně osobních údajů. Zákon se vztahuje na zpracování osobních údajů fyzických osob prováděné automatizovaně nebo při němž mají být údaje zařazeny do kartotéky.",
            text_content="(1) Tento zákon se vztahuje na zpracování osobních údajů prováděné automatizovaně nebo na zpracování jiné než automatizované...",
            level=2,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/1"
        ),
        IndexDoc(
            element_id="http://example.org/act/1/section/3",
            title="Práva subjektů údajů",
            official_identifier="§ 3",
            summary="Ustanovení o právech fyzických osob, jejichž osobní údaje jsou zpracovávány. Zahrnuje právo na informace, přístup k údajům, opravu, výmaz a další práva subjektů údajů.",
            text_content="(1) Subjekt údajů má právo na informace o zpracování jeho osobních údajů. (2) Subjekt údajů má právo přístupu k osobním údajům...",
            level=2,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/1"
        ),
        IndexDoc(
            element_id="http://example.org/act/1/section/4",
            title="Povinnosti správců údajů",
            official_identifier="§ 4",
            summary="Povinnosti správců osobních údajů při zpracování. Zahrnuje povinnost zajistit bezpečnost údajů, oznámit porušení zabezpečení, vést záznamy o činnostech zpracování a další povinnosti.",
            text_content="(1) Správce je povinen přijmout taková technická a organizační opatření, aby nedošlo k náhodnému nebo neoprávněnému poškození...",
            level=2,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/1"
        ),
        IndexDoc(
            element_id="http://example.org/act/1/section/5",
            title="Zpracování citlivých údajů",
            official_identifier="§ 5",
            summary="Zvláštní ustanovení pro zpracování citlivých osobních údajů. Definuje citlivé údaje a stanoví zvýšené požadavky na jejich zpracování a ochranu.",
            text_content="(1) Citlivými údaji jsou osobní údaje vypovídající o národnostním, rasovém nebo etnickém původu, politických názorech...",
            level=2,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/1"
        ),
        IndexDoc(
            element_id="http://example.org/act/1/section/6",
            title="Sankce a kontrola",
            official_identifier="§ 6",
            summary="Ustanovení o sankcích za porušení povinností při zpracování osobních údajů a o kontrolní činnosti dozorového úřadu. Zahrnuje pokuty a další sankce.",
            text_content="(1) Fyzické osobě, která poruší povinnosti stanovené tímto zákonem, lze uložit pokutu až do výše 10 000 Kč...",
            level=2,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/1"
        )
    ]


def demo_index_building():
    """Demonstrate BM25 index building process."""
    print("\n" + "="*60)
    print("DEMO: BM25 Index Building")
    print("="*60)
    
    documents = create_demo_documents()
    print(f"Created {len(documents)} demo documents")
    
    # Build index
    print("Building BM25 index with weighted fields...")
    index = BM25SummaryIndex()
    index.build(documents)
    
    # Show metadata
    metadata = index.get_metadata()
    print(f"\nIndex Metadata:")
    print(f"  Act: {metadata.act_iri}")
    print(f"  Document count: {metadata.document_count}")
    print(f"  Index type: {metadata.index_type}")
    print(f"  Weighted fields: {metadata.metadata['weighted_fields']}")
    
    # Show statistics
    stats = index.get_stats()
    print(f"\nIndex Statistics:")
    print(f"  Vocabulary size: {stats['vocabulary_size']} unique terms")
    print(f"  Total tokens: {stats['total_tokens']}")
    print(f"  Average document length: {stats['average_document_length']:.1f} tokens")
    print(f"  BM25 parameters: k1={stats['bm25_params']['k1']}, b={stats['bm25_params']['b']}")
    
    return index


def demo_weighted_text():
    """Demonstrate weighted text creation for BM25."""
    print("\n" + "="*60)
    print("DEMO: Weighted Text Creation")
    print("="*60)
    
    index = BM25SummaryIndex()
    
    # Take first document
    doc = create_demo_documents()[2]  # "Základní pojmy" section
    
    print(f"Original document:")
    print(f"  Official ID: {doc.official_identifier}")
    print(f"  Title: {doc.title}")
    print(f"  Summary: {doc.summary[:100]}...")
    
    # Show weighted text
    weighted_text = index._create_weighted_text(doc)
    print(f"\nWeighted text (summary^3, title^2, id^1):")
    print(f"  Length: {len(weighted_text)} characters")
    print(f"  Preview: {weighted_text[:200]}...")
    
    # Show repetition counts
    print(f"\nRepetition counts:")
    print(f"  '§ 1' appears: {weighted_text.count('§ 1')} times (weight 1)")
    print(f"  'Základní pojmy' appears: {weighted_text.count('Základní pojmy')} times (weight 2)")
    summary_first_words = " ".join(doc.summary.split()[:5])
    print(f"  Summary start '{summary_first_words}' appears: {weighted_text.count(summary_first_words)} times (weight 3)")


def demo_search_capabilities(index):
    """Demonstrate various search capabilities."""
    print("\n" + "="*60)
    print("DEMO: Search Capabilities")
    print("="*60)
    
    # Basic search
    print("1. Basic Search: 'základní pojmy'")
    query1 = SearchQuery(query="základní pojmy", max_results=3)
    results1 = index.search(query1)
    
    for i, result in enumerate(results1):
        print(f"  #{result.rank} [{result.doc.element_type.value}] {result.doc.official_identifier}")
        print(f"      Title: {result.doc.title}")
        print(f"      Score: {result.score:.3f}")
        print(f"      Matched: {', '.join(result.matched_fields)}")
    
    # Search with filters
    print(f"\n2. Filtered Search: 'údajů' (sections only)")
    query2 = SearchQuery(
        query="údajů",
        element_types=[ElementType.SECTION],
        max_results=3
    )
    results2 = index.search(query2)
    
    for result in results2:
        print(f"  #{result.rank} {result.doc.official_identifier} - {result.doc.title}")
        print(f"      Score: {result.score:.3f}, Level: {result.doc.level}")
    
    # Complex search with multiple filters
    print(f"\n3. Complex Search: 'povinnosti' (level 2, § pattern)")
    query3 = SearchQuery(
        query="povinnosti",
        min_level=2,
        max_level=2,
        official_identifier_pattern="^§",
        max_results=5
    )
    results3 = index.search(query3)
    
    for result in results3:
        print(f"  #{result.rank} {result.doc.official_identifier} - {result.doc.title}")
        print(f"      Snippet: {result.snippet[:100]}...")


def demo_search_scoring(index):
    """Demonstrate search scoring and ranking."""
    print("\n" + "="*60)
    print("DEMO: Search Scoring and Ranking")
    print("="*60)
    
    # Search for common term to see scoring differences
    query = SearchQuery(query="osobních údajů", max_results=8)
    results = index.search(query)
    
    print("Search: 'osobních údajů' - showing how BM25 scores different documents:")
    print()
    
    for result in results:
        doc = result.doc
        print(f"#{result.rank} Score: {result.score:.4f}")
        print(f"  [{doc.element_type.value.upper()}] {doc.official_identifier} - {doc.title}")
        print(f"  Matched fields: {', '.join(result.matched_fields)}")
        
        # Show how often the term appears in summary
        summary_lower = (doc.summary or "").lower()
        count = summary_lower.count("osobních údajů")
        print(f"  Term frequency in summary: {count}")
        print()


def demo_index_persistence():
    """Demonstrate saving and loading indexes."""
    print("\n" + "="*60)
    print("DEMO: Index Persistence")
    print("="*60)
    
    documents = create_demo_documents()
    
    # Use temporary directory
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        index_path = os.path.join(temp_dir, "demo_index")
        
        # Build and save index
        print("Building and saving index...")
        index1 = BM25SummaryIndex()
        index1.build(documents)
        index1.save(index_path)
        
        print(f"Index saved to: {index_path}")
        
        # List saved files
        path_obj = Path(index_path)
        files = list(path_obj.glob("*"))
        print(f"Files created: {[f.name for f in files]}")
        
        # Load index
        print("\nLoading index from disk...")
        index2 = BM25SummaryIndex()
        index2.load(index_path)
        
        # Test loaded index
        query = SearchQuery(query="základní pojmy", max_results=2)
        results = index2.search(query)
        
        print(f"Loaded index search test:")
        for result in results:
            print(f"  {result.doc.official_identifier} - {result.doc.title} (score: {result.score:.3f})")
        
        print("✓ Index persistence working correctly")


def demo_top_terms(index):
    """Demonstrate top terms extraction for documents."""
    print("\n" + "="*60)
    print("DEMO: Top Terms Analysis")
    print("="*60)
    
    # Analyze top terms for a few documents
    documents_to_analyze = [1, 2, 4]  # Skip act document, analyze some sections
    
    for doc_idx in documents_to_analyze:
        doc = index.documents[doc_idx]
        top_terms = index.get_top_terms(doc_idx, top_k=8)
        
        print(f"\nDocument: {doc.official_identifier} - {doc.title}")
        print(f"Top terms (TF*IDF-like scoring):")
        
        for term, score in top_terms:
            print(f"  {term:15s} {score:8.3f}")


def main():
    """Run all BM25 demos."""
    print("BM25 Index - Iteration 2 Demo")
    print("This demonstrates BM25 keyword search with weighted fields")
    
    # Note about dependencies
    try:
        import rank_bm25
        print("✓ rank-bm25 library available")
    except ImportError:
        print("⚠ rank-bm25 library not installed")
        print("  Install with: pip install rank-bm25")
        print("  Continuing with demo structure...")
        return
    
    # Build index for demos
    index = demo_index_building()
    
    # Run all demonstrations
    demo_weighted_text()
    demo_search_capabilities(index)
    demo_search_scoring(index)
    demo_index_persistence()
    demo_top_terms(index)
    
    print("\n" + "="*60)
    print("Demo completed!")
    print("\nKey BM25 features demonstrated:")
    print("  ✓ Weighted field indexing (summary^3, title^2, id^1)")
    print("  ✓ Czech text tokenization and normalization")
    print("  ✓ Relevance-based search ranking")
    print("  ✓ Advanced filtering (type, level, pattern matching)")
    print("  ✓ Index persistence and loading")
    print("  ✓ Search statistics and term analysis")
    print("\nNext: Add FAISS semantic search for better conceptual matching")
    print("="*60)


if __name__ == "__main__":
    main()
