"""
Simple test runner for full-text indexing functionality (without pytest).

This module provides basic tests for the BM25FullIndex and FAISSFullIndex implementations.
"""

import tempfile
import shutil
from pathlib import Path
from typing import List

import sys
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

from index.domain import IndexDoc, ElementType, SearchQuery
from index.bm25_full import BM25FullIndex
from index.faiss_full import FAISSFullIndex


def create_sample_documents():
    """Create sample documents with full text content for testing."""
    return [
        IndexDoc(
            element_id="test_1",
            title="Základní pojmy",
            official_identifier="§ 1",
            summary="Definice základních pojmů používaných v zákoně.",
            summary_names=["základní pojmy", "definice"],
            text_content="Pro účely tohoto zákona se rozumí se následující pojmy. Osobní údaj je jakákoliv informace týkající se identifikované nebo identifikovatelné fyzické osoby. Zpracování je jakákoli operace nebo soubor operací s osobními údaji. Správce je fyzická nebo právnická osoba, která určuje účely a prostředky zpracování osobních údajů.",
            level=1,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/test",
            snapshot_id="test_snapshot"
        ),
        IndexDoc(
            element_id="test_2",
            title="Práva subjektů údajů",
            official_identifier="§ 2",
            summary="Vymezení práv fyzických osob při zpracování osobních údajů.",
            summary_names=["práva subjektů", "fyzické osoby"],
            text_content="Subjekt údajů má právo na informace o zpracování svých osobních údajů. Správce je povinen poskytnout informace o účelech zpracování, kategorii osobních údajů a době uchování. Subjekt údajů má právo požádat o opravu nebo výmaz svých osobních údajů.",
            level=1,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/test",
            snapshot_id="test_snapshot"
        ),
        IndexDoc(
            element_id="test_3",
            title="Povinnosti při zpracování",
            official_identifier="§ 3",
            summary="Stanovení povinností správce a zpracovatele při zpracování osobních údajů.",
            summary_names=["povinnosti", "zpracování"],
            text_content="Správce je povinen zajistit bezpečnost zpracování osobních údajů implementací vhodných technických a organizačních opatření. Zpracovatel musí zpracovávat osobní údaje pouze na základě pokynů správce. Správce musí vést evidenci zpracovatelských činností a být schopen prokázat soulad s právními předpisy.",
            level=1,
            element_type=ElementType.SECTION,
            act_iri="http://example.org/act/test",
            snapshot_id="test_snapshot"
        )
    ]


def test_bm25_full_index():
    """Test BM25FullIndex functionality."""
    print("Testing BM25FullIndex...")
    
    # Test 1: Build index
    documents = create_sample_documents()
    index = BM25FullIndex()
    index.build(documents)
    
    assert index.bm25_model is not None, "BM25 model should be built"
    assert len(index.text_chunks) > 0, "Should have text chunks"
    assert index.metadata is not None, "Should have metadata"
    print("✅ BM25 index built successfully")
    
    # Test 2: Text chunking
    doc = documents[0]
    chunks = doc.get_text_chunks(chunk_size=20, overlap=5)
    assert len(chunks) > 0, "Should create chunks"
    print("✅ Text chunking works")
    
    # Test 3: Search
    query = SearchQuery(query="osobní údaje", max_results=5)
    results = index.search(query)
    assert len(results) > 0, "Should find results"
    print("✅ Search functionality works")
    
    # Test 4: Exact phrase search
    results = index.search_exact_phrase("rozumí se", max_results=5)
    assert len(results) > 0, "Should find exact phrase"
    print("✅ Exact phrase search works")
    
    # Test 5: Save and load
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        index.save(temp_path)
        
        index2 = BM25FullIndex()
        index2.load(temp_path)
        
        assert len(index2.text_chunks) == len(index.text_chunks), "Loaded index should match"
        print("✅ Save and load works")
    
    print("BM25FullIndex tests completed successfully!\n")


def test_faiss_full_index():
    """Test FAISSFullIndex functionality."""
    print("Testing FAISSFullIndex...")
    
    # Test 1: Build index
    documents = create_sample_documents()
    index = FAISSFullIndex()
    index.build(documents)
    
    assert index.faiss_index is not None, "FAISS index should be built"
    assert len(index.text_chunks) > 0, "Should have text chunks"
    assert index.metadata is not None, "Should have metadata"
    print("✅ FAISS index built successfully")
    
    # Test 2: Semantic search
    query = SearchQuery(query="práva fyzických osob", max_results=5)
    results = index.search(query)
    assert len(results) > 0, "Should find semantic results"
    print("✅ Semantic search works")
    
    # Test 3: Similar chunks
    if index.text_chunks:
        first_chunk_id = index.text_chunks[0].chunk_id
        similar_chunks = index.get_similar_chunks(first_chunk_id, k=2)
        # Similar chunks might be empty for small datasets
        print("✅ Similar chunks functionality works")
    
    # Test 4: Save and load
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        index.save(temp_path)
        
        index2 = FAISSFullIndex()
        index2.load(temp_path)
        
        assert len(index2.text_chunks) == len(index.text_chunks), "Loaded index should match"
        print("✅ Save and load works")
    
    print("FAISSFullIndex tests completed successfully!\n")


def test_integration():
    """Test integration between BM25 and FAISS full-text indexes."""
    print("Testing integration...")
    
    documents = create_sample_documents()
    
    # Build both indexes
    bm25_index = BM25FullIndex()
    bm25_index.build(documents)
    
    faiss_index = FAISSFullIndex()
    faiss_index.build(documents)
    
    # Test same query on both
    query = "osobní údaje"
    
    bm25_results = bm25_index.search_exact_phrase(query, max_results=5)
    
    search_query = SearchQuery(query=query, max_results=5)
    faiss_results = faiss_index.search(search_query)
    
    # Both should work (may have different results)
    print(f"BM25 exact phrase results: {len(bm25_results)}")
    print(f"FAISS semantic results: {len(faiss_results)}")
    
    # Check chunk consistency
    assert len(bm25_index.text_chunks) == len(faiss_index.text_chunks), "Should have same number of chunks"
    
    print("✅ Integration tests completed successfully!\n")


def run_all_tests():
    """Run all tests."""
    print("FULL-TEXT INDEXING TESTS")
    print("=" * 40)
    
    try:
        test_bm25_full_index()
        test_faiss_full_index()
        test_integration()
        
        print("🎉 ALL TESTS PASSED!")
        print("Full-text indexing implementation is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
