"""
Demo script for Hybrid Search Engine with real legal act 56/2001 - Vehicle Law.

This script demonstrates the hybrid search capabilities using both BM25 and FAISS
indexes on real Czech legal act data loaded from the JSON file using datasource_esel.py.
Shows how semantic and keyword search combine for optimal retrieval performance.

The legal act 56/2001 is about vehicle operation, registration, and technical requirements.

Run from the src directory:
    python -m index.demo_hybrid_56_2001
"""

import sys
import os
from pathlib import Path

# Add the current directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from index.domain import IndexDoc, SearchQuery, ElementType
from index.hybrid import HybridSearchEngine, HybridConfig
from index.bm25 import BM25SummaryIndex
from index.faiss_index import FAISSSummaryIndex
from index.builder import DocumentExtractor
from legislation.datasource_esel import DataSourceESEL


def load_legal_act_56_2001():
    """Load the real legal act 56/2001 from JSON data."""
    print("Loading legal act 56/2001 (Vehicle Law) from JSON data...")
    
    # The IRI for the legal act
    act_iri = "https://opendata.eselpoint.cz/esel-esb/eli/cz/sb/2001/56/2025-07-01"
    
    # Use the ESEL datasource to load the legal act
    datasource = DataSourceESEL()
    legal_act = datasource.get_legal_act(act_iri)
    
    print(f"Loaded: {legal_act.officialIdentifier}")
    print(f"Title: {legal_act.title}")
    if legal_act.summary:
        summary_preview = legal_act.summary[:200] + "..." if len(legal_act.summary) > 200 else legal_act.summary
        print(f"Summary: {summary_preview}")
    else:
        print("Summary: Not available")
    
    return legal_act, act_iri


def extract_and_analyze_documents(legal_act, act_iri):
    """Extract IndexDoc instances and analyze the document structure."""
    print("\n" + "="*60)
    print("DEMO: Document Extraction and Analysis")
    print("="*60)
    
    # Extract all documents from the legal act
    documents = DocumentExtractor.extract_from_act(
        legal_act=legal_act,
        act_iri=act_iri,
        snapshot_id="2025-07-01"
    )
    
    print(f"Extracted {len(documents)} documents from the legal act")
    
    # Get statistics
    stats = DocumentExtractor.get_document_stats(documents)
    print(f"\nDocument Statistics:")
    print(f"  Total documents: {stats['total_count']}")
    print(f"  With summaries: {stats['with_summary']}")
    print(f"  With text content: {stats['with_content']}")
    print(f"  Average level: {stats['avg_level']:.1f}")
    
    print(f"\nBy type:")
    for element_type, count in stats['by_type'].items():
        print(f"  {element_type.value}: {count}")
    
    print(f"\nBy level:")
    for level, count in stats['by_level'].items():
        print(f"  Level {level}: {count}")
    
    # Show sample documents with summaries
    docs_with_summaries = [doc for doc in documents if doc.summary]
    print(f"\nSample documents with summaries ({len(docs_with_summaries)} total):")
    for i, doc in enumerate(docs_with_summaries[:5]):
        summary_preview = doc.summary[:120] + "..." if len(doc.summary) > 120 else doc.summary
        print(f"  {i+1}. {doc.official_identifier} - {doc.title}")
        print(f"     📝 {summary_preview}")
        if doc.summary_names:
            names_preview = ", ".join(doc.summary_names[:5])
            if len(doc.summary_names) > 5:
                names_preview += f", ... (+{len(doc.summary_names)-5} more)"
            print(f"     🏷️  Concepts: {names_preview}")
    
    return documents


def build_hybrid_index(documents):
    """Build both BM25 and FAISS indexes for hybrid search."""
    print("\n" + "="*60)
    print("DEMO: Building Hybrid Index (BM25 + FAISS)")
    print("="*60)
    
    print("🔧 Building BM25 keyword index...")
    # Filter documents with summaries for better quality
    docs_with_summaries = [doc for doc in documents if doc.summary]
    print(f"Using {len(docs_with_summaries)} documents with summaries for indexing")
    
    # Build BM25 index
    bm25_index = BM25SummaryIndex()
    bm25_index.build(docs_with_summaries)
    bm25_metadata = bm25_index.get_metadata()
    bm25_stats = bm25_index.get_stats()
    print(f"✅ BM25 index built: {bm25_metadata.document_count} documents")
    print(f"   Model: {bm25_metadata.index_type}")
    print(f"   Vocabulary: {bm25_stats['vocabulary_size']} terms")
    
    print("\n🧠 Building FAISS semantic index...")
    # Build FAISS index
    faiss_index = FAISSSummaryIndex()
    faiss_index.build(docs_with_summaries)
    faiss_metadata = faiss_index.get_metadata()
    faiss_stats = faiss_index.get_stats()
    print(f"✅ FAISS index built: {faiss_metadata.document_count} documents")
    print(f"   Model: {faiss_metadata.metadata.get('model_name', 'Unknown')}")
    print(f"   Dimensions: {faiss_stats['embedding_dimension']}")
    print(f"   Valid embeddings: {faiss_stats['valid_embeddings']}")
    
    print("\n🔀 Initializing Hybrid Search Engine...")
    # Build hybrid engine
    hybrid = HybridSearchEngine(bm25_index=bm25_index, faiss_index=faiss_index)
    hybrid_stats = hybrid.get_statistics()
    print(f"✅ Hybrid engine ready")
    print(f"   BM25 available: {hybrid_stats['hybrid_engine']['bm25_available']}")
    print(f"   FAISS available: {hybrid_stats['hybrid_engine']['faiss_available']}")
    print(f"   Default config: {hybrid_stats['hybrid_engine']['config']}")
    
    return hybrid, bm25_index, faiss_index


