#!/usr/bin/env python3
"""
Demo script for HybridSearchEngine - Iteration 4

This demonstrates the hybrid retrieval capabilities combining BM25 and FAISS
for optimal search performance across different query types.
"""

import sys
import logging
from typing import List
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from index.hybrid import HybridSearchEngine, HybridConfig
from index.domain import SearchQuery, SearchResult, IndexDoc, ElementType

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class MockBM25Index:
    """Enhanced mock BM25 for comprehensive demo."""
    
    def __init__(self):
        self.documents = [
            IndexDoc(
                element_id="legal-1",
                title="Základní pojmy",
                summary="Definice základních pojmů používaných v zákoně o silniční dopravě",
                summary_names=["pojem", "definice", "silniční doprava"],
                official_identifier="§ 2",
                level=2,
                element_type=ElementType.SECTION,
                act_iri="https://zakonyprolidi.cz/cs/2001-56",
                snapshot_id="2023-01-01"
            ),
            IndexDoc(
                element_id="legal-2",
                title="Registrace vozidel",
                summary="Postupy a požadavky pro registraci motorových vozidel",
                summary_names=["registrace", "vozidlo", "postup", "požadavky"],
                official_identifier="§ 6",
                level=2,
                element_type=ElementType.SECTION,
                act_iri="https://zakonyprolidi.cz/cs/2001-56",
                snapshot_id="2023-01-01"
            ),
            IndexDoc(
                element_id="legal-3",
                title="Technická kontrola vozidel",
                summary="Pravidla pro pravidelnou technickou kontrolu bezpečnosti vozidel",
                summary_names=["technická kontrola", "vozidlo", "bezpečnost", "pravidelná"],
                official_identifier="§ 47",
                level=2,
                element_type=ElementType.SECTION,
                act_iri="https://zakonyprolidi.cz/cs/2001-56",
                snapshot_id="2023-01-01"
            ),
            IndexDoc(
                element_id="legal-4",
                title="Řidičské oprávnění",
                summary="Podmínky pro získání a držení řidičského oprávnění",
                summary_names=["řidičské oprávnění", "podmínky", "získání", "držení"],
                official_identifier="§ 78",
                level=2,
                element_type=ElementType.SECTION,
                act_iri="https://zakonyprolidi.cz/cs/2001-56",
                snapshot_id="2023-01-01"
            ),
            IndexDoc(
                element_id="legal-5",
                title="Dopravní značky",
                summary="Systém dopravních značek a jejich význam pro řidiče",
                summary_names=["dopravní značky", "význam", "řidiče", "systém"],
                official_identifier="§ 15",
                level=2,
                element_type=ElementType.SECTION,
                act_iri="https://zakonyprolidi.cz/cs/2001-56",
                snapshot_id="2023-01-01"
            )
        ]
    
    def search(self, query, k=10):
        """Enhanced keyword matching."""
        results = []
        query_text = query.query if hasattr(query, 'query') else str(query)
        
        for i, doc in enumerate(self.documents):
            score = 0.0
            
            # Exact keyword matching
            for term in query_text.lower().split():
                if term in doc.title.lower():
                    score += 3.0
                if any(term in name.lower() for name in doc.summary_names):
                    score += 2.0
                if term in doc.summary.lower():
                    score += 1.0
            
            if score > 0:
                results.append(SearchResult(
                    doc=doc,
                    score=score,
                    rank=i + 1,
                    matched_fields=["title", "summary"] if score > 2 else ["summary"],
                    snippet=doc.summary[:80] + "..." if len(doc.summary) > 80 else doc.summary
                ))
        
        results.sort(key=lambda x: x.score, reverse=True)
        for i, result in enumerate(results):
            result.rank = i + 1
        return results[:k]
    
    def get_statistics(self):
        return {
            'index_type': 'bm25_mock',
            'document_count': len(self.documents),
            'model': 'mock_bm25'
        }


