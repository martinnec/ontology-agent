"""
Demo script for SearchService - demonstrating unified search functionality.

This demo shows how to use the SearchService to perform different types of
searches across legal acts.

HOW TO RUN:
From the src directory, run:
    python -m search.demo_search_service

Or from the project root:
    cd src && python -m search.demo_search_service

The demo uses IndexService to build indexes and then demonstrates
various search capabilities.
"""

import os
import sys

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
    
    # Create sections with traffic-related content
    section1 = MockLegalElement(
        id="https://example.com/section/1",
        element_type="LegalSection",
        title="Základní pojmy",
        official_identifier="§ 1",
        summary="Definice základních pojmů: vozidlo, řidič, registrace, technická kontrola",
        text_content="V tomto zákoně se rozumí vozidlem motorové vozidlo určené k provozu na pozemních komunikacích. Řidičem se rozumí osoba řídící vozidlo."
    )
    
    section2 = MockLegalElement(
        id="https://example.com/section/2", 
        element_type="LegalSection",
        title="Registrace vozidel",
        official_identifier="§ 2",
        summary="Postupy registrace motorových vozidel, povinnosti vlastníka, dokumenty",
        text_content="Každé motorové vozidlo musí být před uvedením do provozu registrováno u příslušného úřadu. Vlastník vozidla je povinen předložit technický průkaz a doklad o pojištění."
    )
    
    section3 = MockLegalElement(
        id="https://example.com/section/3",
        element_type="LegalSection", 
        title="Technická kontrola vozidel",
        official_identifier="§ 3",
        summary="Pravidelná technická kontrola, lhůty, kontrolované parametry, sankce",
        text_content="Motorová vozidla podléhají pravidelné technické kontrole každé dva roky. Kontroluje se zejména stav brzd, řízení, osvětlení a výfukového systému."
    )
    
    section4 = MockLegalElement(
        id="https://example.com/section/4",
        element_type="LegalSection",
        title="Povinnosti řidiče",
        official_identifier="§ 4", 
        summary="Základní povinnosti řidiče, rychlost, bezpečnost, přednost v jízdě",
        text_content="Řidič je povinen řídit vozidlo opatrně a ohleduplně, dodržovat dopravní značení a nepřekročit povolenou rychlost. Musí dát přednost vozidlům jedoucím zprava."
    )
    
    section5 = MockLegalElement(
        id="https://example.com/section/5",
        element_type="LegalSection",
        title="Dopravní přestupky a sankce",
        official_identifier="§ 5",
        summary="Klasifikace dopravních přestupků, výše pokut, bodový systém",
        text_content="Za překročení rychlosti o více než 20 km/h se ukládá pokuta 2500 Kč a 3 trestné body. Za jízdu pod vlivem alkoholu se ukládá pokuta 25000 Kč."
    )
    
    chapter1 = MockLegalElement(
        id="https://example.com/chapter/1",
        element_type="LegalChapter",
        title="Obecná ustanovení",
        official_identifier="Hlava I",
        summary="Základní ustanovení, definice pojmů, registrace vozidel",
        elements=[section1, section2]
    )
    
    chapter2 = MockLegalElement(
        id="https://example.com/chapter/2", 
        element_type="LegalChapter",
        title="Technické požadavky",
        official_identifier="Hlava II",
        summary="Technická kontrola vozidel a související povinnosti",
        elements=[section3]
    )
    
    chapter3 = MockLegalElement(
        id="https://example.com/chapter/3",
        element_type="LegalChapter", 
        title="Pravidla provozu",
        official_identifier="Hlava III",
        summary="Povinnosti řidičů a sankce za porušení pravidel",
        elements=[section4, section5]
    )
    
    legal_act = MockLegalElement(
        id="https://example.com/act/demo-act",
        element_type="LegalAct",
        title="Demo zákon o silničním provozu",
        official_identifier="Zákon č. 123/2024 Sb.",
        summary="Demonstrační zákon upravující pravidla silničního provozu, registraci vozidel a sankce",
        elements=[chapter1, chapter2, chapter3]
    )
    
    print(f"✓ Created mock legal act: {legal_act.title}")
    return legal_act

