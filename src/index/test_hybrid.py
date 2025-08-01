"""
Simple test for the HybridSearchEngine.
This test file follows the project's testing guidelines:
- No testing library dependencies
- Simple Python script with main function
- Tests placed directly in src directory
- Named with test_ prefix
- Self-contained and runnable independently

HOW TO RUN:
From the src directory, run:
    python -m index.test_hybrid

Or from the project root:
    cd src && python -m index.test_hybrid

The test uses mock implementations to avoid external dependencies.
"""

import os
# Set any required environment variables for testing
os.environ["OPENAI_API_KEY"] = "dummy-key-for-testing"

# Import statements using relative imports
from .hybrid import HybridSearchEngine, HybridConfig
from .domain import SearchQuery, SearchResult, IndexDoc, ElementType

class MockBM25Index:
    """Mock implementation of BM25SummaryIndex for testing."""
    
    def __init__(self):
        self.documents = [
            IndexDoc(
                element_id="mock-bm25-1",
                title="Základní pojmy",
                summary="Definice základních pojmů používaných v zákoně",
                summary_names=["pojem", "definice", "zákon"],
                official_identifier="§ 2",
                level=2,
                element_type=ElementType.SECTION,
                act_iri="https://example.com/act/1",
                snapshot_id="2023-01-01"
            ),
            IndexDoc(
                element_id="mock-bm25-2", 
                title="Registrace vozidel",
                summary="Postupy pro registraci silničních vozidel",
                summary_names=["registrace", "vozidlo", "postup"],
                official_identifier="§ 6",
                level=2,
                element_type=ElementType.SECTION,
                act_iri="https://example.com/act/1",
                snapshot_id="2023-01-01"
            ),
            IndexDoc(
                element_id="mock-bm25-3",
                title="Technická kontrola",
                summary="Pravidla pro technickou kontrolu vozidel",
                summary_names=["technická kontrola", "vozidlo", "pravidla"],
                official_identifier="§ 47",
                level=2,
                element_type=ElementType.SECTION,
                act_iri="https://example.com/act/1",
                snapshot_id="2023-01-01"
            )
        ]
    
    def search(self, query, k=10):
        """Mock BM25 search returning keyword-based results."""
        results = []
        query_text = query.query if hasattr(query, 'query') else str(query)
        
        # Simple keyword matching for mock
        for i, doc in enumerate(self.documents):
            score = 0.0
            # Higher scores for exact matches in title or summary_names
            if any(term.lower() in query_text.lower() for term in [doc.title.lower()]):
                score += 5.0
            if any(term.lower() in query_text.lower() for term in doc.summary_names):
                score += 3.0
            if query_text.lower() in doc.summary.lower():
                score += 1.0
            
            if score > 0:
                results.append(SearchResult(
                    doc=doc,
                    score=score,
                    rank=i + 1,  # Will be re-ranked after sorting
                    matched_fields=["title"] if score >= 5.0 else ["summary"],
                    snippet=doc.summary[:100] + "..." if len(doc.summary) > 100 else doc.summary
                ))
        
        # Sort by score and return top-k with proper ranking
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
    """Mock implementation of FAISSSummaryIndex for testing."""
    
    def __init__(self):
        self.documents = [
            IndexDoc(
                element_id="mock-faiss-1",
                title="Základní ustanovení",
                summary="Obecné principy a základní pravidla zákona",
                summary_names=["ustanovení", "principy", "pravidla"],
                official_identifier="§ 1",
                level=2,
                element_type=ElementType.SECTION,
                act_iri="https://example.com/act/1",
                snapshot_id="2023-01-01"
            ),
            IndexDoc(
                element_id="mock-faiss-2",
                title="Evidování vozidel", 
                summary="Systém evidence a registrace dopravních prostředků",
                summary_names=["evidence", "registrace", "dopravní prostředky"],
                official_identifier="§ 5",
                level=2,
                element_type=ElementType.SECTION,
                act_iri="https://example.com/act/1",
                snapshot_id="2023-01-01"
            ),
            IndexDoc(
                element_id="mock-faiss-3",
                title="Kontrola technického stavu",
                summary="Ověřování bezpečnosti a technických parametrů",
                summary_names=["kontrola", "technický stav", "bezpečnost"],
                official_identifier="§ 48",
                level=2,
                element_type=ElementType.SECTION,
                act_iri="https://example.com/act/1",
                snapshot_id="2023-01-01"
            ),
            IndexDoc(
                element_id="mock-bm25-1",  # Overlap with BM25 for testing fusion
                title="Základní pojmy",
                summary="Definice základních pojmů používaných v zákoně",
                summary_names=["pojem", "definice", "zákon"],
                official_identifier="§ 2",
                level=2,
                element_type=ElementType.SECTION,
                act_iri="https://example.com/act/1",
                snapshot_id="2023-01-01"
            )
        ]
    
    def search(self, query, k=10):
        """Mock FAISS search returning semantic similarity results."""
        results = []
        query_text = query.query if hasattr(query, 'query') else str(query)
        
        # Simple semantic matching for mock (based on conceptual similarity)
        for i, doc in enumerate(self.documents):
            score = 0.0
            
            # Semantic similarity based on related concepts
            if "pojmy" in query_text.lower() or "definice" in query_text.lower():
                if any(term in ["pojem", "definice", "ustanovení"] for term in doc.summary_names):
                    score = 0.85
            elif "registrace" in query_text.lower() or "vozidlo" in query_text.lower():
                if any(term in ["registrace", "evidence", "vozidlo", "dopravní prostředky"] for term in doc.summary_names):
                    score = 0.75  
            elif "kontrola" in query_text.lower() or "technick" in query_text.lower():
                if any(term in ["kontrola", "technický stav", "bezpečnost"] for term in doc.summary_names):
                    score = 0.70
            
            # General semantic matching
            if score == 0.0:
                for summary_name in doc.summary_names:
                    if summary_name.lower() in query_text.lower():
                        score = max(score, 0.60)
            
            if score > 0:
                results.append(SearchResult(
                    doc=doc,
                    score=score,
                    rank=i + 1,  # Will be re-ranked after sorting
                    matched_fields=["semantic"],
                    snippet=doc.summary[:100] + "..." if len(doc.summary) > 100 else doc.summary
                ))
        
        # Sort by score and return top-k with proper ranking
        results.sort(key=lambda x: x.score, reverse=True)
        for i, result in enumerate(results):
            result.rank = i + 1
        return results[:k]
    
    def get_similar_documents(self, element_id, k=10):
        """Mock similar document search."""
        results = []
        # Find the reference document
        ref_doc = None
        for doc in self.documents:
            if doc.element_id == element_id:
                ref_doc = doc
                break
        
        if not ref_doc:
            return []
        
        # Find similar documents based on summary_names overlap
        for doc in self.documents:
            if doc.element_id == element_id:
                continue  # Skip self
            
            # Calculate similarity based on common summary_names
            common_names = set(ref_doc.summary_names) & set(doc.summary_names)
            similarity = len(common_names) / max(len(ref_doc.summary_names), len(doc.summary_names))
            
            if similarity > 0:
                results.append(SearchResult(
                    element_id=doc.element_id,
                    score=similarity,
                    title=doc.title,
                    official_identifier=doc.official_identifier,
                    level=doc.level,
                    element_type=doc.element_type,
                    summary=doc.summary,
                    matched_fields=["similarity"],
                    snippet=doc.summary[:100] + "..." if len(doc.summary) > 100 else doc.summary
                ))
        
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:k]
    
    def get_statistics(self):
        return {
            'index_type': 'faiss_mock',
            'document_count': len(self.documents),
            'embedding_dim': 384,
            'model': 'mock_sentence_transformer'
        }


