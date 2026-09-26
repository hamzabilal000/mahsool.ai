# Project status and handoff

Last updated: 2026-09-26 (project review; roadmap in [`ROADMAP.md`](ROADMAP.md))

## Overall status (project review, 2026-09-26)
Mahsool AI is in Phase 1 (MVP) of the 4-phase, 10-week plan. Weeks 1–4 are built, ahead of the plan's calendar
(which starts 28 Sep): the Income Tax Ordinance, Rules and TY2027 rate card are ingested (1,416 chunks), the
retrieval pipeline and its ablation are done (the `/ask` default reaches Hit@5 93.5% on 168 in-scope test
questions, 92.9% for both Urdu and Roman Urdu), and `/ask`, the React chat UI with citation cards, feedback storage
and the eval page work locally. What is not done for Phase 1: the end-to-end eval with the current answer prompt
(17 of 189 test questions run; blocked by Groq's free daily quota), answer-correctness scoring, the re-judging of 64
test questions, latency (57 s per answer vs the 4 s target), Langfuse, Prompt Guard, Docker and deployment. Phases
2–4 and the v2 features have not started. Roughly 40% of the whole project is done (Phase 1 about 80%).

## Working rules (from Hamza)
- Hamza is the only author. No "Co-Authored-By", "Generated with …" or other AI attribution in commits, PRs, code,
  docs, branch names or PR text.
- Work and push directly on `main` (no feature branches, no pull requests).
- In a fresh clone, set the identity and install the commit-msg hook (git hooks are not versioned, so a copy lives
  in `scripts/`):
  ```sh
  git config user.name "Hamza Bilal" && git config user.email "hamzaakbar666333@gmail.com"
  sh scripts/setup-hooks.sh
  ```
- No Docker: Qdrant runs embedded (`QDRANT_URL` empty); logs and feedback go to Neon Postgres when `DATABASE_URL`
  is set, else to `data/mahsool.db` (SQLite).
- Conventional commits in small steps, pushed to `main`. Never commit secrets (`.env` is gitignored).
- Never invent legal content. If an FBR URL fails or a newer consolidated version exists, report it.
- Work milestone by milestone (see PROJECT_PLAN build schedule). At the end of each milestone: tests, commit, push,
  append to `docs/LEARNING.md`, update `docs/DECISIONS.md`, then stop and report.
- `"verified": "machine"` = Qwen judge + number check passed (D45); Gemini is a non-blocking second opinion.
  Report metrics on the test split only.

## Start of every session (until each is done)
1. `python -m eval.verify_testset`: Qwen re-judges with the three-question prompt (D51) and Gemini gives its second
   opinion (20 a day, resets at midnight Pacific). **56 directly judged questions (64 with translations) still wait
   for Qwen** after 2026-09-26; fix anything it flags through `eval/review/changes.json` + `python -m
   eval.apply_changes` (check each fix against the law text first), then commit `testset.jsonl`, `FLAGGED.md`,
   `cache/verify.jsonl` and update the counts in README / D51.
2. `python -m eval.run_e2e --split test`: the answer prompt changed (D51), so the run restarted: **172 of 189 test
   questions left** after 2026-09-26 (~65 answers a day on GPT OSS 120B's free tier, ~3 days). It resumes from the cache and stops answering at the
   daily limit; record how many are left here, then `python -m eval.summary`, update README / D44, commit.

## Done
- **M1:** Income Tax Ordinance 2001 (amended to 30.06.2026): 885 chunks, 380/380 sections. 90 English eval questions.
- **M2 (part 1):**
  - Income Tax Rules 2002 (amended to 15.09.2026): 498 chunks, 381/381 rules.
  - WHT rate card TY2027: 33 chunks, 29 sections.
  - 200-question test set (60 dev / 140 test).
  - Retrieval stack (`backend/app/rag/`): BGE-M3 embedder, Qdrant store, BM25, RRF.
  - `ingestion/index.py` and `eval/run_eval.py`.
  - BM25 baseline, Hit@5 on the test split: English 87.3%, Urdu 3.6%, Roman Urdu 50.0%.

- **M2 (part 2):**
  - BGE-M3 (dense + sparse) index of all 1,416 chunks in embedded Qdrant (28 min on a 4-core CPU).
  - Encoder max length raised to 2,048 after measuring real token counts (D21).
  - Hybrid baseline on the test split: Hit@5 84.9%, Recall@5 (all gold) 81.9%, MRR@10 0.764.
    By language, Hit@5: English 95.2%, Urdu 78.6%, Roman Urdu 67.9% (D22).

- **M3 (part 1):**
  - Glossary `data/glossary_ur.csv` (170 terms), direct section lookup, language/tax-year rules, query rewrite
    (code + prompt, not yet run), bge-reranker-v2-m3, `RAGPipeline` with ablation switches.
  - `POST /ask` (FastAPI) with guardrails, citation check and refusals; 112 tests pass without models or network.
  - `eval/REVIEW.md` checklist for Hamza.
  - Test split Hit@5: + lookup 96.8 / 78.6 / 67.9 (En / Ur / Roman); + reranker 96.8 / 92.9 / 64.3.

- **M3 (part 2):**
  - Index rebuilt (1,416 points, 24 min); hybrid baseline reproduced exactly.
  - Rewrite prompt v2, tuned on dev only (D32): no invented section numbers, clearer scope rules, Urdu glossary
    terms must start a word.
  - Test split Hit@5 (En / Ur / Roman): + rewrite 98.4 / 100 / 89.3; + rewrite + reranker 96.8 / 89.3 / 71.4;
    full pipeline (default) 96.8 / 92.9 / 75.0. The reranker undoes part of the rewrite's gain (D33).
    Chart: `eval/reports/ablation-test.png`.
  - Dev experiments: rerank with max(question, rewrite) score (`full-max`: +1 Roman Urdu question on dev at 2x
    reranker time, not adopted; run once on test for the record: 96.8 / 92.9 / 92.9, D33); refusal threshold
    0.001 → 0.0005; future tax years refused (D34).
  - `eval/run_e2e.py`: 85 / 140 test questions before Groq's 200k tokens/day limit (D36). Correct citation on 68 of
    69 answered in-scope questions; 13 / 13 out-of-scope refused (biased: the 8 not run are the harder ones); both
    Roman Urdu questions that ran were wrongly refused by the reranker-score check.
  - Groq client fails fast on the daily limit (503 `LLM_UNAVAILABLE` at once). `/ask` tested live with uvicorn:
    "non filer hun, bank se cash nikalwaun to kitna tax katega?" → Roman Urdu answer, 0.8% above Rs 50,000 a day,
    citing section 231AB (checked against the law text), 27 s (26 s of it CPU reranking); PRA question →
    `OUT_OF_SCOPE`; tax year 2028 → `TAX_YEAR_NOT_COVERED`; 2-character question → 422 `VALIDATION_ERROR`.
  - 115 tests pass without models or network; `ruff` clean.

- **M3 (part 3):**
  - Chunk title fix (D37); 39 FBR-sourced test questions (D39); translations `language_ok` (D41); `/ask` default
    `full-max` (D40).
  - Gemini as a second LLM provider, provider + model per role (D42).
  - Test set: all 239 `"verified": "machine"` (Qwen + number check, D45); Gemini agreed on 15 of 15 it checked;
    `eval/expert_sample.json` (30 questions) waits for a tax professional.
  - Ablation on all 158 in-scope test questions (D44): `/ask` default Hit@5 93.0% all, 87.2% FBR, 96.8% English,
    92.9% Urdu, 92.9% Roman Urdu.
  - End to end: 85 / 179 with the old answer prompt; restarted with the new one (see "Start of every session").

- **After M4, 2026-09-26: AI legal review and completeness (D50, D51):**
  - Legal review of a 30-question sample by ChatGPT (OpenAI), an AI legal-review tool with web access, 26 Sep 2026:
    19 correct, 10 partly correct, 1 wrong; all 11 corrections checked against the corpus and applied at the English
    source and every translation. Not a human review; the tax-professional review is still pending.
  - Completeness sweep: 11 more answers fixed by hand, 4 more found by the judge's new completeness question; every
    change listed in `eval/FLAGGED.md`. 10 new condition-focused test questions (249 total, 189 on test).
  - Answer prompt states conditions (ATL / non-ATL, who a rule applies to, exceptions); judge asks about omitted
    conditions; `"verified": "reviewed"` status; `eval/apply_changes.py` keeps translations in sync.

- **M4 (done 2026-09-26):**
  - API: `POST /ask/stream` (server-sent events: stages, then the checked answer, then the envelope; D46),
    `POST /feedback`, `GET /eval/summary`, `GET /eval/ablation.png`, CORS for the Vite dev server; `/ask` returns
    a logged id.
  - Question log + feedback (`backend/app/db/`): Postgres via `DATABASE_URL`, else SQLite; no IP or user id (D47).
  - `frontend/`: React 19 + Vite + Tailwind 4 chat UI (English / Urdu / Roman Urdu, RTL Nastaliq for Urdu script,
    streamed answers, citation cards with FBR PDF page links, tax-year selector, "show sources", thumbs up/down with
    comment, starter questions) and the public eval page (D48).
  - `python -m eval.summary` writes the eval page's numbers from the committed reports.
  - Checked live (uvicorn + Vite + Playwright): English and Urdu questions streamed with both stages, citation cards,
    sources, feedback saved to SQLite, eval page and 390 px mobile layout without horizontal scroll.
  - Dev option `MAHSOOL_LLM_CACHE_PATH=eval/cache/groq.jsonl` replays cached answers when the quota is used up.
  - Langfuse deferred to Milestone 5 (D49). 133 backend tests + 3 frontend tests pass; `ruff` and `oxlint` clean.

## Resume here
State: everything committed and pushed on `main`. New container: `sh scripts/setup-hooks.sh`, git identity,
`pip install -e ".[dev,ml]"`, `python -m ingestion.index` (~30 min; the index is not committed),
`cd frontend && npm install`. `GROQ_API_KEY` and `GEMINI_API_KEY` set. Then the start-of-session steps above.

Run the app: `uvicorn backend.app.main:app --port 8000` and `cd frontend && npm run dev` → http://localhost:5173.

Rules learned the hard way: never `pkill -f` or `pgrep -f | kill` (it matches the calling shell); kill by exact
process id. Only one process may open the embedded Qdrant at a time (stop uvicorn before `run_e2e` / `run_eval`).
Keep GPT OSS 120B for the answers only.

## Next: Milestone 5 (per PROJECT_PLAN)
Fix top failures, Docker, deploy (backend on Hugging Face Spaces, frontend on Vercel), demo. Carried in: latency,
Langfuse (D49), score-refusal false positives on Roman Urdu, answer-correctness judging (D35), the Groq daily limit
for the demo (D36).

## Open for Milestone 5
- Latency: a warm answer through the UI took 57 s on this 4-core container (first request 145 s with model
  loading); the target is under 4 s. The default (`full-max`, D40) doubles the reranker work, so this needs a faster
  reranker (ONNX / fewer candidates / GPU / API).
- Citation cards show rate tables as raw `| … |` text; render tables in the card.

## Open items for Hamza
- Delete the old branch `claude/mahsool-gemini-eval-cla2bx` on GitHub (Branches → trash icon): this session's git
  proxy refused the delete; `main` already contains all of it.
- Optional: enable billing on the Google project to finish Gemini's second opinion in one run (20 a day free, D42).
- Optional: set `DATABASE_URL` (Neon) in `.env` to keep logs and feedback in Postgres instead of SQLite.
- Send `eval/expert_sample.json` to a tax expert (30 questions; fill `expert_ok` / `expert_notes`).
- Review `data/glossary_ur.csv` as a native speaker (D25).
- Consider a paid Groq tier (or another answer model) before the Milestone 5 demo (D36).
- Spot-check `data/processed/*/spot_check.md`.
- Set the GitHub repo description and topics in the UI.
