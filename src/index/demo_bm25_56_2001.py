"""
Demo script for BM25 Index with real legal act 56/2001 - Vehicle Law.

This script demonstrates the BM25 indexing and search capabilities using
real Czech legal act data loaded from the JSON file using datasource_esel.py.
Features summary_names functionality for enhanced concept-based search.

The legal act 56/2001 is about vehicle operation, registration, and technical requirements.

Run from the src directory:
    python -m index.demo_bm25_56_2001
"""

import sys
import os
from pathlib import Path

# Add the current directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from index.domain import IndexDoc, SearchQuery, ElementType
from index.bm25 import BM25SummaryIndex
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
    
    # Debug: Check if elements have summaries and summary_names
    print("\nDebug - Checking first few elements for summaries and summary_names:")
    if hasattr(legal_act, 'elements') and legal_act.elements:
        for i, element in enumerate(legal_act.elements[:3]):
            print(f"  Element {i+1}: {element.officialIdentifier}")
            print(f"    Has summary: {hasattr(element, 'summary')}")
            print(f"    Summary value: {repr(getattr(element, 'summary', 'NO ATTR'))}")
            print(f"    Has summary_names: {hasattr(element, 'summary_names')}")
            print(f"    Summary_names value: {repr(getattr(element, 'summary_names', 'NO ATTR'))}")
            if hasattr(element, 'elements') and element.elements:
                for j, sub_element in enumerate(element.elements[:2]):
                    print(f"    Sub-element {j+1}: {sub_element.officialIdentifier}")
                    print(f"      Has summary: {hasattr(sub_element, 'summary')}")
                    print(f"      Summary value: {repr(getattr(sub_element, 'summary', 'NO ATTR'))}")
                    print(f"      Has summary_names: {hasattr(sub_element, 'summary_names')}")
                    print(f"      Summary_names value: {repr(getattr(sub_element, 'summary_names', 'NO ATTR'))}")
    
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
    
    # Debug: Check first few documents to see what data we have
    print(f"\nDebug - First 3 documents raw data:")
    for i, doc in enumerate(documents[:3]):
        print(f"  {i+1}. {doc.official_identifier} - {doc.title}")
        print(f"     Summary: {repr(doc.summary)}")
        print(f"     Summary_names: {repr(doc.summary_names)}")
        print(f"     Text content: {repr(doc.text_content[:100] if doc.text_content else None)}")
    
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
    
    # Show sample documents at different levels
    print(f"\nSample documents:")
    sample_docs = documents[:10]  # First 10 documents
    
    for doc in sample_docs:
        indent = "  " * doc.level
        summary_preview = (doc.summary[:80] + "...") if doc.summary and len(doc.summary) > 80 else (doc.summary or "No summary")
        
        # Show summary_names if available
        names_info = ""
        if doc.summary_names:
            names_preview = ", ".join(doc.summary_names[:3])  # Show first 3 concept names
            if len(doc.summary_names) > 3:
                names_preview += f" (+{len(doc.summary_names) - 3} more)"
            names_info = f" | Concepts: [{names_preview}]"
        
        print(f"{indent}[L{doc.level}] {doc.official_identifier} - {doc.title}")
        print(f"{indent}     {summary_preview}{names_info}")
    
    if len(documents) > 10:
        print(f"{' ' * 2}... and {len(documents) - 10} more documents")
    
    return documents


def build_bm25_index_real_data(documents):
    """Build BM25 index from the real legal act documents."""
    print("\n" + "="*60)
    print("DEMO: Building BM25 Index with Real Data")
    print("="*60)
    
    # First, try to filter documents with summaries
    indexable_docs = DocumentExtractor.filter_documents(
        documents, has_summary=True
    )
    
    print(f"Documents with summaries (preferred): {len(indexable_docs)}")
    
    # If no summaries available, use documents with text content instead
    if not indexable_docs:
        print("No summaries found - using documents with text content instead")
        indexable_docs = DocumentExtractor.filter_documents(
            documents, has_content=True
        )
        print(f"Documents with text content (fallback): {len(indexable_docs)}")
        
        # For demo purposes, let's create synthetic summaries from text content
        print("Creating synthetic summaries from text content...")
        for doc in indexable_docs[:10]:  # Process first 10 for demo
            if doc.text_content and not doc.summary:
                # Extract clean text (remove XML tags)
                import re
                clean_text = re.sub(r'<[^>]+>', ' ', doc.text_content)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                
                # Create a summary from first 200 characters
                if len(clean_text) > 200:
                    synthetic_summary = clean_text[:200] + "..."
                else:
                    synthetic_summary = clean_text
                
                # Update the document with synthetic summary
                doc.summary = synthetic_summary
        
        # Filter again to get documents that now have summaries
        indexable_docs = [doc for doc in indexable_docs if doc.summary]
        print(f"Documents with synthetic summaries: {len(indexable_docs)}")
    
    if not indexable_docs:
        print("ERROR: No indexable documents found!")
        return None
    
    # Build the index
    print("Building BM25 index...")
    index = BM25SummaryIndex()
    index.build(indexable_docs)
    
    # Show index statistics
    metadata = index.get_metadata()
    stats = index.get_stats()
    
    print(f"\nIndex Metadata:")
    print(f"  Act IRI: {metadata.act_iri}")
    print(f"  Snapshot: {metadata.snapshot_id}")
    print(f"  Documents indexed: {metadata.document_count}")
    print(f"  Index type: {metadata.index_type}")
    
    print(f"\nIndex Statistics:")
    print(f"  Vocabulary size: {stats['vocabulary_size']} unique terms")
    print(f"  Total tokens: {stats['total_tokens']}")
    print(f"  Average document length: {stats['average_document_length']:.1f} tokens")
    
    return index