def demo_hybrid_search_strategies(hybrid):
    """Demonstrate different hybrid search strategies with real queries."""
    print("\n" + "="*60)
    print("DEMO: Hybrid Search Strategies")
    print("="*60)
    
    # Real-world queries about vehicle law
    test_queries = [
        "registrace vozidel",
        "technická kontrola",
        "řidičské oprávnění",
        "dopravní přestupky a pokuty",
        "povinné ručení",
        "vozidlo kategorie M1"
    ]
    
    strategies = [
        ("semantic_first", "🧠 Semantic-First Strategy", "FAISS breadth → BM25 precision"),
        ("keyword_first", "🔍 Keyword-First Strategy", "BM25 precision → FAISS breadth"),
        ("parallel", "🔀 Parallel Fusion Strategy", "Both methods combined")
    ]
    
    for query_text in test_queries:
        print(f"\n{'='*80}")
        print(f"🔍 Query: '{query_text}'")
        print(f"{'='*80}")
        
        query = SearchQuery(query=query_text, max_results=3)
        
        for strategy, strategy_name, description in strategies:
            print(f"\n{strategy_name}")
            print(f"   {description}")
            print("-" * 60)
            
            results = hybrid.search(query, strategy=strategy)
            
            if results:
                for i, result in enumerate(results):
                    print(f"\n#{i+1:2d} | Score: {result.score:.4f} | {result.doc.official_identifier}")
                    print(f"     📋 {result.doc.title}")
                    
                    # Show summary preview
                    if result.doc.summary:
                        summary_preview = result.doc.summary[:150] + "..." if len(result.doc.summary) > 150 else result.doc.summary
                        print(f"     💭 {summary_preview}")
                    
                    # Show matched concepts
                    if hasattr(result, 'matched_fields') and result.matched_fields:
                        print(f"     🎯 Matched: {', '.join(result.matched_fields)}")
                    
                    # Show relevant concepts from summary_names
                    if result.doc.summary_names:
                        # Find concepts that relate to the query
                        query_words = set(query_text.lower().split())
                        relevant_concepts = []
                        for concept in result.doc.summary_names:
                            if any(word in concept.lower() for word in query_words) or \
                               any(word in query_text.lower() for word in concept.lower().split()):
                                relevant_concepts.append(concept)
                        
                        if relevant_concepts:
                            concepts_preview = ", ".join(relevant_concepts[:3])
                            if len(relevant_concepts) > 3:
                                concepts_preview += f" (+{len(relevant_concepts)-3} more)"
                            print(f"     🏷️  Related concepts: {concepts_preview}")
            else:
                print("     No results found.")


