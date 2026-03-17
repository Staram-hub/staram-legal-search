# Staram Legal Search — Multi-Agent Legal Research with Google ADK

A multi-agent AI system for legal research, built on [Google's Agent Development Kit (ADK)](https://google.github.io/adk-docs/). It combines a Neo4j knowledge graph, Weaviate vector database, and multiple LLM providers to deliver structured legal opinions with citations.

This repository is published for **research and reference purposes**.

**Architecture:** Head Agent → SequentialAgent [ Discovery → ParallelAgent [ Legislation Research, Caselaw Research ] → Report Composer ]

## What This Project Does

Given a natural language legal query, the system:

1. **Classifies** the query into one of four types (interpretation, judgment analysis, fact-law synthesis, or statutory + case law synthesis).
2. **Discovers** relevant Acts and legislation nodes via full-text search on a Neo4j knowledge graph.
3. **Retrieves in parallel** — statutory content from Neo4j and semantically similar case law from Weaviate using FIRAC-based embeddings (Facts, Issues, Rules, Analysis, Conclusion).
4. **Composes** a structured legal opinion with inline citations and a formatted references section.

The pipeline runs as a set of cooperating ADK agents that share state through callbacks and tool context.

## Project Structure

```
├── app/
│   ├── agent.py               # Multi-agent pipeline orchestration
│   ├── config.py              # Configuration (env-based)
│   ├── data/
│   │   └── graph_data.py      # Neo4j node types & court names
│   ├── prompts/
│   │   ├── agentic_prompts.py # Agent system instructions (stubs — customize)
│   │   ├── prompts.py         # Query classification prompts (stubs — customize)
│   │   ├── cypher_queries.py  # Neo4j Cypher query templates
│   │   └── output_format_prompts.py
│   ├── services/
│   │   ├── neo4j_database.py
│   │   ├── neo4j_connection_pool.py
│   │   ├── weaviate_database.py
│   │   └── llm_service/
│   │       ├── gemini_llm.py
│   │       └── openai_embedder.py
│   ├── tools/
│   │   ├── classify_query.py
│   │   ├── legislation_retrieval_tools.py
│   │   ├── rules_retrieval_tools.py
│   │   └── caselaw_retrieval.py
│   └── utils/
│       ├── get_logger.py
│       ├── verify_token.py
│       └── object_to_dict.py
├── .env.example
├── pyproject.toml
├── requirements.txt
├── Makefile
└── BEST_PRACTICES.md
```

## Prerequisites

- Python 3.10+
- Neo4j database(s) with your legal knowledge graph
- Weaviate instance with FIRAC-embedded case law
- At least one LLM provider API key (Gemini, OpenAI, or OpenRouter)

## Setup

```bash
git clone <your-repo-url>
cd <repo>
cp .env.example .env
# Edit .env with your credentials

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

The prompt files (`app/prompts/agentic_prompts.py` and `app/prompts/prompts.py`) ship as stubs with `TODO` markers. Customize them for your domain before running.

## Running

ADK provides built-in UIs — no custom frontend needed:

```bash
adk web app            # Interactive chat playground
adk api_server app     # API server for programmatic access
```

## Architecture

The system uses a 3-phase pipeline built on Google ADK's agent primitives:

**Phase 1 — Discovery:** An `LlmAgent` searches the Neo4j knowledge graph using full-text indices to find relevant Acts, then retrieves structural nodes (Sections, Chapters, etc.) under those Acts. Results are parsed via `discovery_callback` into shared state.

**Phase 2 — Parallel Deep Research:** A `ParallelAgent` runs two sub-agents simultaneously. The legislation agent retrieves statutory content using node IDs from discovery. The caselaw agent runs hybrid search — Neo4j for section-referenced cases, Weaviate for semantic similarity using FIRAC embeddings. Both write results to shared state via `ToolContext`.

**Phase 3 — Composition:** A final `LlmAgent` reads all research data from state and composes a structured legal opinion with inline citations and a formatted references section.

See `BEST_PRACTICES.md` for deeper architectural details.

---

## Setting Up Your Own Neo4j Knowledge Graph

The pipeline expects a Neo4j graph with the following structure. You can populate it with your own legal data or any hierarchical document corpus.

### Node Labels & Properties

**Legislation graph (primary database):**

| Label | Key Properties | Purpose |
|---|---|---|
| `Law` | `name`, `law_id` | Top-level legal domain (e.g., "Corporate Law") |
| `Act` | `title`, `year`, `publish_date`, `preamble` | Primary legislation (e.g., "Indian Contract Act, 1872") |
| `Chapter` | `title`, `content` | Structural division within an Act |
| `Part` | `title`, `content` | Higher-level structural division |
| `Section` | `title`, `content`, `section_id`, `section_num`, `tag_id` | Specific legal provision — the primary citable unit |
| `SubSection` | `content`, `tag_id` | Clause within a Section |
| `Paragraph` | `content`, `tag_id` | Granular text within a Section/SubSection |
| `Rule` | `title` | Secondary legislation (rules made under an Act) |
| `Concept` | `name` | Abstract legal concept for semantic linking |

**Metadata nodes** (attached to Acts/Sections for structured queries):

| Label | Purpose |
|---|---|
| `Applicability_of_Statute` | Scope and jurisdiction of an Act |
| `Key_Dates` | Enactment, effective, amendment dates |
| `Definitions_and_Terms` | Legal glossary extracted from Act text |
| `Procedural_Steps` | Step-by-step legal/administrative processes |
| `Regulatory_Bodies` | Authorities established by the Act |
| `Eligibility_Criteria` | Qualification conditions under the Act |
| `Judicial_Precedents` | Key principles from interpreting court cases |
| `Amendments_and_Repeals` | Change history of the Act |

**Caselaw graph (separate database):**

| Label | Key Properties | Purpose |
|---|---|---|
| `Case` | `CaseNo`, `display_name`, `Court`, `BenchValue`, `FIRAC_Conclusion`, `FIRAC_Analysis`, `FIRAC_HeadNote` | Individual court case |
| `Section` | `section_id`, `section_num`, `title` | Legislation section referenced by a case |

### Relationships

```
(Law)<-[:UNDER]-(Act)
(Act)-[*1..10]->(Chapter)-[*]->(Section)-[*]->(SubSection)
(Act)-[*1..10]->(Section)-[*]->(Paragraph)
(Act)<--(Rule)-[*]->(Section)
(Case)-[:REFERS_TO_SECTION]->(Section)
```

### Required Full-Text Indices

The discovery phase relies on these Neo4j full-text indices:

```cypher
-- On your legislation database:
CREATE FULLTEXT INDEX actTitleIndex FOR (n:Act) ON EACH [n.title]
CREATE FULLTEXT INDEX ruleTitleIndex FOR (n:Rule) ON EACH [n.title]
```

### Minimal Mock Data Example

To get a working prototype, you need at minimum one Act with a few Sections:

```cypher
CREATE (a:Act {title: "Sample Contract Act, 2024", year: 2024, publish_date: "2024-01-01"})
CREATE (ch:Chapter {title: "Chapter I - General Provisions", content: "General provisions of the Act"})
CREATE (s1:Section {title: "Definitions", content: "In this Act, unless the context otherwise requires...", section_id: "sample-s1", section_num: 1, tag_id: "S1"})
CREATE (s2:Section {title: "Formation of Contract", content: "A contract is formed when...", section_id: "sample-s2", section_num: 2, tag_id: "S2"})
CREATE (ss1:SubSection {content: "The term 'agreement' means...", tag_id: "S1(a)"})
CREATE (a)-[:HAS_CHAPTER]->(ch)
CREATE (ch)-[:HAS_SECTION]->(s1)
CREATE (ch)-[:HAS_SECTION]->(s2)
CREATE (s1)-[:HAS_SUBSECTION]->(ss1)
```

For caselaw (separate database):

```cypher
CREATE (c:Case {
  CaseNo: "2024-SC-001",
  display_name: "State v. Sample Corp",
  Court: "SUPREME COURT OF INDIA",
  BenchValue: 3,
  FIRAC_Conclusion: "The court held that...",
  FIRAC_Analysis: "Applying Section 2 of the Sample Contract Act...",
  FIRAC_HeadNote: "Contract formation requires valid consideration."
})
CREATE (s:Section {section_id: "sample-s2", section_num: 2, title: "Formation of Contract"})
CREATE (c)-[:REFERS_TO_SECTION]->(s)
```

---

## Setting Up Your Own Weaviate Vector Database

The caselaw retrieval uses Weaviate for semantic similarity search. Each case law document is split by FIRAC components and embedded.

### Collections

Create three collections, split by court tier for priority-based search:

| Collection Name | Court Tier | Purpose |
|---|---|---|
| `FIRAC_PARAGRAPHS_SC` | Supreme Court | Highest authority cases |
| `FIRAC_PARAGRAPHS_HC` | High Courts | State-level appellate cases |
| `FIRAC_PARAGRAPHS_OTHERS` | Other courts/tribunals | Lower courts, commissions |

### Object Properties

Each object in a collection represents a paragraph-level chunk from a case, with these properties:

| Property | Type | Description |
|---|---|---|
| `CaseNo` | string | Unique case identifier (must match Neo4j `Case.CaseNo`) |
| `content` | string | The actual text content of this chunk |
| `content_Label` | string | FIRAC component: one of `"Facts"`, `"Issues"`, `"Rules"`, `"Analysis"`, `"Conclusion"` |
| `contentType` | string | Always `"Paragraph"` for searchable chunks |
| `court` | string | Court name (e.g., `"SUPREME COURT OF INDIA"`) |

### Embedding Strategy

Each FIRAC component of a case is embedded separately using OpenAI's embedding model. This allows targeted similarity search — for example, searching only against the "Facts" component to find cases with similar factual scenarios, or against "Analysis" to find similar legal reasoning.

### How Search Works

1. The user query keywords are embedded using the same model.
2. All three collections are searched in parallel via `near_vector` queries.
3. Results are filtered by `content_Label` (FIRAC component) and `contentType`.
4. If `section_ids` are provided, results are further filtered to cases matching specific `CaseNo` values (pre-filtered from Neo4j).
5. Results from all three collections are merged and sorted: SC first, then HC, then Others. Within the same tier, sorted by embedding distance.

### Minimal Setup

Using the Weaviate Python client:

```python
import weaviate
from weaviate.classes.config import Configure, Property, DataType

client = weaviate.connect_to_local()  # or connect_to_custom(...)

for collection_name in [
    "FIRAC_PARAGRAPHS_SC",
    "FIRAC_PARAGRAPHS_HC",
    "FIRAC_PARAGRAPHS_OTHERS",
]:
    client.collections.create(
        name=collection_name,
        properties=[
            Property(name="CaseNo", data_type=DataType.TEXT),
            Property(name="content", data_type=DataType.TEXT),
            Property(name="content_Label", data_type=DataType.TEXT),
            Property(name="contentType", data_type=DataType.TEXT),
            Property(name="court", data_type=DataType.TEXT),
        ],
        vectorizer_config=Configure.Vectorizer.none(),  # we provide our own vectors
    )
```

Then insert objects with pre-computed embeddings:

```python
from openai import OpenAI

openai_client = OpenAI()
collection = client.collections.get("FIRAC_PARAGRAPHS_SC")

# Embed and insert a case paragraph
text = "The court examined whether consideration was adequate..."
embedding = openai_client.embeddings.create(
    input=text, model="your-openai-embedding-model"
).data[0].embedding

collection.data.insert(
    properties={
        "CaseNo": "2024-SC-001",
        "content": text,
        "content_Label": "Analysis",
        "contentType": "Paragraph",
        "court": "SUPREME COURT OF INDIA",
    },
    vector=embedding,
)
```

---

## License

This project is licensed under the Apache License 2.0. See the license headers in source files for details.

## Acknowledgments

Built with Google's [Agent Development Kit (ADK)](https://google.github.io/adk-docs/), [Neo4j](https://neo4j.com/), and [Weaviate](https://weaviate.io/).