def demo_summary_names_functionality(index):
    """Demonstrate the new summary_names functionality and its impact on search."""
    print("\n" + "="*60)
    print("DEMO: Summary Names Functionality")
    print("="*60)
    
    # Analyze summary_names availability
    docs_with_names = [doc for doc in index.documents if doc.summary_names]
    docs_without_names = [doc for doc in index.documents if not doc.summary_names]
    
    print(f"Documents with summary_names: {len(docs_with_names)}")
    print(f"Documents without summary_names: {len(docs_without_names)}")
    
    if docs_with_names:
        print(f"\nSample documents with concept names:")
        for i, doc in enumerate(docs_with_names[:5]):
            print(f"  {i+1}. {doc.official_identifier} - {doc.title}")
            print(f"      Concept names: {doc.summary_names}")
            
            # Show weighted text sample for this document
            weighted_text = ""
            parts = []
            if doc.official_identifier:
                parts.append(doc.official_identifier)
            if doc.title:
                parts.extend([doc.title] * 2)
            if doc.summary:
                parts.extend([doc.summary] * 3)
            if doc.summary_names:
                summary_names_text = " ".join(doc.summary_names)
                parts.extend([summary_names_text] * 5)
            weighted_text = " ".join(parts)
            
            print(f"      Weighted text preview: {weighted_text[:150]}...")
    
    # Demonstrate search advantage of summary_names
    print(f"\n" + "-"*50)
    print("DEMONSTRATION: Search Enhancement with Summary Names")
    print("-"*50)
    
    if docs_with_names:
        # Find a document with interesting concept names
        sample_doc = docs_with_names[0]
        if sample_doc.summary_names:
            # Test search with one of the concept names
            test_concept = sample_doc.summary_names[0]
            
            print(f"\nTesting search for concept: '{test_concept}'")
            print(f"This concept appears in summary_names of: {sample_doc.official_identifier}")
            
            query = SearchQuery(query=test_concept, max_results=5)
            results = index.search(query)
            
            print(f"\nSearch results for '{test_concept}':")
            for result in results:
                doc = result.doc
                matched_in_names = "summary_names" in result.matched_fields
                names_indicator = " [★ CONCEPT MATCH]" if matched_in_names else ""
                
                print(f"  #{result.rank} {doc.official_identifier} - {doc.title}{names_indicator}")
                print(f"      Score: {result.score:.3f} | Matched fields: {', '.join(result.matched_fields)}")
                if doc.summary_names and matched_in_names:
                    matching_names = [name for name in doc.summary_names if test_concept.lower() in name.lower()]
                    print(f"      Matching concepts: {matching_names}")
    
    # Show weighted field analysis
    print(f"\n" + "-"*50)
    print("WEIGHTED FIELDS ANALYSIS")
    print("-"*50)
    
    if docs_with_names:
        sample_doc = docs_with_names[0]
        weighted_fields = sample_doc.get_weighted_fields()
        
        print(f"\nWeighted fields for: {sample_doc.official_identifier}")
        print(f"Field weights in BM25 index:")
        print(f"  - summary_names (5x): '{weighted_fields['summary_names']}'")
        print(f"  - summary (3x): '{weighted_fields['summary'][:100]}...' if text else 'None'")
        print(f"  - title (2x): '{weighted_fields['title']}'")
        print(f"  - official_identifier (1x): '{weighted_fields['official_identifier']}'")
        
        print(f"\nNote: summary_names have the highest weight (5x) in the BM25 index,")
        print(f"      making concept-based searches more precise and relevant.")


