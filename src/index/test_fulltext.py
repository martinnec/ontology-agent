"""
Tests for full-text indexing functionality.

This module tests the BM25FullIndex and FAISSFullIndex implementations
for exact phrase searches and semantic search over text chunks.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import List

from index.domain import IndexDoc, ElementType, SearchQuery
from index.bm25_full import BM25FullIndex
from index.faiss_full import FAISSFullIndex


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_documents():
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


class TestBM25FullIndex:
    """Test cases for BM25FullIndex."""
    
    def test_build_index(self, sample_documents, temp_dir):
        """Test building BM25 full-text index."""
        index = BM25FullIndex()
        index.build(sample_documents)
        
        assert index.bm25_model is not None
        assert len(index.text_chunks) > 0
        assert len(index.chunk_texts) == len(index.text_chunks)
        assert index.metadata is not None
        assert index.metadata.index_type == "bm25_full"
    
    def test_text_chunking(self, sample_documents):
        """Test text chunking functionality."""
        doc = sample_documents[0]
        chunks = doc.get_text_chunks(chunk_size=20, overlap=5)
        
        assert len(chunks) > 1  # Should create multiple chunks
        
        # Check chunk structure
        for chunk in chunks:
            assert 'text' in chunk
            assert 'chunk_id' in chunk
            assert 'element_id' in chunk
            assert chunk['element_id'] == doc.element_id
    
    def test_search(self, sample_documents, temp_dir):
        """Test BM25 full-text search."""
        index = BM25FullIndex()
        index.build(sample_documents)
        
        # Test keyword search
        query = SearchQuery(query="osobní údaje", max_results=5)
        results = index.search(query)
        
        assert len(results) > 0
        assert all(result.score > 0 for result in results)
        assert all("osobní údaje" in result.doc.text_content.lower() for result in results)
    
    def test_exact_phrase_search(self, sample_documents):
        """Test exact phrase search functionality."""
        index = BM25FullIndex()
        index.build(sample_documents)
        
        # Test exact phrase that exists in the text
        results = index.search_exact_phrase("rozumí se", max_results=5)
        
        assert len(results) > 0
        for result in results:
            assert "rozumí se" in result.doc.text_content.lower()
            assert result.snippet is not None
    
    def test_exact_phrase_not_found(self, sample_documents):
        """Test exact phrase search when phrase doesn't exist."""
        index = BM25FullIndex()
        index.build(sample_documents)
        
        # Test phrase that doesn't exist
        results = index.search_exact_phrase("neexistující fráze", max_results=5)
        
        assert len(results) == 0
    
    def test_save_and_load(self, sample_documents, temp_dir):
        """Test saving and loading BM25 full-text index."""
        # Build and save index
        index1 = BM25FullIndex()
        index1.build(sample_documents)
        index1.save(temp_dir)
        
        # Load index
        index2 = BM25FullIndex()
        index2.load(temp_dir)
        
        # Verify loaded index works
        assert len(index2.text_chunks) == len(index1.text_chunks)
        assert index2.metadata.index_type == "bm25_full"
        
        # Test search on loaded index
        query = SearchQuery(query="osobní údaje", max_results=5)
        results = index2.search(query)
        assert len(results) > 0
    
    def test_empty_documents(self):
        """Test behavior with empty document list."""
        index = BM25FullIndex()
        
        with pytest.raises(ValueError, match="Cannot build index from empty document list"):
            index.build([])
    
    def test_no_text_content(self):
        """Test behavior with documents that have no text content."""
        docs_without_text = [
            IndexDoc(
                element_id="no_text",
                title="Test",
                official_identifier="§ 1",
                summary="Test summary",
                level=1,
                element_type=ElementType.SECTION
            )
        ]
        
        index = BM25FullIndex()
        
        with pytest.raises(ValueError, match="No text content found"):
            index.build(docs_without_text)


