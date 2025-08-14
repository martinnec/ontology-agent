"""
Search service providing unified access to search functionality.

This module provides the main public interface for search operations across
different index types, implementing various search strategies and result processing.
"""

import time
from typing import List, Optional, Dict, Any, Union
from .domain import SearchOptions, SearchStrategy, SearchResults, SearchResultItem


class SearchService:
    """
    Main service for search operations across different index types.
    
    Provides a unified interface for keyword, semantic, hybrid, and full-text search
    while coordinating with the IndexService for index access.
    """
    
    def __init__(self, index_service, legal_act):
        """
        Initialize the search service.
        
        Args:
            index_service: IndexService instance for the legal act
            legal_act: LegalAct domain object from legislation module
        """
        self.index_service = index_service
        self.legal_act = legal_act
        self._indexes = None
        self._load_indexes()
    
    def _load_indexes(self) -> None:
        """Load all available indexes for the legal act."""
        self._indexes = self.index_service.get_indexes(self.legal_act, force_rebuild=False)
    
    def search(self, query: str, strategy: SearchStrategy = SearchStrategy.HYBRID_SEMANTIC_FIRST,
               options: Optional[SearchOptions] = None) -> SearchResults:
        """
        Perform search using the specified strategy.
        
        Args:
            query: Search query text
            strategy: Search strategy to use
            options: Search options and filters
            
        Returns:
            SearchResults containing matched documents
        """
        if options is None:
            options = SearchOptions()
        
        start_time = time.time()
        
        # Route to appropriate search method based on strategy
        if strategy == SearchStrategy.KEYWORD:
            results = self._search_keyword(query, options)
        elif strategy == SearchStrategy.SEMANTIC:
            results = self._search_semantic(query, options)
        elif strategy == SearchStrategy.HYBRID_SEMANTIC_FIRST:
            results = self._search_hybrid_semantic_first(query, options)
        elif strategy == SearchStrategy.HYBRID_KEYWORD_FIRST:
            results = self._search_hybrid_keyword_first(query, options)
        elif strategy == SearchStrategy.HYBRID_PARALLEL:
            results = self._search_hybrid_parallel(query, options)
        elif strategy == SearchStrategy.FULLTEXT:
            results = self._search_fulltext(query, options)
        elif strategy == SearchStrategy.SEMANTIC_FULLTEXT:
            results = self._search_semantic_fulltext(query, options)
        elif strategy == SearchStrategy.HYBRID_FULLTEXT_SEMANTIC_FIRST:
            results = self._search_hybrid_fulltext_semantic_first(query, options)
        elif strategy == SearchStrategy.HYBRID_FULLTEXT_KEYWORD_FIRST:
            results = self._search_hybrid_fulltext_keyword_first(query, options)
        elif strategy == SearchStrategy.HYBRID_FULLTEXT_PARALLEL:
            results = self._search_hybrid_fulltext_parallel(query, options)
        else:
            raise ValueError(f"Unknown search strategy: {strategy}")
        
        # Calculate search time
        search_time_ms = (time.time() - start_time) * 1000
        
        # Create and return SearchResults
        return self._create_search_results(
            query=query,
            strategy=strategy,
            options=options,
            items=results,
            search_time_ms=search_time_ms
        )
    
    def search_keyword_summary(self, query: str, options: Optional[SearchOptions] = None) -> SearchResults:
        """
        Perform keyword-based search using BM25 index on summaries.
        
        Args:
            query: Search query text
            options: Search options and filters
            
        Returns:
            SearchResults containing matched documents
        """
        return self.search(query, SearchStrategy.KEYWORD, options)
    
    def search_semantic_summary(self, query: str, options: Optional[SearchOptions] = None) -> SearchResults:
        """
        Perform semantic search using FAISS index on summaries.
        
        Args:
            query: Search query text
            options: Search options and filters
            
        Returns:
            SearchResults containing matched documents
        """
        return self.search(query, SearchStrategy.SEMANTIC, options)
    
    def search_hybrid_summary(self, query: str, strategy: str = "semantic_first",
                             options: Optional[SearchOptions] = None) -> SearchResults:
        """
        Perform hybrid search combining keyword and semantic approaches on summaries.
        
        Args:
            query: Search query text
            strategy: Hybrid strategy ("semantic_first", "keyword_first", "parallel")
            options: Search options and filters
            
        Returns:
            SearchResults containing matched documents
        """
        strategy_map = {
            "semantic_first": SearchStrategy.HYBRID_SEMANTIC_FIRST,
            "keyword_first": SearchStrategy.HYBRID_KEYWORD_FIRST,
            "parallel": SearchStrategy.HYBRID_PARALLEL
        }
        
        search_strategy = strategy_map.get(strategy, SearchStrategy.HYBRID_SEMANTIC_FIRST)
        return self.search(query, search_strategy, options)
    
    def search_keyword_fulltext(self, query: str, options: Optional[SearchOptions] = None) -> SearchResults:
        """
        Perform keyword-based full-text search in document text chunks.
        
        Args:
            query: Search query text
            options: Search options and filters
            
        Returns:
            SearchResults containing matched documents
        """
        return self.search(query, SearchStrategy.FULLTEXT, options)
    
    def search_semantic_fulltext(self, query: str, options: Optional[SearchOptions] = None) -> SearchResults:
        """
        Perform semantic search in document text chunks using FAISS full-text index.
        
        Args:
            query: Search query text
            options: Search options and filters
            
        Returns:
            SearchResults containing matched documents
        """
        return self.search(query, SearchStrategy.SEMANTIC_FULLTEXT, options)
    
    def search_hybrid_fulltext(self, query: str, strategy: str = "semantic_first",
                              options: Optional[SearchOptions] = None) -> SearchResults:
        """
        Perform hybrid search combining keyword and semantic approaches on full text.
        
        Args:
            query: Search query text
            strategy: Hybrid strategy ("semantic_first", "keyword_first", "parallel")
            options: Search options and filters
            
        Returns:
            SearchResults containing matched documents
        """
        strategy_map = {
            "semantic_first": SearchStrategy.HYBRID_FULLTEXT_SEMANTIC_FIRST,
            "keyword_first": SearchStrategy.HYBRID_FULLTEXT_KEYWORD_FIRST,
            "parallel": SearchStrategy.HYBRID_FULLTEXT_PARALLEL
        }
        
        search_strategy = strategy_map.get(strategy, SearchStrategy.HYBRID_FULLTEXT_SEMANTIC_FIRST)
        return self.search(query, search_strategy, options)
    
    def search_similar(self, element_id: str, options: Optional[SearchOptions] = None) -> SearchResults:
        """
        Find documents similar to the specified element (semantic similarity).
        
        Args:
            element_id: ID of the reference element
            options: Search options and filters
            
        Returns:
            SearchResults containing similar documents
        """
        if options is None:
            options = SearchOptions()
        
        start_time = time.time()
        
        # Get FAISS index for similarity search
        faiss_index = self._indexes.get_index('faiss')
        if not faiss_index:
            return self._create_empty_results(f"similar:{element_id}", SearchStrategy.SEMANTIC, options)
        
        # Perform similarity search
        try:
            similar_docs = faiss_index.get_similar_documents(element_id, options.max_results)
            results = self._convert_similarity_results(similar_docs)
        except Exception as e:
            print(f"Warning: Similarity search failed: {e}")
            results = []
        
        search_time_ms = (time.time() - start_time) * 1000
        
        return self._create_search_results(
            query=f"similar:{element_id}",
            strategy=SearchStrategy.SEMANTIC,
            options=options,
            items=results,
            search_time_ms=search_time_ms,
            index_types=['faiss']
        )
    
    def _search_keyword(self, query: str, options: SearchOptions) -> List[SearchResultItem]:
        """Perform keyword search using BM25 index."""
        bm25_index = self._indexes.get_index('bm25')
        if not bm25_index:
            return []
        
        # Create search query for BM25
        search_query = self._create_legacy_query(query, options)
        
        try:
            raw_results = bm25_index.search(search_query)
            return self._convert_legacy_results(raw_results, ['bm25'])
        except Exception as e:
            print(f"Warning: BM25 search failed: {e}")
            return []
    
    def _search_semantic(self, query: str, options: SearchOptions) -> List[SearchResultItem]:
        """Perform semantic search using FAISS index."""
        faiss_index = self._indexes.get_index('faiss')
        if not faiss_index:
            return []
        
        # Create search query for FAISS
        search_query = self._create_legacy_query(query, options)
        
        try:
            raw_results = faiss_index.search(search_query)
            return self._convert_legacy_results(raw_results, ['faiss'])
        except Exception as e:
            print(f"Warning: FAISS search failed: {e}")
            return []
    
    def _search_hybrid_semantic_first(self, query: str, options: SearchOptions) -> List[SearchResultItem]:
        """Hybrid search: semantic first, then keyword reranking."""
        # Get broader semantic results
        semantic_options = SearchOptions(**options.model_dump())
        semantic_options.max_results = options.rerank_count
        
        semantic_results = self._search_semantic(query, semantic_options)
        if not semantic_results:
            return []
        
        # Re-rank with keyword search
        return self._rerank_with_keyword(query, semantic_results, options)
    
    def _search_hybrid_keyword_first(self, query: str, options: SearchOptions) -> List[SearchResultItem]:
        """Hybrid search: keyword first, then semantic reranking."""
        # Get broader keyword results
        keyword_options = SearchOptions(**options.model_dump())
        keyword_options.max_results = options.rerank_count
        
        keyword_results = self._search_keyword(query, keyword_options)
        if not keyword_results:
            return []
        
        # Re-rank with semantic search
        return self._rerank_with_semantic(query, keyword_results, options)
    
    def _search_hybrid_parallel(self, query: str, options: SearchOptions) -> List[SearchResultItem]:
        """Hybrid search: parallel execution with score fusion."""
        # Run both searches in parallel (conceptually)
        keyword_results = self._search_keyword(query, options)
        semantic_results = self._search_semantic(query, options)
        
        # Fuse results using hybrid alpha
        return self._fuse_results(keyword_results, semantic_results, options.hybrid_alpha)
    
    def _search_fulltext(self, query: str, options: SearchOptions) -> List[SearchResultItem]:
        """Perform full-text search in document chunks."""
        bm25_full_index = self._indexes.get_index('bm25_full')
        if not bm25_full_index:
            return []
        
        # Create search query for full-text search
        search_query = self._create_legacy_query(query, options)
        
        try:
            raw_results = bm25_full_index.search(search_query)
            return self._convert_legacy_results(raw_results, ['bm25_full'])
        except Exception as e:
            print(f"Warning: Full-text search failed: {e}")
            return []
    
    def _search_semantic_fulltext(self, query: str, options: SearchOptions) -> List[SearchResultItem]:
        """Perform semantic search in document chunks using FAISS full-text index."""
        faiss_full_index = self._indexes.get_index('faiss_full')
        if not faiss_full_index:
            return []
        
        # Create search query for semantic full-text search
        search_query = self._create_legacy_query(query, options)
        
        try:
            raw_results = faiss_full_index.search(search_query)
            return self._convert_legacy_results(raw_results, ['faiss_full'])
        except Exception as e:
            print(f"Warning: Semantic full-text search failed: {e}")
            return []
    
    def _search_hybrid_fulltext_semantic_first(self, query: str, options: SearchOptions) -> List[SearchResultItem]:
        """Hybrid full-text search: semantic first, then keyword reranking."""
        # Get broader semantic results
        semantic_options = SearchOptions(**options.model_dump())
        semantic_options.max_results = options.rerank_count
        
        semantic_results = self._search_semantic_fulltext(query, semantic_options)
        if not semantic_results:
            return []
        
        # Re-rank with keyword search on full text
        return self._rerank_with_keyword_fulltext(query, semantic_results, options)
    
    def _search_hybrid_fulltext_keyword_first(self, query: str, options: SearchOptions) -> List[SearchResultItem]:
        """Hybrid full-text search: keyword first, then semantic reranking."""
        # Get broader keyword results
        keyword_options = SearchOptions(**options.model_dump())
        keyword_options.max_results = options.rerank_count
        
        keyword_results = self._search_fulltext(query, keyword_options)
        if not keyword_results:
            return []
        
        # Re-rank with semantic search on full text
        return self._rerank_with_semantic_fulltext(query, keyword_results, options)
    
    def _search_hybrid_fulltext_parallel(self, query: str, options: SearchOptions) -> List[SearchResultItem]:
        """Hybrid full-text search: parallel execution with score fusion."""
        # Run both searches in parallel (conceptually)
        keyword_results = self._search_fulltext(query, options)
        semantic_results = self._search_semantic_fulltext(query, options)
        
        # Fuse results using hybrid alpha
        return self._fuse_results(keyword_results, semantic_results, options.hybrid_alpha)
    
    def _create_legacy_query(self, query: str, options: SearchOptions):
        """Create a legacy SearchQuery object for existing indexes."""
        # Import here to avoid circular dependencies
        from index.domain import SearchQuery, ElementType
        
        # Convert element types
        element_types = None
        if options.element_types:
            element_types = []
            type_mapping = {
                "legal_act": ElementType.LEGAL_ACT,
                "part": ElementType.PART,
                "chapter": ElementType.CHAPTER,
                "division": ElementType.DIVISION,
                "section": ElementType.SECTION,
                "unknown": ElementType.UNKNOWN
            }
            for et in options.element_types:
                if et.lower() in type_mapping:
                    element_types.append(type_mapping[et.lower()])
        
        return SearchQuery(
            query=query,
            max_results=options.max_results,
            element_types=element_types,
            min_level=options.min_level,
            max_level=options.max_level,
            official_identifier_pattern=None  # Could be added to SearchOptions
        )
    
    def _convert_legacy_results(self, raw_results: List, index_types: List[str]) -> List[SearchResultItem]:
        """Convert legacy SearchResult objects to SearchResultItem objects."""
        items = []
        
        for result in raw_results:
            # Extract document info from legacy result
            doc = result.doc
            
            item = SearchResultItem(
                element_id=doc.element_id,
                title=doc.title,
                official_identifier=doc.official_identifier,
                summary=doc.summary,
                text_content=doc.text_content,
                score=result.score,
                rank=result.rank,
                element_type=doc.element_type.value,
                level=doc.level,
                parent_id=doc.parent_id,
                matched_fields=result.matched_fields or [],
                highlighted_text=result.snippet
            )
            items.append(item)
        
        return items
    
    def _convert_similarity_results(self, similar_docs: List) -> List[SearchResultItem]:
        """Convert similarity search results to SearchResultItem objects."""
        items = []
        
        for i, (doc, score) in enumerate(similar_docs):
            item = SearchResultItem(
                element_id=doc.element_id,
                title=doc.title,
                official_identifier=doc.official_identifier,
                summary=doc.summary,
                text_content=doc.text_content,
                score=float(score),
                rank=i + 1,
                element_type=doc.element_type.value,
                level=doc.level,
                parent_id=doc.parent_id,
                matched_fields=["similarity"],
                highlighted_text=None
            )
            items.append(item)
        
        return items
    
    def _rerank_with_keyword(self, query: str, results: List[SearchResultItem], 
                           options: SearchOptions) -> List[SearchResultItem]:
        """Re-rank semantic results using keyword scores."""
        # This is a simplified implementation
        # In practice, you'd want to get keyword scores for these specific documents
        return results[:options.max_results]
    
    def _rerank_with_semantic(self, query: str, results: List[SearchResultItem],
                            options: SearchOptions) -> List[SearchResultItem]:
        """Re-rank keyword results using semantic scores."""
        # This is a simplified implementation
        # In practice, you'd want to get semantic scores for these specific documents
        return results[:options.max_results]
    
    def _rerank_with_keyword_fulltext(self, query: str, results: List[SearchResultItem], 
                                    options: SearchOptions) -> List[SearchResultItem]:
        """Re-rank semantic full-text results using keyword scores."""
        # This is a simplified implementation
        # In practice, you'd want to get keyword scores for these specific documents using bm25_full
        return results[:options.max_results]
    
    def _rerank_with_semantic_fulltext(self, query: str, results: List[SearchResultItem],
                                     options: SearchOptions) -> List[SearchResultItem]:
        """Re-rank keyword full-text results using semantic scores."""
        # This is a simplified implementation
        # In practice, you'd want to get semantic scores for these specific documents using faiss_full
        return results[:options.max_results]
    
    def _fuse_results(self, keyword_results: List[SearchResultItem], 
                     semantic_results: List[SearchResultItem],
                     alpha: float) -> List[SearchResultItem]:
        """Fuse keyword and semantic results using weighted combination."""
        # Create a combined result set
        combined = {}
        
        # Add keyword results
        for item in keyword_results:
            combined[item.element_id] = item
            combined[item.element_id].score = (1 - alpha) * item.score
        
        # Add semantic results
        for item in semantic_results:
            if item.element_id in combined:
                # Combine scores
                combined[item.element_id].score += alpha * item.score
            else:
                combined[item.element_id] = item
                combined[item.element_id].score = alpha * item.score
        
        # Sort by combined score and return
        results = list(combined.values())
        results.sort(key=lambda x: x.score, reverse=True)
        
        # Update ranks
        for i, item in enumerate(results):
            item.rank = i + 1
        
        return results
    
    def _create_search_results(self, query: str, strategy: SearchStrategy,
                             options: SearchOptions, items: List[SearchResultItem],
                             search_time_ms: float, index_types: Optional[List[str]] = None) -> SearchResults:
        """Create a SearchResults object from search results."""
        if index_types is None:
            index_types = []
        
        # Calculate score range
        score_range = {"min": 0.0, "max": 0.0}
        if items:
            scores = [item.score for item in items]
            score_range = {"min": min(scores), "max": max(scores)}
        
        # Apply filters
        filters_applied = {}
        if options.element_types:
            filters_applied["element_types"] = options.element_types
        if options.min_level is not None:
            filters_applied["min_level"] = options.min_level
        if options.max_level is not None:
            filters_applied["max_level"] = options.max_level
        
        return SearchResults(
            query=query,
            strategy=strategy,
            options=options,
            items=items,
            total_found=len(items),
            search_time_ms=search_time_ms,
            index_types_used=index_types,
            filters_applied=filters_applied,
            score_range=score_range
        )
    
    def _create_empty_results(self, query: str, strategy: SearchStrategy,
                            options: SearchOptions) -> SearchResults:
        """Create empty SearchResults object."""
        return self._create_search_results(query, strategy, options, [], 0.0)
    
    def get_index_info(self) -> Dict[str, Any]:
        """Get information about available indexes."""
        info = {
            "act_iri": self._indexes.act_iri,
            "available_indexes": self._indexes.get_available_indexes(),
            "document_count": self._indexes.get_document_count()
        }
        
        return info
