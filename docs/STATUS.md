# Project status and handoff

Last updated: 2026-09-25 (end of Milestone 2, part 1)

## Working rules (from Hamza)
- Hamza is the only author. No "Co-Authored-By", "Generated with …" or other AI attribution in commits, PRs, code or docs.
- In a fresh clone, recreate the commit-msg hook (git hooks are not versioned):
  ```sh
  printf '#!/bin/sh\ngrep -v -i -E '"'"'^(Co-Authored-By:|.*Generated with)'"'"' "$1" > "$1.tmp" && mv "$1.tmp" "$1"\n' > .git/hooks/commit-msg
  chmod +x .git/hooks/commit-msg
  git config user.name "Hamza Bilal" && git config user.email "hamzaakbar666333@gmail.com"
  ```
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

## Next
1. **Finish M2:** index with BGE-M3 and run the dense and hybrid baselines.
   ```sh
   pip install -e ".[dev,ml]"
   python -m ingestion.index
   python -m eval.run_eval --retriever dense --split test
   python -m eval.run_eval --retriever hybrid --split test
   ```
   Then fill the ablation rows in README.md and commit the reports in `eval/reports/`. This needs network access to
   `huggingface.co` / `*.hf.co`, which was blocked in the first build environment.
2. **M3:**
   - Query understanding (language detect, English rewrite with the Groq rewrite model, tax year, direct section lookup).
   - Urdu glossary: `data/glossary_ur.csv`.
   - bge-reranker-v2-m3.
   - FastAPI `/ask` returning `{success, data, error, code}`, with a grounded, cited answer and a citation check.
   - Complete the ablation table.

## Open items for Hamza
- Verify eval questions by hand (set `verified: true`).
- Spot-check `data/processed/*/spot_check.md`.
- Set the GitHub repo description and topics in the UI.
