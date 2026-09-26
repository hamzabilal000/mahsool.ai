# Mahsool AI — Roadmap

Project review of 2026-09-26 (repo state: `main` at 1c36082). Sections 2, 3, 10 and 11 of the review; the overall
status is in [`STATUS.md`](STATUS.md). Plan: [`PROJECT_PLAN.md`](../PROJECT_PLAN.md). Deviations and their reasons:
[`DECISIONS.md`](DECISIONS.md).

## 2. Milestone checklist

The plan's calendar starts on 28 Sep 2026; Weeks 1–4 were built before that date, so the project is ahead of the
calendar but behind on the quota-bound evaluation.

| Week / phase | Planned goal | Status | What's missing |
| --- | --- | --- | --- |
| Week 1 · Phase 1 | Repo setup; parse and chunk the Income Tax Ordinance; start the test set (90 English questions) | Done | Nothing. 885 chunks, 380/380 sections, 90 English questions. Docling replaced by PyMuPDF tables (D3). |
| Week 2 · Phase 1 | Rules 2002 + rate card; embed into Qdrant; Urdu + Roman Urdu questions; baseline Recall@5 on all 200 | Done | Nothing. 498 Rules chunks, 33 rate-card chunks, BGE-M3 hybrid index (1,416 points), 200 → now 249 questions. |
| Week 3 · Phase 1 | Query rewrite, hybrid search, reranker; FastAPI `/ask` with citation check; ablation table filled | Done (eval partial) | Ablation filled (10 setups). Missing: Prompt Guard input screening; end-to-end eval complete (17/189 with the current prompt); answer-correctness judging (D35); Ragas faithfulness. |
| Week 4 · Phase 1 | React chat UI, citation cards, feedback, Postgres logs, Langfuse | Partly done | UI, cards, feedback, logs done (SQLite locally; Neon Postgres supported but not configured). Langfuse deferred (D49). |
| Week 5 · Phase 1 | Fix top eval failures; Docker; deploy; README; demo video; LinkedIn post 1 | Not started | Latency fix (57 s → < 4 s), backend Dockerfile, deployment (backend + frontend + vector store), live link, demo video, LinkedIn post 1. README is current but has no live link. |
| Week 6 · Phase 2 | Sales Tax Act, Sales Tax Rules, Special Procedures Rules, ICT (Tax on Services) Ordinance | Not started | Ingestion configs, glossary terms, test questions, eval. |
| Week 7 · Phase 3 | Federal Excise Act + Rules, Customs Act + Rules; law filter in UI; test set covers 4 laws | Not started | Everything; law filter is a scope check today (D29). |
| Week 8 · Phase 4 | Finance Acts, SROs, circulars; tax-year versioning; "what changed" for 10 sample sections | Not started | Older snapshots, per-section history, SRO/circular ingestion, versioned search. |
| Week 9 · v2 | Salary calculator, Urdu voice, shareable links | Not started | All three. |
| Week 10 · wrap-up | Full re-evaluation; practitioner review; polish; eval page updated; LinkedIn post 2 | Not started | Tax-practitioner review (only an AI-tool review so far, D50), final eval, post 2. |

Cross-cutting items from the plan: CI runs lint, test-set validation and unit tests on every push, but **not** the
planned 30-question retrieval regression gate, and not the frontend tests.

## 3. Features checklist

**MVP (phase 1)**

