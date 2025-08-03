"""
Hybrid retrieval strategy combining BM25 and FAISS for optimal search performance.
This module implements the HybridSearchEngine that leverages both keyword-based
and semantic search to provide comprehensive retrieval capabilities.

The default strategy: FAISS for semantic breadth → re-rank with BM25 for keyword precision.
"""

import logging
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass
from pathlib import Path
import json

from .domain import SearchQuery, SearchResult, IndexDoc, ElementType
from .builder import IndexBuilder

# Optional imports with graceful fallbacks
try:
    from .bm25 import BM25SummaryIndex
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    BM25SummaryIndex = None

try:
    from .faiss_index import FAISSSummaryIndex
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    FAISSSummaryIndex = None

try:
    from .bm25_full import BM25FullIndex
    BM25_FULL_AVAILABLE = True
except ImportError:
    BM25_FULL_AVAILABLE = False
    BM25FullIndex = None

try:
    from .faiss_full import FAISSFullIndex
    FAISS_FULL_AVAILABLE = True
except ImportError:
    FAISS_FULL_AVAILABLE = False
    FAISSFullIndex = None

logger = logging.getLogger(__name__)


@dataclass
class HybridConfig:
    """Configuration for hybrid search strategy."""
    # Retrieval parameters
    faiss_k: int = 50  # Number of results from FAISS (semantic breadth)
    bm25_k: int = 30   # Number of results from BM25 (keyword precision)
    final_k: int = 20  # Final number of results to return
    
    # Full-text search parameters
    use_full_text: bool = False  # Whether to include full-text search
    full_text_weight: float = 0.3  # Weight for full-text results
    faiss_full_k: int = 20  # Number of results from FAISS full-text
    bm25_full_k: int = 15  # Number of results from BM25 full-text
    
    # Fusion weights
    faiss_weight: float = 0.6  # Weight for FAISS scores
    bm25_weight: float = 0.4   # Weight for BM25 scores
    
    # Re-ranking strategy
    rerank_strategy: str = "rrf"  # "rrf" (Reciprocal Rank Fusion) or "weighted"
    rrf_k: int = 60  # RRF parameter
    
    # Performance thresholds
    min_faiss_score: float = 0.3  # Minimum FAISS similarity score
    min_bm25_score: float = 0.1   # Minimum BM25 relevance score
    
    # Fallback behavior
    fallback_to_single: bool = True  # Fall back to single method if other fails


