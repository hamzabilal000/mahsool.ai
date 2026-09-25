# Mahsool AI — محصول

**Cross-lingual RAG assistant for Pakistani tax law (FBR) — English, Urdu & Roman Urdu with section-level citations.**

Ask *"Mera tax kitna katega 1.5 lakh salary pe?"* or *"freelancer ko bahar se paisa aye to kitna tax?"* and get an
answer grounded in the Income Tax Ordinance, with every claim citing the exact section, clause or rate table it came
from. When the law doesn't cover the question, Mahsool says so.

> ⚠️ For information only, not tax advice. Confirm with a tax practitioner or FBR.

![Demo](docs/demo.gif)
<sub>_Demo GIF coming in Milestone 5._</sub>

## Status

| Milestone | Scope | State |
| --- | --- | --- |
| 1 | Repo, ingestion of the Income Tax Ordinance 2001, 90 English eval questions | ✅ done |
| 2 | Income Tax Rules 2002 + WHT rate card, BGE-M3 → Qdrant, Urdu / Roman Urdu questions, baseline Recall@5 | ✅ done |
| 3 | Query rewrite, hybrid search + RRF, reranker, FastAPI `/ask` with citation check | |
| 4 | React chat UI, citation cards, feedback, Postgres logs, Langfuse | |
| 5 | Fix top failures, Docker, deploy, demo | |

## Architecture

**Ingestion** (runs once per law, and again after every Finance Act):

```mermaid
flowchart LR
  A[FBR PDFs] --> B[Parser<br/>PyMuPDF]
  B --> C[Section-aware<br/>chunker]
  C --> D[Metadata<br/>law, section, tax year,<br/>amended_by]
  D --> E[BGE-M3<br/>dense + sparse]
  E --> F[(Qdrant)]
```

**Answering a question** (Milestones 3–4):

```mermaid
flowchart TD
  U[React chat UI] --> API[FastAPI /ask]
  API --> Q[Query understanding<br/>language, tax year, law]
  Q --> R[Hybrid search<br/>Qdrant dense + sparse, RRF]
  R --> RR[Reranker<br/>bge-reranker-v2-m3]
  RR --> G[LLM answer<br/>with citations]
  G --> V[Citation check]
  V --> U
  API --> L[(Logs + feedback<br/>Postgres)]
```

## What's in the index today

All three phase-1 sources are the latest FBR versions; SHA-256 checksums are in
[`data/sources.manifest.json`](data/sources.manifest.json).

| Source | FBR version | Units covered | Chunks |
| --- | --- | --- | --- |
| Income Tax Ordinance, 2001 | amended up to 30.06.2026 (Finance Act 2026, TY2027) | 380 / 380 sections + all 15 Schedules | 885 |
| Income Tax Rules, 2002 | amended up to 15.09.2026 | 381 / 381 rules (form appendices skipped) | 498 |
| Withholding Tax Rates Card | TY2027, updated to 30.06.2026 | 29 sections, ATL and non-ATL rates | 33 |

"Units covered" is checked against each PDF's own table of contents. Chunks are at most 800 tokens; 899 carry
amendment history (`amended_by`: Finance Acts, SROs).

Each chunk follows the law's own structure: one section, one Second Schedule clause or one rate table. Example:

```json
{
  "chunk_id": "ITO2001-s149",
  "section_id": "ITO2001-s149",
  "law": "Income Tax Ordinance, 2001",
  "section": "149",
  "title": "Salary",
  "chapter": "Chapter X – Procedure",
  "part": "Part V; Division III: Deduction of Tax at Source",
  "amended_by": ["Finance Act, 2025", "Finance Act, 2024", "…"],
  "tax_year_from": 2027,
  "page": 333,
  "version_date": "2026-06-30",
  "text": "149. Salary. — (1) Every [person responsible for] paying salary to an employee shall …"
}
```

## Evaluation

The test set lives in [`eval/testset.jsonl`](eval/testset.jsonl). Every question has gold section IDs, a short
reference answer written only from the law text, a difficulty tag and a fixed dev/test split. All questions start with
`"verified": false` and are checked by hand against the PDF before they are used for reporting.

| Group | Questions | Split (dev / test) |
| --- | --- | --- |
| English | 90 | 27 / 63 |
| Urdu script | 40 | 12 / 28 |
| Roman Urdu | 40 | 12 / 28 |
| Out of scope / trick | 30 | 9 / 21 |
| **Total** | **200** | **60 / 140** |

Urdu and Roman Urdu questions are natural rewrites of English ones and share their gold sections and split.

**Retrieval ablation: Hit@5 on the held-out test split** (Urdu / Roman Urdu is the target group)

| Setup | English | Urdu | Roman Urdu |
| --- | --- | --- | --- |
| BM25 keywords (no model) | 87.3% | 3.6% | 50.0% |
| BGE-M3 sparse only | 92.1% | 7.1% | 60.7% |
| Dense only (BGE-M3), original query | 98.4% | 78.6% | 57.1% |
| + sparse (hybrid, RRF) — **baseline** | 95.2% | 78.6% | 67.9% |
| + English query rewrite | _M3_ | _M3_ | _M3_ |
| + reranker | _M3_ | _M3_ | _M3_ |
| + glossary in rewrite | _M3_ | _M3_ | _M3_ |