| Feature | Status | Notes |
| --- | --- | --- |
| Chat in English, Urdu and Roman Urdu | Done | RTL + Nastaliq for Urdu script (D48). |
| Streamed answers | Done | Streams pipeline stages, then the citation-checked answer; not raw model tokens (D46). |
| Citation cards: law, section, title, original text, FBR PDF page link | Done | Rate tables show as raw `\| … \|` text. |
| Tax-year selector (defaults to TY2027) | Done | Only TY2027 law is loaded; earlier years shown as "not loaded". |
| "Show sources" panel with scores | Done | Reranker scores and search queries. |
| Thumbs up/down saved to the database | Done | SQLite locally; Postgres (Neon) supported, not yet used. |
| Starter questions (salaried, freelancers, businesses) | Done | Six questions, three languages. |
| Public evaluation page | Partly done | Built (`/eval`), reads committed reports; not public until deployed. |
| Guardrails: grounding, citation check, refusals, disclaimer, rate limit | Done | |
| Guardrails: Prompt Guard input screening | Not started | Planned in PROJECT_PLAN; not implemented. |
| Monitoring: Langfuse traces | Not started | Deferred to Milestone 5 (D49); timings are logged per answer. |

**Version 2**

| Feature | Status |
| --- | --- |
| Law filter (Income Tax, Sales Tax, Federal Excise, Customs) | Not started (scope check only, D29) |
| Salary tax calculator citing the rate table | Not started |
| "What changed this year" view | Not started |
| Urdu voice questions (Whisper on Groq) | Not started |
| Section browser | Not started |
| Shareable answer links | Not started |
| Admin page: upload PDF, re-index, re-run evals | Not started |

## 10. Plan for the rest

Free-tier budget used below: GPT OSS 120B ≈ 200k tokens/day (≈ 65 answers at ~3k tokens), Qwen ≈ 200k
tokens/day (≈ 100–150 judge calls), GPT OSS 20B shares a separate daily quota (rewrites are small), Gemini 20
requests/day. All three Groq quotas are rolling 24-hour windows.

| # | Step | Why this order | Estimate | Quotas | Hamza must |
| --- | --- | --- | --- | --- | --- |
| 1 | **Finish the Phase 1 eval**: Qwen re-judges the 56 waiting questions; end-to-end on the 172 remaining test questions; Gemini second opinion each session | Every public number depends on it; it only needs quota, so it runs at the start of every session alongside other work | 3–4 days (quota-bound), a few minutes of work per day | 120B ~520k tokens; Qwen ~100k; Gemini 20/day | Nothing (or approve a paid Groq tier to finish in one day) |
| 2 | **Answer-correctness judging** (D35): LLM judge compares each answer with the reference; Hamza hand-checks 50 as the plan says | The plan's first success target (≥ 85%) is not measured at all yet | 1 session + 1–2 days of quota | Qwen ~190 calls (~300k tokens) | Hand-check 50 answers (checklist provided) |
| 3 | **Latency**: fewer rerank candidates, ONNX/int8 reranker, cache embeddings of common queries; tune on dev, re-run test ablation | < 4 s is a target and a deploy blocker (57 s now); must be fixed before the demo | 1–2 sessions | 20B for rewrite re-runs only (cached mostly) | Decide on hosted reranker vs local (decision 2) |
| 4 | **Top eval failures**: Roman Urdu wrong refusals, FBR-question misses, rate-table rendering in cards, Prompt Guard | Plan's Week 5 goal; cheap wins before people see it | 1–2 sessions | 120B for re-running affected answers | Review the failure list |
| 5 | **Langfuse + deploy**: backend Dockerfile, Hugging Face Space (backend), Vercel (frontend), Qdrant Cloud or embedded index in the Space, Neon for logs, keep-alive, answer cache | Makes the MVP live (Phase 1 done) | 2 sessions | Answer quota for smoke tests | Create accounts/keys: Hugging Face, Vercel, Neon, Langfuse, (Qdrant Cloud); set secrets; decide Groq tier (decision 1) |
| 6 | **Demo video + README live link + LinkedIn post 1** | Plan: post 1 at the end of Week 5, once the live link works and Phase 1 numbers are complete | 1 session | none | Record/approve video; publish the post |
| 7 | **Phase 2: Sales Tax Act 1990, Rules 2006, Special Procedures Rules 2007, ICT services ordinance** | Plan order; reuses the pipeline; adds the law filter's first real use | 3–4 sessions | 20B rewrites for new questions; Qwen to verify ~60–80 new questions (~1 day); 120B e2e for them (~1–2 days) | Native check of new Urdu/Roman Urdu questions; glossary additions |
| 8 | **Phase 3: Federal Excise Act + Rules, Customs Act + Rules; law filter in UI** | Plan order; longer, more technical texts | 4 sessions | Same pattern as Phase 2 (~2–3 days of quotas) | Same as Phase 2 |
| 9 | **Phase 4: Finance Acts, SROs, circulars; tax-year versioning; "what changed"** | Needs all laws in place; hardest data work (older snapshots, amendment history) | 4–5 sessions | Moderate (rewrites, some e2e) | Decide which Finance Acts / SROs are in scope (decision 8) |
| 10 | **v2 features: salary calculator, shareable links, section browser, Urdu voice; admin page last** | Calculator and links are cheap and demo well; voice needs Whisper quota | 3–4 sessions | Whisper on Groq for voice | Decide which v2 features matter most |
| 11 | **Full re-evaluation, tax-practitioner review, polish, eval page, LinkedIn post 2** | Final numbers after all phases | 2 sessions + 4–6 days of quotas | 120B for the full e2e (~250+ questions ≈ 4 days) | Find a tax practitioner for the 30-question sample (and ideally the 50 hand checks); publish post 2 |