class MockFAISSIndex:
    """Enhanced mock FAISS for comprehensive demo."""
    
    def __init__(self):
        self.documents = [
            IndexDoc(
                element_id="legal-1",
                title="Základní pojmy",
                summary="Definice základních pojmů používaných v zákoně o silniční dopravě",
                summary_names=["pojem", "definice", "silniční doprava"],
                official_identifier="§ 2",
                level=2,
                element_type=ElementType.SECTION,
                act_iri="https://zakonyprolidi.cz/cs/2001-56",
                snapshot_id="2023-01-01"
            ),
            IndexDoc(
                element_id="legal-2",
                title="Registrace vozidel",
                summary="Postupy a požadavky pro registraci motorových vozidel",
                summary_names=["registrace", "vozidlo", "postup", "požadavky"],
                official_identifier="§ 6",
                level=2,
                element_type=ElementType.SECTION,
                act_iri="https://zakonyprolidi.cz/cs/2001-56",
                snapshot_id="2023-01-01"
            ),
            IndexDoc(
                element_id="legal-3",
                title="Technická kontrola vozidel",
                summary="Pravidla pro pravidelnou technickou kontrolu bezpečnosti vozidel",
                summary_names=["technická kontrola", "vozidlo", "bezpečnost", "pravidelná"],
                official_identifier="§ 47",
                level=2,
                element_type=ElementType.SECTION,
                act_iri="https://zakonyprolidi.cz/cs/2001-56",
                snapshot_id="2023-01-01"
            ),
            IndexDoc(
                element_id="legal-4",
                title="Řidičské oprávnění",
                summary="Podmínky pro získání a držení řidičského oprávnění",
                summary_names=["řidičské oprávnění", "podmínky", "získání", "držení"],
                official_identifier="§ 78",
                level=2,
                element_type=ElementType.SECTION,
                act_iri="https://zakonyprolidi.cz/cs/2001-56",
                snapshot_id="2023-01-01"
            ),
            IndexDoc(
                element_id="legal-6",
                title="Dopravní přestupky",
                summary="Klasifikace a sankce za dopravní přestupky",
                summary_names=["dopravní přestupky", "klasifikace", "sankce"],
                official_identifier="§ 125",
                level=2,
                element_type=ElementType.SECTION,
                act_iri="https://zakonyprolidi.cz/cs/2001-56",
                snapshot_id="2023-01-01"
            )
        ]
    
    def search(self, query, k=10):
        """Enhanced semantic similarity matching."""
        results = []
        query_text = query.query if hasattr(query, 'query') else str(query)
        
        # Semantic similarity patterns
        semantic_patterns = {
            "kontrola": ["technická kontrola", "bezpečnost", "pravidelná"],
            "vozidlo": ["registrace", "technická kontrola", "motorová vozidla"],
            "řidič": ["řidičské oprávnění", "podmínky", "získání"],
            "registrace": ["vozidlo", "postup", "požadavky"],
            "doprava": ["silniční doprava", "dopravní značky", "dopravní přestupky"]
        }
        
        for i, doc in enumerate(self.documents):
            score = 0.0
            
            # Semantic matching based on conceptual similarity
            for pattern_key, related_terms in semantic_patterns.items():
                if pattern_key in query_text.lower():
                    if any(term in doc.summary.lower() or 
                          any(term in name.lower() for name in doc.summary_names)
                          for term in related_terms):
                        score += 0.85
                        break
            
            # General semantic matching
            if score == 0.0:
                for name in doc.summary_names:
                    if any(word in query_text.lower() for word in name.lower().split()):
                        score = max(score, 0.65)
            
            if score > 0:
                results.append(SearchResult(
                    doc=doc,
                    score=score,
                    rank=i + 1,
                    matched_fields=["semantic"],
                    snippet=doc.summary[:80] + "..." if len(doc.summary) > 80 else doc.summary
                ))
        
        results.sort(key=lambda x: x.score, reverse=True)
        for i, result in enumerate(results):
            result.rank = i + 1
        return results[:k]
    
    def get_statistics(self):
        return {
            'index_type': 'faiss_mock',
            'document_count': len(self.documents),
            'model': 'mock_faiss',
            'dimensions': 384
        }


