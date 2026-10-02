# Mahsool AI — محصول

**Cross-lingual RAG assistant for Pakistani tax law (FBR) — English, Urdu & Roman Urdu with section-level citations.**

Ask *"Mera tax kitna katega 1.5 lakh salary pe?"* or *"freelancer ko bahar se paisa aye to kitna tax?"* and get an
answer grounded in the Income Tax Ordinance, with every claim citing the exact section, clause or rate table it came
from. When the law doesn't cover the question, Mahsool says so.

> ⚠️ For information only, not tax advice. Confirm with a tax practitioner or FBR.

**Live demo:** launching on Vercel (project `mahsool-ai`); the link goes here once the project is created. The
API runs on a laptop behind ngrok ([How it's hosted](#how-its-hosted-d64)), so the site sometimes says "Mahsool AI
is resting right now".

![Demo](docs/demo.gif)
<sub>_Demo GIF coming in Milestone 5._</sub>

## Status

| Milestone | Scope | State |
| --- | --- | --- |
| 1 | Repo, ingestion of the Income Tax Ordinance 2001, 90 English eval questions | ✅ done |
| 2 | Income Tax Rules 2002 + WHT rate card, BGE-M3 → Qdrant, Urdu / Roman Urdu questions, baseline Recall@5 | ✅ done |
| 3 | Query rewrite, hybrid search + RRF, reranker, FastAPI `/ask` with citation check | ✅ built and evaluated · test set verified: 257 of 262 (D45, D51) · ✅ end-to-end eval 189/189 (Groq daily limit, D36) |
| 4 | React chat UI, citation cards, feedback, Postgres logs, eval page | ✅ done (Langfuse moved to M5, D49) |
| 5 | Fix top failures, deploy, demo | 🔄 launch prep done: ATL / non-ATL rates fixed (D63), backend on a laptop behind ngrok + frontend on Vercel (D64, **Vercel link pending**), prebuilt index (D65), latency ~7.5 s (D62), Prompt Guard (D60), demo limits (D59) |

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
  R --> RR[Reranker<br/>gte-multilingual-reranker-base]
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
`"verified": false`.

**How the test set is verified:** machine-verified by an independent LLM judge (Qwen) plus an automatic number check;
a second judge (Gemini) agreed on 38 of 40 it checked with the current three-question prompt (the 2 disagreements concern tax-year-2022 provisos that do not apply to TY2027; three more of its flags, en-025, en-028 and en-035, were correct and fixed on 28-30 Sep). Legal review of a 30-question sample by ChatGPT (OpenAI), an AI legal-review tool with web access,
26 Sep 2026: 19 correct, 10 partly correct, 1 wrong; all fixed and a completeness sweep applied to the full set. This
is an AI tool's review, not a human one; a review by a tax professional is still pending.

In [`eval/verify_testset.py`](eval/verify_testset.py) Qwen reads only the gold law text and answers three questions:
does it answer the question, does it support the reference answer, and does the reference omit a condition or
exception that changes the answer (added after the review showed that the judges passed incomplete answers, D51).
Code checks that every number in the reference answer is in the law text. Gemini 3 Flash, a different model family,
runs the same check as a non-blocking second opinion as far as its free tier allows (20 a day). Neither model wrote
the questions. Every correction from the review was checked against the corpus before it was applied, and every
change to a reference answer is listed with before and after in [`eval/FLAGGED.md`](eval/FLAGGED.md) (D50).

**Current state (2026-10-01):** 257 of 262 questions are machine-verified (30 of them also "reviewed": marked correct
or corrected per the AI review, then re-verified). The one left, en-092 (rent paid by a company to an individual
landlord), is flagged by Qwen: whether Division V's rates depend on the landlord or the tenant is not stated in the
corpus, so it waits for the tax-practitioner review instead of a guess. Decisions D38, D42, D45, D50, D51.

| Group | Questions | Split (dev / test) |
| --- | --- | --- |
| English | 102 | 29 / 73 |
| Urdu script | 42 | 14 / 28 |
| Roman Urdu | 42 | 14 / 28 |
| English, from FBR pages (D39) | 39 | 0 / 39 |
| Out of scope / trick | 37 | 16 / 21 |
| **Total** | **262** | **73 / 189** |

Urdu and Roman Urdu questions are natural rewrites of English ones and share their gold sections and split.

**Retrieval ablation: Hit@5 on the held-out test split** (Urdu / Roman Urdu is the target group)

![Retrieval ablation, Hit@5 on the test split](eval/reports/ablation-test.png)

| Setup | English (written, 73) | English (FBR pages, 39) | Urdu (28) | Roman Urdu (28) | **All (168)** |
| --- | --- | --- | --- | --- | --- |
| BM25 keywords (no model) | 87.7% | 71.8% | 3.6% | 50.0% | 63.7% |
| BGE-M3 sparse only | 93.2% | 84.6% | 7.1% | 60.7% | 71.4% |
| Dense only (BGE-M3), original query | 98.6% | 79.5% | 78.6% | 57.1% | 83.9% |
| + sparse (hybrid, RRF) — **baseline** | 95.9% | 87.2% | 78.6% | 67.9% | 86.3% |
| + direct section lookup (in every row below) | 97.3% | 87.2% | 78.6% | 67.9% | 86.9% |
| + reranker (bge-reranker-v2-m3, top 30), no rewrite | 97.3% | 87.2% | 89.3% | 64.3% | 88.1% |
| + English query rewrite (GPT OSS 20B), no reranker | **98.6%** | 84.6% | **100%** | 89.3% | **94.0%** |
| + rewrite + reranker | 97.3% | **89.7%** | 89.3% | 75.0% | 90.5% |
| + glossary in rewrite = full pipeline, reranking with the question only | 97.3% | **89.7%** | 92.9% | 75.0% | 91.1% |
| full pipeline, reranking with max(question, rewrite) score (D40) | 97.3% | 87.2% | 92.9% | **92.9%** | 93.5% |
| 15 rerank candidates, max score only for Urdu / Roman Urdu (D52) | **98.6%** | 87.2% | 92.9% | **92.9%** | 94.0% |
| + section 2 definition lookup (D57), bge reranker | **98.6%** | 94.9% | 92.9% | **92.9%** | **95.8%** |
| gte-multilingual-reranker-base at 256 tokens instead of bge (D62) | 97.3% | **97.4%** | **96.4%** | 89.3% | **95.8%** |
| + glossary row for foreign salary, section 102 (D68) | 97.3% | **97.4%** | 96.4% | 92.9% | 96.4% |
| + glossary sections in the reranker pool, best-window reranking (D69) = **`/ask` default** | **98.6%** | **97.4%** | **100%** | **100%** | **98.8%** |

All 168 in-scope test questions, re-run on 2026-09-26 after the legal-review fixes and the 10 new condition-focused
English questions (en-091 … en-100, all 10 found in the top 5 by the default pipeline; D51). Reference-answer fixes
do not change retrieval; the written-English column moves only because of the new questions. The `/ask` default has
Recall@5 (all gold) 93.2% and MRR@10 0.848 on all 168 (bge: 92.8% and 0.906; the smaller reranker keeps Hit@5 but
ranks the right section first less often, D62). The last two rows are Milestone 5 changes: the reranker scores
15 candidates and uses the English rewrite only for Urdu / Roman Urdu (tuned on dev for speed, D52), and a definition
lookup pins the section 2 clause for "what is X?" questions (D57), which lifts the FBR-sourced group (D39) from 87.2%
to 94.9%. That rule was found by reading test misses (the FBR questions exist only on the test split), so part of
that gain is in-sample; dev was unchanged by it.

The rewrite is the big win (Roman Urdu 67.9% → 89.3%). The reranker then undoes part of it for Urdu and Roman Urdu:
it scores chunks against the original question, which it reads poorly in Roman Urdu. Letting the reranker also score
the English rewrite and keep the higher score (`full-max`, last row) fixes most of that. It was chosen on the dev
split (Hit@5 96.1% vs 94.1%, Roman Urdu 83.3% vs 75.0%) and is now the `/ask` default
([D40](docs/DECISIONS.md)); it doubles the reranker time, which is the open latency problem for Milestone 5.

**Hybrid baseline from Milestone 2, test split (the 119 written in-scope questions of that time; on today's 168: Hit@5 86.3%):**

| Group | n | Hit@5 ("Recall@5") | Recall@5 (all gold) | MRR@10 |
| --- | --- | --- | --- | --- |
| English | 63 | 95.2% | 94.4% | 0.861 |
| Urdu script | 28 | 78.6% | 71.4% | 0.693 |
| Roman Urdu | 28 | 67.9% | 64.3% | 0.617 |
| **All** | 119 | **84.9%** | **81.9%** | **0.764** |

Metric definitions are in [DECISIONS D19](docs/DECISIONS.md). English numbers are optimistic because the questions
were written from the section text (D20). 257 of 262 questions are machine-verified (D51); a 30-question sample
was checked by an AI legal-review tool, and none by a tax professional yet (D50). Full reports, with every miss:
[`eval/reports/`](eval/reports/).

**Targets (held-out test split only)**

| Metric | Target | Result |
| --- | --- | --- |
| Retrieval Hit@5 (Urdu / Roman Urdu) | ≥ 80% | `/ask` default: Urdu 100% ✅ / Roman Urdu 100% ✅; all 168: 98.8%, Recall@5 96.3%, FBR 97.4% (D69) |
| Answer correctness | ≥ 85% | ❌ (1 Oct, before D69; the D69 re-run of the test answers is in progress) **129 of 168 (76.8%)** match the reference, 146 of 168 (86.9%) at least partly (Qwen judge, D56). Strict by group: English 59 of 73 (80.8%), FBR pages 33 of 39 (84.6%), Urdu 17 of 28 (60.7%), Roman Urdu 20 of 28 (71.4%)* |
| Answers with a correct citation | ≥ 90% | ✅ 159 of 164 answered in-scope questions (97.0%); 4 of 168 wrongly refused* |
| Correct refusal on out-of-scope questions | ≥ 90% | ✅ 21 of 21 (with the out-of-scope rules, D67)* |
| Median latency | < 4 s | ❌ ~7.5 s for a new English question on 4 CPU cores (live, rerank ~2.7 s), ~9 s for Roman Urdu; estimated ~8-9 s p50 / ~13 s p95 on 2 vCPU (D62); ~10 ms for a repeated question (answer cache) |

\* End-to-end on the test split ([`eval/run_e2e.py`](eval/run_e2e.py)) with the `/ask` default (gte reranker, D62;
Tenth Schedule companions, D63; out-of-scope rules, D67), **complete: all 189 test questions** over four daily
quotas (27 Sep to 1 Oct). English and FBR-page answers are near the target; the Urdu and Roman Urdu answers are not,
and the condition-focused English questions added after the legal review (en-076 to en-100) are the hardest. The
wrong or incomplete answers cluster in a few topics: residency (only the 183-day test), a widow's return under
section 115(3), the mixed-use vehicle perquisite, arrears of salary (section 12(7) election), pension (section
149(1A)), the PSEB freelancer rate (section 154A) and section 21 (both wrongly refused). The section 102 foreign-salary
miss is fixed in retrieval (D68); its answers are re-asked in the next run. The first, English-heavy run with the
older reranker scored 38 of 39 (D58); it is superseded.
Re-run after a change: `python -m eval.run_e2e --split test --order mixed` (only changed prompts call the model), then
`python -m eval.judge_answers --split test`.
Report: [`eval/reports/2026-10-01-e2e-test.md`](eval/reports/2026-10-01-e2e-test.md); hand-check sheet:
[`eval/answer_check.md`](eval/answer_check.md) (50 answers, seed 2027).

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

# 1. Install the prebuilt vector index (8.6 MB, committed; D65). BGE-M3 downloads on first use.
python scripts/get_index.py
#    Only after the chunks change: re-embed all 1,416 chunks (~30 min on 4 cores), then re-pack.
#    python -m ingestion.index && python scripts/get_index.py --pack

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

**Ask questions through the API** (needs the index, and `GROQ_API_KEY` in `.env` from
[console.groq.com](https://console.groq.com) → API Keys). The test-set judge also needs `GEMINI_API_KEY` from
[aistudio.google.com](https://aistudio.google.com) → Get API key. Which provider and model serves each role
(answer, rewrite, judge 1, judge 2) is set in [`backend/app/config.py`](backend/app/config.py) (DECISIONS D42):

```bash
uvicorn backend.app.main:app --port 8000        # first start loads BGE-M3 + reranker (~30 s)
curl -s localhost:8000/ask -H 'content-type: application/json' \
  -d '{"question": "non filer hun, bank se cash nikalwaun to kitna tax katega?"}'
```

Interactive docs at http://localhost:8000/docs. Every response is
`{"success": …, "data": {answer, citations, sources, …}, "error": …, "code": "OK" | "REFUSED" | …}`.
On a laptop CPU the reranker makes each answer slow (tens of seconds); see DECISIONS D26.

**Ablation presets:** `python -m eval.run_eval --pipeline {lookup, lookup-rerank, rewrite, rewrite-rerank, full, full-max}
--split test`, then `python -m eval.plot_ablation` for the chart. End to end: `python -m eval.run_e2e --split test`.
LLM and reranker outputs are cached in `eval/cache/`, so re-runs are fast and reproducible without a key.

**Chat UI** (Milestone 4; needs Node 20+ and the API above running on port 8000):

```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173 — chat at /, evaluation page at /eval
npm test && npm run lint    # parser/format unit tests and oxlint
```

The UI calls the API at `VITE_API_URL` (default `http://localhost:8000`; see `frontend/.env.example`). Answers
stream in over `POST /ask/stream`; thumbs up/down go to `POST /feedback`. After new eval runs,
`python -m eval.summary` refreshes the numbers on the eval page.

**Question log and feedback:** stored in Postgres when `DATABASE_URL` is set (a free [Neon](https://neon.tech)
project's connection string works as is), otherwise in a local SQLite file, `data/mahsool.db`, so nothing else is
needed for development. Tables are created on startup; no IP address or user id is stored (D47).

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

## How it's hosted (D64)

**Live:** the chat UI is on **Vercel** (project `mahsool-ai`); the API runs on **Hamza's laptop** and is reached
through ngrok's free static domain, `https://resident-coil-delusion.ngrok-free.dev`. Nothing costs money. When the
laptop is off, the site says *"Mahsool AI is resting right now. Please try again later."*

```mermaid
flowchart LR
  U[Visitor's browser] -->|HTTPS| V[Vercel<br/>React app]
  U -->|HTTPS + ngrok-skip-browser-warning| N[ngrok static domain]
  N -->|tunnel| L[Laptop: uvicorn 127.0.0.1:8000<br/>BGE-M3 + gte reranker + embedded Qdrant + SQLite]
  L -->|answers, rewrites, Prompt Guard| G[Groq free tier]
```

**Backend (Windows laptop):** [`docs/RUN_ON_MY_LAPTOP.md`](docs/RUN_ON_MY_LAPTOP.md) (install Python 3.11, Git,
ngrok; `ngrok config add-authtoken ...`; then one command):

```powershell
.\scripts\run_local.ps1          # first run installs everything (py -3.11 venv, CPU PyTorch, index); later just starts
.\scripts\run_local.ps1 -Check   # local and public health check
```

It asks for `GROQ_API_KEY` once and keeps it in `.env` (gitignored), installs the prebuilt index
(`scripts/get_index.py`, D65), starts ngrok on the static domain in a second window and uvicorn with local SQLite.
Ubuntu: `bash scripts/run_local.sh`.

**Frontend (Vercel):** the API address is in [`frontend/.env.production`](frontend/.env.production). Either
`VERCEL_TOKEN=... sh scripts/deploy_vercel.sh`, or on vercel.com: Add New → Project → import this repo →
**Root Directory `frontend`** → Deploy ([`frontend/vercel.json`](frontend/vercel.json) sends every route to the app).
The API allows `https://mahsool-ai.vercel.app` and its preview URLs (CORS, `MAHSOOL_CORS_ORIGIN_REGEX`).

**Free-tier behaviour of the live demo (D53, D59):** repeated questions are answered from the answer cache (no
quota, no reranking, never counted); each visitor can ask 10 new questions a day
(`MAHSOOL_DAILY_QUESTIONS_PER_VISITOR`) and all visitors together get 60 new answers a day
(`MAHSOOL_DAILY_ANSWERS_GLOBAL`, sized to Groq's free quota); past either limit, or when Groq's daily quota is used
up, the app says "come back tomorrow" politely, in the question's language. uvicorn trusts `X-Forwarded-For` only
from the local ngrok agent, so visitors are told apart. Questions are screened by Prompt Guard 2 on Groq first (D60).

**Other hosting, prepared for later:** an Oracle Cloud Always Free Ampere VM ([`deploy/oracle/`](deploy/oracle),
[`docs/DEPLOY_ORACLE.md`](docs/DEPLOY_ORACLE.md): cloud-init without secrets, systemd services, health check,
keep-alive; needs a card at sign-up), and the Hugging Face Docker Space ([`Dockerfile`](Dockerfile),
`scripts/deploy_space.py`), which now needs HF PRO (D61).

## Repository layout

```
ingestion/           download → parse → chunk → index; one config per law in ingestion/laws/; ratecard.py
backend/app/         main.py (FastAPI), api/ask.py (/ask, /ask/stream, /feedback), api/eval.py (eval page data),
                     service.py (guardrails), config.py (all model ids), db/ (question log + feedback)
backend/app/rag/     embedder, Qdrant store, BM25, RRF, retriever, lookup, query_rewrite, reranker,
                     pipeline, generator, citations
data/glossary_ur.csv Urdu / Roman Urdu → legal English glossary used by the query rewrite
eval/                testset.jsonl (239 Qs), validator, verify_testset.py, run_eval.py (retrieval), run_e2e.py
                     (/ask end to end), plot_ablation.py, summary.py (eval page), reports/, cache/
data/processed/      committed chunks, coverage report and spot-check sample per law snapshot
data/sources.manifest.json   URL, version date and SHA-256 of every source PDF
tests/               unit tests + regression tests on the real outputs
docs/                LEARNING.md (concepts explained), DECISIONS.md (deviations from the plan)
docker-compose.yml   optional local Qdrant server + Postgres (not needed to run)
scripts/             commit-msg hook and setup-hooks.sh
frontend/            React + Vite + Tailwind chat UI and eval page (src/Pages, src/components, src/api)
```

## Docs

- [`docs/LEARNING.md`](docs/LEARNING.md): how each part works and why, in plain English.
- [`docs/DECISIONS.md`](docs/DECISIONS.md): every deviation from the project plan and the reason for it.
