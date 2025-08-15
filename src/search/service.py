"""
Search service providing unified access to search functionality.

Developer Guide (HOW TO CHOOSE A SEARCH METHOD)
================================================
The `SearchService` exposes a matrix of retrieval capabilities over two content layers:
1. Summary layer (titles + summaries)  → fast, conceptual, good for topical discovery & navigation.
2. Full‑text layer (chunked raw provisions) → slower, granular, good for precise citation & phrase search.

Strategy Families (Summary layer):
    search_keyword_summary      BM25 lexical match (precise term / phrase lookups, auto‑complete seeds)
    search_semantic_summary     Embedding similarity (paraphrase / intent, cross‑lingual nuance)
    search_hybrid_summary       Combined BM25 + Semantic (semantic_first | keyword_first | parallel)

Strategy Families (Full‑text layer):
    search_keyword_fulltext     BM25 over text chunks (exact wording, phrase queries in quotes)
    search_semantic_fulltext    Embedding similarity on chunks (concept / paraphrase passage retrieval)
    search_hybrid_fulltext      Hybrid BM25 + Semantic for passages (same variants)

Similarity / Recommendation:
    search_similar(element_id)  Related sections (semantic neighborhood) for “Users also viewed” / clustering.

Hybrid Variant Selection:
    semantic_first : High recall of conceptual candidates → lexical re‑rank for precision (default general UX).
    keyword_first  : Start from tight lexical matches → semantic re‑rank for nuanced ordering (short / exact queries).
    parallel       : Run both independently then fuse using `hybrid_alpha` (diversity, low coordination overhead).

Typical Workflow Patterns:
    Progressive Drill‑Down:
        1. summary hybrid (semantic_first) for broad topical hit list.
        2. user narrows / selects a section.
        3. full‑text hybrid (keyword_first if phrase‑heavy, else semantic_first) for authoritative passages.

    Exploratory Dashboard:
        - parallel hybrid (summary) for balanced diverse list shown instantly; allow user to toggle to full‑text on demand.

    Context Expansion for QA / LLM:
        - summary semantic → gather candidate IDs → full‑text semantic/hybrid on those IDs for rich context windows.

Important `SearchOptions` knobs:
    max_results     Truncates final list (after fusion / rerank).
    rerank_count    Candidate pool size for two‑stage hybrids (increase for recall at cost of latency).
    hybrid_alpha    Fusion weight for parallel (0=keyword only, 1=semantic only).
    element_types   Structural filtering (e.g., only 'section' for answer extraction).
    min_level/max_level Hierarchical boundaries; combine with element_types for tight slices.
    boost_title / boost_summary Influence underlying lexical scoring emphasis.

Edge / Behavioral Notes:
    - Missing underlying index returns empty list (no exception); inspect `index_types_used` if needed.
    - Scores are comparable only within a single result set (do not mix raw scores across strategies).
    - Similarity search ignores lexical filtering; post‑filter manually if required.

Combining Programmatically:
    - Use `search(query, strategy=SearchStrategy.XXX)` for enumeration or analytics.
    - Prefer convenience wrappers for clarity & future stability.

Mini Examples:
    results = service.search_hybrid_summary("vehicle registration process", strategy="semantic_first")
    results = service.search_keyword_fulltext('"musí být registrováno"')  # exact phrase
    passages = service.search_hybrid_fulltext("mandatory insurance coverage scope", strategy="parallel")
    related = service.search_similar(section_id)

See `search/demo_search_service.py` + `hybrid_search_engine_cli.py` for comparative usage patterns.
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
        Low‑level unified entry point executing an explicit `SearchStrategy`.

        Prefer the named convenience methods unless you are:
          - Building a strategy comparison / benchmarking tool.
          - Iterating through all strategies programmatically.
          - Dynamically selecting strategy based on user intent classification.

        Args:
            query: Natural language query (wrap phrases in quotes for BM25 exact phrase bias).
            strategy: Explicit enum controlling index choice + orchestration.
            options: Optional tuning / filtering (see module docstring for guidance).

        Returns:
            SearchResults populated with metadata (timing, score range, applied filters).
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
        BM25 (lexical) search over titles + summaries.

        Use when:
            - User supplies statute‑like wording / key domain terms.
            - Implementing quick suggestion lists (top N headings).
            - Need high precision on exact terms before semantic expansion.

        Choose full‑text variant for wording confined to body text, not present in summaries.
        """
        return self.search(query, SearchStrategy.KEYWORD, options)
    
    def search_semantic_summary(self, query: str, options: Optional[SearchOptions] = None) -> SearchResults:
        """
        Embedding (semantic) search over summaries for paraphrased / conceptual intent.

        Good for:
            - User phrasing diverges from statutory wording.
            - Cross‑lingual / synonym heavy queries.
            - Early broad recall before narrowing filters or rerank.

        Consider `search_hybrid_summary` for improved precision ordering.
        """
        return self.search(query, SearchStrategy.SEMANTIC, options)
    
    def search_hybrid_summary(self, query: str, strategy: str = "semantic_first",
                                                        options: Optional[SearchOptions] = None) -> SearchResults:
        """
        Hybrid (BM25 + Semantic) retrieval on summaries with selectable orchestration.

        strategy:
            semantic_first (default): Semantic candidate recall → lexical rerank (balanced general default).
            keyword_first: Lexical precision first (short / specific queries) → semantic rerank for nuance.
            parallel: Independent execution + weighted fusion (`hybrid_alpha`) for diversity.

        Tip: Increase `options.rerank_count` when using *first variants for better recall.
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
        BM25 over full‑text chunks (precise wording / phrase focus).

        Use for:
            - Compliance & citation extraction (exact phrases, quotes).
            - Audits where lexical fidelity is critical.
            - Locating statutory definitions with stable phrasing.

        Wrap phrases in quotes to bias BM25 toward contiguous matches.
        """
        return self.search(query, SearchStrategy.FULLTEXT, options)
    
    def search_semantic_fulltext(self, query: str, options: Optional[SearchOptions] = None) -> SearchResults:
        """
        Semantic passage retrieval (embedding similarity) over full‑text chunks.

        Use for:
            - Natural language questions needing contextual passages.
            - Paraphrased obligations / concepts not sharing identical wording.
            - Feeding downstream LLM summarization / QA pipelines.

        Combine via `search_hybrid_fulltext` for lexical anchoring + conceptual breadth.
        """
        return self.search(query, SearchStrategy.SEMANTIC_FULLTEXT, options)

    def search_hybrid_fulltext(self, query: str, strategy: str = "semantic_first",
                                                        options: Optional[SearchOptions] = None) -> SearchResults:
        """
        Hybrid (BM25 + Semantic) retrieval on full‑text chunks for high quality passage sets.

        strategy guidelines mirror summary hybrid variants:
            semantic_first: Conceptual expansion first → lexical refinement (default for QA pipelines).
            keyword_first : Lexical filtering for precision → semantic ordering (tight queries / phrase heavy).
            parallel      : Fusion for diversity when latency acceptable.

        Pattern: summary hybrid → user chooses relevant heading → full‑text hybrid for deep dive.
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
        Semantic neighborhood lookup ("related sections") for a given element id.

        Scenarios:
            - Sidebar recommendations / "Users also viewed".
            - Thematic clustering / follow‑up exploration.
            - Detect near duplicates (inspect scores & content similarity manually).

        Notes:
            - Currently uses summary semantic index; lexical filters may need manual post‑filtering.
            - Result query string is synthetic: `similar:<element_id>` for traceability.
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
        """Return lightweight diagnostic info about loaded indexes.

        Useful for:
            - Capability gating (hide UI controls if full‑text indexes absent).
            - Health checks / monitoring dashboards.
            - Emitting telemetry on active index coverage.
        """
        info = {
            "act_iri": self._indexes.act_iri,
            "available_indexes": self._indexes.get_available_indexes(),
            "document_count": self._indexes.get_document_count()
        }
        
        return info