class HybridSearchEngine:
    """
    Hybrid search engine combining BM25 keyword search and FAISS semantic search.
    
    The engine provides multiple search strategies:
    1. Semantic-first: FAISS for breadth → BM25 re-ranking for precision
    2. Keyword-first: BM25 for precision → FAISS re-ranking for breadth
    3. Parallel fusion: Run both and fuse results using RRF or weighted scores
    4. Full-text: Includes full-text search capabilities for exact phrase matching
    """
    
    def __init__(self, 
                 bm25_index: Optional[Any] = None,
                 faiss_index: Optional[Any] = None,
                 bm25_full_index: Optional[Any] = None,
                 faiss_full_index: Optional[Any] = None,
                 config: Optional[HybridConfig] = None):
        """
        Initialize hybrid search engine.
        
        Args:
            bm25_index: BM25 summary index instance (optional)
            faiss_index: FAISS summary index instance (optional)
            bm25_full_index: BM25 full-text index instance (optional)
            faiss_full_index: FAISS full-text index instance (optional)
            config: Hybrid search configuration
        """
        self.bm25_index = bm25_index
        self.faiss_index = faiss_index
        self.bm25_full_index = bm25_full_index
        self.faiss_full_index = faiss_full_index
        self.config = config or HybridConfig()
        
        # Validate that at least one index is available
        if not any([self.bm25_index, self.faiss_index, self.bm25_full_index, self.faiss_full_index]):
            raise ValueError("At least one index must be provided")
        
        logger.info(f"HybridSearchEngine initialized with BM25={self.bm25_index is not None}, "
                   f"FAISS={self.faiss_index is not None}, "
                   f"BM25_Full={self.bm25_full_index is not None}, "
                   f"FAISS_Full={self.faiss_full_index is not None}")
    
    @classmethod
    def from_paths(cls, 
                   bm25_path: Optional[Union[str, Path]] = None,
                   faiss_path: Optional[Union[str, Path]] = None,
                   bm25_full_path: Optional[Union[str, Path]] = None,
                   faiss_full_path: Optional[Union[str, Path]] = None,
                   config: Optional[HybridConfig] = None) -> 'HybridSearchEngine':
        """
        Load hybrid search engine from index files.
        
        Args:
            bm25_path: Path to BM25 summary index directory
            faiss_path: Path to FAISS summary index directory
            bm25_full_path: Path to BM25 full-text index directory
            faiss_full_path: Path to FAISS full-text index directory
            config: Hybrid search configuration
            
        Returns:
            HybridSearchEngine instance
        """
        bm25_index = None
        faiss_index = None
        bm25_full_index = None
        faiss_full_index = None
        
        # Load BM25 summary index if available
        if bm25_path and BM25_AVAILABLE:
            try:
                bm25_index = BM25SummaryIndex()
                bm25_index.load(Path(bm25_path))
                logger.info(f"Loaded BM25 summary index from {bm25_path}")
            except Exception as e:
                logger.warning(f"Failed to load BM25 summary index from {bm25_path}: {e}")
        
        # Load FAISS summary index if available
        if faiss_path and FAISS_AVAILABLE:
            try:
                faiss_index = FAISSSummaryIndex()
                faiss_index.load(Path(faiss_path))
                logger.info(f"Loaded FAISS summary index from {faiss_path}")
            except Exception as e:
                logger.warning(f"Failed to load FAISS summary index from {faiss_path}: {e}")
        
        # Load BM25 full-text index if available
        if bm25_full_path and BM25_FULL_AVAILABLE:
            try:
                bm25_full_index = BM25FullIndex()
                bm25_full_index.load(Path(bm25_full_path))
                logger.info(f"Loaded BM25 full-text index from {bm25_full_path}")
            except Exception as e:
                logger.warning(f"Failed to load BM25 full-text index from {bm25_full_path}: {e}")
        
        # Load FAISS full-text index if available
        if faiss_full_path and FAISS_FULL_AVAILABLE:
            try:
                faiss_full_index = FAISSFullIndex()
                faiss_full_index.load(Path(faiss_full_path))
                logger.info(f"Loaded FAISS full-text index from {faiss_full_path}")
            except Exception as e:
                logger.warning(f"Failed to load FAISS full-text index from {faiss_full_path}: {e}")
        
        return cls(
            bm25_index=bm25_index, 
            faiss_index=faiss_index,
            bm25_full_index=bm25_full_index,
            faiss_full_index=faiss_full_index,
            config=config
        )
    
    def search(self, 
               query: Union[str, SearchQuery],
               strategy: str = "semantic_first",
               **kwargs) -> List[SearchResult]:
        """
        Perform hybrid search with specified strategy.
        
        Args:
            query: Search query string or SearchQuery object
            strategy: Search strategy ("semantic_first", "keyword_first", "parallel")
            **kwargs: Additional search parameters
            
        Returns:
            List of SearchResult objects ranked by hybrid score
        """
        # Convert string query to SearchQuery object
        if isinstance(query, str):
            query = SearchQuery(query=query)
        
        # Override config parameters with kwargs
        config = HybridConfig(
            faiss_k=kwargs.get('faiss_k', self.config.faiss_k),
            bm25_k=kwargs.get('bm25_k', self.config.bm25_k),
            final_k=kwargs.get('k', self.config.final_k),
            faiss_weight=kwargs.get('faiss_weight', self.config.faiss_weight),
            bm25_weight=kwargs.get('bm25_weight', self.config.bm25_weight),
            rerank_strategy=kwargs.get('rerank_strategy', self.config.rerank_strategy),
            rrf_k=kwargs.get('rrf_k', self.config.rrf_k),
            min_faiss_score=kwargs.get('min_faiss_score', self.config.min_faiss_score),
            min_bm25_score=kwargs.get('min_bm25_score', self.config.min_bm25_score)
        )
        
        # Route to appropriate strategy
        if strategy == "semantic_first":
            return self._semantic_first_search(query, config)
        elif strategy == "keyword_first":
            return self._keyword_first_search(query, config)
        elif strategy == "parallel":
            return self._parallel_fusion_search(query, config)
        else:
            raise ValueError(f"Unknown search strategy: {strategy}")
    
    def search_exact_phrase(self, phrase: str, max_results: int = 10) -> List[SearchResult]:
        """
        Search for exact phrases in full-text content.
        
        Args:
            phrase: Exact phrase to search for (e.g., "rozumí se", "musí", "je povinen")
            max_results: Maximum number of results to return
            
        Returns:
            List of SearchResult objects containing the exact phrase
        """
        if not self.bm25_full_index:
            logger.warning("BM25 full-text index not available for exact phrase search")
            return []
        
        try:
            return self.bm25_full_index.search_exact_phrase(phrase, max_results)
        except Exception as e:
            logger.error(f"Exact phrase search failed: {e}")
            return []
    
    def search_with_full_text(self, 
                             query: Union[str, SearchQuery],
                             strategy: str = "summary_with_fulltext",
                             **kwargs) -> List[SearchResult]:
        """
        Perform hybrid search including full-text content.
        
        Args:
            query: Search query string or SearchQuery object
            strategy: Search strategy ("summary_with_fulltext", "fulltext_only")
            **kwargs: Additional search parameters
            
        Returns:
            List of SearchResult objects from summary and full-text indexes
        """
        # Convert string query to SearchQuery object
        if isinstance(query, str):
            query = SearchQuery(query=query)
        
        if strategy == "summary_with_fulltext":
            return self._summary_with_fulltext_search(query, **kwargs)
        elif strategy == "fulltext_only":
            return self._fulltext_only_search(query, **kwargs)
        else:
            raise ValueError(f"Unknown full-text search strategy: {strategy}")
    
    def _summary_with_fulltext_search(self, query: SearchQuery, **kwargs) -> List[SearchResult]:
        """
        Search strategy that combines summary and full-text results.
        """
        all_results = []
        
        # Get summary results first (primary results)
        summary_results = self.search(query, strategy="parallel", **kwargs)
        
        # Add full-text results if available
        if self.config.use_full_text and (self.bm25_full_index or self.faiss_full_index):
            full_text_results = self._get_fulltext_results(query, **kwargs)
            
            # Combine results with appropriate weighting
            all_results = self._fuse_summary_and_fulltext_results(
                summary_results, 
                full_text_results,
                self.config.full_text_weight
            )
        else:
            all_results = summary_results
        
        return all_results[:self.config.final_k]
    
    def _fulltext_only_search(self, query: SearchQuery, **kwargs) -> List[SearchResult]:
        """
        Search strategy that uses only full-text indexes.
        """
        return self._get_fulltext_results(query, **kwargs)
    
    def _get_fulltext_results(self, query: SearchQuery, **kwargs) -> List[SearchResult]:
        """Get results from full-text indexes."""
        bm25_full_results = []
        faiss_full_results = []
        
        # Get BM25 full-text results
        if self.bm25_full_index:
            try:
                bm25_full_results = self.bm25_full_index.search(SearchQuery(
                    query=query.query,
                    max_results=self.config.bm25_full_k,
                    element_types=query.element_types,
                    min_level=query.min_level,
                    max_level=query.max_level
                ))
            except Exception as e:
                logger.warning(f"BM25 full-text search failed: {e}")
        
        # Get FAISS full-text results
        if self.faiss_full_index:
            try:
                faiss_full_results = self.faiss_full_index.search(SearchQuery(
                    query=query.query,
                    max_results=self.config.faiss_full_k,
                    element_types=query.element_types,
                    min_level=query.min_level,
                    max_level=query.max_level
                ))
            except Exception as e:
                logger.warning(f"FAISS full-text search failed: {e}")
        
        # Fuse full-text results
        if bm25_full_results and faiss_full_results:
            return self._fuse_results(bm25_full_results, faiss_full_results, self.config)
        elif bm25_full_results:
            return bm25_full_results
        elif faiss_full_results:
            return faiss_full_results
        else:
            return []
    
    def _fuse_summary_and_fulltext_results(self, 
                                          summary_results: List[SearchResult],
                                          fulltext_results: List[SearchResult],
                                          fulltext_weight: float) -> List[SearchResult]:
        """
        Fuse summary and full-text results with appropriate weighting.
        
        Args:
            summary_results: Results from summary indexes
            fulltext_results: Results from full-text indexes
            fulltext_weight: Weight to apply to full-text results
            
        Returns:
            Fused and ranked results
        """
        # Adjust scores for full-text results
        for result in fulltext_results:
            result.score *= fulltext_weight
        
        # Combine all results
        all_results = summary_results + fulltext_results
        
        # Remove duplicates (prefer summary results over chunks from same element)
        seen_elements = set()
        deduplicated_results = []
        
        for result in all_results:
            element_id = result.doc.parent_id or result.doc.element_id
            if element_id not in seen_elements:
                seen_elements.add(element_id)
                deduplicated_results.append(result)
        
        # Re-rank by adjusted scores
        deduplicated_results.sort(key=lambda x: x.score, reverse=True)
        
        # Update ranks
        for i, result in enumerate(deduplicated_results):
            result.rank = i + 1
        
        return deduplicated_results
    
    def _semantic_first_search(self, query: SearchQuery, config: HybridConfig) -> List[SearchResult]:
        """
        Semantic-first strategy: FAISS for breadth → BM25 re-ranking for precision.
        """
        # Step 1: Get semantic candidates from FAISS
        faiss_results = []
        if self.faiss_index:
            try:
                faiss_results = self.faiss_index.search(SearchQuery(
                    query=query.query, 
                    max_results=config.faiss_k,
                    element_types=query.element_types,
                    min_level=query.min_level,
                    max_level=query.max_level
                ))
                logger.debug(f"FAISS returned {len(faiss_results)} semantic candidates")
            except Exception as e:
                logger.warning(f"FAISS search failed: {e}")
        
        # Step 2: Re-rank with BM25 for keyword precision
        if self.bm25_index and faiss_results:
            try:
                # Create document subset for BM25 re-ranking
                candidate_ids = {result.doc.element_id for result in faiss_results}
                bm25_results = self.bm25_index.search(SearchQuery(
                    query=query.query,
                    max_results=config.bm25_k,
                    element_types=query.element_types,
                    min_level=query.min_level,
                    max_level=query.max_level
                ))
                
                # Combine and re-rank
                return self._fuse_results(faiss_results, bm25_results, config, primary="semantic")
            except Exception as e:
                logger.warning(f"BM25 re-ranking failed: {e}")
                return faiss_results[:config.final_k]
        
        # Fallback to single method
        if faiss_results:
            return faiss_results[:config.final_k]
        elif self.bm25_index and config.fallback_to_single:
            return self.bm25_index.search(SearchQuery(
                query=query.query,
                max_results=config.final_k,
                element_types=query.element_types,
                min_level=query.min_level,
                max_level=query.max_level
            ))
        else:
            return []
    
    def _keyword_first_search(self, query: SearchQuery, config: HybridConfig) -> List[SearchResult]:
        """
        Keyword-first strategy: BM25 for precision → FAISS re-ranking for breadth.
        """
        # Step 1: Get keyword candidates from BM25
        bm25_results = []
        if self.bm25_index:
            try:
                bm25_results = self.bm25_index.search(SearchQuery(
                    query=query.query,
                    max_results=config.bm25_k,
                    element_types=query.element_types,
                    min_level=query.min_level,
                    max_level=query.max_level
                ))
                logger.debug(f"BM25 returned {len(bm25_results)} keyword candidates")
            except Exception as e:
                logger.warning(f"BM25 search failed: {e}")
        
        # Step 2: Enhance with FAISS for semantic breadth
        if self.faiss_index and bm25_results:
            try:
                faiss_results = self.faiss_index.search(SearchQuery(
                    query=query.query,
                    max_results=config.faiss_k,
                    element_types=query.element_types,
                    min_level=query.min_level,
                    max_level=query.max_level
                ))
                
                # Combine and re-rank
                return self._fuse_results(faiss_results, bm25_results, config, primary="keyword")
            except Exception as e:
                logger.warning(f"FAISS enhancement failed: {e}")
                return bm25_results[:config.final_k]
        
        # Fallback to single method
        if bm25_results:
            return bm25_results[:config.final_k]
        elif self.faiss_index and config.fallback_to_single:
            return self.faiss_index.search(SearchQuery(
                query=query.query,
                max_results=config.final_k,
                element_types=query.element_types,
                min_level=query.min_level,
                max_level=query.max_level
            ))
        else:
            return []
    
    def _parallel_fusion_search(self, query: SearchQuery, config: HybridConfig) -> List[SearchResult]:
        """
        Parallel fusion strategy: Run both methods and fuse results.
        """
        faiss_results = []
        bm25_results = []
        
        # Run FAISS search
        if self.faiss_index:
            try:
                faiss_results = self.faiss_index.search(SearchQuery(
                    query=query.query,
                    max_results=config.faiss_k,
                    element_types=query.element_types,
                    min_level=query.min_level,
                    max_level=query.max_level
                ))
                logger.debug(f"FAISS parallel search: {len(faiss_results)} results")
            except Exception as e:
                logger.warning(f"FAISS parallel search failed: {e}")
        
        # Run BM25 search
        if self.bm25_index:
            try:
                bm25_results = self.bm25_index.search(SearchQuery(
                    query=query.query,
                    max_results=config.bm25_k,
                    element_types=query.element_types,
                    min_level=query.min_level,
                    max_level=query.max_level
                ))
                logger.debug(f"BM25 parallel search: {len(bm25_results)} results")
            except Exception as e:
                logger.warning(f"BM25 parallel search failed: {e}")
        
        # Fuse results
        if faiss_results and bm25_results:
            return self._fuse_results(faiss_results, bm25_results, config, primary="parallel")
        elif faiss_results:
            return faiss_results[:config.final_k]
        elif bm25_results:
            return bm25_results[:config.final_k]
        else:
            return []
    
    def _fuse_results(self, 
                     faiss_results: List[SearchResult],
                     bm25_results: List[SearchResult],
                     config: HybridConfig,
                     primary: str = "parallel") -> List[SearchResult]:
        """
        Fuse results from FAISS and BM25 using specified strategy.
        
        Args:
            faiss_results: Results from FAISS semantic search
            bm25_results: Results from BM25 keyword search
            config: Hybrid configuration
            primary: Primary search method ("semantic", "keyword", "parallel")
            
        Returns:
            Fused and ranked results
        """
        # Create mapping of element_id to results
        faiss_map = {r.doc.element_id: r for r in faiss_results}
        bm25_map = {r.doc.element_id: r for r in bm25_results}
        
        # Get all unique element IDs
        all_ids = set(faiss_map.keys()) | set(bm25_map.keys())
        
        fused_results = []
        
        for element_id in all_ids:
            faiss_result = faiss_map.get(element_id)
            bm25_result = bm25_map.get(element_id)
            
            # Calculate fused score
            if config.rerank_strategy == "rrf":
                score = self._calculate_rrf_score(faiss_result, bm25_result, 
                                                faiss_results, bm25_results, config)
            else:  # weighted
                score = self._calculate_weighted_score(faiss_result, bm25_result, config)
            
            # Skip if scores are too low
            faiss_score = faiss_result.score if faiss_result else 0.0
            bm25_score = bm25_result.score if bm25_result else 0.0
            
            if (faiss_score < config.min_faiss_score and bm25_score < config.min_bm25_score):
                continue
            
            # Create fused result (prefer the primary method's metadata)
            if primary == "semantic" and faiss_result:
                base_result = faiss_result
            elif primary == "keyword" and bm25_result:
                base_result = bm25_result
            else:
                base_result = faiss_result if faiss_result else bm25_result
            
            # Create fused result with hybrid score
            fused_result = SearchResult(
                doc=base_result.doc,
                score=score,
                rank=0,  # Will be set later
                matched_fields=getattr(base_result, 'matched_fields', []),
                snippet=getattr(base_result, 'snippet', '')
            )
            
            fused_results.append(fused_result)
        
        # Sort by hybrid score and return top-k
        fused_results.sort(key=lambda x: x.score, reverse=True)
        return fused_results[:config.final_k]
    
    def _calculate_rrf_score(self, 
                           faiss_result: Optional[SearchResult],
                           bm25_result: Optional[SearchResult],
                           faiss_results: List[SearchResult],
                           bm25_results: List[SearchResult],
                           config: HybridConfig) -> float:
        """Calculate Reciprocal Rank Fusion (RRF) score."""
        rrf_score = 0.0
        
        # Add FAISS contribution
        if faiss_result:
            faiss_rank = next((i for i, r in enumerate(faiss_results) 
                             if r.doc.element_id == faiss_result.doc.element_id), len(faiss_results))
            rrf_score += config.faiss_weight / (config.rrf_k + faiss_rank + 1)
        
        # Add BM25 contribution
        if bm25_result:
            bm25_rank = next((i for i, r in enumerate(bm25_results) 
                            if r.doc.element_id == bm25_result.doc.element_id), len(bm25_results))
            rrf_score += config.bm25_weight / (config.rrf_k + bm25_rank + 1)
        
        return rrf_score
    
    def _calculate_weighted_score(self, 
                                faiss_result: Optional[SearchResult],
                                bm25_result: Optional[SearchResult],
                                config: HybridConfig) -> float:
        """Calculate weighted average score."""
        weighted_score = 0.0
        total_weight = 0.0
        
        # Add FAISS contribution
        if faiss_result:
            # Normalize FAISS score (cosine similarity 0-1) 
            normalized_faiss = min(1.0, max(0.0, faiss_result.score))
            weighted_score += config.faiss_weight * normalized_faiss
            total_weight += config.faiss_weight
        
        # Add BM25 contribution
        if bm25_result:
            # Normalize BM25 score (assume reasonable range 0-10, cap at 1.0)
            normalized_bm25 = min(1.0, max(0.0, bm25_result.score / 10.0))
            weighted_score += config.bm25_weight * normalized_bm25
            total_weight += config.bm25_weight
        
        return weighted_score / total_weight if total_weight > 0 else 0.0
    
    def get_similar_documents(self, 
                            element_id: str, 
                            k: int = 10,
                            strategy: str = "semantic_first") -> List[SearchResult]:
        """
        Find documents similar to the given element using hybrid approach.
        
        Args:
            element_id: ID of the reference element
            k: Number of similar documents to return
            strategy: Search strategy to use
            
        Returns:
            List of similar documents
        """
        # For similarity search, prefer FAISS if available
        if self.faiss_index:
            try:
                return self.faiss_index.get_similar_documents(element_id, k=k)
            except Exception as e:
                logger.warning(f"FAISS similarity search failed: {e}")
        
        # Fallback: if we have the document, search for its title/summary
        if self.bm25_index:
            try:
                # This is a simplified fallback - in practice, you'd want to 
                # retrieve the document and search for its content
                logger.info(f"Falling back to BM25 search for similar documents to {element_id}")
                return []  # Would need document lookup to implement properly
            except Exception as e:
                logger.warning(f"BM25 similarity fallback failed: {e}")
        
        return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get hybrid search engine statistics."""
        stats = {
            'hybrid_engine': {
                'bm25_available': self.bm25_index is not None,
                'faiss_available': self.faiss_index is not None,
                'config': {
                    'faiss_k': self.config.faiss_k,
                    'bm25_k': self.config.bm25_k,
                    'final_k': self.config.final_k,
                    'faiss_weight': self.config.faiss_weight,
                    'bm25_weight': self.config.bm25_weight,
                    'rerank_strategy': self.config.rerank_strategy
                }
            }
        }
        
        # Add individual index statistics
        if self.bm25_index:
            # Handle both mock and real indexes
            if hasattr(self.bm25_index, 'get_statistics'):
                stats['bm25'] = self.bm25_index.get_statistics()
            elif hasattr(self.bm25_index, 'get_stats'):
                # Real BM25 index uses get_stats() and get_metadata()
                index_stats = self.bm25_index.get_stats()
                index_metadata = self.bm25_index.get_metadata()
                stats['bm25'] = {
                    'index_type': index_metadata.index_type,
                    'document_count': index_metadata.document_count,
                    'vocabulary_size': index_stats['vocabulary_size'],
                    'total_tokens': index_stats['total_tokens']
                }
            else:
                stats['bm25'] = {'error': 'Unable to get BM25 statistics'}
        
        if self.faiss_index:
            # Handle both mock and real indexes  
            if hasattr(self.faiss_index, 'get_statistics'):
                stats['faiss'] = self.faiss_index.get_statistics()
            elif hasattr(self.faiss_index, 'get_stats'):
                # Real FAISS index uses get_stats() and get_metadata()
                index_stats = self.faiss_index.get_stats()
                index_metadata = self.faiss_index.get_metadata()
                stats['faiss'] = {
                    'index_type': index_metadata.index_type,
                    'document_count': index_metadata.document_count,
                    'embedding_dimension': index_stats['embedding_dimension'],
                    'valid_embeddings': index_stats['valid_embeddings'],
                    'model_name': index_metadata.metadata.get('model_name', 'Unknown')
                }
            else:
                stats['faiss'] = {'error': 'Unable to get FAISS statistics'}
        
        return stats