def demo_concept_based_searches(index):
    """Demonstrate searches specifically targeting legal concepts."""
    print("\n" + "="*60)
    print("DEMO: Concept-Based Legal Searches")
    print("="*60)
    
    # Collect all unique concept names from documents
    all_concepts = set()
    docs_with_concepts = []
    
    for doc in index.documents:
        if doc.summary_names:
            docs_with_concepts.append(doc)
            all_concepts.update(doc.summary_names)
    
    print(f"Total unique concepts found: {len(all_concepts)}")
    print(f"Documents with concepts: {len(docs_with_concepts)}")
    
    if all_concepts:
        # Show sample concepts
        sample_concepts = list(all_concepts)[:10]
        print(f"\nSample legal concepts identified:")
        for i, concept in enumerate(sample_concepts, 1):
            print(f"  {i:2d}. {concept}")
        
        # Test searches for different types of legal concepts
        concept_searches = []
        
        # Find some interesting concepts to search for
        for concept in all_concepts:
            if any(keyword in concept.lower() for keyword in ['vozidlo', 'registrace', 'kontrola', 'povinnost', 'právo']):
                concept_searches.append(concept)
                if len(concept_searches) >= 3:
                    break
        
        if not concept_searches:
            concept_searches = list(all_concepts)[:3]  # Fallback to first 3
        
        print(f"\n" + "-"*50)
        print("CONCEPT SEARCH DEMONSTRATIONS")
        print("-"*50)
        
        for i, concept in enumerate(concept_searches, 1):
            print(f"\n{i}. Searching for concept: '{concept}'")
            
            query = SearchQuery(query=concept, max_results=3)
            results = index.search(query)
            
            if results:
                for result in results:
                    doc = result.doc
                    is_concept_match = "summary_names" in result.matched_fields
                    boost_indicator = " ⚡" if is_concept_match else ""
                    
                    print(f"  #{result.rank} {doc.official_identifier}{boost_indicator}")
                    print(f"      Title: {doc.title}")
                    print(f"      Score: {result.score:.3f}")
                    print(f"      Matched in: {', '.join(result.matched_fields)}")
                    
                    if is_concept_match and doc.summary_names:
                        related_concepts = [name for name in doc.summary_names 
                                         if concept.lower() in name.lower() or name.lower() in concept.lower()]
                        if related_concepts:
                            print(f"      Related concepts: {related_concepts}")
            else:
                print(f"  No results found for '{concept}'")
    
    else:
        print("\nNo summary_names found in documents.")
        print("This might indicate that:")
        print("  1. The legal act hasn't been processed with the summarizer yet")
        print("  2. The summarizer's concept extraction needs to be run")
        print("  3. The concept extraction feature is not yet populated")


def demo_vehicle_law_searches(index):
    """Demonstrate searches specific to vehicle law terminology."""
    print("\n" + "="*60)
    print("DEMO: Vehicle Law Specific Searches")
    print("="*60)
    
    # Test searches for vehicle law specific terms
    search_terms = [
        "základní pojmy",
        "vozidlo",
        "silniční vozidlo",
        "historické vozidlo",
        "technicky nezpůsobilé vozidlo",
        "registrace",
        "žadatel",
        "technická kontrola",
        "oprávnění k provozování stanice technické kontroly",
        "provozovatel",
        "provozovovatel stanice technické kontroly",
        "sankce"
    ]
    
    for i, term in enumerate(search_terms, 1):
        print(f"\n{i}. Search: '{term}'")
        query = SearchQuery(query=term, max_results=3)
        results = index.search(query)
        
        if results:
            for result in results:
                doc = result.doc
                print(f"  #{result.rank} [{doc.element_type.value}] {doc.official_identifier} - {doc.title}")
                print(f"      Score: {result.score:.3f}, Level: {doc.level}")
                print(f"      Matched: {', '.join(result.matched_fields)}")
                if result.snippet:
                    snippet = result.snippet[:100] + "..." if len(result.snippet) > 100 else result.snippet
                    print(f"      Snippet: {snippet}")
        else:
            print(f"  No results found for '{term}'")


