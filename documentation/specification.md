# The Agentic Ontology Builder (AOB)

The Agentic Ontology Builder (AOB) loads a **structured legal act** from our service (SPARQL‑backed), uses **summary‑first retrieval** to target the most informative elements, invokes an **LLM extractor** to propose classes/properties/axioms **grounded in the act's exact text**, validates proposals with **SHACL** and **OWL‑RL reasoning**, and then **publishes** accepted axioms into a versioned **Published** ontology graph with complete **PROV‑O provenance**. It operates in small, auditable iterations (plan → extract → validate → publish) and supports human review where needed.

---

## 0. Big Picture — What We’re Building & Core Principles

### 0.1 One‑paragraph overview

The Agentic Ontology Builder (AOB) loads a **structured legal act** from our service (SPARQL‑backed), uses **summary‑first retrieval** to target the most informative elements, invokes an **LLM extractor** to propose classes/properties/axioms **grounded in the act’s exact text**, validates proposals with **SHACL** and **OWL‑RL reasoning**, and then **publishes** accepted axioms into a versioned **Published** ontology graph with complete **PROV‑O provenance**. It operates in small, auditable iterations (plan → extract → validate → publish) and supports human review where needed.

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
|  (BM25 + FAISS)   |     |Planner+ |     | (JSON proposals)  |
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
  - **Indexes** (BM25/FAISS) tied to the act snapshot; **run logs** and metrics.
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
2. Build **summary‑first** lexical and vector indexes over elements.
3. Agent **Planner** selects candidate elements; **Worker** retrieves context and calls **LLM Extractor**.
4. Proposed classes/properties/axioms are checked for conflicts, validated with **SHACL**, and materialized under **OWL‑RL**.
5. If all gates pass, publish to the **Published** ontology graph; otherwise, queue for review.
6. Persist **PROV** for every change with references to element IRIs and fragment/offsets.

**Core artifacts:** Working, Published, and Provenance graphs (Turtle & TriG); index bundles (BM25 + FAISS) tied to an act snapshot; validation reports (SHACL), reasoner summaries, and agent run logs.

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

### 4.2 BM25 Implementation

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

### 4.3 FAISS Implementation

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

### 4.3 Indexes

- **BM25‑Summary (primary):** ✅ IMPLEMENTED - index `summary_names^5 + summary^3 + title^2 + officialIdentifier^1` with concept-enhanced search.
- **BM25‑Full (optional):** TODO - include `textContent` for exact‑phrase lookups (e.g., "rozumí se", "musí", "je povinen").
- **FAISS‑Summary (primary):** ✅ IMPLEMENTED - multilingual embeddings on `summary` (or `title + summary`) with semantic search capabilities.
- **FAISS‑Full (optional):** TODO - embeddings over token‑bounded `textContent` slices for deeper recall.

### 4.4 Document Model

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

### 4.5 Retrieval Strategy

- Default queries → FAISS‑Summary for semantic breadth → re‑rank with BM25‑Summary for keyword precision.
- **Concept-based queries** → leverage `summary_names` highest weight (5x) for precise legal concept matching.
- **Semantic queries** → use FAISS embeddings for conceptual understanding beyond exact keyword matches.
- **Multilingual support** → FAISS handles cross-language queries (English queries finding Czech content).
- For targeted phrases → constrain/re‑rank with BM25‑Full.
- Add structural filters (type/level or `officialIdentifier` regex like `^§`).
- **Document similarity** → use FAISS `get_similar_documents()` for finding related legal provisions.

### 4.5 Caching & Versioning

- Index keys encode the act snapshot id so re‑indexing triggers automatically on updates.

---

## 5. Ontology Store, Modeling, & Validation

### 5.1 Namespaces

`ex:` (project base), `owl:`, `rdfs:`, `xsd:`, `skos:`, `sh:`, `prov:`, `eli:`.

### 5.2 Modeling Conventions

- **Classes**: legal categories, defined terms, roles, statuses.
- **Object properties**: relations among domain entities (e.g., `máSystém`).
- **Datatype properties**: identifiers, codes, literal attributes.
- **Labels**: `skos:prefLabel@cs` mandatory; `skos:altLabel` for synonyms; `rdfs:comment` for definition notes and citations.
- **Axioms**: add `rdfs:domain`/`rdfs:range`, `rdfs:subClassOf`, and `owl:disjointWith` when explicitly supported by text.

### 5.3 Graphs & Files

- **Working** graph: draft assertions under review.
- **Published** graph: validated and approved ontology.
- **Provenance** graph: PROV‑O activities linking each assertion to its source element and span.
- Serialize as Turtle; keep named graphs in TriG when helpful.

### 5.4 Reasoning & Validation

- **Reasoning**: OWL 2 RL materialization for performance and predictable semantics.
- **Validation**: SHACL gates — meta (labels & domain/range) and domain shapes (obligations/cardinalities extracted from text).

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

- `service.get_legal_act(iri: str) -> LegalAct`
- `service.get_element(iri: str) -> LegalStructuralElement`

### 7.2 Indexing

