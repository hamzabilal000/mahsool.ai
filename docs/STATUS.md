# Project status and handoff

Last updated: 2026-09-25 (Milestone 3, part 1: everything that doesn't need the Groq key)

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

## Next (M3 part 2, needs `GROQ_API_KEY` in the environment)
1. Setup: `sh scripts/setup-hooks.sh`, git identity, `pip install -e ".[dev,ml]"`, `python -m ingestion.index`
   (~30 min; the index is not committed). `eval/cache/rerank.tsv` already holds 6,000 reranker scores.
2. Check the key works with one call, then run on **dev** first:
   `python -m eval.run_eval --pipeline rewrite --split dev`, then `rewrite-rerank`, then `full`.
   Look at the rewrites in the report JSON; adjust the prompt on dev only. Then the same three on **test**.
3. On dev: try reranking with max(original, first rewrite) score (D26), and re-tune `refusal_threshold` (D27).
4. End-to-end on test: answers from GPT OSS 120B, refusal accuracy on the 21 out-of-scope questions, citation
   accuracy (cited section in gold/acceptable). Mind Groq free-tier limits (cache in `eval/cache/groq.jsonl`).
5. Fill the README ablation rows, save the bar chart PNG in `eval/reports/`, update docs, commit, push, stop.

## Open items for Hamza
- Verify eval questions by hand with `eval/REVIEW.md` (about 20 a day), and tell Claude Code which are wrong.
- Review `data/glossary_ur.csv` as a native speaker (D25).
- Add `GROQ_API_KEY` to the cloud environment's variables (D31).
- Spot-check `data/processed/*/spot_check.md`.
- Set the GitHub repo description and topics in the UI.