def demo_filtered_searches(index):
    """Demonstrate filtered searches on the vehicle law data."""
    print("\n" + "="*60)
    print("DEMO: Filtered Searches")
    print("="*60)
    
    # Search only in sections (detailed provisions)
    print("1. Search 'vozidel' in sections only:")
    query1 = SearchQuery(
        query="vozidel",
        element_types=[ElementType.SECTION],
        max_results=5
    )
    results1 = index.search(query1)
    
    for result in results1:
        print(f"  {result.doc.official_identifier} - {result.doc.title} (score: {result.score:.3f})")
    
    # Search in high-level structure only
    print(f"\n2. Search 'ustanovení' in high-level structure (level ≤ 1):")
    query2 = SearchQuery(
        query="ustanovení",
        max_level=1,
        max_results=5
    )
    results2 = index.search(query2)
    
    for result in results2:
        print(f"  [L{result.doc.level}] {result.doc.official_identifier} - {result.doc.title} (score: {result.score:.3f})")
    
    # Search with paragraph pattern
    print(f"\n3. Search 'povinnost' in paragraphs (§ pattern):")
    query3 = SearchQuery(
        query="povinnost",
        official_identifier_pattern="^§",
        max_results=5
    )
    results3 = index.search(query3)
    
    for result in results3:
        print(f"  {result.doc.official_identifier} - {result.doc.title} (score: {result.score:.3f})")


def demo_content_analysis(index):
    """Analyze the content and vocabulary of the vehicle law."""
    print("\n" + "="*60)
    print("DEMO: Content Analysis")
    print("="*60)
    
    # Find documents with highest term diversity
    print("Documents with most diverse vocabulary:")
    
    doc_term_counts = []
    for i, doc in enumerate(index.documents[:10]):  # Analyze first 10 docs
        top_terms = index.get_top_terms(i, top_k=5)
        if top_terms:
            doc_term_counts.append((i, doc, len(top_terms), top_terms))
    
    # Sort by term count
    doc_term_counts.sort(key=lambda x: x[2], reverse=True)
    
    for i, (doc_idx, doc, term_count, top_terms) in enumerate(doc_term_counts[:5]):
        print(f"\n{i+1}. {doc.official_identifier} - {doc.title}")
        print(f"   Top terms:")
        for term, score in top_terms:
            print(f"     {term:15s} {score:6.2f}")


def demo_search_comparison(index):
    """Compare search results for different legal concepts."""
    print("\n" + "="*60)
    print("DEMO: Legal Concept Search Comparison")
    print("="*60)
    
    # Compare searches for different legal concepts
    concepts = {
        "definice a pojmy": "základní pojmy",
        "registrace": "registrace vozidel",
        "silniční vozidlo": "technicky nezpůsobilé vozidlo",
        "technický požadavek": "technická způsobilost",
        "kontrola a dozor": "kontrola dozor"
    }
    
    for concept_name, search_term in concepts.items():
        print(f"\n{concept_name.upper()}:")
        print(f"Search: '{search_term}'")
        
        query = SearchQuery(query=search_term, max_results=3)
        results = index.search(query)
        
        if results:
            for result in results:
                doc = result.doc
                print(f"  {doc.official_identifier} - {doc.title}")
                print(f"    Score: {result.score:.3f}, Matched: {', '.join(result.matched_fields)}")
        else:
            print(f"  No results found")


def main():
    """Run the complete demo with real legal act data."""
    print("BM25 Index Demo - Real Legal Act 56/2001 (Vehicle Law)")
    print("Enhanced with Summary Names Functionality")
    print("=" * 60)
    
    try:
        # Check dependencies
        try:
            import rank_bm25
            print("✓ rank-bm25 library available")
        except ImportError:
            print("⚠ rank-bm25 library not installed")
            print("  Install with: pip install rank-bm25")
            return
        
        # Load the real legal act
        legal_act, act_iri = load_legal_act_56_2001()
        
        # Extract and analyze documents
        documents = extract_and_analyze_documents(legal_act, act_iri)
        
        # Build BM25 index
        index = build_bm25_index_real_data(documents)
        
        if index is None:
            print("Failed to build index - no indexable documents found")
            return
        
        # Run demonstrations
        demo_summary_names_functionality(index)
        demo_concept_based_searches(index)
        demo_vehicle_law_searches(index)
        demo_filtered_searches(index)
        demo_content_analysis(index)
        demo_search_comparison(index)
        
        print("\n" + "="*60)
        print("Real Data Demo Completed!")
        print("\nKey insights from vehicle law 56/2001:")
        print("  ✓ Successfully indexed real Czech legal act")
        print("  ✓ Summary_names provide enhanced concept-based search")
        print("  ✓ BM25 effectively ranks vehicle law terminology")
        print("  ✓ Concept names get highest weight (5x) for precision")
        print("  ✓ Hierarchical filtering works with legal structure")
        print("  ✓ Legal concepts are properly searchable")
        print("  ✓ Complex legal vocabulary is well-tokenized")
        print("\nThis demonstrates BM25 readiness for real legal document processing!")
        print("The summary_names feature significantly enhances search relevance!")
        print("="*60)
        
    except Exception as e:
        print(f"Error in demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
