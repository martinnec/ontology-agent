# Agentic Ontology Builder

---

## 0. Big Picture — What We’re Building & Core Principles

### 0.1 One‑paragraph overview

The Agentic Ontology Builder (AOB) loads a **structured legal act** from our service (SPARQL‑backed), uses **hybrid summary‑first retrieval** (combining BM25 keyword and FAISS semantic search) to target the most informative elements, invokes an **LLM extractor** to propose classes/properties/axioms **grounded in the act's exact text**, validates proposals with **SHACL** and **OWL‑RL reasoning**, and then **publishes** accepted axioms into a versioned **Published** ontology graph with complete **PROV‑O provenance**. It operates in small, auditable iterations (plan → extract → validate → publish) and supports human review where needed.


### 0.2 Architecture at a glance

```
                +-----------------------------+
                |      SPARQL-backed source   |
                |  (acts, elements, summaries)|
                +--------------+--------------+
                               |
                     service.get_legal_act()
                               v
+-------------------+     +----+----+     +-------------------+
|  Index Layer      |<--->|  Agent  |<--->|  LLM Extractor    |
|  (Hybrid Search:  |     |Planner+ |     | (JSON proposals)  |
|   BM25 + FAISS)   |     |Worker   |     +---------+---------+
|  over titles &    |     |Worker   |     +---------+---------+
|  summaries        |     +----+----+               |
+---------+---------+          |                    |
          |                    | proposals          |
          v                    v                    v
   +------+--------+   +-------+-------+   +--------+--------+
   | Ontology Store|   | Reason & SHACL|   | Provenance (PROV)|
   | working/publ. |   | (OWL-RL,      |   | per triple       |
   | graphs (TTL)  |   |  pySHACL)     |   | + run ledger     |
   +------+--------+   +-------+-------+   +--------+--------+
          |                        |                   |
          +------------publish-----+-------------------+
```

### 0.3 Inputs, outputs, and lifecycle

- **Inputs**: One legal act and its element tree (each element has `id`, `officialIdentifier`, `title`, `summary`, optional `textContent`).
- **Outputs**:
  - **Working** graph (draft ontology triples), **Published** graph (validated triples), **PROV** graph (who/what/where from), **validation reports**.
  - **Indexes** (Hybrid: BM25+FAISS with configurable fusion) tied to the act snapshot; **run logs** and metrics.
- **Lifecycle**: For each iteration → retrieve targets → extract proposals → apply to working → reason + SHACL → publish/queue → log PROV → continue until coverage and CQ goals are met.

### 0.4 Responsibilities (logical components)

- **Planner**: decides what to do next; prioritizes elements whose summaries suggest definitions, processes, or constraints.
- **Worker**: retrieves context (neighbor summaries), calls **LLM Extractor**, applies ontology patches, runs validation.
- **LLM Extractor**: returns **structured JSON** proposals with confidence and **precise source references** (element + fragment/offsets).
- **Validator**: OWL‑RL materializer + SHACL engine; blocks unsafe or inconsistent changes.
- **Publisher**: promotes high‑confidence, validated axioms from Working → Published.
- **Provenance Recorder**: writes PROV‑O for every triple (derived‑from element + fragment; activity metadata).

### 0.5 Safety & auditability principles

1. **Summary‑guided, text‑grounded** — summaries help target, but evidence must be exact text (fragment id/offsets).
2. **Quality gates** — accept only if (a) extractor confidence ≥ threshold, (b) SHACL passes, (c) no OWL‑RL unsats, (d) no conflicts, (e) human approval for high‑impact edits.
3. **Deterministic loop** — explicit state machine, cutoffs, retries, and logging; same snapshot → same results.
4. **Standards‑first** — OWL 2, SKOS, SHACL, PROV‑O.
5. **Small steps** — patch → reason → validate → publish; everything has provenance.

### 0.6 Typical user journeys

- **Definition mining** (e.g., §2 “Základní pojmy”): Extractor proposes classes; Validator gates; Publisher promotes.
- **Process modeling** (approvals/inspections): Roles, processes, artifacts inferred; cardinalities hinted via SHACL.
- **Governance relations** (authorities/registries): Object properties like `manages`, with citations to exact clauses.

### 0.7 Success criteria

- Coverage of definition‑dense elements; rising **CQ** pass‑rate.
- Zero SHACL violations and zero unsats in Published.
- Each triple carries precise provenance; run ledger complete and readable.

---

## Table of Contents

