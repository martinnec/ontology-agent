## 4. Development Iterations for Indexing & Retrieval

### Iteration 1: Core Index Data Model ✅ COMPLETED

#### Goal:
Create the foundational data structures and interfaces for indexing

#### Tasks:
- Create src/index/ module with __init__.py
- Implement IndexDoc class in src/index/domain.py - represents a searchable document with:
- Implement IndexDoc class in src/index/domain.py - represents a searchable document with:
    - element_id, title, summary, official_identifier
- Optional text_content for full-text indexing
- Metadata (level, type, parent relationships)
- Create IndexBuilder interface in src/index/builder.py
- Write unit tests src/index/test_domain.py

#### Acceptance Criteria:
- IndexDoc properly extracts searchable text from legal act elements
- Clear separation between summary-based and full-text indexing capabilities
- Test coverage for document creation and field extraction

### Iteration 2: BM25 Summary Index ✅ COMPLETED

#### Goal:
Implement BM25-based keyword search over summaries and titles

#### Tasks:
- Implement BM25SummaryIndex in src/index/bm25.py using rank-bm25 library
- Weight fields: summary^3 + title^2 + official_identifier^1
- Create src/index/build.py with CLI interface: python -m index.build <ACT_IRI>
- Implement basic search functionality in src/index/search.py
- Add persistence/loading for BM25 indexes
- Write tests src/index/test_bm25.py

#### Acceptance Criteria:
- BM25 index builds successfully from legal act elements
- Search queries like "Základní pojmy" return relevant sections ranked by relevance
- Index can be persisted and reloaded
- CLI tool works: python -m index.search <query>

### Iteration 3: FAISS Semantic Index ✅ COMPLETED

#### Goal:
Add semantic search capabilities using multilingual embeddings

#### Tasks:
- Implement FAISSSummaryIndex in src/index/faiss_index.py
- Use multilingual sentence transformers (e.g., sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)
- Add embedding generation for summaries and titles
- Implement FAISS vector storage and similarity search
- Add persistence for FAISS indexes and embeddings
- Extend src/index/search.py with semantic search
- Write tests src/index/test_faiss.py

#### Acceptance Criteria:
- FAISS index builds with proper embeddings for Czech legal text
- Semantic search returns conceptually related sections (not just keyword matches)
- Vector similarity search performs efficiently
- Embeddings and FAISS index persist correctly

#### Completion Summary:
- ✅ Complete FAISSSummaryIndex implementation with multilingual embeddings
- ✅ Enhanced CLI tools for building and searching both BM25 and FAISS indexes
- ✅ Comprehensive testing with 9 test functions (all passing)
- ✅ Real data demonstration with legal act 56/2001 (134 documents)
- ✅ Verified semantic understanding, multilingual capabilities, and document similarity
- ✅ Performance: ~6 seconds index building, sub-second search responses
- See detailed results in: src/index/ITERATION_3_SUMMARY.md

### Iteration 4: Hybrid Retrieval Strategy ✅ COMPLETED

#### Goal:
Combine BM25 and FAISS for optimal retrieval

#### Tasks:
- Implement HybridSearchEngine in src/index/hybrid.py
- Default strategy: FAISS for breadth → re-rank with BM25 for precision
- Add configurable retrieval parameters (weights, top-k values)
- Implement result fusion and re-ranking algorithms
- Add structural filters (element type, level, official identifier patterns)
- Write tests src/index/test_hybrid.py

#### Acceptance Criteria:
- Hybrid search outperforms individual methods on test queries
- Configurable retrieval strategies work correctly
- Structural filters properly constrain results
- Performance is acceptable for interactive use

#### Completion Summary:
- ✅ Complete HybridSearchEngine implementation with 3 search strategies
- ✅ Configurable fusion algorithms: RRF and weighted scoring
- ✅ Comprehensive testing with 10/10 test functions passing
- ✅ Real-world demonstration with legal act 56/2001 (134 documents)
- ✅ Performance validation: hybrid search provides superior coverage vs individual methods
- ✅ Production-ready integration with existing BM25/FAISS indexes
- ✅ Created demo_hybrid_56_2001.py for comprehensive real-world demonstration
- See detailed results in: src/index/ITERATION_4_SUMMARY.md

### Iteration 5: Full-Text Indexing (Optional) (1.5 days)

#### Goal:
Add support for exact phrase lookups in full legal text

#### Tasks:
- Extend IndexDoc to handle textContent chunking
- Implement BM25FullIndex for exact phrase searches
- Add FAISSFullIndex for semantic search over text chunks
- Implement targeted phrase search (e.g., "rozumí se", "musí", "je povinen")
- Integrate full-text capabilities into hybrid search
- Write tests src/index/test_fulltext.py

#### Acceptance Criteria:
- Full-text search finds exact legal phrases accurately
- Text chunking preserves semantic coherence
- Full-text indexes integrate seamlessly with summary-based search
- Performance remains acceptable with larger text volumes

### Iteration 6: Caching & Versioning (0.5 days)

#### Goal:
Implement proper caching and version management

#### Tasks:
- Add index versioning based on act snapshot IDs
- Implement cache invalidation when acts are updated
- Add index metadata and version tracking
- Optimize index loading and storage
- Write tests src/index/test_versioning.py

#### Acceptance Criteria:
- Index keys properly encode act snapshot information
- Re-indexing triggers automatically on act updates
- Cache management works correctly
- Index metadata is properly tracked

### Iteration 7: Overall Integration Test (0.5 days)

#### Goal:
Ensure the complete indexing system works end-to-end

#### Tasks:
- Create comprehensive integration test src/index/test_integration.py
- Test full workflow: build indexes → search → retrieve context
- Verify performance with realistic legal act data
- Document API usage and examples

#### Acceptance Criteria:
- Complete indexing workflow works from legal act to search results
- Performance metrics are within acceptable bounds
- API is intuitive and well-documented
- Integration with existing legislation module works correctly
- Dependencies & Prerequisites
- Python packages to add to requirements.txt:

#### Integration points:
- Must work with existing legislation.service for getting legal acts
- Will be used by future agent module for context retrieval
- Should integrate with the ontology extraction workflow
- This plan follows the specification's milestone M1 requirements and provides a solid foundation for the retrieval component that the agent will use to find relevant legal text sections for ontology extraction.