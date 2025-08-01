# Agentic Ontology Extraction — Unified Full Spec & Developer Guide

---

## 0. Big Picture — What We’re Building & Core Principles

### 0.1 One‑paragraph overview

The **Agentic Ontology Builder (AOB)** loads a **structured legal act** from our service (SPARQL‑backed), uses **summary‑first retrieval** to target the most informative elements, invokes an **LLM extractor** to propose classes/properties/axioms **grounded in the act’s exact text**, validates proposals with **SHACL** and **OWL‑RL reasoning**, and then **publishes** accepted axioms into a versioned **Published** ontology graph with complete **PROV‑O provenance**. It operates in small, auditable iterations (plan → extract → validate → publish) and supports human review where needed.

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

## 1. Objectives & Non‑Goals

### Objectives

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
  "textContent": "string | null",    // may include hierarchical fragments (e.g., <f id="..."> ... </f>)
  "elements": [ /* recursive LegalStructuralElement */ ]
}
```

**Notes:** Use `id` IRIs directly for addressing and provenance; when `textContent` carries fragment identifiers (e.g., `<f id>`), cite fragment ids or character offsets in provenance.

---

## 4. Indexing & Retrieval

### 4.1 Indexes

- **BM25‑Summary (primary):** index `summary^3 + title^2 + officialIdentifier^1`.
- **BM25‑Full (optional):** include `textContent` for exact‑phrase lookups (e.g., “rozumí se”, “musí”, “je povinen”).
- **FAISS‑Summary (primary):** multilingual embeddings on `summary` (or `title + summary`).
- **FAISS‑Full (optional):** embeddings over token‑bounded `textContent` slices for deeper recall.

### 4.2 Retrieval Strategy

- Default queries → FAISS‑Summary for breadth → re‑rank with BM25‑Summary for precision.
- For targeted phrases → constrain/re‑rank with BM25‑Full.
- Add structural filters (type/level or `officialIdentifier` regex like `^§`).

### 4.3 Caching & Versioning

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

- **SelectElements**: rank by FAISS‑Summary; re‑rank by BM25‑Summary; prefer short text + rich summary.
- **RetrieveContext**: gather parent/preceding/following **summaries** for scope without token bloat.
- **ExtractCandidates**: provide `summary` as guide and `textContent` (or fragment slices) as evidence; provenance must cite text.
- **ConflictCheck**: cluster by normalized label; compare summaries to detect near‑duplicate concepts; propose SKOS mappings.

---

## 7. Tooling Interfaces (Capabilities)

> **Note:** Signatures are indicative; implement as typed Python functions/classes.

### 7.1 Source & Service

- `service.get_legal_act(iri: str) -> LegalAct`
- `service.get_element(iri: str) -> LegalStructuralElement`

### 7.2 Indexing

- `index.build(elements: Iterable[LegalStructuralElement], fields: Mapping) -> IndexBundle`
- `index.search_summary(query: str, k: int, filters: dict | None = None) -> list[ElementRef]`
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
/index/
  build.py              # create BM25/FAISS indexes from elements
  search.py             # summary/fulltext queries
/llm/
  extractor.py          # JSON/function-call interface to the model
/ontology/
  store.py              # RDFLib graphs, serialization
  shacl.py              # pySHACL runner
  reason.py             # OWL-RL materializer
  patch.py              # OntologyPatch model & apply
/provenance/
  prov.py               # PROV-O recording
/service/
  service.py            # access to legal act & elements (SPARQL-backed)
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

- **M1**: Wire service + confirm summaries; build summary‑first indexes; baseline retrieval quality.
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