def setup_mock_search_service():
    """Set up a mock search service for demonstration."""
    print("Setting up mock search service for demonstration...")
    
    # Create mock components
    class MockSearchResult:
        def __init__(self, doc, score: float, rank: int):
            self.doc = doc
            self.score = score
            self.rank = rank
            self.matched_fields = ["title", "summary"]
            self.snippet = f"Snippet from {doc.title}..."
    
    class MockIndexDoc:
        def __init__(self, element_id: str, title: str, summary: str, element_type: str):
            self.element_id = element_id
            self.title = title
            self.official_identifier = f"§ {element_id.split('/')[-1]}"
            self.summary = summary
            self.text_content = f"Full content for {title}..."
            self.element_type = type('ElementType', (), {'value': element_type})()
            self.level = 1
            self.parent_id = None
    
    class MockIndex:
        def __init__(self, index_type: str):
            self.index_type = index_type
            self._create_mock_docs()
        
        def _create_mock_docs(self):
            self.docs = [
                MockIndexDoc("1", "Základní pojmy", "Definice základních pojmů", "section"),
                MockIndexDoc("2", "Registrace vozidel", "Postupy registrace vozidel", "section"),
                MockIndexDoc("3", "Technická kontrola", "Pravidelná technická kontrola", "section"),
                MockIndexDoc("4", "Povinnosti řidiče", "Základní povinnosti řidiče", "section"),
                MockIndexDoc("5", "Dopravní přestupky", "Sankce za porušení pravidel", "section"),
            ]
        
        def search(self, query):
            # Mock search logic based on simple keyword matching
            results = []
            query_lower = query.query.lower()
            
            for i, doc in enumerate(self.docs):
                score = 0.0
                rank = i + 1
                
                # Simple scoring based on title and summary matching
                if query_lower in doc.title.lower():
                    score += 0.8
                if query_lower in doc.summary.lower():
                    score += 0.6
                
                # Add some variety in scores
                if "registrace" in query_lower and "registrace" in doc.title.lower():
                    score = 0.95
                elif "technická" in query_lower and "technická" in doc.title.lower():
                    score = 0.90
                elif "řidič" in query_lower and "řidič" in doc.title.lower():
                    score = 0.85
                elif "pojmy" in query_lower and "pojmy" in doc.title.lower():
                    score = 0.80
                
                if score > 0.1:
                    results.append(MockSearchResult(doc, score, rank))
            
            # Sort by score descending
            results.sort(key=lambda x: x.score, reverse=True)
            
            # Update ranks
            for i, result in enumerate(results):
                result.rank = i + 1
            
            return results[:5]  # Return top 5 results
        
        def get_similar_documents(self, element_id: str, k: int = 5):
            # Mock similarity search
            similar_docs = [(doc, 0.8 - i * 0.1) for i, doc in enumerate(self.docs[:k])]
            return similar_docs
    
    class MockIndexCollection:
        def __init__(self, act_iri: str):
            self.act_iri = act_iri
            self._indexes = {
                'bm25': MockIndex('bm25'),
                'faiss': MockIndex('faiss'),
                'bm25_full': MockIndex('bm25_full'),
                'faiss_full': MockIndex('faiss_full')
            }
        
        def get_index(self, index_type: str):
            return self._indexes.get(index_type)
        
        def get_available_indexes(self):
            return list(self._indexes.keys())
        
        def get_document_count(self):
            return 8  # Mock document count
    
    class MockIndexService:
        def __init__(self, output_dir: str):
            self.output_dir = output_dir
        
        def get_indexes(self, legal_act, force_rebuild: bool = False):
            return MockIndexCollection(str(legal_act.id))
    
    return MockIndexService

def demo_search_initialization():
    """Demonstrate SearchService initialization."""
    print("\n" + "="*60)
    print("DEMO: SearchService Initialization")
    print("="*60)
    
    from search import SearchService
    
    # Get legal act and set up services
    legal_act = get_legal_act()
    
    # Set up mock index service
    MockIndexService = setup_mock_search_service()
    index_service = MockIndexService("./demo_indexes")
    
    # Initialize SearchService
    print(f"Initializing SearchService for: {legal_act.title}")
    search_service = SearchService(index_service, legal_act)
    
    # Show service information
    info = search_service.get_index_info()
    print("✓ SearchService initialized successfully")
    print(f"  - Act IRI: {info['act_iri']}")
    print(f"  - Available indexes: {', '.join(info['available_indexes'])}")
    print(f"  - Document count: {info['document_count']}")
    
    return search_service

