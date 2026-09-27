# Project status and handoff

Last updated: 2026-09-27 (launch prep: D63 fixed, laptop + ngrok hosting, committed index; roadmap in
[`ROADMAP.md`](ROADMAP.md))

## Overall status (2026-09-27)
Phase 1 is ready to launch as soon as Hamza runs the backend on his laptop and the frontend is deployed on Vercel
(launch checklist below). Hosting (D64): the API on Hamza's Windows laptop behind his free ngrok static domain
(`https://resident-coil-delusion.ngrok-free.dev`), the frontend on Vercel; an Oracle Always Free kit is ready for
later (`deploy/oracle/`). The Vercel deploy itself was **not** done from the session (no `VERCEL_TOKEN`, and
`api.vercel.com` is blocked by the session's network policy). D63 (non-ATL rates) is fixed and checked (D63). The
end-to-end eval with the gte reranker has run 42 of 189 test questions (29 in scope: 27 with a correct citation;
answer judge 19 of 29 strict / 23 of 29 lenient, lower than the English-heavy first batch: residency, section 102,
widow's return and vehicle-perquisite answers are wrong or incomplete in Urdu / Roman Urdu). Roughly 48% of the
whole project is done (Phase 1 about 92%).

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
Groq and Gemini stay on free tiers (D53). Quota-bound runs go first; each stops at the first daily-limit error
(no retries) and resumes from its cache next time. Quota-free work fills the rest of the session.

| # | Command | Left after 2026-09-27 | Quota |
| --- | --- | --- | --- |
| 1 | `python -m eval.run_e2e --split test --order mixed` | 147 of 189 (42 run with gte + D63: Urdu 14, Roman Urdu 14, English 1, out of scope 13); the mixed order asks ur-027 / ru-027 first, so Urdu and Roman Urdu reach 15 each | GPT OSS 120B, ~30-60 answers/day (the D63 companions make some prompts longer) |
| 2 | `python -m eval.judge_answers --split test` | new answers after each e2e run (29 judged with gte) | Qwen |
| 3 | `python -m eval.make_answer_check` | **once**, when ≥ 50 in-scope answers exist (29 now): the sheet for Hamza (fixed seed) | none |
| 4 | `python -m eval.verify_testset` | Qwen: done (en-092 waits for a practitioner, D58); Gemini second opinion: 147 of 169 left (20 of 22 agree) | Gemini 20/day |
| 5 | `python -m eval.summary` | refresh the eval page numbers | none |

When a judge flags a question: check the flag against the law text, record the fix in `eval/review/changes.json`,
run `python -m eval.apply_changes` (it also updates translations), and commit. Update the counts above, in README and
in D58 after every run.

## Launch checklist (Day 3, for Hamza)
Do these in order. Steps 1-4 are one time only.

1. [ ] **Laptop:** install Python 3.11 (next to 3.14 is fine), Git and ngrok; `ngrok config add-authtoken ...`;
   `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` ([`RUN_ON_MY_LAPTOP.md`](RUN_ON_MY_LAPTOP.md) steps 1-4).
2. [ ] **Laptop:** `git clone`, then `.\scripts\run_local.ps1` (first run ~30 min: libraries, index, models); paste
   the Groq key when asked. Power settings: never sleep while plugged in.
3. [ ] **Check:** `.\scripts\run_local.ps1 -Check` shows two OKs; open
   `https://resident-coil-delusion.ngrok-free.dev/health` in a browser.
4. [ ] **Vercel** (not done by the session): vercel.com → Add New → Project → import `hamzabilal000/mahsool.ai` →
   Project Name **`mahsool-ai`** → Root Directory **`frontend`** → Deploy. (Or `VERCEL_TOKEN=... sh
   scripts/deploy_vercel.sh`.) The URL should be `https://mahsool-ai.vercel.app`; a different name needs
   `MAHSOOL_CORS_ORIGIN_REGEX` in `.env` (CORS).
5. [ ] **Smoke test on the live site:** one English question ("tax on bank profit for a filer?" → 20% and 40%), one
   Roman Urdu ("bank munafa par kitna tax katta hai agar main non filer hun?"), one out-of-scope (PRA) → refused,
   thumbs up saved, `/eval` page loads, phone width. Then stop the laptop script: the site shows the "resting"
   message.
6. [ ] Put the Vercel link in README ("Live") and the GitHub repo description.
7. [ ] Before posting publicly: the answer-correctness numbers are low on Urdu / Roman Urdu (19 of 29 strict); fix
   the four known clusters (next section) or state them in the post. Demo video, LinkedIn post 1.

## Done
- **M5, 2026-09-27 (launch prep):**
  - D63 fixed (tuned on dev, checked once on test): Tenth Schedule rule and rate-card companions after the top 6
    answer sources; dev 11 of 11 questions that need the rule get it, test 25 of 30 (the 5 misses are rates that do
    not change with ATL status); the bank-profit example now gives 20% and 40%, and the Roman Urdu non-filer
    question (was refused) answers 40% from the 20% base doubled by rule 1. Glossary: "bank munafa".
  - Hosting (D64): Windows kit `scripts/run_local.ps1` (`py -3.11`, CPU PyTorch, index, Groq key into `.env`, ngrok
    window, uvicorn with SQLite, `-Check`), Ubuntu `scripts/run_local.sh`, `docs/RUN_ON_MY_LAPTOP.md`; Oracle kit
    for later (`deploy/oracle/`, `docs/DEPLOY_ORACLE.md`, syntax-checked only).
  - CORS for `https://mahsool-ai.vercel.app` and preview URLs plus the `ngrok-skip-browser-warning` header; the
    frontend sends that header and shows "Mahsool AI is resting right now. Please try again later." when the API
    is unreachable (checked in Chromium). Live `/ask` through uvicorn with the Vercel origin: 7.4 s.
  - Index committed (D65): `data/index/qdrant-index.tar.gz` (8.6 MB) + manifest, `scripts/get_index.py`; installed
    index reproduces dev Hit@5 98.0% / MRR 0.809 exactly. No GitHub Release (no tool here can create one).
  - `run_e2e --order mixed` and `--ids`; end to end 42 of 189, answer judge 29 (numbers above).
  - Vercel deploy **not done**: no `VERCEL_TOKEN` in the session and `api.vercel.com` blocked.

- **M5, third session of 2026-09-26:**
  - Reranker (Hamza's decision 1, D62): gte-multilingual-reranker-base (Apache-2.0) at 256 tokens replaces
    bge-reranker-v2-m3: dev Hit@5 98.0% and test 95.8% unchanged, MRR lower (test 0.906 → 0.848); rerank p50 4.7 s
    / p95 8.8 s on 2 cores (was ~30 s). Live `/ask`: ~7.5 s English, ~9 s Roman Urdu on 4 cores. mmarco-MiniLM
    (fast, loses 2 dev questions) and gte at 512 tokens rejected; jina-v2 excluded (non-commercial license).
  - Demo limits (decision 2, D59): 10 new questions per visitor per day, 60 answers a day for everyone, cached
    answers never count, "come back tomorrow" in the question's language; visitor key from `X-Forwarded-For`.
  - Prompt Guard 2 on Groq (D60): 0 of 249 test questions flagged; catches 4 of 6 English attacks, 1 of 4 Urdu,
    0 of 4 Roman Urdu.
  - Test deploy (decision 3) blocked: 402 from Hugging Face, Docker Spaces on free CPU need PRO (D61). Nothing
    created. Neon could not be reached from this container (only HTTPS goes out), so `DATABASE_URL` is untested.
  - Old branch `claude/mahsool-gemini-eval-cla2bx` confirmed gone (decision 4): only `main` on origin.
  - End to end 52 of 189 (quota), answer judge 38 of 39, Gemini second opinion 20 of 22 agree.
  - Live finding (D63): the answer to a filer question claimed the 20% rate is the same for non-ATL persons (law: 40%,
    Tenth Schedule rule 1); retrieval fix proposed, not done.

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

- **M5, second session of 2026-09-26:**
  - Qwen re-judge complete: 248 of 249 verified (en-092 waits for a practitioner); Gemini 19 of 21 agree, en-002
    fixed (D58).
  - End to end 50 of 189 (37 in-scope, all correct citations; 13/13 refusals); answer correctness 36 of 37 (D58).
  - Definition lookup (D57): test Hit@5 95.8%, FBR 94.9%.
  - Rate tables render as tables in citation cards.

- **M5 (in progress, 2026-09-26):**
  - Latency measured per stage (D52): the old default spent ~44 s reranking; the new default (15 candidates, max
    score for Urdu / Roman Urdu only, tuned on dev) takes rerank p50 15.1 s, total ~18 s with both live LLM calls
    (~2 s); test Hit@5 94.0% (was 93.5%). int8 reranker available but off (loses 2 dev questions). Still above the
    4 s target: needs Hamza's decision on a hosted or smaller reranker.
  - Free-tier safeguards (D53): no retries after a daily-limit error, answer cache (~30 ms for a repeated
    question), 20 new questions per visitor per day, friendly "try again tomorrow" message in three languages.
  - Deploy prepared, not live (D54): `Dockerfile`, `scripts/deploy_space.py`, `frontend/vercel.json`, keep-alive
    workflow, README "Deploy". The staged bundle was started locally and answered a live question.
  - Answer-correctness judge and the 50-answer check sheet written (D56), waiting for answers.
  - All 100 Urdu / Roman Urdu questions `language_ok` (D55).

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
`pip install -e ".[dev,ml]"`, **`python scripts/get_index.py`** (1 minute; no re-index), `cd frontend && npm install`.
`GROQ_API_KEY` and `GEMINI_API_KEY` set. Then the start-of-session steps above.

Run the app: `uvicorn backend.app.main:app --port 8000` and `cd frontend && npm run dev` → http://localhost:5173.

Rules learned the hard way: never `pkill -f` or `pgrep -f | kill` (it matches the calling shell); kill by exact
process id. Only one process may open the embedded Qdrant at a time (stop uvicorn before `run_e2e` / `run_eval`).
Keep GPT OSS 120B for the answers only. In a cloud session with `DATABASE_URL` set, uvicorn hangs at startup (no
Postgres egress): start it with `env -u DATABASE_URL`. Groq's per-minute token caps (120B 8k TPM, Qwen 7k ITPM) make
`run_e2e` ~2 answers a minute. After a re-index, re-pack: `python scripts/get_index.py --pack`.

## Next: rest of Milestone 5
1. Quota runs each session (table above), then the 50-answer sheet once.
2. Launch checklist above (Hamza), then README "Live" link.
3. Top answer failures from the gte run: residency (section 82: only the 183-day test, also en-029), foreign income
   exemption (section 102 not retrieved for ur-024 / ru-024), widow's return (section 115(3), ur-026 / ru-026),
   vehicle perquisite mixed-use rate (ur-015 / ru-015). Tune on dev equivalents first.
4. Latency ~7-9 s (D62); ONNX / int8 for gte or query-embedding cache.
5. Langfuse, demo video, LinkedIn post 1.

## Open for Milestone 5
- Vercel project not created (step 4 of the checklist).
- Answer correctness on Urdu / Roman Urdu: 19 of 29 strict (above).
- D63 companions add ~1k prompt tokens on ~1 in 4 questions (quota).
- The Oracle kit and the Windows script have not run on a real VM / Windows machine (syntax-checked; the
  PowerShell `.env` helpers were run under PowerShell 7 on Linux).
- Langfuse (D49) not implemented; citation cards repeat the chunk heading (cosmetic).

## Open items for Hamza
- The launch checklist above (laptop, Vercel).
- Optional: a GitHub Release `index-v1` with `data/index/qdrant-index.tar.gz` as its asset (the script prefers it).
- To test Neon from a cloud session, allow outbound Postgres (port 5432) to `*.neon.tech` in the environment's
  network settings, or test it from your machine.
- Langfuse account when deploying (README "Deploy").
- Review `data/glossary_ur.csv` as a native speaker (D25).
- Spot-check `data/processed/*/spot_check.md`.
- Tax-practitioner review of `eval/expert_sample.json` when you find one, plus en-092 (who decides the section 155
  rate, the landlord or the tenant? D58).
- Set the GitHub repo description and topics in the UI.