class TestFAISSFullIndex:
    """Test cases for FAISSFullIndex."""
    
    def test_build_index(self, sample_documents, temp_dir):
        """Test building FAISS full-text index."""
        index = FAISSFullIndex()
        index.build(sample_documents)
        
        assert index.faiss_index is not None
        assert len(index.text_chunks) > 0
        assert index.embeddings is not None
        assert index.metadata is not None
        assert index.metadata.index_type == "faiss_full"
    
    def test_semantic_search(self, sample_documents):
        """Test FAISS semantic search."""
        index = FAISSFullIndex()
        index.build(sample_documents)
        
        # Test semantic search
        query = SearchQuery(query="práva fyzických osob", max_results=5)
        results = index.search(query)
        
        assert len(results) > 0
        assert all(result.score > 0 for result in results)
        # Results should be ranked by semantic similarity
        assert results[0].rank == 1
    
    def test_similar_chunks(self, sample_documents):
        """Test finding similar chunks functionality."""
        index = FAISSFullIndex()
        index.build(sample_documents)
        
        # Get the first chunk ID
        first_chunk_id = index.text_chunks[0].chunk_id
        
        # Find similar chunks
        similar_chunks = index.get_similar_chunks(first_chunk_id, k=3)
        
        assert len(similar_chunks) <= 3
        for chunk, score in similar_chunks:
            assert chunk.chunk_id != first_chunk_id  # Should not include the query chunk itself
            assert 0 <= score <= 1  # Similarity scores should be normalized
    
    def test_save_and_load(self, sample_documents, temp_dir):
        """Test saving and loading FAISS full-text index."""
        # Build and save index
        index1 = FAISSFullIndex()
        index1.build(sample_documents)
        index1.save(temp_dir)
        
        # Load index
        index2 = FAISSFullIndex()
        index2.load(temp_dir)
        
        # Verify loaded index works
        assert len(index2.text_chunks) == len(index1.text_chunks)
        assert index2.metadata.index_type == "faiss_full"
        
        # Test search on loaded index
        query = SearchQuery(query="práva subjektů", max_results=5)
        results = index2.search(query)
        assert len(results) > 0
    
    def test_empty_documents(self):
        """Test behavior with empty document list."""
        index = FAISSFullIndex()
        
        with pytest.raises(ValueError, match="Cannot build index from empty document list"):
            index.build([])
    
    def test_no_text_content(self):
        """Test behavior with documents that have no text content."""
        docs_without_text = [
            IndexDoc(
                element_id="no_text",
                title="Test",
                official_identifier="§ 1",
                summary="Test summary",
                level=1,
                element_type=ElementType.SECTION
            )
        ]
        
        index = FAISSFullIndex()
        
        with pytest.raises(ValueError, match="No text content found"):
            index.build(docs_without_text)


class TestFullTextIntegration:
    """Integration tests for full-text indexing."""
    
    def test_phrase_search_integration(self, sample_documents):
        """Test integration between BM25 and FAISS for phrase search."""
        # Build both indexes
        bm25_index = BM25FullIndex()
        bm25_index.build(sample_documents)
        
        faiss_index = FAISSFullIndex()
        faiss_index.build(sample_documents)
        
        # Test same query on both indexes
        query = "osobní údaje"
        
        # BM25 exact phrase search
        bm25_results = bm25_index.search_exact_phrase(query, max_results=5)
        
        # FAISS semantic search
        search_query = SearchQuery(query=query, max_results=5)
        faiss_results = faiss_index.search(search_query)
        
        # Both should return results
        assert len(bm25_results) > 0
        assert len(faiss_results) > 0
        
        # BM25 should find exact matches
        for result in bm25_results:
            assert query in result.doc.text_content.lower()
    
    def test_chunk_consistency(self, sample_documents):
        """Test that both indexes create consistent chunks."""
        bm25_index = BM25FullIndex()
        bm25_index.build(sample_documents)
        
        faiss_index = FAISSFullIndex()
        faiss_index.build(sample_documents)
        
        # Both should have the same number of chunks
        assert len(bm25_index.text_chunks) == len(faiss_index.text_chunks)
        
        # Chunk IDs should match
        bm25_chunk_ids = {chunk.chunk_id for chunk in bm25_index.text_chunks}
        faiss_chunk_ids = {chunk.chunk_id for chunk in faiss_index.text_chunks}
        assert bm25_chunk_ids == faiss_chunk_ids


# Test runner for manual execution
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