def print_results(results: List[SearchResult], title: str):
    """Pretty print search results."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    
    if not results:
        print("No results found.")
        return
    
    for result in results:
        print(f"\n#{result.rank:2d} | Score: {result.score:.3f} | {result.doc.official_identifier}")
        print(f"     📋 {result.doc.title}")
        print(f"     💭 {result.snippet}")
        if hasattr(result, 'matched_fields') and result.matched_fields:
            print(f"     🎯 Matched: {', '.join(result.matched_fields)}")


def demo_search_strategies():
    """Demonstrate different hybrid search strategies."""
    print("🚀 HybridSearchEngine Demo - Iteration 4")
    print("=" * 60)
    
    # Initialize mock indexes
    bm25_index = MockBM25Index()
    faiss_index = MockFAISSIndex()
    
    # Initialize hybrid engine
    hybrid = HybridSearchEngine(bm25_index=bm25_index, faiss_index=faiss_index)
    
    # Test queries
    test_queries = [
        "technická kontrola vozidel",
        "registrace",
        "řidičské oprávnění podmínky",
        "dopravní značky"
    ]
    
    for query_text in test_queries:
        query = SearchQuery(query=query_text, max_results=3)
        
        print(f"\n🔍 Query: '{query_text}'")
        print("-" * 60)
        
        # Test different strategies
        strategies = [
            ("semantic_first", "Semantic-First Strategy"),
            ("keyword_first", "Keyword-First Strategy"), 
            ("parallel", "Parallel Fusion Strategy")
        ]
        
        for strategy, description in strategies:
            results = hybrid.search(query, strategy=strategy)
            print_results(results, f"{description} ({len(results)} results)")


def demo_configuration_impact():
    """Demonstrate impact of different configurations."""
    print(f"\n{'🔧 Configuration Impact Demo'}")
    print("=" * 60)
    
    bm25_index = MockBM25Index()
    faiss_index = MockFAISSIndex()
    hybrid = HybridSearchEngine(bm25_index=bm25_index, faiss_index=faiss_index)
    
    query = SearchQuery(query="kontrola vozidel", max_results=3)
    
    configurations = [
        ({"faiss_weight": 0.8, "bm25_weight": 0.2}, "FAISS-Heavy (80/20)"),
        ({"faiss_weight": 0.5, "bm25_weight": 0.5}, "Balanced (50/50)"),
        ({"faiss_weight": 0.2, "bm25_weight": 0.8}, "BM25-Heavy (20/80)"),
        ({"rerank_strategy": "rrf"}, "RRF Fusion"),
        ({"rerank_strategy": "weighted"}, "Weighted Fusion")
    ]
    
    for config_params, description in configurations:
        results = hybrid.search(query, strategy="parallel", **config_params)
        print_results(results, f"{description}")


def demo_statistics():
    """Demonstrate statistics reporting."""
    print(f"\n{'📊 Statistics Demo'}")
    print("=" * 60)
    
    bm25_index = MockBM25Index()
    faiss_index = MockFAISSIndex()
    hybrid = HybridSearchEngine(bm25_index=bm25_index, faiss_index=faiss_index)
    
    stats = hybrid.get_statistics()
    
    print("Hybrid Search Engine Statistics:")
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for subkey, subvalue in value.items():
                print(f"    {subkey}: {subvalue}")
        else:
            print(f"  {key}: {value}")


def main():
    """Run the hybrid search demo."""
    try:
        demo_search_strategies()
        demo_configuration_impact()
        demo_statistics()
        
        print(f"\n✅ Iteration 4 Demo Complete!")
        print("=" * 60)
        print("🎯 Hybrid retrieval successfully combines BM25 and FAISS")
        print("🎯 Multiple search strategies support different query types")
        print("🎯 Configurable fusion algorithms optimize results")
        print("🎯 Comprehensive statistics enable performance monitoring")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise


if __name__ == "__main__":
    main()