- [1. Objectives & Non‑Goals](#1-objectives--non-goals)
- [2. System Overview](#2-system-overview)
- [3. Data Sources & Structural Model](#3-data-sources--structural-model)
- [4. Indexing & Retrieval](#4-indexing--retrieval)
- [5. Ontology Store, Modeling, & Validation](#5-ontology-store-modeling--validation)
- [6. Agent Architecture (Planner + Worker)](#6-agent-architecture-planner--worker)
- [7. Tooling Interfaces (Capabilities)](#7-tooling-interfaces-capabilities)
- [8. LLM Extraction & Prompting](#8-llm-extraction--prompting)
- [9. Provenance & Promotion Workflow](#9-provenance--promotion-workflow)
- [10. Developer Guide](#10-developer-guide)
  - [10.1 Project Layout](#101-project-layout)
  - [10.2 Environment & Dependencies](#102-environment--dependencies)
  - [10.3 Configuration](#103-configuration)
  - [10.4 Running an End‑to‑End Extraction](#104-running-an-end-to-end-extraction)
  - [10.5 Observability & Logs](#105-observability--logs)
- [11. Testing & Quality Assurance](#11-testing--quality-assurance)
- [12. Performance & Scaling](#12-performance--scaling)
- [13. Security & Privacy](#13-security--privacy)
- [14. Roadmap & Milestones](#14-roadmap--milestones)
- [15. Junior Developer Playbook (Step‑by‑Step)](#15-junior-developer-playbook-step-by-step)
  - [15.1 Milestones & DoD](#151-milestones--dod)
  - [15.2 Detailed Tasks & Gotchas](#152-detailed-tasks--gotchas)
  - [15.3 Reference Contracts & Pseudocode](#153-reference-contracts--pseudocode)
  - [15.4 Runbooks & Prompts](#154-runbooks--prompts)
  - [15.5 Acceptance Checklists & First Tickets](#155-acceptance-checklists--first-tickets)
- [Appendix A: JSON Schemas](#appendix-a-json-schemas)
- [Appendix B: SHACL Shape Starters](#appendix-b-shacl-shape-starters)
- [Appendix C: Competency Question (CQ) Starters](#appendix-c-competency-question-cq-starters)
- [Appendix D: Error Handling & Retry Policy](#appendix-d-error-handling--retry-policy)
- [Appendix E: Glossary](#appendix-e-glossary)

---

## 1. Objectives

- Extract a domain ontology (OWL 2) from long legal acts in a controlled, auditable manner.
- Leverage structured legal elements retrieved via SPARQL and a custom hierarchical model.
- Use **element summaries** to guide retrieval and LLM extraction while grounding evidence in the authoritative text.
- Validate with SHACL and reason with OWL‑RL prior to publishing ontology updates.
- Record complete provenance for every asserted triple and shape.

---

## 2. System Overview

**Pipeline (high level):**

1. Load a fully structured and summarized legal act via service calls (SPARQL‑backed).
2. Build **hybrid summary‑first** lexical and vector indexes over elements (BM25 + FAISS with configurable fusion strategies).
3. Agent **Planner** selects candidate elements; **Worker** retrieves context and calls **LLM Extractor**.
4. Proposed classes/properties/axioms are checked for conflicts, validated with **SHACL**, and materialized under **OWL‑RL**.
5. If all gates pass, publish to the **Published** ontology graph; otherwise, queue for review.
6. Persist **PROV** for every change with references to element IRIs and fragment/offsets.

**Core artifacts:** Working, Published, and Provenance graphs (Turtle & TriG); hybrid index bundles (BM25 + FAISS with configurable fusion strategies) tied to an act snapshot; validation reports (SHACL), reasoner summaries, and agent run logs.

---

## 3. Data Sources & Structural Model

### 3.1 Source of Truth

- Retrieve acts and their hierarchical elements through the existing service layer backed by a SPARQL endpoint.
- Each element provides: stable `id` (IRI), `officialIdentifier`, `title`, optional `textContent`, optional `summary`, and child `elements`.
- Summaries are bottom‑up and concise; they preserve the element’s language and emphasize concepts/constraints.

### 3.2 Element Schema (canonical)

```json
{
  "id": "IRI",
  "officialIdentifier": "string",
  "title": "string",
  "summary": "string | null",
  "summary_names": ["string"] | null,  // Extracted concept and relationship names
  "textContent": "string | null",    // may include hierarchical fragments (e.g., <f id="..."> ... </f>)
  "elements": [ /* recursive LegalStructuralElement */ ]
}
```

**Notes:** Use `id` IRIs directly for addressing and provenance; when `textContent` carries fragment identifiers (e.g., `<f id>`), cite fragment ids or character offsets in provenance. The `summary_names` field contains AI-extracted legal concepts and relationships in their basic form (singular, first case) for enhanced searchability.

---

## 4. Indexing & Retrieval

### 4.1 Implementation Status

**✅ COMPLETED - Iteration 1: Core Data Model**
- `IndexDoc` class for representing searchable legal elements
- `DocumentExtractor` for converting `LegalStructuralElement` → `IndexDoc`
- Support for hierarchical document extraction with metadata preservation
- Filtering and statistics utilities for document collections
- Comprehensive test coverage with integration tests

**✅ COMPLETED - Iteration 2: BM25 Summary Index**
- `BM25SummaryIndex` implementation with weighted fields (summary_names^5, summary^3, title^2, id^1)
- Enhanced concept-based search with extracted summary names for precise legal concept retrieval
- Czech text tokenization and normalization
- Advanced search filtering (element type, level, official identifier patterns)
- Relevance-based ranking with BM25 scoring
- Index persistence and loading capabilities
- CLI tools: `python -m index.build` and `python -m index.search`
- Comprehensive test coverage and demo scripts

**✅ COMPLETED - Iteration 3: FAISS Semantic Index**
- `FAISSSummaryIndex` implementation with multilingual sentence transformer embeddings
- Semantic search using `paraphrase-multilingual-MiniLM-L12-v2` model optimized for Czech legal text
- 384-dimensional vector embeddings with L2 normalization and cosine similarity
- FAISS IndexFlatIP for efficient vector similarity search
- Document similarity finding capabilities for discovering related legal provisions
- Complete persistence with embeddings, metadata, and index statistics
- Enhanced CLI tools supporting both BM25 and FAISS indexes with auto-detection
- Comprehensive test coverage with 9 test functions (100% pass rate)
- Real data demonstration with legal act 56/2001 covering semantic understanding, multilingual capabilities, and contextual search

**✅ COMPLETED - Iteration 4: Hybrid Retrieval Strategy**
- `HybridSearchEngine` implementation combining BM25 and FAISS for optimal retrieval
- Three search strategies: semantic-first, keyword-first, and parallel fusion
- Configurable fusion algorithms: Reciprocal Rank Fusion (RRF) and weighted scoring
- Flexible parameter configuration (weights, top-k values, fusion strategy)
- Real-world demonstration with legal act 56/2001 showing superior coverage vs individual methods
- Production-ready integration with existing BM25/FAISS indexes
- Comprehensive test coverage with 10/10 test functions passing
- Performance validation: hybrid search provides better recall and precision than individual methods
- Demo scripts: `demo_hybrid.py` (mock data), `demo_hybrid_56_2001.py` (real legal act), matching existing `demo_bm25_56_2001.py` and `demo_faiss_56_2001.py`

**✅ COMPLETED - Iteration 5: Full-Text Indexing & Hierarchical Chunking**

- **Hierarchical XML-aware chunking strategy** implemented for legal acts:
  - Legal documents are parsed as hierarchical trees of fragments (`<f>` elements).
  - Each leaf fragment is extracted as a sequence containing the full ancestral context from root to leaf.
  - Chunking preserves the complete fragment ID path and hierarchical metadata for every chunk.
  - Enables precise retrieval and ontology extraction by maintaining legal structure relationships.

- **BM25FullIndex** and **FAISSFullIndex**:
  - BM25FullIndex: Exact phrase keyword search over full text chunks, supporting legal phrase queries.
  - FAISSFullIndex: Semantic search over hierarchical text chunks using multilingual embeddings.
  - Both indexes operate on hierarchical leaf sequences, not independent fragments.

- **IndexDoc** enhancements:
  - New chunking logic: `get_text_chunks()` now extracts leaf sequences with full context.
  - Metadata for each chunk includes fragment ID path, context, depth, and sequence index.
  - Fallback to simple chunking for plain text (non-XML).

- **Demonstration & Validation**:
  - Interactive demo script (`demo_hierarchical_chunking.py`) showcases step-by-step extraction, chunking, and comparison.
  - Real legal act (§ 61, 56/2001) processed to verify correct hierarchical chunking.
  - All tests passed: hierarchical structure, chunking, and comparison with old approach.

- **Key Benefits**:
  - Zero information loss: Each chunk contains complete legal context from root to leaf.
  - Perfect for ontology extraction: Enables accurate concept and relationship modeling.
  - Eliminates URL pollution and preserves semantic coherence.
  - Ready for production use on full legal act corpus.

**Summary:**  
Iteration 5 delivers a robust, production-ready hierarchical chunking and full-text indexing system for legal acts, supporting both keyword and semantic search, and enabling precise, context-aware ontology extraction.

### 4.2 Architecture Refactoring ✅ COMPLETED

Following completion of the core indexing iterations, a comprehensive architecture refactoring was successfully completed in January 2025 to modernize the system with unified interfaces and consistent patterns.

**✅ COMPLETED - Phase 1: Core Architecture Foundation**
- **IndexService**: Unified interface for all index operations (`src/index/service.py`)
- **Storage Standardization**: Act-based directory structure: `./demo_indexes/[act-id]/[index-type]/`
- **Legal Act Identifiers**: Proper extraction from Czech ELI IRIs (e.g., `56-2001-2025-07-01`)
- **Integration Testing**: 7/7 IndexService tests passing with real legal act data
- **Consistency**: All IndexBuilder implementations updated for uniform storage patterns

**✅ COMPLETED - Phase 2: Search Integration**
- **SearchService**: Unified search interface supporting all strategies (`src/search/service.py`)
- **Strategy Support**: Keyword, semantic, hybrid (semantic-first, keyword-first, parallel), fulltext
- **End-to-End Integration**: Complete workflow validation from legal act loading to search results
- **Performance**: 9/9 SearchService integration tests passing, ~30ms search response times
- **Module Integration**: Seamless coordination between legislation, index, and search modules

**✅ COMPLETED - Phase 3: Legacy Code Migration**
- **CLI Modernization**: Migrated `hybrid_search_engine_cli.py` from legacy HybridSearchEngine to SearchService
- **Interface Unification**: All search commands now use unified SearchOptions and SearchResults
- **Backward Compatibility**: Complete CLI functionality preserved while using modern architecture
- **Real Data Validation**: All operations tested and working with Czech legal act 56/2001
- **Clean Architecture**: No direct index access outside of builder implementations

**Architecture Benefits Achieved:**
- **Unified Interfaces**: Single point of access for index and search operations
- **Clean Separation**: Proper dependency injection and separation of concerns
- **Testability**: Comprehensive test coverage with mock implementations
- **Maintainability**: Easy to extend and modify individual components
- **Performance**: Maintained search performance while improving code quality
- **Production Ready**: Robust error handling and real-world validation

The refactored architecture provides a solid foundation for future development while maintaining all existing functionality and performance characteristics.

### 4.3 BM25 Implementation

The `BM25SummaryIndex` provides:
- **Weighted indexing:** `summary_names^5 + summary^3 + title^2 + officialIdentifier^1` for relevance tuning
- **Concept-enhanced search:** Summary names contain extracted legal concepts and relationships with highest search weight
- **Czech tokenization:** Handles diacritics and legal text patterns
- **Advanced filtering:** Element type, hierarchical level, regex pattern matching
- **Search features:** Relevance scoring, matched field detection, snippet generation
- **Persistence:** Save/load indexes with metadata and statistics
- **CLI interface:** Build indexes and perform searches from command line

**Performance characteristics:**
- Fast keyword-based search suitable for exact term matching
- Enhanced precision through concept-based retrieval via summary_names
- Optimized for legal document structure with weighted fields
- Efficient storage and loading of pre-built indexes
- Supports complex filtering scenarios common in legal research

### 4.4 FAISS Implementation

The `FAISSSummaryIndex` provides:
- **Multilingual embeddings:** Uses `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` optimized for Czech legal text
- **Vector similarity search:** 384-dimensional embeddings with L2 normalization and cosine similarity
- **FAISS IndexFlatIP:** Efficient inner product search for cosine similarity
- **Semantic understanding:** Goes beyond keyword matching to find conceptually related content
- **Cross-language capabilities:** English queries can find relevant Czech legal content
- **Document similarity:** `get_similar_documents()` method for finding related legal provisions
- **Persistence:** Complete serialization of embeddings, index, and metadata
- **Performance:** ~6 seconds to build index for 134 documents, sub-second search responses

**Key features:**
- Semantic search that understands legal concepts and relationships
- Multilingual support for cross-language legal research
- Integration with existing BM25 infrastructure
- Structural filtering combined with semantic search
- Comprehensive testing and real-data verification

### 4.5 Indexes

- **BM25‑Summary (primary):** ✅ IMPLEMENTED - index `summary_names^5 + summary^3 + title^2 + officialIdentifier^1` with concept-enhanced search.
- **BM25‑Full (optional):** ✅ IMPLEMENTED - include `textContent` for exact‑phrase lookups (e.g., "rozumí se", "musí", "je povinen").
- **FAISS‑Summary (primary):** ✅ IMPLEMENTED - multilingual embeddings on `summary` (or `title + summary`) with semantic search capabilities.
- **FAISS‑Full (optional):** ✅ IMPLEMENTED - embeddings over token‑bounded `textContent` slices for deeper recall.

### 4.6 Document Model

The `IndexDoc` class provides:
- **Core fields:** `element_id`, `title`, `summary`, `summary_names`, `official_identifier`, `text_content`
- **Summary names:** List of extracted legal concepts and relationships for enhanced search precision
- **Metadata:** `level`, `element_type`, `parent_id`, `child_ids`, `act_iri`, `snapshot_id`
- **Search utilities:** `get_searchable_text()`, `get_weighted_fields()`
- **Extraction:** `from_legal_element()` class method for conversion from legislation domain

The `DocumentExtractor` utility provides:
- **Hierarchy processing:** `extract_from_act()` recursively processes legal act structure
- **Filtering:** `filter_documents()` supports type, level, content presence filters
- **Analytics:** `get_document_stats()` provides document collection statistics

### 4.7 Retrieval Strategy

**✅ IMPLEMENTED - Hybrid Search (Primary Strategy)**
- **Default approach**: `HybridSearchEngine` combining BM25 and FAISS for optimal retrieval
- **Three strategies**:
  - **Semantic-first**: FAISS breadth → BM25 precision re-ranking
  - **Keyword-first**: BM25 precision → FAISS breadth enhancement  
  - **Parallel fusion**: Both methods combined using RRF or weighted scoring
- **Configurable weights**: Adjustable FAISS/BM25 influence (default 60/40)
- **Fusion algorithms**: Choose between Reciprocal Rank Fusion (RRF) or weighted average
- **Real-world validated**: Demonstrated superior coverage on legal act 56/2001 with 134 documents

**Individual Methods (Components)**
- **Concept-based queries** → leverage `summary_names` highest weight (5x) for precise legal concept matching via BM25.
- **Semantic queries** → use FAISS embeddings for conceptual understanding beyond exact keyword matches.
- **Multilingual support** → FAISS handles cross-language queries (English queries finding Czech content).
- For targeted phrases → constrain/re‑rank with BM25‑Full.
- Add structural filters (type/level or `officialIdentifier` regex like `^§`).
- **Document similarity** → use FAISS `get_similar_documents()` for finding related legal provisions.

### 4.8 Caching & Versioning

- Index keys encode the act snapshot id so re‑indexing triggers automatically on updates.

---

## 5. Ontology Store, Modeling, & Validation

### 5.1 Implementation Status

**✅ COMPLETED - Comprehensive Ontology Module**

The ontology module provides a complete practical framework for legal ontology management with the following implemented components:

**✅ COMPLETED - Core Domain Models**
- `OntologyClass`: Complete class representation with labels, definitions, hierarchies, and provenance
- `OntologyProperty`: Object and datatype properties with domain/range specifications
- `ClassNeighborhood`: Class exploration with connected entities via property relationships
- `SimilarClass`: Semantic similarity scoring for concept discovery
- `OntologyStats`: Comprehensive ontology metrics and statistics

**✅ COMPLETED - OntologyService Public Interface**
- Unified high-level interface for all ontology operations (`src/ontology/service.py`)
- Working ontology overview for agent integration
- Class neighborhood exploration and hierarchy analysis
- Semantic similarity-based concept search
- LLM extraction result integration with validation
- Property relationship validation and management

**✅ COMPLETED - OntologyStore Backend**
- In-memory RDF store with working and published graph separation
- Complete namespace management (OWL, RDFS, SKOS, XSD, custom)
- CRUD operations for classes and properties with full provenance
- Semantic similarity engine integration using multilingual sentence transformers
- Class and property embedding computation for concept discovery

**✅ COMPLETED - Semantic Similarity Integration**
- `SemanticSimilarity` engine using `paraphrase-multilingual-MiniLM-L12-v2` model
- Multilingual concept matching (Czech and English legal text)
- Text embedding computation for classes and properties
- Vector similarity scoring for concept discovery and relationship inference
- Integration with search and classification workflows

**✅ COMPLETED - Testing & Documentation**
- Comprehensive test coverage: 4/4 test modules with 100% pass rate
- Integration tests with real ontological concepts and relationships
- Demo script showcasing complete workflow from concept extraction to similarity analysis
- Complete documentation of public interfaces and domain models

### 5.2 Core Architecture

The ontology module follows a clean layered architecture:

```
OntologyService (Public Interface)
       ↓
OntologyStore (RDF Storage & CRUD)
       ↓
SemanticSimilarity (AI-powered concept matching)
       ↓
Domain Models (Typed data structures)
```

**Key Design Principles:**
- **Single Public Interface**: All external access through `OntologyService`
- **Graph Separation**: Working vs. Published graphs for staged development
- **Semantic Enhancement**: AI-powered similarity for concept discovery
- **Full Provenance**: Source element tracking for all assertions
- **Multilingual Support**: Czech and English labels, definitions, and comments

### 5.3 Namespaces & Standards

**Implemented Namespaces:**
- `ex:` Project base namespace (`https://example.org/ontology/`)
- `owl:` OWL 2 Web Ontology Language
- `rdfs:` RDF Schema vocabulary
- `skos:` Simple Knowledge Organization System
- `xsd:` XML Schema datatypes

**Standards Compliance:**
- **OWL 2**: Full class and property modeling
- **SKOS**: Preferred and alternative labels
- **RDF/RDFS**: Standard property hierarchies and typing
- **Multilingual**: Czech (`@cs`) and English (`@en`) language tags

### 5.4 Modeling Conventions

**Classes (`OntologyClass`)**:
- Legal categories, defined terms, roles, statuses extracted from legal acts
- Multilingual labels: `{"cs": "Silniční vozidlo", "en": "Road vehicle"}`
- Definitions with legal grounding and source element provenance
- Hierarchical relationships: parent classes, subclasses with `rdfs:subClassOf`
- Property relationships: incoming/outgoing object properties, datatype properties

**Properties (`OntologyProperty`)**:
- **Object properties**: Relations among domain entities (e.g., `máSystém`, `náležíDo`)
- **Datatype properties**: Identifiers, codes, literal attributes (e.g., `maIdentifikator`)
- Domain and range specifications with proper OWL semantics
- Multilingual definitions and usage examples from legal text

**Labeling Standards**:
- `skos:prefLabel@cs` mandatory for Czech legal terminology
- `skos:prefLabel@en` for English translations when available
- `rdfs:comment` for definition notes and legal citations
- Source element provenance for every assertion

### 5.5 Graph Management

**Working Graph (`working_graph`)**:
- Draft assertions under development and review
- Staging area for LLM-extracted concepts before validation
- Supports iterative refinement and conflict resolution
- Complete provenance tracking to source legal elements

**Published Graph (`published_graph`)**:
- Validated and approved ontology ready for production use
- Quality gates: reasoning consistency, SHACL compliance, human approval
- Immutable versioned releases with complete audit trail
- Integration endpoint for external systems and queries

**Graph Operations**:
- **Serialization**: Turtle format for human readability
- **Persistence**: File-based storage with version control integration
- **Querying**: SPARQL endpoint compatibility for complex queries
- **Validation**: Future SHACL and OWL-RL reasoning integration

### 5.6 Public Interface: OntologyService

The `OntologyService` class provides the complete public API for ontology operations:

#### Core Operations

```python
# Ontology Overview
def get_working_ontology() -> Dict[str, Any]
# Returns complete ontology with classes, properties, and statistics

# Class Operations  
def get_class_neighborhood(class_iri: str) -> ClassNeighborhood
def get_similar_classes(class_iri: str, limit: int = 10) -> List[SimilarClass]
def get_class_hierarchy(class_iri: str) -> Dict[str, List[URIRef]]

# Property Operations
def get_property_details(property_iri: str) -> OntologyProperty

# Concept Search
def search_by_concept(concept_text: str) -> List[Dict[str, Any]]
# Semantic similarity search across classes and properties

# LLM Integration
def add_extraction_results(extracted_concepts: List[Dict[str, Any]]) -> bool
# Process LLM-extracted concepts with validation and conflict resolution
```

#### LLM Extraction Integration

The service provides seamless integration with LLM extraction workflows:

**Input Format for Classes:**
```python
{
    "type": "class",
    "name_cs": "Silniční vozidlo",
    "name_en": "Road vehicle", 
    "definition_cs": "Vozidlo určené k provozu na pozemních komunikacích",
    "definition_en": "Vehicle intended for operation on roads",
    "parent_class": "ex:Vozidlo",
    "source_element": "https://example.org/legal/element/123"
}
```

**Input Format for Properties:**
```python
{
    "type": "property",
    "property_type": "ObjectProperty",
    "name_cs": "má technickou způsobilost",
    "name_en": "has technical fitness",
    "domain": "ex:SilnicniVozidlo",
    "range": "ex:TechnickaZpusobilost",
    "source_element": "https://example.org/legal/element/456"
}
```

#### Semantic Search Capabilities

**Concept-based Search:**
- Multilingual query support (Czech and English)
- Semantic similarity scoring using sentence transformers
- Fallback to text matching when similarity engine unavailable
- Relevance ranking with configurable similarity thresholds

**Search Results:**
```python
[{
    "type": "class|property",
    "iri": "concept_iri",
    "score": 0.85,  # Similarity/relevance score
    "labels": {"cs": "...", "en": "..."},
    "definitions": {"cs": "...", "en": "..."},
    "additional_info": {...}  # Type-specific details
}]
```

#### Class Exploration

**Neighborhood Analysis:**
- Target class with complete property relationships
- Connected classes via object properties (domain/range relationships)  
- Property details for relationship understanding
- Hierarchical context (parent/child classes)

**Similarity Discovery:**
- Find conceptually similar classes using semantic embeddings
- Multilingual similarity computation (Czech ↔ English)
- Configurable similarity thresholds and result limits
- Basis tracking (labels, definitions, combined)

### 5.7 Future Validation & Reasoning

**Planned SHACL Integration:**
- Meta shapes: Validate required labels, proper domain/range specifications
- Domain shapes: Legal obligations, cardinalities extracted from text
- Validation gates preventing inconsistent or incomplete assertions

**Planned OWL-RL Reasoning:**
- Materialization for performance and predictable semantics
- Consistency checking before publishing to approved graph
- Inference of implicit relationships from explicit assertions

**Quality Gates (Planned):**
1. **Reasoning consistency**: No unsatisfiable classes or property conflicts
2. **SHACL compliance**: All meta and domain shapes validated
3. **Provenance completeness**: Every assertion traced to source elements
4. **Human approval**: High-impact changes reviewed before publication

### 5.8 Integration Points

**With Legislation Module:**
- Consume legal acts and structural elements for concept extraction
- Source element provenance linking every assertion to legal text
- Summary and concept name utilization for targeted extraction

**With Index/Search Module:**
- Semantic similarity engine shared with FAISS indexing
- Concept-based search supporting ontology development
- Retrieval of related legal elements for context expansion

**With Future Agent Module:**
- Working ontology overview for agent decision making
- Concept search for avoiding duplicate extractions
- LLM extraction result processing with conflict resolution

**With Future LLM Module:**
- Structured concept extraction with proper domain/property modeling
- Ontology view provision for context-aware extraction
- Refinement suggestions based on similarity analysis

---

## 6. Agent Architecture (Planner + Worker)

### 6.1 State Machine

`EnsureActLoaded` → `SelectElements` → `RetrieveContext` → `ExtractCandidates` → `ConflictCheck` → `ApplyToWorking` → `ReasonAndValidate` → `PublishOrQueue` → `NextBatch`.

### 6.2 Batch Policy

Start with **definitions** and concept‑dense elements (ranked by summary); maintain a **processing cursor** per act snapshot; apply back‑pressure (max proposals/iteration, timeouts, retries).

### 6.3 Use of Summaries by Step

- **SelectElements**: rank by FAISS‑Summary; re‑rank by BM25‑Summary; prefer short text + rich summary + concept names.
- **RetrieveContext**: gather parent/preceding/following **summaries** and **summary_names** for scope without token bloat.
- **ExtractCandidates**: provide `summary` and `summary_names` as guide and `textContent` (or fragment slices) as evidence; provenance must cite text.
- **ConflictCheck**: cluster by normalized label; compare summaries and concept names to detect near‑duplicate concepts; propose SKOS mappings.

---

## 7. Tooling Interfaces (Capabilities)

> **Note:** Signatures are indicative; implement as typed Python functions/classes.

### 7.1 Source & Service

**✅ IMPLEMENTED - Unified Service Interface**
- `service.get_legal_act(iri: str) -> LegalAct` (via `LegislationService`)
- `service.get_element(iri: str) -> LegalStructuralElement`
- `service.summarize_act(legal_act: LegalAct) -> LegalAct` (AI summarization with concept extraction)

### 7.2 Indexing & Search

**✅ IMPLEMENTED - Unified IndexService Interface**
- `index_service = IndexService(output_dir: str)` (unified index management)
- `index_service.get_indexes(legal_act, force_rebuild: bool = False) -> IndexCollection`
- `index_service.build_indexes(legal_act, index_types: List[str] = None) -> IndexCollection`
- `index_service.index_exists(legal_act, index_type: str) -> bool`
- `index_service.clear_indexes(legal_act) -> None`

**✅ IMPLEMENTED - Unified SearchService Interface**
- `search_service = SearchService(index_service, legal_act)` (unified search operations)
  Public convenience methods (explicit summary vs full‑text separation):
  - `search_service.search(query: str, strategy: SearchStrategy, options: SearchOptions | None = None) -> SearchResults` (low‑level unified entrypoint)
  - `search_service.search_keyword_summary(query, options=None)`  – BM25 over titles+summaries
  - `search_service.search_semantic_summary(query, options=None)` – FAISS semantic over summaries
  - `search_service.search_hybrid_summary(query, strategy="semantic_first"|"keyword_first"|"parallel", options=None)` – hybrid summaries
  - `search_service.search_keyword_fulltext(query, options=None)`  – BM25 over full‑text chunks (phrase search by quoting: `"musí být"`)
  - `search_service.search_semantic_fulltext(query, options=None)` – FAISS semantic over full‑text chunks
  - `search_service.search_hybrid_fulltext(query, strategy="semantic_first"|"keyword_first"|"parallel", options=None)` – hybrid full‑text passage retrieval
  - `search_service.search_similar(element_id, options=None)` – semantic neighborhood (related elements)
  - `search_service.get_index_info()` – diagnostic index availability

  (Legacy method names like `search_keyword`, `search_fulltext`, `search_exact_phrase` have been consolidated into the explicit summary/full‑text API. Exact phrase search is performed by quoting the phrase in `search_keyword_fulltext`.)

## Search Strategies & Use Cases (Updated)

We distinguish two content layers and associated strategy groups:

1. Summary layer (titles + summaries) – conceptual, fast navigation.
2. Full‑text layer (hierarchical chunks) – detailed, citation & phrase fidelity.

`SearchStrategy` enum (summary): `keyword`, `semantic`, `hybrid_semantic_first`, `hybrid_keyword_first`, `hybrid_parallel`

`SearchStrategy` enum (full‑text): `fulltext`, `semantic_fulltext`, `hybrid_fulltext_semantic_first`, `hybrid_fulltext_keyword_first`, `hybrid_fulltext_parallel`

### Summary Layer Convenience Methods

| Method | Purpose | Pick When |
|--------|---------|-----------|
| `search_keyword_summary` | BM25 lexical over summaries | Exact legal terms, identifiers, short queries |
| `search_semantic_summary` | Embedding similarity over summaries | Paraphrased / conceptual / cross‑lingual queries |
| `search_hybrid_summary(..., semantic_first)` | Semantic breadth → lexical rerank | Balanced default general use |
| `search_hybrid_summary(..., keyword_first)` | Lexical precision → semantic rerank | Short / highly specific terms, compliance checks |
| `search_hybrid_summary(..., parallel)` | Independent + fused | Need diversity, exploratory UI |

### Full‑Text Layer Convenience Methods

| Method | Purpose | Pick When |
|--------|---------|-----------|
| `search_keyword_fulltext` | BM25 on chunks (supports quoted phrases) | Exact phrase / wording verification, citations |
| `search_semantic_fulltext` | Embedding passage retrieval | Natural language question → passages |
| `search_hybrid_fulltext(..., semantic_first)` | Concept first → lexical refine | LLM answer generation, broad Q&A |
| `search_hybrid_fulltext(..., keyword_first)` | Lexical filter → semantic order | Phrase heavy or regulation code queries |
| `search_hybrid_fulltext(..., parallel)` | Fused diversity | Research & analysis breadth |

### Similarity
`search_similar(element_id)` – related sections (semantic neighborhood) for recommendations, clustering, or expansion.

### Phrase Search
Use quotes inside keyword methods (summary or full‑text) to bias BM25 toward phrase matching: `search_keyword_fulltext('"musí být vybaven"')`.

### Pattern Examples
```python
# Broad conceptual to detailed drill‑down
topics = search_service.search_hybrid_summary("vehicle registration process")
passages = search_service.search_hybrid_fulltext("mandatory insurance coverage scope")

# Exact phrase verification in statute wording
phrase_hits = search_service.search_keyword_fulltext('"je povinen zajistit"')

# Recommendations while viewing a section
related = search_service.search_similar(section_id)
```

### Strategy Selection Heuristics
* Start summary layer (`search_hybrid_summary` semantic_first) for navigation.
* Escalate to full‑text hybrid for answer extraction / citation.
* Use keyword_first when precision matters and query is tight.
* Use parallel when UI benefits from a blended diverse first page.
* Maintain a larger `rerank_count` in options for *first hybrids to preserve recall.

## Advanced Features

### **Document Similarity Discovery**
```python
# Find documents similar to a specific legal element (semantic neighborhood)
similar = search_service.search_similar(
  element_id="https://...legal-element-iri",
  options=SearchOptions(max_results=10)
)
```
**Use cases:** Discovering related legal provisions, finding similar regulatory patterns, legal precedent research

### **Search Configuration with SearchOptions**
```python
options = SearchOptions(
  max_results=20,                 # Final result list size
  min_score=0.0,                  # Client-side thresholding
  element_types=["section"],      # Structural filter (act|part|chapter|division|section|unknown)
  min_level=None, max_level=None, # Hierarchy bounds
  include_content=True,           # Include text_content in result items if available
  boost_summary=2.0, boost_title=1.5,  # Lexical weighting hints (BM25 layer)
  hybrid_alpha=0.5,               # Fusion weight (parallel hybrids): 0=keyword,1=semantic
  rerank_count=50,                # Candidate pool for *first hybrids
  chunk_overlap=True, chunk_size=500  # Full‑text chunking behavior
)
```

### **Strategic Search Combinations**
```python
# Progressive search refinement
broad_results = search_service.search_semantic("vehicle safety")
specific_results = search_service.search_keyword("bezpečnost vozidel")
exact_phrases = search_service.search_exact_phrase("bezpečnostní systém")

# Multi-strategy validation
hybrid_results = search_service.search_hybrid_parallel("dopravní nehoda")
keyword_check = search_service.search_keyword("dopravní nehoda")
```

## Performance Characteristics & Selection Guide

| Strategy (Layer) | Precision | Recall | Typical Latency* | Primary Use |
|------------------|----------|--------|------------------|-------------|
| keyword (summary) | High | Med | Low | Exact terms / identifiers |
| semantic (summary) | Med | High | Low | Concept / paraphrase |
| hybrid_semantic_first (summary) | High | High | Low | General default |
| hybrid_keyword_first (summary) | Very High | High | Low | Precision‑critical |
| hybrid_parallel (summary) | High | Very High | Low-Med | Diverse exploration |
| fulltext (keyword) | High | High | Med | Phrase / wording verification |
| semantic_fulltext | Med | High | Med | Passage retrieval for QA |
| hybrid_fulltext_semantic_first | High | High | Med | Answer generation contexts |
| hybrid_fulltext_keyword_first | Very High | High | Med | Tight compliance queries |
| hybrid_fulltext_parallel | High | Very High | Med | Comprehensive research |

*Indicative relative latencies; actual values depend on corpus size and hardware.

## Decision Matrix for Strategy Selection

**Choose KEYWORD when:**
- You know exact legal terms or identifiers
- Searching for specific definitions (`"rozumí se"`)
- Need fast, precise matches
- Working with official identifiers (`§`, `článek`)

**Choose SEMANTIC when:**
- Exploring legal concepts broadly
- Using natural language queries
- Cross-language research needs
- Discovering related provisions

**Choose HYBRID_SEMANTIC_FIRST when:**
- General legal research (recommended default)
- Need both precision and coverage
- Balanced exploration and accuracy
- Most common search scenarios

**Choose HYBRID_KEYWORD_FIRST when:**
- Precision is critical
- Starting with specific legal terms
- Compliance and regulatory checks
- Definition-focused research

**Choose HYBRID_PARALLEL when:**
- Maximum comprehensive coverage needed
- Research and analysis scenarios
- Comparing search method effectiveness
- Exploring all aspects of a topic

**Choose FULLTEXT when:**
- Need to search within full legal text
- Summaries/titles insufficient
- Detailed content analysis required
- Understanding contextual usage

Phrase queries are handled by quoting terms in keyword methods (e.g., `search_keyword_fulltext('"musí být"')`).

**All searches return `SearchResults` with unified `SearchResultItem` objects.**
Scores are only comparable within a single result set; do not fuse raw scores across different strategy runs manually unless normalized.

### 7.3 LLM Extraction

- `llm.extract(element: LegalStructuralElement, neighbors: list[LegalStructuralElement], ontology_view: OntologyView, schema: JsonSchema) -> ExtractionProposal`
- `llm.refine_for_shacl(proposal: ExtractionProposal, shacl_report: ShaclReport) -> ExtractionProposal`

### 7.4 Ontology Operations

**✅ IMPLEMENTED - OntologyService Interface**

```python
# Core Ontology Service
ontology_service = OntologyService(store: Optional[OntologyStore] = None)

# Working Ontology Overview
ontology_service.get_working_ontology() -> Dict[str, Any]
# Returns: {"classes": [...], "object_properties": [...], "datatype_properties": [...], "stats": {...}}

# Class Operations
ontology_service.get_class_neighborhood(class_iri: str) -> ClassNeighborhood
ontology_service.get_similar_classes(class_iri: str, limit: int = 10) -> List[SimilarClass] 
ontology_service.get_class_hierarchy(class_iri: str) -> Dict[str, List[URIRef]]

# Property Operations  
ontology_service.get_property_details(property_iri: str) -> OntologyProperty

# Semantic Concept Search
ontology_service.search_by_concept(concept_text: str) -> List[Dict[str, Any]]
# Multilingual similarity search across classes and properties

# LLM Integration
ontology_service.add_extraction_results(extracted_concepts: List[Dict[str, Any]]) -> bool
# Process LLM-extracted concepts with validation and IRI generation
```

**Domain Models Available:**
- `OntologyClass`: Complete class with labels, definitions, hierarchies, provenance
- `OntologyProperty`: Object/datatype properties with domain/range specifications  
- `ClassNeighborhood`: Class exploration with connected entities via properties
- `SimilarClass`: Semantic similarity scoring for concept discovery
- `OntologyStats`: Comprehensive ontology metrics and statistics

**Planned Future Extensions:**
- `ont.reason_rl() -> ReasonReport` (OWL-RL materialization)
- `ont.validate_shacl(shapes: PathLike) -> ShaclReport` (SHACL validation gates)
- `ont.apply_patch(patch: OntologyPatch) -> ApplyResult` (Structured ontology updates)
- `ont.serialize(path: PathLike, format: str = "turtle") -> None` (Graph serialization)

### 7.5 Orchestration

- `planner.step(state: PlannerState) -> PlannerDecision`
- `worker.execute(decision: PlannerDecision) -> WorkerResult`

---

## 8. LLM Extraction & Prompting

### 8.1 Inputs to the Extractor

- `element.summary` (high‑signal guidance)
- `element.summary_names` (extracted legal concepts and relationships for targeted extraction)
- `element.textContent` (authoritative evidence; may be sliced by fragment id or char offsets)
- `element.title`, `element.officialIdentifier`
- `neighbor_summaries[]` (parent, siblings, neighbors)
- `ontology_view` (labels/IRIs of related classes/properties already in the graph)

### 8.2 Output Contract

```json
{
  "classes": [{
    "candidate_iri": "ex:SilnicniVozidlo",
    "labels": {"cs": "Silniční vozidlo", "en": "Road vehicle"},
    "definition_cs": "...",
    "source": {"element": "IRI", "fragment": "f-12"},
    "relations": [{"type": "subClassOf", "target": "ex:Vozidlo"}],
    "confidence": 0.86
  }],
  "object_properties": [{
    "candidate_iri": "ex:maSystem",
    "labels": {"cs": "má systém"},
    "domain": "ex:Vozidlo",
    "range": "ex:SystemVozidla",
    "source": {"element": "IRI", "fragment": "f-37"},
    "confidence": 0.74
  }],
  "datatype_properties": [],
  "notes": "assumptions/ambiguities"
}
```

### 8.3 Prompt Scaffold (summary‑aware)

- **System:** “You are a legal ontology engineer. Use the **summary** to target likely concepts/relations. **Justify each proposal by quoting or citing spans** from `textContent` (fragment id/offsets). Output valid JSON only.”
- **Controls:** cap max candidates per element; require `source` for every assertion; encourage conservative domains/ranges.

---

## 9. Provenance & Promotion Workflow

### 9.1 Provenance

- For each triple or shape: attach `prov:wasDerivedFrom` with `{element IRI, fragment id or offsets}` and a `prov:Activity` record (tool, prompts, timestamps, model id, run id).

### 9.2 Gates & Publishing

1. **Extractor confidence** ≥ threshold.
2. **Reasoner** (OWL‑RL) finds no unsatisfiable classes.
3. **SHACL** passes (no `Violation` severities).
4. **ConflictCheck** resolved (no duplicate/contradictory labels without SKOS alignment).
5. **Impact** high? → require human approval; otherwise auto‑publish.

### 9.3 Run Ledger

- Persist agent decisions, retrieval hits, prompts, responses, SHACL/Reasoner reports, and ontology diffs; include hashes of `summary` and `textContent` used in each step.

---

## 10. Developer Guide

### 10.1 Project Layout

```
/agent/
  planner.py            # state machine & policies
  worker.py             # tool calls and side-effects
/index/                 # ✅ IMPLEMENTED - Iterations 1-5 + Architecture Refactoring
  __init__.py           # module initialization ✅
  domain.py             # IndexDoc, SearchQuery, SearchResult models ✅
  builder.py            # IndexBuilder interface, DocumentExtractor utilities ✅
  service.py            # IndexService unified interface ✅
  collection.py         # IndexCollection management ✅
  bm25.py               # BM25SummaryIndex implementation ✅
  bm25_full.py          # BM25FullIndex for full-text search ✅
  faiss_index.py        # FAISSSummaryIndex implementation ✅
  faiss_full.py         # FAISSFullIndex for semantic full-text ✅
  hybrid.py             # HybridSearchEngine with multiple fusion strategies ✅
  processor.py          # Document processing and chunking ✅
  registry.py           # Index type registry and factory ✅
  store.py              # Index storage and persistence ✅
  test_*.py             # comprehensive test coverage ✅
  demo_*.py             # demonstration scripts with real legal data ✅
/search/                # ✅ IMPLEMENTED - Unified Search Interface
  __init__.py           # module initialization ✅
  domain.py             # SearchStrategy, SearchOptions, SearchResults models ✅
  service.py            # SearchService unified interface ✅
  test_*.py             # comprehensive test coverage ✅
  demo_search_service.py # end-to-end search demonstration ✅
/llm/
  extractor.py          # JSON/function-call interface to the model
/ontology/              # ✅ IMPLEMENTED - Complete Ontology Module
  __init__.py           # module initialization ✅
  domain.py             # OntologyClass, OntologyProperty, ClassNeighborhood models ✅
  service.py            # OntologyService public interface ✅
  store.py              # OntologyStore RDF backend with semantic similarity ✅
  similarity.py         # SemanticSimilarity engine for concept discovery ✅
  test_domain.py        # domain model tests ✅
  test_service.py       # service interface tests ✅
  test_store.py         # store implementation tests ✅
  test_similarity.py    # similarity engine tests ✅
  demo_ontology_service.py # comprehensive workflow demonstration ✅
  # Future planned components:
  # shacl.py            # pySHACL validation runner
  # reason.py           # OWL-RL materializer  
  # patch.py            # OntologyPatch model & apply
/provenance/
  prov.py               # PROV-O recording
/legislation/           # ✅ IMPLEMENTED  
  __init__.py           # module initialization ✅
  domain.py             # LegalAct, LegalStructuralElement models ✅
  datasource.py         # data source interface ✅
  datasource_esel.py    # ESEL implementation ✅
  service.py            # high-level service operations ✅
  summarizer.py         # AI summarization and concept name extraction ✅
  test_*.py             # comprehensive test coverage ✅
/tests/
  unit/  integration/  e2e/
/config/
  settings.toml         # endpoint URLs, thresholds, model ids
/shapes/
  meta.ttl  domain.ttl  # Future SHACL shapes
/ontologies/
  working.ttl  published.ttl  prov.trig  # Future ontology serialization
```

### 10.2 Environment & Dependencies

**Core Requirements:**
- Python ≥ 3.11
- **RDF & Ontology**: `rdflib` (RDF graph management), `sentence-transformers` (semantic similarity)
- **Search & Indexing**: `numpy`, `faiss-cpu` (or GPU), `rank-bm25`, `scikit-learn`
- **Legal Text Processing**: Multilingual sentence transformers for Czech legal text
- **Data Models**: `pydantic`/`attrs` for typed domain models
- **HTTP & SPARQL**: HTTP client for SPARQL endpoints, `requests`
- **Performance**: `uvloop` (optional for async operations)

**Future Extensions:**
- **Validation**: `pyshacl` (SHACL validation), `owlrl` (OWL-RL reasoning)
- **LLM Integration**: Client SDK for LLM provider with JSON/function-calling support

**Current Implementation Dependencies:**
```
# Core ontology and similarity
rdflib>=7.0.0
sentence-transformers>=2.2.2  
numpy>=1.24.0

# Search and indexing  
faiss-cpu>=1.7.4
rank-bm25>=0.2.2
scikit-learn>=1.3.0

# Data processing
pydantic>=2.0.0
requests>=2.31.0

# Development and testing
pytest>=7.4.0
pytest-cov>=4.1.0
```

### 10.3 Configuration

**Data Sources:**
- **SPARQL**: endpoint URL, default graph(s), page size, timeouts
- **Legal Acts**: act repository, snapshot management, caching strategy

**Indexing & Search:**
- **Embedding Model**: `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions)
- **FAISS Parameters**: IndexFlatIP, cosine similarity, L2 normalization
- **BM25 Configuration**: field weights, tokenization, Czech text processing
- **Hybrid Search**: fusion strategies (RRF, weighted), strategy weights

**Ontology Management:**
- **Namespaces**: base URIs, standard ontology imports (OWL, RDFS, SKOS)
- **Similarity Thresholds**: concept matching, duplicate detection, classification
- **IRI Generation**: naming patterns, conflict resolution, versioning
- **Graph Storage**: working/published separation, serialization formats

**Agent Orchestration (Planned):**
- **Batch Processing**: sizes, max candidates, confidence thresholds
- **Retry Policy**: timeouts, backoff strategies, error handling
- **Quality Gates**: validation thresholds, approval workflows

**Validation & Reasoning (Planned):**
- **SHACL**: shape files, severity levels, custom constraints
- **OWL-RL**: reasoner configuration, materialization strategy
- **Provenance**: run ID strategy, log destinations, PII redaction

**Example Configuration:**
```toml
[ontology]
base_namespace = "https://example.org/ontology/"
similarity_threshold = 0.3
iri_generation_pattern = "camelCase"

[ontology.embeddings]
model_name = "paraphrase-multilingual-MiniLM-L12-v2"
dimensions = 384
cache_embeddings = true

[ontology.graphs]
working_graph_path = "ontologies/working.ttl"
published_graph_path = "ontologies/published.ttl"
serialization_format = "turtle"
```

### 10.4 Running an End‑to‑End Extraction

1. `service.get_legal_act(iri)` → assert summaries exist on elements (summarization is assumed complete beforehand).
2. `index.build(elements)` → produce BM25‑Summary and FAISS‑Summary bundles.
3. Start agent loop: `planner.step()` → `worker.execute()`.
4. On each iteration: retrieve elements (summary‑first), extract proposals (summary‑guided, text‑grounded), apply patch to **Working**, reason + SHACL, then publish or queue.
5. Serialize `working.ttl`, `published.ttl`, `prov.trig`; store reports and logs.

### 10.5 Observability & Logs

- Structured logs per step: timings, tokens, index hits, rejected proposals (with reasons), SHACL/Reasoner outcomes.
- Metrics: coverage (% elements processed), acceptance rate, avg confidence, CQ pass‑rate.

---

## 11. Testing & Quality Assurance

### 11.1 Implemented Testing Coverage

**✅ ONTOLOGY MODULE - Complete Test Coverage**
- **Domain Model Tests** (`test_domain.py`): Data structure validation, type checking, model construction
- **Service Interface Tests** (`test_service.py`): Public API contracts, error handling, integration workflows  
- **Store Implementation Tests** (`test_store.py`): RDF operations, CRUD functionality, persistence
- **Similarity Engine Tests** (`test_similarity.py`): Semantic matching, embedding computation, multilingual support
- **Integration Tests**: End-to-end workflows with real ontological concepts and relationships
- **Demo Validation**: Complete workflow demonstration from concept extraction to similarity analysis

**✅ INDEX & SEARCH MODULES - Comprehensive Testing**
- **Unit Tests**: 20+ test modules with 100% pass rate covering all index and search strategies
- **Integration Tests**: Real legal act data validation with Czech legal text (act 56/2001)
- **Performance Tests**: Response time validation, memory usage, index building performance
- **End-to-End Tests**: Complete search workflows from legal act loading to result ranking

**✅ LEGISLATION MODULE - Service Testing**
- **Service Contract Tests**: Legal act loading, element structure validation, summarization
- **Data Integration Tests**: ESEL datasource integration, real legal data processing
- **Concept Extraction Tests**: AI summarization, legal concept name extraction validation

### 11.2 Testing Strategy

**Unit Testing Principles:**
- **Service Contracts**: All public interfaces have contract tests validating inputs/outputs
- **Domain Model Integrity**: Type safety, validation rules, immutability constraints
- **Component Isolation**: Mocked dependencies, focused testing, clear failure attribution
- **Error Handling**: Exception paths, invalid input handling, graceful degradation

**Integration Testing Approach:**
- **Real Data Validation**: Czech legal act 56/2001 used across all modules
- **Cross-Module Integration**: Index ↔ Search ↔ Ontology ↔ Legislation workflows
- **Performance Validation**: Response times, memory usage, index building benchmarks
- **Consistency Checks**: Data integrity across module boundaries

**Future Testing Extensions:**
- **SHACL Validation Tests**: Meta-shapes, domain shapes, constraint validation
- **OWL-RL Reasoning Tests**: Consistency checking, inference validation, performance
- **Provenance Tests**: Fragment citation accuracy, source element tracing
- **End-to-End Agent Tests**: Complete extraction loops, quality gate validation

### 11.3 Quality Metrics

**Current Achievement:**
- **Ontology Module**: 4/4 test modules, 100% pass rate
- **Index/Search Modules**: 20+ test modules, 100% pass rate  
- **Legislation Module**: Complete service testing with real data
- **Overall Test Coverage**: >90% line coverage across implemented modules

**Quality Gates:**
- All public interfaces have comprehensive contract tests
- Real legal data validation in integration tests
- Performance benchmarks for all search operations
- Type safety enforcement with comprehensive domain models

**Future Quality Targets:**
- **Coverage Metrics**: % elements processed, acceptance rate, confidence distribution
- **Validation Metrics**: SHACL pass-rate, OWL-RL consistency, provenance completeness
- **Competency Questions**: CQ set definition, SPARQL translation, pass-rate tracking
- **Performance SLAs**: Response time targets, memory usage limits, throughput requirements

---

## 12. Performance & Scaling

- Prefer **summary‑only** retrieval for candidate selection; fetch `textContent` slices on demand for grounding.
- Use FAISS IVF+PQ for large corpora; shard by act.
- Cache neighbor summaries; limit LLM calls per iteration; backoff on rate limits.

---

## 13. Security & Privacy

- Secrets in env vars; no logs of raw credentials.
- PII redaction pass (if elements can carry personal data in annexes/examples).
- Provenance records exclude raw secret values; store model ids and hashes only.

---

## 14. Roadmap & Milestones

### Completed Milestones ✅

**M1 - Foundation Infrastructure (COMPLETED)**
- Wire service + confirm summaries ✅
- Build summary‑first indexes (BM25 + FAISS semantic) ✅  
- Baseline retrieval quality with hybrid search strategies ✅
- Unified IndexService and SearchService interfaces ✅
- Full-text indexing with hierarchical chunking ✅
- Architecture refactoring with clean separation of concerns ✅

**M2 - Ontology Framework (COMPLETED)**
- Complete ontology module with OntologyService public interface ✅
- RDF store with working/published graph separation ✅
- Semantic similarity engine for concept discovery ✅
- Domain models for classes, properties, neighborhoods ✅
- LLM extraction integration with validation ✅
- Comprehensive testing and demonstration ✅

**M3 - Legislation Integration (COMPLETED)**
- Legal act loading and structural element processing ✅
- AI summarization with concept name extraction ✅
- ESEL datasource integration ✅
- Service layer for unified legislation operations ✅
- Real legal data validation (Czech act 56/2001) ✅

### Current Status: Foundation Complete

**Core Infrastructure**: All fundamental modules implemented and tested
- **Legislation Module**: Complete legal act processing and summarization
- **Index/Search Module**: Advanced hybrid search with 8 different strategies  
- **Ontology Module**: Practical ontology management with semantic similarity
- **Integration**: Seamless coordination between all modules

**Ready for Agent Development**: Foundation infrastructure supports:
- Legal act loading and processing
- Advanced concept-based search and retrieval
- Ontology creation and management with LLM integration
- Semantic similarity for concept discovery and relationship inference

### Next Phase Milestones

**M4 - Agent Architecture (PLANNED)**
- Planner state machine with element selection strategies
- Worker implementation with tool integration  
- LLM extractor with structured JSON output contracts
- Agent orchestration with batch processing and retry logic

**M5 - Validation & Publishing (PLANNED)**
- SHACL meta-shapes and domain constraint validation
- OWL-RL reasoning for consistency checking
- Quality gates with automated and manual approval workflows
- Ontology patch system with structured updates

**M6 - Provenance & Auditing (PLANNED)** 
- PROV-O recording for complete audit trails
- Fragment-level citation and source element tracking
- Run ledger with decision logging and metrics
- Competency Question (CQ) framework and validation

**M7 - Production Features (PLANNED)**
- Performance optimization: caching, batching, parallel processing
- Metrics dashboard and monitoring
- Multi-act coordination and cross-act alignment
- Human review interface for queued extractions

### Development Priorities

**Immediate Next Steps:**
1. **LLM Extractor**: Structured JSON extraction with confidence scoring
2. **Agent Planner**: State machine for element selection and processing
3. **Agent Worker**: Tool integration and side-effect management
4. **Basic Validation**: SHACL meta-shapes and consistency checking

**Foundation Strengths:**
- **Robust Infrastructure**: All core modules implemented and tested
- **Real Data Validation**: Proven with Czech legal act 56/2001
- **Clean Architecture**: Unified interfaces and separation of concerns  
- **Semantic Capabilities**: Advanced similarity and concept discovery
- **Performance Validated**: Sub-second search, efficient indexing
- **M5**: Multi‑act runs; alignment across acts; reviewer UI for queued items.

---

## 15. Junior Developer Playbook (Step‑by‑Step)

> A practical, incremental path to a demo with clear acceptance criteria.

### 15.1 Milestones & DoD

- **M0 — Bootstrap (0.5 day)**: Run `service.get_legal_act(iri)`, print tree, verify summaries. **DoD:** non‑empty titles & summaries on multiple levels.
- **M1 — Indexing (2 days)**: Build BM25‑Summary & FAISS‑Summary; CLI search (e.g., “Základní pojmy”). **DoD:** relevant sections bubble to top.
- **M2 — Ontology skeleton (2 days)**: Create working/published/prov graphs; SHACL meta file; validate empty graph. **DoD:** zero violations.
- **M3 — LLM Extractor (3 days)**: Return structured JSON with `source.element` + `fragment/offsets`. **DoD:** at least one class proposal on a definition section.
- **M4 — Apply + Validate (3 days)**: Convert proposal → patch; apply to working; reason & SHACL. **DoD:** readable validation reports, prov entries per triple.
- **M5 — Planner Loop (3 days)**: Wire planner/worker; run N iterations; publish gated results. **DoD:** non‑trivial published classes/properties with provenance.
- **M6 — CQs & Demo (2 days)**: 10 CQs + CLI target. **DoD:** ≥6 CQs return results.

### 15.2 Detailed Tasks & Gotchas

- **T1 Flatten Elements:** Build `IndexDoc` list with `{element_id,title,officialIdentifier,summary,textContent?,level}`. *Gotcha:* preserve `<f id>` fragments in raw text.
- **T2 BM25‑Summary:** weight summary>title>identifier. *Gotcha:* diacritics/tokenization for Czech.
- **T3 FAISS‑Summary:** vectors on `summary` or `title+summary`. *Gotcha:* persist with snapshot id.
- **T4 Search API:** `index.search_summary(query,k,filters)`; filter by level/regex `^§`.
- **T5 Graphs & Prefixes:** three RDFLib graphs; one prefix map.
- **T6 SHACL Meta:** require `skos:prefLabel@cs` for classes; domain/range for properties.
- **T7 Extractor:** input: summary + text slice + neighbor summaries + ontology view; output: JSON with `source` for every item. *Gotcha:* never cite only summaries.
- **T8 Patch & Apply:** deterministic IRIs; attach `prov:wasDerivedFrom` (element + fragment/offsets).
- **T9 Validation Gate:** run OWL‑RL + SHACL; reject on `Violation` or unsats; optionally call `llm.refine_for_shacl`.
- **T10 Publish/Queue:** promote when gates pass; otherwise queue with reports.

### 15.3 Reference Contracts & Pseudocode

**Types**

```python
class ElementRef(TypedDict):
    element_id: str
    score: float
    level: str
    title: str
    officialIdentifier: str

class ExtractionProposal(TypedDict):
    classes: list[dict]
    object_properties: list[dict]
    datatype_properties: list[dict]
    notes: str | None

class OntologyPatch(TypedDict):
    entities: list[dict]
    axioms: list[dict]
    provenance: list[dict]
```

**Planner loop (sketch)**

```python
def loop(act_iri: str, max_iters: int = 50):
    act = service.get_legal_act(act_iri)
    idx = index.build(act.elements)
    for _ in range(max_iters):
        targets = index.search_summary("definitions OR rozumí se", k=5, filters={"level": "Section"})
        for ref in targets:
            el = service.get_element(ref.element_id)
            neighbors = get_neighbor_summaries(el)
            proposal = llm.extract(el, neighbors, ontology_view=ont.snapshot_view(), schema=EXTRACT_SCHEMA)
            patch = to_patch(proposal)
            ont.apply_patch(patch)
            reason = ont.reason_rl()
            shacl = ont.validate_shacl("shapes/meta.ttl")
            if gate_ok(proposal, reason, shacl):
                publisher.promote()
            else:
                queue_for_review(proposal, reason, shacl)
```

**Gate function (sketch)**

```python
def gate_ok(proposal, reason_report, shacl_report, conf=0.7):
    min_conf = min([c.get("confidence", 1.0) for c in proposal.get("classes", [])] + [1.0])
    return (
        min_conf >= conf and not reason_report.unsatisfiable and shacl_report.max_severity < VIOLATION and not has_conflicts(proposal)
    )
```

### 15.4 Runbooks & Prompts

**Quick start**

1. Set `ACT_IRI` in `.env` → `python -m service.print_act $ACT_IRI` (verify summaries).
2. `python -m index.build $ACT_IRI` → build BM25+FAISS.
3. `python -m agent.run $ACT_IRI --iters 20` → run the loop.
4. Inspect `ontologies/working.ttl`, `published.ttl`, `prov.trig`.

**Extractor — System prompt**

```
You are a legal ontology engineer. Use the element summary to focus, but justify every proposal by quoting or citing spans from `textContent`. Return ONLY JSON matching the provided schema. Include `source.element` and a `fragment` id or character `offsets` for each item. Be conservative with domains/ranges. Do not invent entities.
```

**Extractor — User template**

```
ELEMENT
- id: {element.id}
- officialIdentifier: {element.officialIdentifier}
- title: {element.title}
- summary: {element.summary}
- summary_names: {element.summary_names}
- textContent (slice):
{slice_text}

NEIGHBOR SUMMARIES
{neighbor_summaries}

EXISTING ONTOLOGY VIEW (labels only)
{ontology_view}

OUTPUT SCHEMA
{EXTRACT_SCHEMA_JSON}
```

**Refinement template (on SHACL errors)**

```
The previous proposal caused these SHACL errors:
{shacl_errors}

Please adjust ONLY the problematic items so that:
- every property has domain and range consistent with the classes provided
- no cardinality conflicts are introduced
- keep the original sources and labels
Return ONLY JSON per schema.
```

### 15.5 Acceptance Checklists & First Tickets

**Module DoD**

- Indexing deterministic; persisted with snapshot id; CLI works.
- Extractor never omits `source`; JSON validates.
- Ontology prefixes correct; apply idempotent.
- SHACL meta passes on empty graphs; violations are actionable.
- Planner loop saves cursor; metrics emitted.

**First tickets**

1. Build `IndexDoc` builder. 2. BM25‑Summary + CLI. 3. FAISS‑Summary + persistence. 4. Graphs & prefixes. 5. SHACL meta shapes. 6. Extractor JSON. 7. Patch writer + PROV. 8. Gate & reason/validate. 9. Planner loop. 10. CQ CLI.

---

## Appendix A: JSON Schemas

### A.1 StructuralUnit (canonical)

```json
{
  "unit_id": "string",
  "unit_type": "string",
  "title": "string",
  "officialIdentifier": "string",
  "summary": "string | null",
  "text": "string | null",
  "position": { "level": "Part|Chapter|...", "index": 0 },
  "citations": [{ "target": "string", "type": "internal|external" }],
  "source": { "graph": "string", "doc": "string" }
}
```

### A.2 ExtractionProposal

```json
{
  "classes": [ { "candidate_iri": "string", "labels": {"cs": "string", "en": "string"}, "definition_cs": "string", "source": {"element": "IRI", "fragment": "string"}, "relations": [ {"type": "subClassOf", "target": "string"} ], "confidence": 0.0 } ],
  "object_properties": [ { "candidate_iri": "string", "labels": {"cs": "string"}, "domain": "string", "range": "string", "source": {"element": "IRI", "fragment": "string"}, "confidence": 0.0 } ],
  "datatype_properties": [ /* ... */ ],
  "notes": "string"
}
```

### A.3 OntologyPatch (write contract)

```json
{
  "entities": [ { "iri": "string", "type": "Class|ObjectProperty|DatatypeProperty", "labels": {"cs": "string", "en": "string"}, "comment_cs": "string" } ],
  "axioms": [ { "subject": "string", "predicate": "string", "object": "string" } ],
  "provenance": [ { "triple": 0, "element": "IRI", "fragment": "string", "activity": "uuid" } ]
}
```

---

## Appendix B: SHACL Shape Starters

- **Meta**: every `owl:Class` must have `skos:prefLabel@cs`; every property must have `rdfs:domain` and `rdfs:range`.
- **Domain** (vehicle illustration): `RoadVehicle` exactly one `hasCategory`; `TestingStation` at least one `Accreditation`; `TypeApproval` at least one `ApprovalCertificate`.

---

## Appendix C: Competency Question (CQ) Starters

- Which vehicle categories exist and what are their formal definitions?
- What processes and authorities are involved in type approval?
- What obligations fall on the vehicle operator before operation on public roads?

---

## Appendix D: Error Handling & Retry Policy

- **SPARQL/Service**: exponential backoff; page size fallback; circuit breaker on sustained errors.
- **LLM**: timeout + limited retries; cache identical prompts; drop to partial results on repeated failures.
- **Index**: rebuild on checksum mismatch; guard against empty fields.
- **Ontology writes**: transactional apply; rollback on SHACL `Violation` or reasoning unsat.

---

## Appendix E: Glossary

- **Element summary**: concise bottom‑up synopsis of an element’s meaning/obligations.
- **Fragment**: addressable subsection of `textContent` (e.g., `<f id>`), used in provenance.
- **Working/Published graph**: staging vs. released ontology graphs.
- **CQ**: competency question; SPARQL‑expressible test of ontology utility.