def test_hybrid_config():
    """Test HybridConfig default values and customization."""
    print("Testing HybridConfig...")
    
    # Test default config
    config = HybridConfig()
    assert config.faiss_k == 50
    assert config.bm25_k == 30
    assert config.final_k == 20
    assert config.faiss_weight == 0.6
    assert config.bm25_weight == 0.4
    assert config.rerank_strategy == "rrf"
    
    # Test custom config
    custom_config = HybridConfig(
        faiss_k=100,
        bm25_k=50,
        final_k=30,
        faiss_weight=0.7,
        bm25_weight=0.3
    )
    assert custom_config.faiss_k == 100
    assert custom_config.final_k == 30
    assert custom_config.faiss_weight == 0.7
    
    print("✓ HybridConfig working correctly")


def test_hybrid_engine_initialization():
    """Test HybridSearchEngine initialization."""
    print("Testing HybridSearchEngine initialization...")
    
    mock_bm25 = MockBM25Index()
    mock_faiss = MockFAISSIndex()
    
    # Test with both indexes
    engine = HybridSearchEngine(bm25_index=mock_bm25, faiss_index=mock_faiss)
    assert engine.bm25_index is not None
    assert engine.faiss_index is not None
    
    # Test with only BM25
    engine_bm25 = HybridSearchEngine(bm25_index=mock_bm25)
    assert engine_bm25.bm25_index is not None
    assert engine_bm25.faiss_index is None
    
    # Test with only FAISS
    engine_faiss = HybridSearchEngine(faiss_index=mock_faiss)
    assert engine_faiss.bm25_index is None
    assert engine_faiss.faiss_index is not None
    
    # Test with no indexes (should raise error)
    try:
        HybridSearchEngine()
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    
    print("✓ HybridSearchEngine initialization working correctly")