**Hybrid baseline, test split (119 in-scope questions):**

| Group | n | Hit@5 ("Recall@5") | Recall@5 (all gold) | MRR@10 |
| --- | --- | --- | --- | --- |
| English | 63 | 95.2% | 94.4% | 0.861 |
| Urdu script | 28 | 78.6% | 71.4% | 0.693 |
| Roman Urdu | 28 | 67.9% | 64.3% | 0.617 |
| **All** | 119 | **84.9%** | **81.9%** | **0.764** |

Metric definitions are in [DECISIONS D19](docs/DECISIONS.md). English numbers are optimistic because the questions
were written from the section text (D20), and no question is hand-verified yet. Full reports, with every miss:
[`eval/reports/`](eval/reports/).

**Targets (held-out test split only)**

| Metric | Target | Result |
| --- | --- | --- |
| Retrieval Recall@5 (Urdu / Roman Urdu) | ≥ 80% | hybrid baseline: 78.6% / 67.9% (Milestone 3 query rewrite should close the gap) |
| Answer correctness | ≥ 85% | _Milestone 3_ |
| Answers with a correct citation | ≥ 90% | _Milestone 3_ |
| Correct refusal on out-of-scope questions | ≥ 90% | _Milestone 3_ |
| Median latency | < 4 s | _Milestone 4_ |

## Run locally (no Docker)

Requires Python 3.11+ and about 5 GB of free disk (PyTorch + 2.3 GB of BGE-M3 weights). Everything runs
in-process: Qdrant is **embedded** (stored under `data/qdrant/`), so no Docker and no server are needed.

```bash
git clone https://github.com/hamzabilal000/mahsool.ai.git && cd mahsool.ai
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu   # optional: CPU-only PyTorch, ~2 GB smaller
pip install -e ".[dev,ml]"          # drop ",ml" if you only want BM25, tests and the validator
cp .env.example .env                # keep QDRANT_URL empty = embedded Qdrant
sh scripts/setup-hooks.sh           # commit-msg hook (contributors only)

# 1. Build the vector index: downloads BGE-M3 on first run, then embeds all 1,416 chunks
#    (dense + sparse). ~35 min on a 4-core laptop CPU; re-run only when chunks change.
python -m ingestion.index

# 2. Evaluate retrieval on the held-out test split (reports go to eval/reports/)
python -m eval.run_eval --retriever bm25   --split test
python -m eval.run_eval --retriever dense  --split test
python -m eval.run_eval --retriever sparse --split test
python -m eval.run_eval --retriever hybrid --split test

# 3. Checks
python -m eval.validate_testset
ruff check . && pytest
```

The processed chunks are committed, so tests, the validator and the BM25 baseline run without downloading
anything. Only one process can open the embedded Qdrant folder at a time, so don't run `ingestion.index` and
`eval.run_eval` side by side.

**Postgres** (conversation logs and feedback, needed from Milestone 4): create a free project on
[Neon](https://neon.tech) and paste its connection string into `DATABASE_URL` in `.env`.

**Optional:** [`docker-compose.yml`](docker-compose.yml) starts a local Qdrant server and Postgres if you'd rather
use Docker. Set `QDRANT_URL=http://localhost:6333` to point at it.

**Re-running ingestion from the FBR PDFs** (only needed when FBR publishes a new version):

```bash
python -m ingestion.download --law ITO2001 --check-latest   # exits 2 if FBR has a newer version
python -m ingestion.download --law ITO2001                  # skips the download if unchanged
python -m ingestion.parse    --law ITO2001
python -m ingestion.chunk    --law ITO2001                  # repeat for ITR2002
python -m ingestion.download --law WHT2027 && python -m ingestion.ratecard --law WHT2027
python -m ingestion.spot_check --law ITR2002 --n 20
```

## Repository layout

```
ingestion/           download → parse → chunk → index; one config per law in ingestion/laws/; ratecard.py
backend/app/         config.py (all model ids) and rag/: embedder, Qdrant store, BM25, RRF fusion, retriever
eval/                testset.jsonl (200 Qs), schema, validator, metrics, run_eval.py, reports/
data/processed/      committed chunks, coverage report and spot-check sample per law snapshot
data/sources.manifest.json   URL, version date and SHA-256 of every source PDF
tests/               unit tests + regression tests on the real outputs
docs/                LEARNING.md (concepts explained), DECISIONS.md (deviations from the plan)
docker-compose.yml   optional local Qdrant server + Postgres (not needed to run)
scripts/             commit-msg hook and setup-hooks.sh
frontend/            React app (Milestone 4)
```

## Docs

- [`docs/LEARNING.md`](docs/LEARNING.md): how each part works and why, in plain English.
- [`docs/DECISIONS.md`](docs/DECISIONS.md): every deviation from the project plan and the reason for it.