- `index.build(elements: Iterable[LegalStructuralElement], fields: Mapping) -> IndexBundle`
- `index.search_summary(query: str, k: int, filters: dict | None = None) -> list[ElementRef]`
- `index.search_semantic(query: str, k: int, filters: dict | None = None) -> list[ElementRef]`  # ✅ FAISS
- `index.get_similar_documents(element_id: str, k: int) -> list[ElementRef]`  # ✅ FAISS similarity
- `index.search_fulltext(query: str, k: int, filters: dict | None = None) -> list[ElementRef]`

### 7.3 LLM Extraction

- `llm.extract(element: LegalStructuralElement, neighbors: list[LegalStructuralElement], ontology_view: OntologyView, schema: JsonSchema) -> ExtractionProposal`
- `llm.refine_for_shacl(proposal: ExtractionProposal, shacl_report: ShaclReport) -> ExtractionProposal`

### 7.4 Ontology Operations

- `ont.search_labels(query: str, limit: int = 50) -> list[OntologyMatch]`
- `ont.apply_patch(patch: OntologyPatch) -> ApplyResult`
- `ont.reason_rl() -> ReasonReport`
- `ont.validate_shacl(shapes: PathLike) -> ShaclReport`
- `ont.serialize(path: PathLike, format: str = "turtle") -> None`

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
/index/                 # ✅ IMPLEMENTED - Iterations 1-3
  __init__.py           # module initialization ✅
  domain.py             # IndexDoc, SearchQuery, SearchResult models ✅
  builder.py            # IndexBuilder interface, DocumentExtractor utilities ✅
  build.py              # CLI for building BM25/FAISS indexes ✅
  search.py             # CLI for searching indexes ✅
  bm25.py               # BM25 index implementation ✅
  faiss_index.py        # FAISS index implementation ✅
  hybrid.py             # hybrid search strategy (TODO - Iteration 4)
  test_domain.py        # unit tests for domain models ✅
  test_integration.py   # integration tests ✅
  test_bm25.py          # BM25 implementation tests ✅
  test_faiss.py         # FAISS implementation tests ✅
  demo.py               # basic indexing demo ✅
  demo_bm25.py          # BM25 functionality demo ✅
  demo_bm25_56_2001.py  # BM25 real data demo ✅
  demo_faiss_56_2001.py # FAISS real data demo ✅
  ITERATION_2_SUMMARY.md # BM25 completion summary ✅
  ITERATION_3_SUMMARY.md # FAISS completion summary ✅
/llm/
  extractor.py          # JSON/function-call interface to the model
/ontology/
  store.py              # RDFLib graphs, serialization
  shacl.py              # pySHACL runner
  reason.py             # OWL-RL materializer
  patch.py              # OntologyPatch model & apply
/provenance/
  prov.py               # PROV-O recording
/legislation/           # ✅ IMPLEMENTED
  __init__.py           # module initialization
  domain.py             # LegalAct, LegalStructuralElement models
  datasource.py         # data source interface
  datasource_esel.py    # ESEL implementation
  service.py            # high-level service operations
  summarizer.py         # AI summarization and concept name extraction
  test_service.py       # service tests
```
  cache.py              # snapshots of acts and elements
/tests/
  unit/  integration/  e2e/
/config/
  settings.toml         # endpoint URLs, thresholds, model ids
/shapes/
  meta.ttl  domain.ttl
/ontologies/
  working.ttl  published.ttl  prov.trig
```

### 10.2 Environment & Dependencies

- Python ≥ 3.11
- Core: `rdflib`, `pyshacl`, `owlrl`, `numpy`, `faiss-cpu` (or GPU), `rank-bm25`/`whoosh` or Elasticsearch client, `pydantic`/`attrs` for models, `uvloop` (optional), HTTP client for SPARQL.
- LLM: client SDK for your provider; support JSON/function‑calling.

### 10.3 Configuration

- **SPARQL**: endpoint URL, default graph(s), page size, timeouts.
- **Index**: embedding model name, vector dim, FAISS params (IVF, PQ), BM25 backend.
- **Agent**: batch sizes, max candidates, confidence thresholds, retry policy, timeouts.
- **Validation**: SHACL shape files; reasoner toggle.
- **Provenance**: run id strategy; log destinations; PII redaction toggle.

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

- **Unit tests**: service contracts (elements & summaries), index determinism, ontology patcher (idempotence), SHACL meta‑shapes.
- **Integration tests**: extraction on definition‑dense sections; ensure provenance cites fragment ids/offsets.
- **End‑to‑end**: run full loop on one act; assert no SHACL violations, no unsats, and minimal duplicate labels.
- **Competency Questions**: define CQ set; translate to SPARQL; track pass‑rate per build.

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

- **M1**: Wire service + confirm summaries; build summary‑first indexes (BM25 + FAISS semantic); baseline retrieval quality. ✅ COMPLETED
- **M2**: Ontology skeleton + meta SHACL; first extraction on definitions; provenance end‑to‑end.
- **M3**: Processes/roles; domain SHACL; auto‑publish gates; CQ harness.
- **M4**: Re‑ranking, batching, and caching for throughput; dashboard for metrics.
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

