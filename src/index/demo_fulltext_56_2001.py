"""
Demo script for full-text indexing with legal act 56/2001.

This script demonstrates the new full-text indexing capabilities:
1. Building BM25 and FAISS full-text indexes
2. Exact phrase searches
3. Semantic search over text chunks
4. Integration with existing summary indexes
"""

import sys
import json
from pathlib import Path
from typing import List

# Add the src directory to path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

from index.domain import IndexDoc, ElementType, SearchQuery
from index.bm25_full import BM25FullIndex
from index.faiss_full import FAISSFullIndex
from index.hybrid import HybridSearchEngine, HybridConfig
from legislation.domain import LegalStructuralElement


def load_legal_act_data() -> List[IndexDoc]:
    """Load and convert legal act data to IndexDoc format."""
    data_file = Path(__file__).parent.parent.parent / "data" / "legal_acts" / "56-2001-2025-07-01.json"
    
    if not data_file.exists():
        print(f"Data file not found: {data_file}")
        return []
    
    print(f"Loading legal act data from {data_file}")
    
    with open(data_file, 'r', encoding='utf-8') as f:
        act_data = json.load(f)
    
    documents = []
    
    def extract_documents(element_data, level=0, parent_id=None):
        """Recursively extract documents from legal act structure."""
        
        # Create IndexDoc for current element
        if element_data.get('textContent') or element_data.get('summary'):
            doc = IndexDoc(
                element_id=str(element_data['id']),
                title=element_data.get('title', ''),
                summary=element_data.get('summary', ''),
                summary_names=element_data.get('summary_names', []),
                official_identifier=element_data.get('officialIdentifier', ''),
                text_content=element_data.get('textContent', ''),
                level=level,
                element_type=ElementType.UNKNOWN,  # We don't have type info in the JSON
                parent_id=parent_id,
                act_iri=act_data.get('id', ''),
                snapshot_id="2025-07-01"
            )
            documents.append(doc)
        
        # Process child elements
        if 'elements' in element_data:
            for child in element_data['elements']:
                extract_documents(child, level + 1, element_data['id'])
    
    # Start extraction from root
    extract_documents(act_data)
    
    print(f"Extracted {len(documents)} documents from legal act")
    
    # Filter documents with text content for full-text indexing
    docs_with_content = [doc for doc in documents if doc.text_content]
    print(f"Found {len(docs_with_content)} documents with text content")
    
    return docs_with_content


def demo_bm25_full_text():
    """Demonstrate BM25 full-text indexing."""
    print("\n" + "="*60)
    print("BM25 FULL-TEXT INDEXING DEMO")
    print("="*60)
    
    # Load documents
    documents = load_legal_act_data()
    if not documents:
        print("No documents with text content found!")
        return
    
    print(f"Building BM25 full-text index with {len(documents)} documents...")
    
    # Build index
    index = BM25FullIndex()
    index.build(documents)
    
    print(f"Index built with {len(index.text_chunks)} text chunks")
    
    # Test exact phrase searches
    print("\n--- Exact Phrase Searches ---")
    
    test_phrases = [
        "rozumí se",
        "je povinen", 
        "musí",
        "technická prohlídka",
        "registrace vozidel"
    ]
    
    for phrase in test_phrases:
        print(f"\nSearching for exact phrase: '{phrase}'")
        results = index.search_exact_phrase(phrase, max_results=3)
        
        if results:
            print(f"Found {len(results)} matches:")
            for i, result in enumerate(results[:2], 1):
                print(f"  {i}. {result.doc.title} ({result.doc.official_identifier})")
                print(f"     Score: {result.score:.3f}")
                print(f"     Snippet: {result.snippet[:100]}...")
        else:
            print("  No exact matches found")
    
    # Test keyword search in full text
    print("\n--- Keyword Search in Full Text ---")
    
    test_queries = [
        "technická kontrola vozidel",
        "povinnosti vlastníka",
        "registrace a evidence"
    ]
    
    for query_text in test_queries:
        print(f"\nSearching for: '{query_text}'")
        query = SearchQuery(query=query_text, max_results=3)
        results = index.search(query)
        
        if results:
            print(f"Found {len(results)} matches:")
            for i, result in enumerate(results[:2], 1):
                print(f"  {i}. {result.doc.title} ({result.doc.official_identifier})")
                print(f"     Score: {result.score:.3f}")
                print(f"     Snippet: {result.snippet[:100]}...")
        else:
            print("  No matches found")