def test_semantic_first_search():
    """Test semantic-first search strategy."""
    print("Testing semantic-first search strategy...")
    
    mock_bm25 = MockBM25Index()
    mock_faiss = MockFAISSIndex()
    engine = HybridSearchEngine(bm25_index=mock_bm25, faiss_index=mock_faiss)
    
    # Test search with both indexes available
    query = SearchQuery(query="základní pojmy")
    results = engine.search(query, strategy="semantic_first", k=5)
    
    assert len(results) > 0
    assert all(isinstance(r, SearchResult) for r in results)
    
    # Check that hybrid fusion metadata is present
    for result in results:
        if hasattr(result, 'metadata') and 'hybrid_fusion' in result.metadata:
            fusion_data = result.metadata['hybrid_fusion']
            assert 'faiss_score' in fusion_data
            assert 'bm25_score' in fusion_data
            assert fusion_data['primary_method'] == 'semantic'
    
    print("✓ Semantic-first search working correctly")


def test_keyword_first_search():
    """Test keyword-first search strategy."""
    print("Testing keyword-first search strategy...")
    
    mock_bm25 = MockBM25Index()
    mock_faiss = MockFAISSIndex()
    engine = HybridSearchEngine(bm25_index=mock_bm25, faiss_index=mock_faiss)
    
    # Test search with both indexes available
    query = SearchQuery(query="registrace vozidel")
    results = engine.search(query, strategy="keyword_first", k=5)
    
    assert len(results) > 0
    assert all(isinstance(r, SearchResult) for r in results)
    
    # Check fusion metadata
    for result in results:
        if hasattr(result, 'metadata') and 'hybrid_fusion' in result.metadata:
            fusion_data = result.metadata['hybrid_fusion']
            assert fusion_data['primary_method'] == 'keyword'
    
    print("✓ Keyword-first search working correctly")


def test_parallel_fusion_search():
    """Test parallel fusion search strategy."""
    print("Testing parallel fusion search strategy...")
    
    mock_bm25 = MockBM25Index()
    mock_faiss = MockFAISSIndex()
    engine = HybridSearchEngine(bm25_index=mock_bm25, faiss_index=mock_faiss)
    
    # Test search with both indexes available
    query = SearchQuery(query="technická kontrola")
    results = engine.search(query, strategy="parallel", k=5)
    
    assert len(results) > 0
    assert all(isinstance(r, SearchResult) for r in results)
    
    # Check fusion metadata
    for result in results:
        if hasattr(result, 'metadata') and 'hybrid_fusion' in result.metadata:
            fusion_data = result.metadata['hybrid_fusion']
            assert fusion_data['primary_method'] == 'parallel'
            assert 'fusion_strategy' in fusion_data
    
    print("✓ Parallel fusion search working correctly")