def demo_keyword_search(search_service):
    """Demonstrate keyword search functionality."""
    print("\n" + "="*60)
    print("DEMO: Keyword Search")
    print("="*60)
    
    # Test various keyword searches
    test_queries = [
        "registrace vozidel",
        "technická kontrola", 
        "řidič povinnosti",
        "základní pojmy"
    ]
    
    for query in test_queries:
        print(f"\nSearching for: '{query}'")
        try:
            results = search_service.search_keyword(query)
            
            print(f"✓ Found {len(results.items)} results in {results.search_time_ms:.1f}ms")
            print(f"  Strategy: {results.strategy.value}")
            print(f"  Score range: {results.score_range['min']:.2f} - {results.score_range['max']:.2f}")
            
            # Show top results
            for i, item in enumerate(results.items[:3]):
                print(f"  {i+1}. {item.title} (score: {item.score:.2f})")
                print(f"     {item.official_identifier}: {item.summary}")
                
        except Exception as e:
            print(f"✗ Search failed: {e}")

def demo_semantic_search(search_service):
    """Demonstrate semantic search functionality."""
    print("\n" + "="*60)
    print("DEMO: Semantic Search")
    print("="*60)
    
    # Test semantic searches
    test_queries = [
        "car registration process",
        "vehicle safety inspection",
        "driver responsibilities",
        "traffic violations penalties"
    ]
    
    for query in test_queries:
        print(f"\nSemantic search for: '{query}'")
        try:
            results = search_service.search_semantic(query)
            
            print(f"✓ Found {len(results.items)} results in {results.search_time_ms:.1f}ms")
            print(f"  Strategy: {results.strategy.value}")
            
            # Show top results
            for i, item in enumerate(results.items[:2]):
                print(f"  {i+1}. {item.title} (score: {item.score:.2f})")
                
        except Exception as e:
            print(f"✗ Semantic search failed: {e}")

def demo_hybrid_search(search_service):
    """Demonstrate hybrid search functionality."""
    print("\n" + "="*60)
    print("DEMO: Hybrid Search")
    print("="*60)
    
    query = "registrace vozidel"
    print(f"Hybrid search for: '{query}'")
    
    # Test different hybrid strategies
    strategies = ["semantic_first", "keyword_first", "parallel"]
    
    for strategy in strategies:
        print(f"\n  Testing {strategy} strategy:")
        try:
            results = search_service.search_hybrid(query, strategy=strategy)
            
            print(f"  ✓ Found {len(results.items)} results using {results.strategy.value}")
            print(f"    Search time: {results.search_time_ms:.1f}ms")
            
            if results.items:
                best_result = results.items[0]
                print(f"    Best match: {best_result.title} (score: {best_result.score:.2f})")
                
        except Exception as e:
            print(f"  ✗ {strategy} search failed: {e}")

def demo_search_with_filters(search_service):
    """Demonstrate search with filtering options."""
    print("\n" + "="*60)
    print("DEMO: Search with Filters")
    print("="*60)
    
    from search.domain import SearchOptions
    
    # Test search with element type filter
    print("Searching with element type filter (sections only):")
    options = SearchOptions(
        max_results=3,
        element_types=["section"],
        min_score=0.1
    )
    
    try:
        results = search_service.search_keyword("vozidel", options)
        
        print(f"✓ Found {len(results.items)} results")
        print(f"  Filters applied: {results.filters_applied}")
        
        for item in results.items:
            print(f"  - {item.element_type}: {item.title}")
            
    except Exception as e:
        print(f"✗ Filtered search failed: {e}")
    
    # Test search with level filter
    print("\nSearching with level filter (level 1-2):")
    options = SearchOptions(
        min_level=1,
        max_level=2,
        boost_title=2.0
    )
    
    try:
        results = search_service.search_keyword("povinnosti", options)
        
        print(f"✓ Found {len(results.items)} results")
        print(f"  Title boost: {options.boost_title}")
        
    except Exception as e:
        print(f"✗ Level filtered search failed: {e}")

def demo_similarity_search(search_service):
    """Demonstrate similarity search functionality."""
    print("\n" + "="*60)
    print("DEMO: Similarity Search")
    print("="*60)
    
    # Test similarity search
    reference_element = "https://example.com/section/2"
    print(f"Finding documents similar to: {reference_element}")
    
    try:
        results = search_service.search_similar(reference_element)
        
        print(f"✓ Found {len(results.items)} similar documents")
        print(f"  Strategy: {results.strategy.value}")
        print(f"  Query: {results.query}")
        
        for i, item in enumerate(results.items):
            print(f"  {i+1}. {item.title} (similarity: {item.score:.2f})")
            print(f"     Matched fields: {', '.join(item.matched_fields)}")
            
    except Exception as e:
        print(f"✗ Similarity search failed: {e}")

