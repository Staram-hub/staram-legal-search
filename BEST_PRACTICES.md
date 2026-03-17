# Best Practices — Multi-Agent Legal Research with Google ADK

This document covers the architectural decisions, prompt engineering patterns, and operational learnings from building this multi-agent legal research system.

## 1. Architecture Patterns

### Why Multi-Agent over Single-Agent

A single agent handling discovery, retrieval, and composition tends to lose focus on longer queries. By splitting into specialized agents, each one has a narrow, well-defined task with its own tools and instructions. This produces significantly better results because each agent operates within a focused context window rather than juggling everything at once.

The three-phase design (discover → retrieve → compose) mirrors how a human legal researcher works: first identify relevant sources, then gather the material, then write the opinion.

### Sequential + Parallel Composition

The pipeline uses ADK's `SequentialAgent` and `ParallelAgent` primitives:

```
SequentialAgent [
    Discovery Agent              # Phase 1: find relevant Acts/nodes
    ParallelAgent [              # Phase 2: retrieve in parallel
        Legislation Agent        #   statutory content from Neo4j
        Caselaw Agent            #   case law from Neo4j + Weaviate
    ]
    Composer Agent               # Phase 3: synthesize final output
]
```

Legislation and caselaw retrieval are independent operations that each take 5-15 seconds. Running them in parallel cuts total latency nearly in half. If you have additional data sources (regulatory guidance, secondary commentary, international law), add them as parallel sub-agents in Phase 2. The composer will see all results in shared state.

### Head Agent as Router

The `legal_head_agent` sits above the pipeline as a router. It classifies queries first, then decides whether to invoke the full pipeline or respond directly (for non-legal queries). This avoids wasting pipeline resources on greetings or off-topic questions.

---

## 2. Knowledge Graph Design

The Neo4j knowledge graph models legislation as a tree:

```
Act
├── Chapter / Part        (structural groupings)
│   ├── Section           (citable legal provisions)
│   │   ├── SubSection    (specific clauses)
│   │   └── Paragraph     (granular text)
├── Concept               (semantic tags)
├── Amendments_and_Repeals
├── Key_Dates
├── Definitions_and_Terms
├── Procedural_Steps
├── Regulatory_Bodies
├── Eligibility_Criteria
└── Judicial_Precedents
```

Key design principles:

**Separate structural and semantic nodes.** Structural nodes (Act → Chapter → Section) represent the legal text hierarchy. Semantic nodes (Concept, Procedural_Steps, etc.) represent extracted knowledge. This allows querying by structure ("get Section 10 of this Act") and by meaning ("find all provisions about penalties") independently.

**Use full-text indices for discovery.** The `actTitleIndex` and `ruleTitleIndex` full-text indices enable fast keyword-based discovery without embedding overhead — the right choice for the first phase where you need broad coverage, not precision.

**Path filtering prevents cross-contamination.** The Cypher queries use `NONE(x IN nodes(p)[1..-1] WHERE x:Act OR x:Rule)` to ensure traversal paths don't accidentally cross from one Act into another through shared intermediate nodes.

---

## 3. Vector Search Strategy

### FIRAC-Based Embeddings

Case law is embedded using the FIRAC framework — each case is split into five components (Facts, Issues, Rules, Analysis, Conclusion), and each component is embedded separately. This allows targeted similarity search: "find cases with similar facts" vs. "find cases with similar legal reasoning."

### Court Hierarchy in Search

The Weaviate database is split into three collections by court tier: Supreme Court (SC), High Courts (HC), and Others. All three are queried in parallel and results are merged with SC prioritized over HC, and HC over Others. Within the same tier, results are sorted by embedding distance.

### Hybrid Search Pattern

Caselaw retrieval uses a two-step hybrid approach:

1. **Graph-based filtering:** Neo4j identifies cases that reference specific sections of Acts.
2. **Semantic ranking:** Weaviate ranks the filtered cases by embedding similarity to the query keywords.

This combination is more effective than pure semantic search (which may return unrelated but linguistically similar cases) or pure graph traversal (which misses semantically relevant cases not explicitly linked to the sections).

---

## 4. Prompt Engineering

### General Principles

**Be specific about output format.** Agents work best when the expected output structure is explicitly defined. Include JSON schemas, markdown templates, or worked examples in the prompt.

**Tell agents what NOT to do.** Negative instructions ("Do not answer from your own knowledge," "Do not cite overruled cases") are as important as positive ones. LLMs default to helpfulness, which can mean hallucinating content when retrieval returns nothing.