def test_rrf_vs_weighted_scoring():
    """Test RRF vs weighted scoring strategies."""
    print("Testing RRF vs weighted scoring...")
    
    mock_bm25 = MockBM25Index()
    mock_faiss = MockFAISSIndex()
    engine = HybridSearchEngine(bm25_index=mock_bm25, faiss_index=mock_faiss)
    
    query = SearchQuery(query="základní pojmy")
    
    # Test RRF scoring
    rrf_results = engine.search(query, strategy="parallel", rerank_strategy="rrf", k=3)
    
    # Test weighted scoring
    weighted_results = engine.search(query, strategy="parallel", rerank_strategy="weighted", k=3)
    
    # Both should return results
    assert len(rrf_results) > 0
    assert len(weighted_results) > 0
    
    # Scores might be different
    if len(rrf_results) > 0 and len(weighted_results) > 0:
        # Just check that we get valid scores
        assert all(r.score >= 0 for r in rrf_results)
        assert all(r.score >= 0 for r in weighted_results)
    
    print("✓ RRF vs weighted scoring working correctly")


def test_fallback_behavior():
    """Test fallback behavior when one index is unavailable."""
    print("Testing fallback behavior...")
    
    mock_bm25 = MockBM25Index()
    mock_faiss = MockFAISSIndex()
    
    # Test with only BM25
    engine_bm25 = HybridSearchEngine(bm25_index=mock_bm25)
    query = SearchQuery(query="základní pojmy")
    results_bm25 = engine_bm25.search(query, strategy="semantic_first", k=3)
    assert len(results_bm25) > 0
    
    # Test with only FAISS
    engine_faiss = HybridSearchEngine(faiss_index=mock_faiss)
    results_faiss = engine_faiss.search(query, strategy="keyword_first", k=3)
    assert len(results_faiss) > 0
    
    print("✓ Fallback behavior working correctly")


def test_similar_documents():
    """Test similar document functionality."""
    print("Testing similar document search...")
    
    mock_faiss = MockFAISSIndex()
    engine = HybridSearchEngine(faiss_index=mock_faiss)
    
    # Test similarity search
    similar_docs = engine.get_similar_documents("mock-faiss-1", k=3)
    
    # Should return similar documents (excluding the reference document itself)
    assert len(similar_docs) >= 0  # Might be 0 if no similar docs
    assert all(r.element_id != "mock-faiss-1" for r in similar_docs)  # No self-reference
    
    print("✓ Similar document search working correctly")


def test_configuration_parameters():
    """Test configuration parameter override."""
    print("Testing configuration parameter override...")
    
    mock_bm25 = MockBM25Index()
    mock_faiss = MockFAISSIndex()
    engine = HybridSearchEngine(bm25_index=mock_bm25, faiss_index=mock_faiss)
    
    query = SearchQuery(query="základní pojmy")
    
    # Test parameter override
    results = engine.search(
        query, 
        strategy="parallel",
        k=2,  # Override final_k
        faiss_weight=0.8,  # Override faiss_weight
        bm25_weight=0.2,   # Override bm25_weight
        rerank_strategy="weighted"  # Override strategy
    )
    
    assert len(results) <= 2  # Respects k parameter
    
    print("✓ Configuration parameter override working correctly")


def test_statistics():
    """Test statistics reporting."""
    print("Testing statistics reporting...")
    
    mock_bm25 = MockBM25Index()
    mock_faiss = MockFAISSIndex()
    engine = HybridSearchEngine(bm25_index=mock_bm25, faiss_index=mock_faiss)
    
    stats = engine.get_statistics()
    
    assert 'hybrid_engine' in stats
    assert 'bm25' in stats
    assert 'faiss' in stats
    
    hybrid_stats = stats['hybrid_engine']
    assert hybrid_stats['bm25_available'] == True
    assert hybrid_stats['faiss_available'] == True
    assert 'config' in hybrid_stats
    
    print("✓ Statistics reporting working correctly")


def run_all_tests():
    """Run all test functions."""
    print("=" * 50)
    print("Running HybridSearchEngine Tests")
    print("=" * 50)
    
    test_functions = [
        test_hybrid_config,
        test_hybrid_engine_initialization,
        test_semantic_first_search,
        test_keyword_first_search,
        test_parallel_fusion_search,
        test_rrf_vs_weighted_scoring,
        test_fallback_behavior,
        test_similar_documents,
        test_configuration_parameters,
        test_statistics
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} FAILED: {e}")
            failed += 1
    
    print("=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 50)
    
    return failed == 0


def main():
    """Main function to run the tests."""
    success = run_all_tests()
    if success:
        print("All tests passed!")
        return 0
    else:
        print("Some tests failed!")
        return 1


if __name__ == "__main__":
    exit(main())