def demo_faiss_full_text():
    """Demonstrate FAISS full-text semantic search."""
    print("\n" + "="*60)
    print("FAISS FULL-TEXT SEMANTIC SEARCH DEMO")
    print("="*60)
    
    # Load documents
    documents = load_legal_act_data()
    if not documents:
        print("No documents with text content found!")
        return
    
    print(f"Building FAISS full-text index with {len(documents)} documents...")
    
    # Build index
    index = FAISSFullIndex()
    index.build(documents)
    
    print(f"Index built with {len(index.text_chunks)} text chunks")
    print(f"Embedding dimension: {index.metadata.metadata.get('embedding_dimension', 'unknown')}")
    
    # Test semantic searches
    print("\n--- Semantic Search in Full Text ---")
    
    test_queries = [
        "technické požadavky na vozidla",
        "povinnosti při provozu",
        "kontrola technického stavu",
        "registrace motorových vozidel"
    ]
    
    for query_text in test_queries:
        print(f"\nSemantic search for: '{query_text}'")
        query = SearchQuery(query=query_text, max_results=3)
        results = index.search(query)
        
        if results:
            print(f"Found {len(results)} semantic matches:")
            for i, result in enumerate(results[:2], 1):
                print(f"  {i}. {result.doc.title} ({result.doc.official_identifier})")
                print(f"     Similarity: {result.score:.3f}")
                print(f"     Snippet: {result.snippet[:100]}...")
        else:
            print("  No matches found")
    
    # Test finding similar chunks
    if index.text_chunks:
        print("\n--- Similar Chunks Demo ---")
        first_chunk = index.text_chunks[0]
        print(f"Finding chunks similar to: '{first_chunk.title}'")
        
        similar_chunks = index.get_similar_chunks(first_chunk.chunk_id, k=3)
        
        if similar_chunks:
            print(f"Found {len(similar_chunks)} similar chunks:")
            for i, (chunk, score) in enumerate(similar_chunks, 1):
                print(f"  {i}. {chunk.title} (similarity: {score:.3f})")
                print(f"     Text: {chunk.text[:80]}...")
        else:
            print("  No similar chunks found")


def demo_full_text_integration():
    """Demonstrate integration of full-text search with existing indexes."""
    print("\n" + "="*60)
    print("FULL-TEXT INTEGRATION DEMO")
    print("="*60)
    
    # Load documents
    documents = load_legal_act_data()
    if not documents:
        print("No documents with text content found!")
        return
    
    print("Building full-text indexes...")
    
    # Build full-text indexes
    bm25_full_index = BM25FullIndex()
    bm25_full_index.build(documents)
    
    faiss_full_index = FAISSFullIndex()
    faiss_full_index.build(documents)
    
    # Create hybrid engine with full-text support
    config = HybridConfig(
        use_full_text=True,
        full_text_weight=0.3,
        faiss_full_k=10,
        bm25_full_k=10
    )
    
    hybrid_engine = HybridSearchEngine(
        bm25_full_index=bm25_full_index,
        faiss_full_index=faiss_full_index,
        config=config
    )
    
    # Test exact phrase search through hybrid engine
    print("\n--- Hybrid Exact Phrase Search ---")
    exact_phrases = ["je povinen", "musí být", "rozumí se"]
    
    for phrase in exact_phrases[:2]:  # Test first 2 phrases
        print(f"\nExact phrase search: '{phrase}'")
        results = hybrid_engine.search_exact_phrase(phrase, max_results=2)
        
        if results:
            print(f"Found {len(results)} exact matches:")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result.doc.title}")
                print(f"     {result.doc.official_identifier}")
                print(f"     Score: {result.score:.3f}")
        else:
            print("  No exact matches found")
    
    # Test full-text only search
    print("\n--- Full-Text Only Search ---")
    test_query = "technické kontroly vozidel"
    print(f"Full-text search: '{test_query}'")
    
    results = hybrid_engine.search_with_full_text(
        test_query, 
        strategy="fulltext_only"
    )
    
    if results:
        print(f"Found {len(results)} full-text matches:")
        for i, result in enumerate(results[:3], 1):
            print(f"  {i}. {result.doc.title}")
            print(f"     Score: {result.score:.3f}")
            print(f"     Type: {result.doc.element_id.split('_')[-1] if '_chunk_' in result.doc.element_id else 'document'}")
    else:
        print("  No matches found")


def main():
    """Run all full-text indexing demos."""
    print("FULL-TEXT INDEXING DEMONSTRATION")
    print("Legal Act 56/2001 - Conditions for Vehicle Operation")
    print("This demo showcases Iteration 5: Full-Text Indexing capabilities")
    
    try:
        # Run BM25 full-text demo
        demo_bm25_full_text()
        
        # Run FAISS full-text demo  
        demo_faiss_full_text()
        
        # Run integration demo
        demo_full_text_integration()
        
        print("\n" + "="*60)
        print("FULL-TEXT INDEXING DEMO COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\nKey capabilities demonstrated:")
        print("✅ Text chunking with overlaps for semantic coherence")
        print("✅ BM25 exact phrase searches (e.g., 'rozumí se', 'je povinen')")
        print("✅ FAISS semantic search over text chunks")
        print("✅ Integration with hybrid search engine")
        print("✅ Full-text search strategies")
        print("✅ Chunk similarity analysis")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