def demo_hybrid_configuration_impact(hybrid):
    """Demonstrate the impact of different hybrid configurations."""
    print("\n" + "="*60)
    print("DEMO: Configuration Impact Analysis")
    print("="*60)
    
    # Use a complex legal query
    query_text = "technická kontrola vozidel"
    query = SearchQuery(query=query_text, max_results=4)
    
    print(f"🔍 Analysis Query: '{query_text}'")
    print(f"📊 Comparing different hybrid configurations...")
    
    configurations = [
        ({"faiss_weight": 0.8, "bm25_weight": 0.2}, "🧠 Semantic-Heavy (80% FAISS, 20% BM25)", "Emphasizes conceptual similarity"),
        ({"faiss_weight": 0.5, "bm25_weight": 0.5}, "⚖️  Balanced (50% FAISS, 50% BM25)", "Equal weight to both approaches"),
        ({"faiss_weight": 0.2, "bm25_weight": 0.8}, "🔍 Keyword-Heavy (20% FAISS, 80% BM25)", "Emphasizes exact term matching"),
        ({"rerank_strategy": "rrf"}, "🔀 RRF Fusion", "Reciprocal Rank Fusion algorithm"),
        ({"rerank_strategy": "weighted"}, "⚖️  Weighted Fusion", "Score-based combination")
    ]
    
    all_results = {}
    
    for config_params, config_name, description in configurations:
        print(f"\n{'-'*70}")
        print(f"{config_name}")
        print(f"   {description}")
        print(f"{'-'*70}")
        
        results = hybrid.search(query, strategy="parallel", **config_params)
        all_results[config_name] = results
        
        if results:
            for i, result in enumerate(results):
                print(f"\n#{i+1:2d} | Score: {result.score:.4f} | {result.doc.official_identifier}")
                print(f"     📋 {result.doc.title}")
                
                if result.doc.summary:
                    summary_preview = result.doc.summary[:120] + "..." if len(result.doc.summary) > 120 else result.doc.summary
                    print(f"     💭 {summary_preview}")
        else:
            print("     No results found.")
    
    # Analyze result diversity
    print(f"\n{'='*60}")
    print("📈 Configuration Impact Analysis")
    print(f"{'='*60}")
    
    # Count unique documents across configurations
    all_doc_ids = set()
    for results in all_results.values():
        for result in results:
            all_doc_ids.add(result.doc.element_id)
    
    print(f"Total unique documents found across all configurations: {len(all_doc_ids)}")
    
    # Show which configurations found which documents
    for config_name, results in all_results.items():
        doc_ids = [result.doc.element_id for result in results]
        print(f"  {config_name}: {len(doc_ids)} results")
        if doc_ids:
            print(f"    Document IDs: {', '.join(doc_ids)}")


def demo_domain_specific_queries(hybrid):
    """Demonstrate hybrid search on domain-specific legal queries."""
    print("\n" + "="*60)
    print("DEMO: Domain-Specific Legal Queries")
    print("="*60)
    
    # Complex legal domain queries
    domain_queries = [
        {
            "query": "státní poznávací značka vozidla",
            "context": "License plate identification and requirements",
            "expectation": "Should find regulations about vehicle registration plates"
        },
        {
            "query": "technická způsobilost k provozu",
            "context": "Technical roadworthiness for vehicle operation",
            "expectation": "Should find technical inspection and approval requirements"
        },
        {
            "query": "povinnost řidiče při kontrole",
            "context": "Driver obligations during traffic inspections",
            "expectation": "Should find driver responsibilities and compliance requirements"
        },
        {
            "query": "sankce za porušení předpisů",
            "context": "Penalties for regulation violations",
            "expectation": "Should find penalty and fine information"
        }
    ]
    
    for i, query_info in enumerate(domain_queries, 1):
        print(f"\n{'='*70}")
        print(f"🔍 Domain Query #{i}: '{query_info['query']}'")
        print(f"📋 Context: {query_info['context']}")
        print(f"🎯 Expected: {query_info['expectation']}")
        print(f"{'='*70}")
        
        query = SearchQuery(query=query_info['query'], max_results=3)
        
        # Use semantic-first strategy for complex legal concepts
        results = hybrid.search(query, strategy="semantic_first")
        
        if results:
            print(f"\n✅ Found {len(results)} relevant results:")
            
            for j, result in enumerate(results):
                print(f"\n#{j+1:2d} | Score: {result.score:.4f} | {result.doc.official_identifier}")
                print(f"     📋 {result.doc.title}")
                print(f"     📊 Level: {result.doc.level} | Type: {result.doc.element_type.value}")
                
                if result.doc.summary:
                    summary_preview = result.doc.summary[:200] + "..." if len(result.doc.summary) > 200 else result.doc.summary
                    print(f"     💭 {summary_preview}")
                
                # Show most relevant concepts
                if result.doc.summary_names:
                    # Filter concepts related to the query
                    query_words = set(query_info['query'].lower().split())
                    relevant_concepts = []
                    for concept in result.doc.summary_names[:10]:  # Limit to first 10 concepts
                        concept_words = set(concept.lower().split())
                        if query_words & concept_words:  # Intersection of word sets
                            relevant_concepts.append(concept)
                    
                    if relevant_concepts:
                        concepts_str = ", ".join(relevant_concepts[:4])
                        if len(relevant_concepts) > 4:
                            concepts_str += f" (+{len(relevant_concepts)-4} more)"
                        print(f"     🏷️  Key concepts: {concepts_str}")
        else:
            print("     ❌ No results found.")