def demo_fulltext_search(search_service):
    """Demonstrate full-text search functionality."""
    print("\n" + "="*60)
    print("DEMO: Full-text Search")
    print("="*60)
    
    # Test full-text searches
    queries = [
        "motorové vozidlo",
        "pravidelná kontrola",
        "pokuta za překročení"
    ]
    
    for query in queries:
        print(f"\nFull-text search for: '{query}'")
        try:
            results = search_service.search_fulltext(query)
            
            print(f"✓ Found {len(results.items)} text chunks")
            print(f"  Strategy: {results.strategy.value}")
            
            if results.items:
                best_result = results.items[0]
                print(f"  Best match: {best_result.title}")
                if best_result.highlighted_text:
                    print(f"  Snippet: {best_result.highlighted_text}")
                    
        except Exception as e:
            print(f"✗ Full-text search failed: {e}")

def demo_exact_phrase_search(search_service):
    """Demonstrate exact phrase search functionality."""
    print("\n" + "="*60)
    print("DEMO: Exact Phrase Search")
    print("="*60)
    
    # Test exact phrase searches
    phrases = [
        "je povinen",
        "motorové vozidlo", 
        "technická kontrola"
    ]
    
    for phrase in phrases:
        print(f"\nExact phrase search for: '{phrase}'")
        try:
            results = search_service.search_exact_phrase(phrase)
            
            print(f"✓ Found {len(results.items)} exact matches")
            print(f"  Strategy: {results.strategy.value}")
            
            if results.items:
                for i, item in enumerate(results.items[:2]):
                    print(f"  {i+1}. {item.title} (score: {item.score:.2f})")
                    
        except Exception as e:
            print(f"✗ Exact phrase search failed: {e}")

def demo_search_comparison(search_service):
    """Demonstrate comparing different search strategies."""
    print("\n" + "="*60)
    print("DEMO: Search Strategy Comparison")
    print("="*60)
    
    query = "technická kontrola"
    print(f"Comparing search strategies for: '{query}'\n")
    
    from search.domain import SearchStrategy
    
    strategies = [
        SearchStrategy.KEYWORD,
        SearchStrategy.SEMANTIC,
        SearchStrategy.HYBRID_SEMANTIC_FIRST,
        SearchStrategy.FULLTEXT
    ]
    
    comparison_results = {}
    
    for strategy in strategies:
        try:
            results = search_service.search(query, strategy=strategy)
            comparison_results[strategy.value] = {
                'count': len(results.items),
                'time': results.search_time_ms,
                'best_score': results.items[0].score if results.items else 0.0,
                'best_title': results.items[0].title if results.items else "No results"
            }
            print(f"✓ {strategy.value}: {len(results.items)} results in {results.search_time_ms:.1f}ms")
            
        except Exception as e:
            print(f"✗ {strategy.value} failed: {e}")
            comparison_results[strategy.value] = {'error': str(e)}
    
    # Show comparison summary
    print("\nComparison Summary:")
    print("-" * 40)
    for strategy, data in comparison_results.items():
        if 'error' not in data:
            print(f"{strategy:20} | {data['count']:2} results | {data['time']:5.1f}ms | Best: {data['best_score']:.2f}")
        else:
            print(f"{strategy:20} | ERROR: {data['error']}")

def main():
    """Main demo function."""
    print("SearchService Demo")
    print("This demo showcases the unified search functionality")
    print("of the SearchService across different search strategies.")
    
    try:
        # Initialize search service
        search_service = demo_search_initialization()
        
        # Run all demo sections
        demo_keyword_search(search_service)
        demo_semantic_search(search_service)
        demo_hybrid_search(search_service)
        demo_search_with_filters(search_service)
        demo_similarity_search(search_service)
        demo_fulltext_search(search_service)
        demo_exact_phrase_search(search_service)
        demo_search_comparison(search_service)
        
        print("\n" + "="*60)
        print("DEMO COMPLETED")
        print("="*60)
        print("This demo showed:")
        print("✓ Keyword search using BM25 indexes")
        print("✓ Semantic search using FAISS indexes")
        print("✓ Hybrid search strategies")
        print("✓ Search filtering and options")
        print("✓ Similarity search")
        print("✓ Full-text search in document chunks")
        print("✓ Exact phrase matching")
        print("✓ Strategy comparison")
        print("\nThe SearchService provides a unified interface for all")
        print("search operations, making it easy to experiment with")
        print("different strategies and find the best approach for")
        print("your specific search needs.")
        
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