Total: roughly 22–28 working sessions plus quota waits, i.e. on the plan's 10-week calendar if about 3 sessions a
week happen and the quota runs overlap with other work.

**LinkedIn posts:** post 1 after step 6 (MVP live, complete Phase 1 numbers, demo video), around the end of the
plan's Week 5 (≈ 1 Nov 2026) or earlier. Post 2 after step 11 (all phases, practitioner review, final eval), around
Week 10 (≈ 6 Dec 2026). Do not post before the numbers in the post come from complete runs.

## 11. Decisions needed from Hamza

1. **Answer model quota for the public demo.** The free tier gives ~65 answers/day and failed the eval twice. *Recommendation:* enable Groq's pay-as-you-go tier with a monthly spend cap inside the < 2,000 PKR target (check current Groq pricing first), and keep the free tier for development.
2. **Latency approach.** *Recommendation:* try local fixes first (15 rerank candidates, int8/ONNX reranker, drop full-max if it costs too much time) and measure on dev; switch to a hosted reranker only if local stays above ~6 s.
3. **Hosting.** *Recommendation:* backend on a free Hugging Face Space (CPU, 16 GB RAM fits BGE-M3 + reranker), frontend on Vercel, logs on Neon, vector index embedded in the Space (1,416 points) instead of Qdrant Cloud until Phase 2 grows it.
4. **Deploy before or after the eval is complete?** *Recommendation:* finish steps 1–2 first (3–4 days of quota), so the live eval page and post 1 show complete numbers.
5. **Answer-correctness method.** *Recommendation:* Qwen as judge on all test answers plus your hand check of 50, as the plan says; report both.
6. **Tax-practitioner review.** *Recommendation:* yes, before post 2; send the 30-question sample now (it is ready), and ask whether they would also look at 20 answers.
7. **Gemini billing.** *Recommendation:* no; keep Gemini as an optional second opinion at 20/day.
8. **Scope of Phases 2–4.** *Recommendation:* keep Phase 2 in full; in Phase 3 do the Federal Excise Act and Customs Act first and add their Rules only if time allows; in Phase 4 limit to Finance Acts 2025–2026 and income-tax SROs/circulars for TY2026–2027.
9. **Monitoring.** *Recommendation:* create a free Langfuse Cloud account in step 5; it is needed to measure p50/p95 latency and cost as the plan says.
10. **The 20 Urdu / Roman Urdu out-of-scope questions without a language check.** *Recommendation:* read them (10 minutes) and mark `language_ok`.
11. **Old branch on GitHub.** *Recommendation:* delete `claude/mahsool-gemini-eval-cla2bx` in the GitHub UI (fully merged; the session proxy refused the delete).