**Use state keys as a contract.** Each agent writes to specific state keys (e.g., `discovery_findings`, `legislation_sources`, `caselaw_sources`). Document these in the prompt so the agent knows exactly what downstream agents expect.

### Prompt Constants Reference

**`agentic_prompts.py`:**

| Constant | Controls |
|---|---|
| `HEAD_AGENT_INSTRUCTION` | Query routing — when to use pipeline vs. respond directly |
| `DISCOVERY_AGENT_INSTRUCTION` | Act/node discovery — keyword extraction, node selection |
| `LEGISLATION_RESEARCH_INSTRUCTION_TEMPLATE` | Statutory retrieval — when to fetch rules, subsection depth |
| `CASELAW_RESEARCHER_INSTRUCTION_TEMPLATE` | Case law retrieval — court filters, similarity type |
| `LEGAL_REPORT_COMPOSER_INSTRUCTION` | Final synthesis — tone, depth, citation format |

**`prompts.py`:**

| Constant | Controls |
|---|---|
| `system_prompt_classify_user_query` | Query type classification (Types 1–4) |
| `caselaw_instructions_v3` | Caselaw resolution rules and court hierarchy |

### What Worked Well

- Chain-of-thought in the discovery agent (explain keyword reasoning before searching) improved Act selection accuracy.
- Few-shot examples in the classification prompt reduced misclassification between Type 2 and Type 4.
- Explicit citation rules for the composer ("only cite sources present in the provided research data") reduced hallucinated citations.
- Temperature 0 across all agents — legal research requires deterministic, reproducible outputs.

---

## 5. Agent Pipeline Design

### Callbacks as Glue

The pipeline uses ADK's `after_agent_callback` to extract structured data from one phase and prepare state for the next. This is preferable to having agents pass data through their text output because it avoids JSON parsing errors from LLM output, allows tools to write directly to state via `ToolContext`, and keeps agent instructions focused on reasoning rather than data formatting.

Key patterns:

- Always handle missing/malformed state gracefully. The `discovery_callback` sets empty defaults if no findings exist.
- Parse JSON defensively. LLMs sometimes wrap JSON in markdown code blocks. The `_parse_json_from_string` helper handles this.
- Log extensively in callbacks — they're the hardest part to debug because they run between agent turns.

### Tools Writing to State

Agent tools use `ToolContext` to write results directly to shared state. This preserves full data fidelity (no LLM summarization/loss) and lets the agent's output focus on reasoning rather than data relay.

---

## 6. State Management

| Key | Written By | Read By |
|---|---|---|
| `discovery_findings` | Discovery Agent (output_key) | discovery_callback |
| `act_list` | discovery_callback | Legislation Agent |
| `node_ids` | discovery_callback | Legislation Agent |
| `section_ids` | discovery_callback | Legislation + Caselaw Agents |
| `legislation_nodes_data` | Legislation tools (ToolContext) | legislation_callback |
| `legislation_sources` | legislation_callback | Composer Agent |
| `caselaw_section_data` | Caselaw tools (ToolContext) | caselaw_callback |
| `caselaw_keyword_data` | Caselaw tools (ToolContext) | caselaw_callback |
| `caselaw_sources` | caselaw_callback | Composer Agent |
| `query_type` | Head Agent | Caselaw Agent, Composer |
| `output_format` | Head Agent | Composer |
| `final_legal_opinion` | Composer (output_key) | citation_callback |
| `formatted_legal_opinion` | citation_callback | ADK UI / API consumer |

State should be treated as append-only. Tools extend existing state lists (`existing.extend(result)`) rather than replacing them, so multiple tool calls within the same agent turn accumulate correctly.

---

## 7. Performance & Reliability

**Connection pooling:** Neo4j uses a singleton async driver per `(uri, user)` pair (`neo4j_connection_pool.py`). Weaviate uses a module-level singleton with lazy connection. Both avoid creating and tearing down connections on every tool call.

**Timeouts:** Neo4j queries default to 120 seconds. Important for full-text searches on large indices.

**Parallel Weaviate queries:** All three court-tier collections are searched in parallel via `asyncio.gather()` — roughly 3x faster than sequential and safe because each collection query is independent.

**Error handling:** Tools return descriptive error messages rather than raising exceptions, so the agent can decide how to proceed. Callbacks handle `None` and empty state gracefully.

---

## Further Reading

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/)
- [Weaviate Documentation](https://weaviate.io/developers/weaviate)
- [FIRAC Framework](https://en.wikipedia.org/wiki/IRAC)
