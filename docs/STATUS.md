# Project status and handoff

Last updated: 2026-09-25 evening (Milestone 3, part 3: Gemini added; verification and end-to-end eval paused on daily quotas)

## Working rules (from Hamza)
- Hamza is the only author. No "Co-Authored-By", "Generated with …" or other AI attribution in commits, PRs, code or docs.
- In a fresh clone, set the identity and install the commit-msg hook (git hooks are not versioned, so a copy lives
  in `scripts/`):
  ```sh
  git config user.name "Hamza Bilal" && git config user.email "hamzaakbar666333@gmail.com"
  sh scripts/setup-hooks.sh
  ```
- No Docker: Qdrant runs embedded (`QDRANT_URL` empty), Postgres is hosted on Neon (`DATABASE_URL`).
- Conventional commits, pushed to `main` after each milestone. Never commit secrets (`.env` is gitignored).
- Never invent legal content. If an FBR URL fails or a newer consolidated version exists, report it.
- Work milestone by milestone (see PROJECT_PLAN build schedule). At the end of each milestone: tests, commit, push,
  append to `docs/LEARNING.md`, update `docs/DECISIONS.md`, then stop and report.
- Eval questions stay `"verified": false` until Hamza checks them. Report metrics on the test split only.

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

- **M3 (part 3, in progress):**
  - Chunk title fix (D37), "Surcharge" title for ITO 4AB; 53 chunks re-embedded.
  - Language check applied: all 80 translations `language_ok: true` (67 read by Hamza, 13 approved as is; D41).
  - 39 FBR-sourced test questions `fbr-001`…`fbr-039` (D39); test set now 239 questions (179 on test).
  - `/ask` default is now `full-max` (D40).
  - **Gemini as a second LLM provider (D42):** provider + model per role in `backend/app/config.py` (answer = GPT OSS
    120B on Groq, rewrite = GPT OSS 20B on Groq, judge 1 = Gemini 3 Flash, judge 2 = Qwen on Groq), rate limiter,
    404 model fallback, shared cache. Gemini 3 Flash is served as `gemini-3-flash-preview`; `gemini-2.5-flash` is
    closed to new users. **Free tier on this key: 20 Gemini requests a day per model** (not 1,500).
  - **Verification (D43):** en-009, en-063, en-089 fixed; excerpt and number-check fixes (fbr-021). Qwen + number
    check pass all 159 directly judged questions; Gemini has judged 14 (all passed). 26 of 239 are
    `"verified": "machine"`, nothing removed. `eval/expert_sample.json` written (30, stratified, seed 2027).
  - **Ablation re-run on all 158 in-scope test questions (D44):** `/ask` default Hit@5 93.0% all, 87.2% FBR,
    96.8% English, 92.9% Urdu, 92.9% Roman Urdu. Chart now has an FBR series.
  - **End to end (D44):** 68 / 179 test questions before GPT OSS 120B's daily limit; 111 left. Correct citation
    53 / 55 in-scope run (98.2% of answered); 13 / 13 out-of-scope refused.
  - 125 tests pass; `ruff` clean.

## Resume here (M3 part 3)
State: everything committed and pushed on `claude/mahsool-gemini-eval-cla2bx`, caches committed
(`eval/cache/groq.jsonl`, `rerank.tsv`, `verify.jsonl`). Every run resumes from them.

0. New container: `sh scripts/setup-hooks.sh`, git identity, `pip install -e ".[dev,ml]"`, then
   `python -m ingestion.index` (~30 min; the index is not committed). `GROQ_API_KEY` and `GEMINI_API_KEY` set.
1. `python -m eval.run_e2e --split test`: 111 questions left, ~65 a day on GPT OSS 120B's free tier (rolling 24-hour window:
   2026-09-25's use frees up gradually from ~13:30 UTC on 09-26). Commit after each day's run.
2. `python -m eval.verify_testset`: 145 questions still need Gemini (20 a day, resets at midnight Pacific; ~8 days),
   or enable billing on the Google project and finish in one run. Fix anything it flags.
3. When both are done: update README (targets table), DECISIONS D44 and this file; append to `docs/LEARNING.md`;
   close Milestone 3 and merge to `main`.

Rules learned the hard way: never `pkill -f` or `pgrep -f | kill` (it matches the calling shell); kill by exact
process id. Only one process may open the embedded Qdrant at a time. Keep GPT OSS 120B for the answers only.

## After that
1. **Milestone 4** (per PROJECT_PLAN): React chat UI, citation cards, feedback, Postgres logs on Neon, Langfuse.
2. **Carried to Milestone 5, decide on dev:** score-refusal false positives on Roman Urdu, answer-correctness
   judging (D35), the Groq daily limit for the demo (D36).

## Open for Milestone 5
- Latency: the live `/ask` answer took 27 s (26 s of it CPU reranking); the target is under 4 s. The new default
  (`full-max`, D40) doubles the reranker work, so this needs a faster reranker (ONNX / fewer candidates / GPU / API).

## Open items for Hamza
- Gemini free tier is 20 requests a day per model on this key: enable billing on the Google project to finish the
  judge in one run, or accept ~8 more days (D42).
- Send `eval/expert_sample.json` to a tax expert (30 questions; fill `expert_ok` / `expert_notes`).
- Verify eval questions by hand with `eval/REVIEW.md` (about 20 a day), and tell Claude Code which are wrong.
- Review `data/glossary_ur.csv` as a native speaker (D25).
- Consider a paid Groq tier (or another answer model) before the Milestone 5 demo (D36).
- Spot-check `data/processed/*/spot_check.md`.
- Set the GitHub repo description and topics in the UI.