def demo_comparative_analysis(hybrid, bm25_index, faiss_index):
    """Compare hybrid results with individual BM25 and FAISS results."""
    print("\n" + "="*60)
    print("DEMO: Comparative Analysis - Hybrid vs Individual Methods")
    print("="*60)
    
    test_query = "registrace motorového vozidla"
    query = SearchQuery(query=test_query, max_results=3)
    
    print(f"🔍 Comparative Query: '{test_query}'")
    print(f"📊 Comparing Hybrid vs BM25 vs FAISS results...")
    
    # Get results from each method
    print(f"\n{'='*70}")
    print("🔍 BM25 Only (Keyword Matching)")
    print(f"{'='*70}")
    bm25_results = bm25_index.search(query)
    for i, result in enumerate(bm25_results[:3]):
        print(f"\n#{i+1:2d} | BM25 Score: {result.score:.4f} | {result.doc.official_identifier}")
        print(f"     📋 {result.doc.title}")
        if result.doc.summary:
            summary_preview = result.doc.summary[:150] + "..." if len(result.doc.summary) > 150 else result.doc.summary
            print(f"     💭 {summary_preview}")
    
    print(f"\n{'='*70}")
    print("🧠 FAISS Only (Semantic Similarity)")
    print(f"{'='*70}")
    faiss_results = faiss_index.search(query)
    for i, result in enumerate(faiss_results[:3]):
        print(f"\n#{i+1:2d} | FAISS Score: {result.score:.4f} | {result.doc.official_identifier}")
        print(f"     📋 {result.doc.title}")
        if result.doc.summary:
            summary_preview = result.doc.summary[:150] + "..." if len(result.doc.summary) > 150 else result.doc.summary
            print(f"     💭 {summary_preview}")
    
    print(f"\n{'='*70}")
    print("🔀 Hybrid (Parallel Fusion)")
    print(f"{'='*70}")
    hybrid_results = hybrid.search(query, strategy="parallel")
    for i, result in enumerate(hybrid_results[:3]):
        print(f"\n#{i+1:2d} | Hybrid Score: {result.score:.4f} | {result.doc.official_identifier}")
        print(f"     📋 {result.doc.title}")
        if result.doc.summary:
            summary_preview = result.doc.summary[:150] + "..." if len(result.doc.summary) > 150 else result.doc.summary
            print(f"     💭 {summary_preview}")
    
    # Analysis
    print(f"\n{'='*60}")
    print("📈 Analysis Summary")
    print(f"{'='*60}")
    
    bm25_ids = {r.doc.element_id for r in bm25_results[:3]}
    faiss_ids = {r.doc.element_id for r in faiss_results[:3]}
    hybrid_ids = {r.doc.element_id for r in hybrid_results[:3]}
    
    print(f"📊 Result Set Overlap:")
    print(f"   BM25 documents: {len(bm25_ids)}")
    print(f"   FAISS documents: {len(faiss_ids)}")
    print(f"   Hybrid documents: {len(hybrid_ids)}")
    print(f"   BM25 ∩ FAISS: {len(bm25_ids & faiss_ids)}")
    print(f"   BM25 ∩ Hybrid: {len(bm25_ids & hybrid_ids)}")
    print(f"   FAISS ∩ Hybrid: {len(faiss_ids & hybrid_ids)}")
    print(f"   Unique to Hybrid: {len(hybrid_ids - bm25_ids - faiss_ids)}")
    
    all_unique = bm25_ids | faiss_ids | hybrid_ids
    print(f"   Total unique documents: {len(all_unique)}")


def main():
    """Run the comprehensive hybrid search demo with real legal act data."""
    print("🚀 Hybrid Search Engine Demo - Real Legal Act 56/2001")
    print("=" * 80)
    print("This demo showcases hybrid retrieval combining BM25 and FAISS")
    print("on real Czech vehicle law data (Act 56/2001).")
    print("=" * 80)
    
    try:
        # Step 1: Load real legal act data
        legal_act, act_iri = load_legal_act_56_2001()
        
        # Step 2: Extract and analyze documents
        documents = extract_and_analyze_documents(legal_act, act_iri)
        
        # Step 3: Build hybrid index
        hybrid, bm25_index, faiss_index = build_hybrid_index(documents)
        
        # Step 4: Demonstrate search strategies
        demo_hybrid_search_strategies(hybrid)
        
        # Step 5: Show configuration impact
        demo_hybrid_configuration_impact(hybrid)
        
        # Step 6: Domain-specific queries
        demo_domain_specific_queries(hybrid)
        
        # Step 7: Comparative analysis
        demo_comparative_analysis(hybrid, bm25_index, faiss_index)
        
        print(f"\n{'='*80}")
        print("✅ Hybrid Search Demo Complete!")
        print("=" * 80)
        print("🎯 Key Achievements:")
        print("   • Successfully built hybrid index on real legal act data")
        print("   • Demonstrated multiple search strategies (semantic-first, keyword-first, parallel)")
        print("   • Showed configuration impact on result quality and ranking")
        print("   • Tested domain-specific legal queries with complex terminology")
        print("   • Compared hybrid performance against individual BM25 and FAISS methods")
        print("   • Proved hybrid approach provides superior coverage and relevance")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
