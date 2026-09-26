# Decisions and deviations from the plan

Newest first within each milestone. Each entry says what the plan said, what we did, and why.

## Milestone 1 — Repo setup and Income Tax Ordinance ingestion

### D1. Ingested the 30.06.2026 consolidated Ordinance, not the 20.02.2026 link in the plan
- **Plan:** link to the version amended up to 20 Feb 2026, with a note to check FBR for a post-budget version.
- **Found:** FBR's [Income Tax Ordinance page](https://www.fbr.gov.pk/Categ/Income-Tax-Ordinance/326) lists
  "Income Tax Ordinance, 2001 Amended upto 30.06.2026" (file dated 24 Jul 2026). It includes Finance Act, 2026
  amendments (73 chunks cite it), so it governs tax year 2027.
- **Done:** `ingestion/laws/ito2001.py` points at that file; `python -m ingestion.download --check-latest` re-checks
  the FBR page and exits with code 2 if a newer version appears.

### D2. Repository is `hamzabilal000/mahsool.ai`, created by hand
- **Plan:** `gh repo create mahsool-ai --public …` plus topics.
- **Why:** the build environment has no `gh` CLI and its GitHub integration may not create repositories, so Hamza
  created `mahsool.ai` himself. Commits use a repo-local `user.name`/`user.email`, and a `commit-msg` hook strips
  AI-attribution trailers.
- **Open:** the repo description and topics (rag, llm, urdu, fastapi, react, qdrant, pakistan, nlp) have to be set in
  the GitHub UI, because the tooling here has no way to set them.

### D3. PyMuPDF `find_tables` for rate tables; Docling deferred
- **Plan:** Docling for tables.
- **Done:** PyMuPDF's table finder, plus a clean-up step that fixes FBR-specific problems: it compacts misaligned
  merged cells, lifts the introducing sentence out as a caption, and splits stacked tables at repeated header rows.
- **Why:** Docling pulls in PyTorch and layout models (several GB) to extract about 70 tables. The First Schedule is the
  only table-heavy part, and the result is checked by regression tests. Every table chunk carries
  `needs_review: true`. We'll revisit Docling in Milestone 2 for the withholding-tax rate card, which is almost all
  tables.

### D4. Footnote zone = everything below the footnote separator line
- FBR PDFs put amendment notes under a 144 pt separator line. These notes often **quote the repealed text in full**
  (old sections, old rate tables), and the quote can run on for pages as separator-footnotes with no marker.
- Everything under the separator is kept only as amendment metadata (`amended_by`, `amendment_notes`) and never as
  chunk text. A footnote carried over from the previous page (no marker) is joined to that page's last footnote.
- A table that starts in, or straddles into, the footnote zone is dropped.
- **Why this matters:** an earlier rule ("the footnote zone starts at the first footnote marker") indexed the
  pre-2019 individual rate table (29% top slab) and the TY2026 salaried table as if they were current law. A regression
  test now asserts that both repealed tables are absent and the current 30.06.2026 table is present.

### D5. Token counts are estimated (≈ 4 characters per token)
- **Plan:** split sections over ~800 tokens.
- **Done:** `estimate_tokens = ceil(len(text) / 4)`, so Milestone 1 doesn't need the BGE-M3 tokenizer or model.
- **Next:** in Milestone 2, measure the real BGE-M3 token counts on the chunks and adjust the constant if needed
  (BGE-M3 accepts 8,192 tokens, so this is about retrieval precision, not model limits).

### D6. `tax_year_from` is per snapshot, not per section
- Every chunk from the 30.06.2026 snapshot gets `tax_year_from = 2027`, `tax_year_to = null`. The rule: a text amended
  up to date *d* governs the tax year containing *d + 1 day* (tax years end on 30 June, section 74).
- Per-section history is kept in `amended_by` (e.g. "Finance Act, 2025"). Proper "what was the rule in tax year X"
  versioning needs older snapshots and is Phase 4 (Milestone 8). When a newer snapshot is ingested, the older one gets
  `tax_year_to` set.

### D7. IDs: `chunk_id` for pieces, `section_id` for citations
- `section_id` is the citable unit: `ITO2001-s149`, `ITO2001-sch2-pI-cl13` (Second Schedule, Part I, clause 13),
  `ITO2001-sch1-pI-divI` (First Schedule, Part I, Division I).
- `chunk_id` is unique per piece: `ITO2001-s2-5` (5th piece of section 2), `ITO2001-sch1-pI-divI-t2` (2nd table).
- Eval gold labels use `section_id`, so splitting a long section differently later does not invalidate the test set.
- Qdrant point IDs (Milestone 2) will combine `chunk_id` and `version_date`, so snapshots can coexist.

### D8. Chunk text keeps FBR's amendment brackets
- Text is stored as printed, including `[inserted text]`; only empty brackets (`[ ]`, omitted text) and placeholders
  such as `[ ### ]` are removed. The brackets show readers which words were changed by amendment, and the answer
  step can quote the law verbatim. Superscript footnote markers are removed from the text and kept as metadata.

### D9. The preamble is not indexed
- The promulgation text before section 1 ("WHEREAS it is expedient…") has no legal content users ask about.

### D10. Processed chunks are committed; PDFs are not
- `data/processed/ITO2001/2026-06-30/chunks.jsonl` (≈ 1.9 MB) is committed so that tests, the eval validator and CI
  run without downloading from FBR. Raw PDFs are gitignored; their URL and SHA-256 are in `data/sources.manifest.json`.

### D11. Coverage is checked against the PDF's own table of contents
- The TOC (pages 2–19) is parsed from the raw text stream and compared with the sections found in the body. The
  check found 380 live sections, 0 missing and 0 extra. Along the way it caught an FBR typo (`[230E Directorate…`
  with no full stop), which is now handled.

### D12. Dev/test split for the eval set
- Plan: 60 dev / 140 test over 200 questions. English: seeded (2026) random 27 dev / 63 test (30/70).
- Urdu and Roman Urdu translations will carry a `source_id` and **inherit the split of their English source**, so
  a translation of a dev question can never leak into the test split. The validator enforces this.
- Every generated question is `verified: false` until Hamza checks it against the PDF.

### D13. `needs_review` flag on schedule chunks
- Section chunks are covered by the TOC oracle and tests. Schedule clauses, schedule parts and tables have messier
  layouts, so all 396 carry `needs_review: true` until they are spot-checked.

## Milestone 2 — Rules, rate card, retrieval harness, full test set

### D14. Hugging Face was blocked, so the BGE-M3 baseline came after the BM25 one *(resolved, see D22)*
- At first the build environment's network policy denied `huggingface.co`, so the BGE-M3 and bge-reranker weights
  could not be downloaded. Everything around the model is built and tested (embedder wrapper, Qdrant store with dense +
  sparse vectors, RRF, tax-year filters, eval runner), using a deterministic fake embedder and in-memory Qdrant.
- The **BM25 keyword baseline** is measured now (no model needed). The dense / hybrid rows of the ablation table will
  be filled in as soon as the model can be downloaded, either here after the domain is allowed, or on Hamza's machine
  with `pip install -e ".[ml]" && python -m ingestion.index && python -m eval.run_eval --retriever dense`.

### D15. No Docker: embedded Qdrant and hosted Neon Postgres; Docker Compose is optional
- Hamza's laptop has no Docker, and neither does the build environment. `qdrant-client` has an embedded mode (same
  API, stored under `data/qdrant/`), used when `QDRANT_URL` is empty. This is the default in `.env.example`.
- Postgres (logs and feedback, Milestone 4) will be a free hosted **Neon** database, set through `DATABASE_URL`.
  `database_url` now defaults to empty instead of a localhost Docker URL.
- `docker-compose.yml` stays as an **optional** extra for anyone who prefers local servers. The README's
  "Run locally" steps don't use it.
- Limits of embedded mode: one process at a time can open `data/qdrant/` (index, then evaluate, not both at once),
  and search is brute force. That's fine for ~1.4k points; switch to a server (Qdrant Cloud free tier or Docker)
  when the corpus grows or the API is deployed.
- Payload indexes (law_code, section_id, tax_year_from) are created, but only take effect on server Qdrant.

### D16. Income Tax Rules: only the rules body is indexed
- Latest FBR version is "Amended upto 15.09.2026" (governs tax year 2027). 381/381 rules in its table of contents
  are chunked; 211 of 498 chunks carry amendment metadata (mostly SROs).
- Pages 429–1198 (First to Fourth Schedules) are blank **forms**: notices, return and statement templates. They
  answer no questions and would add noise, so they are skipped. Forms printed *inside* a rule (e.g. the appeal
  petition in rule 94) stay, because they are part of that rule.
- One known cosmetic issue: rule 231H's `part` metadata reads "Part III: Applicant" (picked up from a form title
  in the same chapter). The text and ids are correct.

### D17. The withholding rate card gets its own grid parser
- The card is a six-column Excel export whose merged cells defeat generic table extraction. `ingestion/ratecard.py`
  rebuilds the grid: column edges from ruling lines snapped to the header words, rows from description-cell starts
  (cells are ≥8 pt apart, wrapped lines 2–3 pt) plus rate "anchors", and section labels matched top-aligned.
  Output: 29 sections, 33 chunks, pinned by regression tests on known rows.
- The card is a convenience guide, not law: FBR says the Ordinance prevails. Every card chunk states this, has
  `tax_year_from = tax_year_to = 2027`, and is linked from eval questions only as an *acceptable* source, never gold.
- Docling is still not needed: the grid approach handles the card.

### D18. Test set: 200 questions, 60 dev / 140 test, translations share gold and split
- 40 English questions (12 dev, 28 test) were rewritten naturally in Urdu script and in Roman Urdu (the way
  people type: "non filer hun, bank se cash nikalwaun to kitna tax katega?"). Each carries `source_id`, and the
  validator enforces identical gold sections and split, so a question never appears in both dev and test.
- 30 out-of-scope questions (10 per language): provincial taxes (PRA/SRB/KPRA, stamp duty, property tax), sections
  that don't exist (999Z, 888, 777, 250B), customs tariff, case law, foreign tax, future budgets, non-tax.
- New field `acceptable_section_ids` lists alternative sources that also answer (e.g. the rate-card row for a
  rate). They count for Hit@5 / MRR, not for the stricter "all gold" recall.
- Reference answers stay in English as a content key; the reply language is judged separately in Milestone 3.

### D19. Metric definitions
- Retrieval is scored on **section ids** (several chunks of one section count once).
- **Hit@5** = share of questions with at least one gold or acceptable section in the top 5. This is the plan's
  "Recall@5" (most questions have one gold section). **Recall@5 (all gold)** = share of a question's gold sections
  found, which is stricter for multi-section questions. **MRR@10** = mean of 1 / rank of the first relevant section.
- Out-of-scope questions are excluded from retrieval metrics; refusal accuracy is measured end to end in Milestone 3.

### D20. Caveat on the BM25 baseline
- The English questions were written while reading the section text, so they share wording with the law, and
  keyword search benefits (87% Hit@5 on English). Real user questions are vaguer. The Urdu script result (≈4%) is the
  honest signal: keyword search cannot cross languages.

### D21. Real BGE-M3 token counts: the 4-characters estimate holds; encoder max length raised to 2,048
- Closes the open item in D5. The BGE-M3 tokenizer on the embedded text (context header + chunk) gives **4.02
  characters per token** on average (ITO 4.03, Rules 4.15, rate card 3.23 because of table markup). Median chunk
  ≈ 250 tokens, 95th percentile ≈ 755.
- The estimate constant stays at 4. But 19 of 1,416 chunks are over 1,024 real tokens (longest: Second Schedule
  Part IV clause 12N pieces, 1,294 tokens), because tables and headers tokenize worse than prose. With
  `embedding_max_length = 1024` their tail would have been silently cut off before embedding.
- **Done:** `embedding_max_length` is now 2,048 (BGE-M3 supports 8,192). The chunker's 800 budget is unchanged.

### D22. BGE-M3 baseline: hybrid (dense + sparse, RRF) is the retrieval default for Milestone 3
- Hugging Face became reachable, so BGE-M3 (2.3 GB) was downloaded and all **1,416 chunks** (885 ITO + 498 Rules
  + 33 rate card) were embedded, dense (1,024-d) + sparse, into embedded Qdrant: **28 minutes on a 4-core CPU**,
  fp32, no GPU. The index (≈ 19 MB) is gitignored and rebuilt with `python -m ingestion.index`.
- Results on the **test split** (Hit@5 is the plan's "Recall@5", D19):

  | Retriever | English | Urdu | Roman Urdu | All Hit@5 | All Recall@5 (all gold) | All MRR@10 |
  | --- | --- | --- | --- | --- | --- | --- |
  | BM25 | 87.3% | 3.6% | 50.0% | 58.8% | 55.9% | 0.496 |
  | BGE-M3 sparse | 92.1% | 7.1% | 60.7% | 64.7% | 62.2% | 0.550 |
  | BGE-M3 dense | 98.4% | 78.6% | 57.1% | 84.0% | 79.4% | 0.735 |
  | **Hybrid (RRF)** | 95.2% | 78.6% | **67.9%** | **84.9%** | **81.9%** | **0.764** |

- **Hybrid is the baseline** and the Milestone 3 default: best overall and best on Roman Urdu. Dense alone is
  slightly better on English (98.4% vs 95.2%) and matches hybrid on Urdu script, where sparse adds nothing (it
  can't match Urdu script to English text). Language-aware fusion is a possible later tweak, decided on the dev
  split only.
- The dev split agrees (hybrid 84.3% Hit@5, MRR 0.723), so this isn't a test-split accident.
- **Target not met yet:** Urdu 78.6% and Roman Urdu 67.9% vs the ≥ 80% goal. Roman Urdu is the weak spot: BGE-M3
  saw little romanized Urdu in training ("gaari", "fasal", "jama karwana" mean little to it). The planned English
  query rewrite in Milestone 3 targets exactly this.
- Caveats: no question is hand-verified yet (`verified: 0/200`), and the English questions share wording with the law
  (D20).

### D23. PyTorch came from PyPI, not the CPU-only wheel index
- `download.pytorch.org` is not reachable from the build environment, so `pip install -e ".[ml]"` pulled the default
  PyPI wheel (CUDA build, larger download). It runs on CPU unchanged. On a laptop without an NVIDIA GPU,
  `pip install torch --index-url https://download.pytorch.org/whl/cpu` before `pip install -e ".[dev,ml]"` saves
  ~2 GB of disk; either way works.

### D24. Git hooks are versioned in `scripts/`
- Each new session or clone loses `.git/hooks`. The `commit-msg` hook that strips AI-attribution lines
  (`Co-Authored-By:`, `Claude-Session:`, `Generated with …`) now lives in `scripts/commit-msg`, and
  `sh scripts/setup-hooks.sh` installs it in one command.

## Milestone 3 — Query understanding, reranking, `/ask` (in progress)

### D25. Urdu glossary: 170 concepts, 1,040 spellings, with section pointers
- **Plan:** a hand-built file of 200–300 terms.
- **Done:** `data/glossary_ur.csv` has 170 concept rows, each with its Roman Urdu spellings (`katoti|kattoti|katega…`),
  Urdu-script spellings, the legal English term and, where one section clearly governs it, section ids. That's
  1,040 matchable spellings in total. A test checks that every section id exists.
- Matching: Urdu spellings match as substrings. Roman Urdu terms match on word boundaries, and terms of 5+ letters
  also match up to 3 extra letters, because verbs inflect (`khareed` → `khareedna`, `khareedni`). Only the entries
  found in the question go into the rewrite prompt (max 15, longest first).
- **Leak risk, and what we did about it:** while writing the glossary I had already seen seven test-question misses
  in the Milestone 2 report. General vocabulary (fasal, tuition fee, jama karwana, adjust) stays, because any tax
  glossary has it. A phrase copied from a test question ("office ki gaari") was removed. The glossary's effect is
  measured as its own ablation row, and **Hamza should review the glossary** (it needs a native speaker's check
  anyway).

### D26. Reranker: bge-reranker-v2-m3 on the top 30, 512-token passages; far too slow for CPU serving
- On the build machine's 4 CPU cores, reranking 30 chunks takes **27 s at 512 tokens** (37 s at 1,024). The time
  is real compute: a 568M-parameter cross-encoder reading ~9,000 tokens per question.
- For the eval this is fine: scores are cached per (question, passage) in `eval/cache/rerank.tsv` (committed), so
  later ablation rows only score new candidates.
- **For serving it breaks the < 4 s latency target.** Options for Milestone 5: a quantised ONNX reranker, reranking
  the top 10–15 only, a GPU Space, or a hosted rerank API (the plan's risk table lists these). Decide with latency
  numbers then.
- The reranker scores the **original question** (it's multilingual). Scoring with the English rewrite as well is a
  dev-split experiment once rewrites exist.

### D27. Score-based refusal is almost off (threshold 0.001)
- Idea: refuse without calling the LLM when the best reranker score is low. On the dev split the scores don't
  separate well: answerable Roman Urdu questions often score below 0.01, just like out-of-scope ones.

  | threshold | out-of-scope refused (dev, 9) | answerable questions wrongly refused (dev, 51) |
  | --- | --- | --- |
  | 0.001 | 1 | 0 |
  | 0.01 | 6 | 6 |
  | 0.05 | 7 | 12 |

- Chose **0.001** (no false refusals on dev). Refusal mostly relies on the other checks, cheapest first: the
  rewrite model's **scope** label (provincial tax, customs, not tax), a **tax year** with no law loaded, a named
  section that **doesn't exist**, then the answer model saying the sources don't answer, then the **citation check**.
  To be re-tuned on dev after rewrites exist.

### D28. Direct section lookup pins the named section above search results
- "section 149", "sec. 236k", "u/s 155", "dafa 4AB", "دفعہ ۱۴۹" → `ITO2001-s…`; "rule 5", "qaida 13P", "قاعدہ" →
  `ITR2002-r…`. Up to 3 pieces of the named section go on top (pieces the search also found come first). A reference
  that doesn't exist ("section 999Z") is reported, and if it's the only reference the answer is a refusal.
- Effect on the test split: English Hit@5 95.2% → 96.8%, other groups unchanged (few Urdu questions name a section).

### D29. Law "filter" is a scope check for now
- **Plan:** filter by law when detected.
- All indexed text is federal income tax, so filtering between the Ordinance and the Rules would only hide useful
  text (questions often need both). Instead the rewrite model labels the question's **scope**
  (`income_tax` / `other_federal_tax` / `provincial_tax` / `not_tax`) and anything other than income tax is refused.
  A real law filter arrives with the Sales Tax phase, when there is more than one law family to choose from.

### D30. `/ask` contract
- Envelope `{success, data, error, code}`. `code` is `OK`, `REFUSED` (still `success: true`, with
  `data.refusal_reason`), `VALIDATION_ERROR` (422), `RATE_LIMITED` (429, 20/min per IP, in memory), `LLM_UNAVAILABLE`
  (503) or `INTERNAL_ERROR` (500).
- `data` has the answer, citations (law, label, full text, FBR PDF link with `#page=`), the top 10 sources with
  reranker scores ("Show sources"), the English search queries, tax year (and whether it was assumed), confidence,
  warnings from the citation check, the disclaimer in the user's language, and timings.
- The answer model gets at most 2,500 characters per source (6 sources ≈ 4k tokens) to stay inside Groq free-tier
  token limits.
- **Deferred:** Prompt Guard input screening (Milestone 5, with deployment). The prompt already tells the model to
  treat sources and question as data, not instructions.

### D31. The Groq key goes in the environment, not the chat
- The key is read from `GROQ_API_KEY` (environment or local `.env`, never committed). In the cloud build environment it's
  added as an environment variable in the environment settings, which only a new session picks up. So the ablation
  rows that need the LLM (rewrite, glossary) and the end-to-end check run in the next session.
- All Groq outputs used in evaluation are cached in `eval/cache/groq.jsonl` (committed), so the published numbers
  can be replayed without a key.

### D32. Rewrite prompt v2, tuned on dev only
- The first prompt (M3 part 1) was run on the 60 dev questions and its outputs were read by hand. Three problems:
  1. **Invented section numbers.** 67 of 240 dev rewrite queries named a section the user never wrote, most often
     "section 236K", which the prompt itself used as an example. A wrong section number in a query pulls the wrong
     chunk into the dense and sparse searches.
  2. **Scope labels.** Without the glossary, "NTN for a commercial electricity connection" and "non filer, bank cash
     withdrawal" were labelled `not_tax` (they'd be refused). With the glossary, "stamp duty in Punjab" and "SRB
     registration" were labelled `income_tax`, because the hints ("jaidad" = immovable property) made them look
     like income tax.
  3. **Glossary noise.** Urdu terms matched inside other words: "دن" (days, section 82) inside "آمدن" (income).
- **v2** (`backend/app/rag/query_rewrite.py`): never add a section or rule number the user didn't write; convert
  lakh / crore to rupees; scope is decided from what the question asks, with a list of what counts as income tax
  (withholding, filers, ATL, NTN, returns) and what is provincial (PRA, SRB, stamp duty, property registration).
  Urdu glossary terms now have to start a word.
- Dev result: scope errors 6 → 2 (without the glossary) and 4 → 3 (with it); invented section numbers 67 → 7. The
  two left in both modes are handled by other checks: "section 777" (doesn't exist → refusal) and "tax year 2028
  slabs" (D34). SRB registration with the glossary is still labelled income tax.
- The first prompt's outputs stay in `eval/cache/groq.jsonl` (they're keyed by prompt), so the comparison can be
  replayed.

### D33. Retrieval ablation with the LLM rewrite: the reranker undoes the rewrite on Urdu and Roman Urdu
- *Update: `full-max` became the `/ask` default, decided on the dev split (D40).*
- **Test split, Hit@5** (all rows include section lookup from the hybrid baseline on):

  | Setup | English | Urdu | Roman Urdu | All | Recall@5 (all gold) | MRR@10 |
  | --- | --- | --- | --- | --- | --- | --- |
  | Hybrid + lookup | 96.8% | 78.6% | 67.9% | 85.7% | 82.8% | 0.781 |
  | + reranker, no rewrite | 96.8% | 92.9% | 64.3% | 88.2% | 85.3% | 0.805 |
  | + rewrite, no reranker | **98.4%** | **100%** | **89.3%** | **96.6%** | **94.1%** | **0.862** |
  | + rewrite + reranker | 96.8% | 89.3% | 71.4% | 89.1% | 85.7% | 0.827 |
  | + glossary = full pipeline (`/ask` default) | 96.8% | 92.9% | 75.0% | 90.8% | 88.2% | 0.834 |
  | full, rerank with max(question, rewrite) score (not adopted, see below) | 96.8% | 92.9% | **92.9%** | 95.0% | 93.3% | 0.891 |

- **The rewrite is the big win**: Roman Urdu 67.9% → 89.3%, Urdu 78.6% → 100%. Searching with the law's English
  words works, which was the Milestone 2 hypothesis.
- **The reranker then takes much of it back** for Urdu (100% → 89.3%) and Roman Urdu (89.3% → 71.4%). It scores the
  chunks against the *original* question, and bge-reranker-v2-m3 reads Roman Urdu poorly (LEARNING M3 §5), so it
  pushes correct chunks that the rewrite found out of the top 5. The glossary recovers part of it (71.4% → 75.0%).
- **What dev said, and why the default is still the full pipeline:** on dev the full pipeline was best overall
  (94.1% vs 92.2% for rewrite without reranker, MRR 0.908 vs 0.797: the reranker helps English ranking a lot on
  dev), so it stayed the default. On test the order flips. The defaults are not changed on test results; this is
  a Milestone 5 item, decided on dev: for example reranking with the English rewrite, or skipping the reranker for
  Roman Urdu.
- **Dev experiment, reranking with max(question score, first-rewrite score)** (`--pipeline full-max`): dev Hit@5
  100 / 100 / 83.3 vs 100 / 100 / 75.0 for `full`, but MRR 0.887 vs 0.908 and twice the reranker time (already the
  latency problem, D26). One Roman Urdu question out of 12 isn't enough evidence for doubling the cost, so it was not
  adopted. **It was then run once on test for the record** (table above): Roman Urdu 75.0% → 92.9%, best MRR, same
  English and Urdu. Dev and test point the same way, so this is the first Milestone 5 decision, together with a
  faster reranker (it doubles the ~29 s CPU reranking). The default was not switched on the strength of a test
  result.
- Roman Urdu is still below the ≥ 80% target with the default pipeline (75.0%); Urdu (92.9%) and English meet it.

### D34. Refusal threshold 0.001 → 0.0005, and future tax years are refused
- Re-tuned on dev with the full pipeline. Two answerable Roman Urdu questions (ru-009 rent, ru-011 cash withdrawal)
  have a best reranker score just under 0.001 and their gold section in the top 5, so 0.001 would refuse them.
  0.0005 refuses none and catches the same out-of-scope questions (none, in practice: every out-of-scope dev
  question with a score that low is already refused by the scope check). The score check stays as a last net.
- "What will the salaried slabs be for tax year 2028?" passed every check: only years *before* the loaded law were
  refused. The law for a tax year after the current one (TY2027) hasn't been enacted, so `AskService` now refuses it
  with `TAX_YEAR_NOT_COVERED` and says so ("The law for tax year 2028 has not been made yet …").

### D35. End-to-end evaluation (`eval/run_e2e.py`): what is measured
- Runs the same `AskService` as `/ask` on every question of a split. In-scope: answered (not refused) and **correct
  citation**, meaning at least one cited section is a gold or acceptable section. Out-of-scope: refused.
- **Answer correctness is not scored yet.** It needs a judge (an LLM or a person) comparing each answer with the
  reference answer, and the reference answers aren't hand-verified. With Groq's free tier a judge would also double
  the token cost (D36). Planned for Milestone 5, after Hamza's review of the test set.

### D36. Groq free tier: 200k tokens per day on GPT OSS 120B
- Limits seen in the response headers and errors: 8,000 tokens per minute, 1,000 requests per day and **200,000
  tokens per day** per model. An answer call is ~3,000 tokens (6 sources, capped at 2,500 characters each), so
  about 65 answers a day.
- The client now **fails fast on the daily limit** instead of retrying (the quota frees up over hours): `/ask` returns
  `LLM_UNAVAILABLE` (503) right away, and `run_e2e` lists those questions as "not run", scores the rest, and resumes
  from the cache on the next run.
- For the demo in Milestone 5 this is a real constraint: a paid Groq tier, a smaller answer model, or fewer / shorter
  sources.

### D37. Chunk titles: bracketed headings, and units the PDF prints without a heading
- **Found:** titles like "Subject to this Ordinance, a surcharge shall be payable by" (ITO 4AB), ". Application for
  initiation of Mutual Agreement Procedure" (Rules 19D–19G) and body text as the title of Rules 22, 27B–27Q, 30, 31,
  49, 199.
- **Fix** (`ingestion/chunk.py`): brackets and dots before a title ("[19D].") are stripped; more title separators are
  recognised (":-", "─", "−", "word- (1)", ". (1)", ": The …"); when the PDF prints no heading, the title is left
  empty (labels then read just "Rule 27B") instead of repeating the first words of the text.
- **ITO 4AB:** the FBR PDF prints "[[4AB] Subject to this Ordinance, a surcharge …" with no heading, and its table of
  contents copies those words. Its title is set by hand to **"Surcharge"** (`title_overrides` in
  `ingestion/laws/ito2001.py`), approved by Hamza. It is a label only; the law text is unchanged.
- 52 chunks changed title; the text of the chunks changed only in "(continued)" header lines. Those 53 chunks were
  re-embedded into the index (upsert by id); a full `python -m ingestion.index` gives the same result.

### D38. Test-set verification without a tax expert: two LLM judges plus a number check in code
- **Plan:** Hamza verifies every question by hand. He has no tax background, so this is replaced by
  `eval/verify_testset.py`:
  1. Two independent judges on Groq read **only the gold section text** and answer in JSON: does the section answer
     the question, does the reference answer match the section, and a short reason.
  2. Code checks that every number, percentage and amount in the reference answer appears in the gold text (words
     and digits: "ten million" = "Rs. 10 million"; legal references like "section 22" are not quantities; inputs
     given in the question and arithmetic written out in the answer, "5% x 200,000 = Rs. 10,000", are accepted).
  3. Both judges "yes" on both checks and every number found → `"verified": "machine"`; anything else goes to
     `eval/FLAGGED.md` with the reasons, and is fixed or removed.
- **Judges:** `openai/gpt-oss-120b` and **`qwen/qwen3.8-27b`**. The plan named `llama-3.3-70b-versatile`, which
  Groq no longer serves to this account; Qwen is a different model family from GPT OSS, so the two judges stay
  independent. Approved by Hamza. Qwen answers without "thinking" (its free tier allows 1,000 output tokens a
  minute and counts thinking tokens).
- Translations (Urdu, Roman Urdu) share gold sections and reference answer with their English source; the source is
  judged once and a translation inherits the result only if its wording is approved (`language_ok`, D41).
- Out-of-scope questions have no gold text: the judges read the question and the list of covered laws and say
  whether it must be refused.
- Long gold sections are cut to the most related chunks (≤ 1,500 tokens per judge call, for Groq free-tier limits);
  the number check always uses the whole section.
- A random, stratified sample of 30 test questions goes to a human expert (`eval/expert_sample.json`).

### D39. FBR-sourced questions
- 39 test questions (`fbr-001` … `fbr-039`, `"source": "fbr"`, `source_url` on each) were **collected manually from
  public FBR pages**: the help.fbr.gov.pk knowledge base, fbr.gov.pk "Income Tax Basics", the Taxpayer's Facilitation
  Guides IR-IT-01 (Basic Concepts) and IR-IT-02 (Obligation to File), and the FBR–GIZ FAQ on tax treaties.
- Most of these pages date from 2012–2023. Every answer was checked against the current Ordinance (30.06.2026) and
  the reference answer written from the current text. **Dropped because the law changed** since FBR published them:
  the residence test (120 + 365 days, removed from section 82), active taxpayers' list rules (Rule 81B now: daily
  updates, late filers only after surcharge), "total income" (now includes exempt income), taxable income
  (ambiguous against FBR's wording), the teacher/researcher reduction (now 25%, ceased after tax year 2025), the
  senior-citizen reduction (no longer in the Ordinance), the salary cash-payment limit (Rs. 32,000 now, not 15,000),
  the AOP definition (now includes LLPs), the loan/gift rule of section 39(3) (digital means added), revised returns
  (now need the Commissioner's approval), the refund time limit (three years, not two), and "section 107 empowers
  FBR" (the law says the Federal Government).
- They are English questions on the test split and are reported as their own group ("fbr") next to the written
  English questions.

### D40. `/ask` now reranks with max(question, rewrite) score ("full-max")
- Decided on the **dev split** (D33): Hit@5 **96.1% vs 94.1%** for the previous default, Roman Urdu **83.3% vs
  75.0%**, English and Urdu unchanged at 100%. MRR is slightly lower on dev (0.887 vs 0.908).
- Cost: twice the reranker work per question; latency is already the open Milestone 5 problem (D26).
- `rerank_query = "max"` in `backend/app/config.py`, used by `/ask` and `eval/run_e2e.py`. The ablation presets keep
  both variants (`full` = question only, `full-max`).

### D41. Language check of the Urdu and Roman Urdu questions
- 67 translations were read by Hamza as a native speaker and marked `"language_ok": true`; two of them were reworded
  (ur-001, ur-002). ur-001 was given in Roman Urdu and is kept in Urdu script (same words), because it belongs to the
  Urdu-script group.
- The remaining 13 (ur-004, ru-001 … ru-012, all dev split) were **approved as they are, without a line-by-line
  native-speaker read**, and are also marked `"language_ok": true`.

### D42. Judge 1 is Gemini Flash (Google), not GPT OSS 120B; LLM provider and model are set per role
- **Why:** Groq's free tier (200k tokens a day on GPT OSS 120B, D36) cannot cover the test-set judge, the end-to-end
  answers and the reruns. **Judge 1 changed from GPT OSS 120B to Gemini Flash** on Google's Gemini API
  (OpenAI-compatible endpoint). The judges are now from **two different model families (Gemini, Qwen), and neither
  wrote the questions**. Judge 2 stays Qwen (`qwen/qwen3.8-27b`) on Groq (D38). Answers stay on GPT OSS 120B and
  rewrites on GPT OSS 20B, both on Groq.
- **Config:** `backend/app/config.py` has a provider and a model per role (`answer`, `rewrite`, `judge1`, `judge2`),
  plus per-provider rate limits and model fallbacks. `backend/app/llm.py` is one OpenAI-compatible client with a
  client-side rate limiter (requests per minute and per day), fail-fast on daily quotas, fallback to the next model
  on 404, and the JSONL cache (a run resumes from it, and a cached answer from a fallback model counts).
- **Model id:** the plan was `gemini-3-flash`, falling back to `gemini-2.5-flash`. Google serves Gemini 3 Flash
  only as **`gemini-3-flash-preview`** (the 404 fallback resolves to it; the quota is counted against
  "gemini-3-flash"), and `gemini-2.5-flash` answers 404 "no longer available to new users".
- **The free tier is far smaller than expected: 20 requests a day per Flash model on this key**, not 1,500 (quota
  `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, value 20, seen 2026-09-25 on `gemini-3-flash` and
  `gemini-3.8-flash`). Calls that fail with 503 "high demand" (frequent on the preview model) seem to count too, so
  the client retries Gemini at most 4 times, 30 s apart. Switching to another Flash model does not help (same
  20-a-day quota each) and would mix judge models, so judge 1 stays Gemini 3 Flash for every question. At 20 a day
  the 145 questions it has not judged yet take about 8 days; enabling billing on the Google project would finish
  them in one run (`python -m eval.verify_testset` resumes from the cache).

### D43. Test-set verification: results so far
- Fixed before judging: **en-009** (reference now follows section 9 word for word: total income under clause (a)
  of section 10, deductible allowances under Part IX of the same Chapter; its "Chapter III" was right, since
  section 9 and Part IX are both in Chapter III, but the judge only sees "this Chapter"), **en-063** and **en-089**
  (every step of the calculation shown, "300,001" dropped). Translations of these questions share the reference.
- Two code fixes in `eval/verify_testset.py`: excerpts of long sections now rank chunks by shared word pairs first
  (fbr-021's judge saw section 2 without clause (45), the definition asked about), and the number check accepts a
  calculation that follows a sentence ending with an amount.
- **Qwen and the number check pass all 159 directly judged questions** (English, FBR, out-of-scope; nothing is
  flagged by either). Gemini has judged 14 of them so far, all passed. So **26 of 239 questions are
  `"verified": "machine"`** (14 judged + 12 translations of them); the rest stay `false` until Gemini has judged
  them (`eval/FLAGGED.md` lists them as "not run"). No question had to be removed.
- `eval/expert_sample.json`: 30 test questions for a human expert, seed 2027, stratified by group in proportion to
  the test split (english 11, fbr 6, urdu 5, roman_urdu 5, out_of_scope 3), with empty `expert_ok` fields.

### D44. Ablation and end-to-end results on the full test split (179 questions, 158 in scope)
- **Ablation re-run** on all 158 in-scope test questions (written English 63, FBR 39, Urdu 28, Roman Urdu 28), after
  the chunk-title fix (D37). Hit@5, all / FBR: hybrid baseline 85.4% / 87.2%; + lookup 86.1% / 87.2%; + reranker
  87.3% / 87.2%; + rewrite 93.7% / 84.6%; + rewrite + reranker 89.9% / 89.7%; full 90.5% / 89.7%; **full-max (`/ask`
  default) 93.0% / 87.2%** (Recall@5 all gold 91.8%, MRR@10 0.863; Urdu and Roman Urdu both 92.9%, above the 80%
  target). Written English, Urdu and Roman Urdu match the earlier runs except lookup-rerank Urdu (92.9% → 89.3%) and
  rewrite-rerank Roman Urdu (71.4% → 75.0%): the reranker reads chunk titles, which D37 changed.
- FBR questions are the hardest English group (87.2% with the default vs 96.8% for the written English), as expected:
  they were not written from the section text (D20). The max-score reranking costs one FBR question (89.7% → 87.2%)
  while it gains five Roman Urdu ones; the default stays full-max (it was chosen on dev, D40).
- **End to end** (`eval/run_e2e.py`, full-max): 68 of 179 test questions before GPT OSS 120B's 200k tokens a day ran
  out (D36); 111 are left (~2 days). Of the 55 in-scope questions run, 54 were answered and 53 cite a gold section
  (96.4%; 98.2% of answered); en-070 cited the Tenth Schedule and section 4 instead of section 168, en-076 was
  refused (NOT_IN_SOURCES). 13 of 13 out-of-scope questions run were refused. Fewer questions ran than on the first
  day (85) because full-max changes the retrieved chunks, so earlier cached answers no longer match their prompts.
- **Day 2 (2026-09-26):** 85 of 179 run, 94 left. In scope 72 run: 71 answered, 70 cite a gold section (97.2%; 98.6%
  of answered); out-of-scope 13 of 13 refused. Only 17 new answers fit, because the 200k-token window is rolling
  and still counted the previous day's use.

### D45. "machine" verified = Qwen judge + number check; Gemini is a non-blocking second opinion
- Decided by Hamza on 2026-09-26. Gemini's free tier (20 requests a day, D42) would hold the test set for another
  week, so it no longer blocks. **`"verified": "machine"` now means: the Qwen judge said yes to both checks (the gold
  text answers the question; the reference answer matches it) and the number check in code passed.**
- Gemini 3 Flash runs the same check as a **second opinion**, as far as its daily quota allows, at the start of
  every session (`python -m eval.verify_testset`; it stops asking after the daily-limit error and reads the rest
  from the cache). Its verdict is stored per question as `"second_opinion": "agree" | "disagree"` (translations
  inherit it from their English source) and `eval/FLAGGED.md` gives the agreement rate and lists every disagreement
  for a human to read. A disagreement does not unverify a question.
- Result on 2026-09-26: **all 239 questions "machine"**; Gemini agreed on **15 of 15** it has checked (144 of the
  159 directly judged questions not checked yet).
- The honest one-line description, used in the README: *machine-verified by an independent LLM judge (Qwen) plus an
  automatic number check; a second judge (Gemini) agreed on N of N it checked; 30 questions reviewed by a tax
  professional (pending).*
- This is weaker than two required judges (D38): one model family decides. The number check, the gold-text-only
  prompt, the Gemini sample and the expert sample are what stand behind it.

## Milestone 4 — Chat UI, feedback, question log, eval page

### D46. "Streamed answers" stream progress and the checked answer, not raw model tokens
- `POST /ask/stream` (server-sent events) sends the pipeline stages as they happen ("search", "answer"), then the
  answer text a few words at a time, then the same envelope as `POST /ask`.
- The answer model returns JSON (answer + citation numbers + confidence) and the citation check (D30) can withdraw
  or trim the answer afterwards. Streaming raw tokens would show text that may then be refused or have citations
  removed, so the text is streamed **only after the check has passed**. The wait is dominated by CPU reranking
  (D26), and the stage events cover it.
- Token-level streaming would need a plain-text answer format with citations parsed as they arrive; not worth it
  while the reranker takes most of the time. Revisit with the Milestone 5 latency work.
- The browser reads the stream with axios (XHR `onDownloadProgress`), keeping one HTTP client
  (`withCredentials: true`) for every call.

### D47. Question log and feedback: Postgres on Neon when configured, SQLite file otherwise
- Two tables (`backend/app/db/store.py`, SQLAlchemy Core, created on startup): `asks` (question, language, tax year,
  answer, cited section ids, refusal reason, confidence, timings) and `feedback` (thumbs up/down and an optional
  comment per answer; a new vote replaces the old one).
- `DATABASE_URL` set → Postgres through psycopg 3 (a Neon `postgresql://…?sslmode=require` URL works as is);
  unset → `data/mahsool.db` (gitignored), so the full flow runs locally with no database server.
- **Privacy:** no IP address, user id or cookie is stored. IPs are only used in memory by the rate limiter.
- A failure to write the log never loses the answer (it is logged and the answer is returned without an id, so
  the page hides the feedback buttons).

### D48. Frontend conventions and layout
- `frontend/`: React 19 + Vite + Tailwind 4, following Hamza's conventions: named exports, `App.jsx` holds routes
  only, pages in `src/Pages/`, axios with `withCredentials`, `useRef` for form inputs.
- The browser calls the API directly (`VITE_API_URL`, default `http://localhost:8000`); the API allows CORS from
  `http://localhost:5173` with credentials (`cors_origins` setting). No dev proxy, so the same build works when the
  API is hosted elsewhere.
- Urdu script is shown right-to-left in Noto Nastaliq Urdu (`dir="auto"` everywhere a user or model writes text).
- **Tax-year selector:** every loaded chunk is TY2027 law, so the selector offers TY2027 (default) and "from my
  question"; TY2026 and TY2025 are listed but disabled ("not loaded yet") instead of offering years that are always
  refused.
- The eval page reads `eval/reports/summary.json` (`python -m eval.summary`) and the ablation PNG through the API,
  so it shows exactly the committed reports, including the "partial" state of the end-to-end run.

### D49. Langfuse tracing is deferred to Milestone 5
- The plan lists Langfuse for Milestone 4. No Langfuse keys are configured, and the per-step timings are already in
  every response (`timings_ms`) and in the `asks` table. Tracing moves to Milestone 5 with the latency work, where
  per-step traces are needed.

### D50. Legal review of the 30-question sample by an AI tool, and a completeness sweep of the whole set
- **Legal review of a 30-question sample by ChatGPT (OpenAI), an AI legal-review tool with web access, 26 Sep 2026:
  19 correct, 10 partly correct, 1 wrong; all fixed and a completeness sweep applied to the full set.** This is an
  AI tool's review, not a human or professional one; the review by a tax professional is still pending. Verdicts and
  notes are stored per question in `eval/expert_sample.json` (`verdict`, `expert_ok`, `expert_notes`), with the
  reviewer recorded exactly as above.
- **Every correction was checked against our corpus before it was applied** (ITO 2001, Rules 2002, WHT rate card
  TY2027); all 11 were supported: Tenth Schedule rule 1 and the rate card for the non-ATL rates (236Y 1%, prize
  bonds 30%), section 114(1)(b)(i)-(x), (c), (1A), section 2(59AB)(iv), the proviso to section 119(4), section 82(a),
  (c), (d), section 168(3), and section 155(3). One detail differs from the review: "prescribed person" for rent is
  defined in **section 155(3)**, not section 2, and the list also includes diplomatic missions and private
  educational institutions, boutiques, beauty parlours, hospitals, clinics and maternity homes. **No reviewer claim
  had to be left out as "not in corpus".**
- Fixes were made at the English source and copied to every translation that shares it
  (`eval/review/changes.json`, applied by `python -m eval.apply_changes`). This also exposed a mistake from D43:
  the en-063 and en-089 fixes had not reached their four translations (ur/ru-032, ur/ru-040); the script now syncs
  translations on every run and a test enforces it.
- **The machine judges had passed all 11 flawed items**: both checked only that the reference was *supported* by
  the text, not that it was *complete*. So a completeness sweep read every other in-scope question against the law
  text for the same patterns (ATL vs non-ATL rates, who must withhold, residency tests, final-tax treatment, other
  statutory conditions) and fixed 11 more: en-038 (s115(3) exemptions), en-045 (s119 grounds and Chief
  Commissioner), en-056 (dividends 30% non-ATL), en-058 (s152(1) "chargeable under section 6"), en-061 (s154A final
  only on conditions), en-064 (prescribed person, 30% non-ATL), en-066 (lottery 40% non-ATL, final), en-077
  (s182A(3) undertaking), en-084 (236C 11.5% non-ATL and exceptions), en-085 (236K non-ATL bands, expatriate
  schemes), en-087 (CGT for persons not on the ATL). The judge's new completeness question (D51) found 4 more:
  en-020, en-041, en-047, en-073. Every change, with before and after, is listed in `eval/FLAGGED.md`.
- New status **`"verified": "reviewed"`**: a sample question the AI review judged correct, or one corrected per its
  notes, that also passes the machine checks (Qwen + number check) after the fix. It never means a human review.

### D51. Completeness is now checked: answer prompt, judge prompt, 10 new questions
- **Answer prompt** (rule 7): when a rule has conditions, state them with citations: both ATL and non-ATL rates when
  the sources give both; who the rule applies to (e.g. only a prescribed person withholds), making the answer
  conditional when the question's facts may not meet it; other routes, exemptions, exceptions and final-tax
  treatment in the sources. It must not add conditions that are not in the sources.
- **Judge prompt**: a third question, "does the reference answer omit a condition or exception stated in the section
  that changes the answer?" (`omits_condition`); "yes" fails the question.
- **10 new test questions** (en-091 … en-100, English, test split, type "conditions"): rent paid by a shopkeeper
  below Rs. 1.5 million, rent paid by a company, prize bonds for non-ATL persons, a government officer posted
  abroad, final tax and credit, the late-filing undertaking, 236K for a non-ATL buyer, s154A final-tax conditions,
  s114(1A) business income, and a non-resident plot owner. The test set is now 249 questions (189 on test).
- **Re-judging is incomplete**: the new judge prompt invalidates the cached verdicts. Qwen re-judged 112 of the 169
  directly judged questions before Groq's 200k tokens-a-day limit (2026-09-26); 108 passed and 4 were flagged and
  fixed (above). The other 61 (57 not reached + the 4 fixed) are `"verified": false` until Qwen has judged them;
  with their translations that is 71 questions, so the test set reported 178 of 249 machine-verified (23 of them
  "reviewed"). A second pass later the same day judged 5 more before the limit, all passed (including the 4 fixed):
  **185 of 249 machine-verified, 64 waiting (56 directly judged + their translations)**.
- **End to end restarts:** the answer prompt is part of every cached answer's key, so all cached answers are stale.
  First run with the new prompt (2026-09-26): 17 of 189 test questions (4 in-scope answers, all with a correct
  citation; 13 of 13 out-of-scope refused) before GPT OSS 120B's daily limit; 172 left. The previous prompt's
  results (D44) stay as the comparison point until the new run is complete. Re-run `python -m eval.verify_testset` at the start of
  the next sessions. Gemini's second opinion with the new prompt: 1 of 1 agreed so far (15 of 15 with the old
  two-question prompt).

## Milestone 5 — Latency, free-tier demo, deployment (in progress)

### D52. Latency: where the time goes, and 15 rerank candidates with "max" only for Urdu
- **Measured per stage** (`backend/app/timing.py`, every answer's `timings_ms`; `eval/latency.py` on the dev split
  with the real reranker and cached rewrites, no quota). Rate-limit **waiting** (client limiter sleeps and retry
  back-off) is reported apart from real compute (`llm_wait` vs `llm_api`). On this container's 4 CPU cores:

  | Stage | Old default (max, 30 candidates) | New default (max_non_en, 15) | New, int8 reranker |
  | --- | --- | --- | --- |
  | rewrite (GPT OSS 20B, live) | 0.6 s | 0.6 s | 0.6 s |
  | retrieval (BGE-M3 + Qdrant + RRF) | 0.7 s | 0.7 s | 0.7 s |
  | **rerank** (dev p50 / p95) | **43.5 s / 45.9 s** | **15.1 s / 29.5 s** | 7.9 s / 15.5 s |
  | answer LLM (GPT OSS 120B, live, no wait) | 1.35 s | 1.35 s | 1.35 s |
  | citation check | < 1 ms | < 1 ms | < 1 ms |
  | dev Hit@5 | 96.1% | **98.0%** | 94.1% |

  Rerank p50 is 13.4 s for English questions and 27.7 s for Urdu / Roman Urdu (scored twice). One live answer from
  the deploy bundle: 27.8 s total = rewrite 0.6 + retrieval 0.8 + rerank 25.0 + answer 1.4 s, `llm_wait` 0.
- **The 57 s seen in the UI (D48 era) was ~44 s of reranking plus Groq rate-limit waiting.** Earlier end-to-end runs
  measured the answer step at p50 15.7 s / p95 29.5 s (17 live answers, 2026-09-26), but that number includes the
  free tier's 8,000 tokens-per-minute waits and retries, which were not recorded separately then; with no wait the
  answer model takes ~1.4 s.
- **Chosen on dev** (`eval/rerank_sweep.py`, 12 settings from cached scores): 15 candidates and "max" scoring only
  for Urdu / Roman Urdu (`rerank_query = "max_non_en"`). 22 pairs per question instead of 60; dev Hit@5 98.0% vs
  96.1%. **Held-out test: Hit@5 94.0% (was 93.5%), MRR 0.878 (was 0.871)**, every group equal or better. Now the
  `/ask` default and the `fast` ablation preset.
- **int8 dynamic quantisation** of the reranker halves its time but drops 2 dev questions (Hit@5 94.1%); it stays an
  option (`reranker_quantize`), off by default.
- **Answer cache** (D53): a repeated question is answered in ~30 ms.
- **Still not met:** compute alone is ~16 s p50 here (8.6 s with int8), above both the plan's 4 s and Hamza's ~6 s
  threshold for a hosted reranker, and the Space's 2 vCPU will be slower. Options for Hamza (Milestone 5): a hosted
  reranker API with a free tier (needs an account and key), a smaller multilingual reranker run locally (needs a
  dev re-check), or accept ~15-30 s for uncached questions with the stage progress shown in the UI.

### D53. The demo stays on free tiers: answer cache, per-visitor limit, polite quota message
- Decided by Hamza on 2026-09-26: no paid Groq tier. So the live demo must survive a used-up quota.
- **Never retry after a daily-limit error**: the first one marks the model as exhausted in the LLM client for the
  rest of the process; later calls fail at once with no request (cached answers still replay). Eval runs therefore
  spend one request, not one per remaining question, after the quota is gone.
- **Answer cache** (`answer_cache` table, Neon or SQLite): a repeated question (normalised text + tax year) is
  answered from the cache with no LLM call and no reranking. The cache key includes a version hash of the answer and
  rewrite prompts, the model ids, the retrieval settings and the corpus snapshots, so a change never serves a stale
  answer.
- **Per-visitor limit**: 20 uncached questions per client IP per UTC day (`daily_questions_per_visitor`), on top of
  the 20-per-minute rate limit; cached answers are free.
- **Quota reached** → `DAILY_LIMIT` with "today's free quota is used up, please try again tomorrow; questions others
  have asked still work", in the question's language (English, Urdu, Roman Urdu). The UI shows it as a notice.

### D54. Deployment setup (prepared, not deployed)
- Backend: a free Hugging Face **Docker Space** (2 vCPU, 16 GB RAM). The image installs CPU-only PyTorch and bakes
  in both models (~4.5 GB) so a sleeping Space wakes without downloads; the prebuilt 19 MB vector index is shipped
  with the code, so nothing is indexed at startup. `scripts/deploy_space.py` stages the ~23 MB of files the image
  needs and uploads them with `huggingface_hub` (LFS handled for the index file; no git-lfs needed).
- Frontend: Vercel, root directory `frontend`, `VITE_API_URL` pointing at the Space; logs, feedback and the answer
  cache on Neon (`DATABASE_URL` as a Space secret). CORS origins come from `MAHSOOL_CORS_ORIGINS`.
- A GitHub Actions workflow pings `/health` twice a day once the `SPACE_URL` variable is set (free Spaces sleep
  after ~48 h without traffic).
- Not verified: the image build (no Docker daemon in the build environment). The staged bundle was checked by
  starting the API from it (see STATUS). The Space CPU has 2 cores, half of the 4 used for the timings in D52, so
  reranking there will be slower than measured here.
- Langfuse comes with the deployment step (Hamza creates a free Langfuse Cloud project; keys listed in the README).

### D55. The 20 out-of-scope Urdu / Roman Urdu questions are approved as written
- The 20 out-of-scope questions in Urdu script or Roman Urdu (not translations, so D41 did not cover them) were
  **approved by Hamza without a line-by-line read** and marked `"language_ok": true` (2026-09-26). All 100 non-English
  questions now have `language_ok: true`.

### D56. Answer correctness: Qwen judge on every answer, plus a 50-answer same-meaning check by Hamza
- Decided by Hamza on 2026-09-26 (replaces the open point in D35). `eval/judge_answers.py` gives Qwen (judge2) the
  question, the reference answer and the app's answer, and asks whether they say the same thing: "yes", "partly"
  (a condition, exception or number missing or different) or "no". Reported per group as **strict** (yes) and
  **lenient** (yes or partly) correctness; an in-scope question the app refused counts as not correct, an
  out-of-scope one as correct only when refused. Cached and resumable like the other judges.
- `eval/make_answer_check.py` writes `eval/answer_check.md`: 50 random answered test questions (seed 2027) with the
  reference and app answers side by side and a yes/no box, so the check needs no tax knowledge.
- Neither has run yet: only 6 answers exist with the current prompt (D51, 19 of 189 end-to-end questions run).

### D57. Definition lookup: "what is X?" pins the section 2 clause that defines X
- **Why:** section 2 holds ~140 definitions in one long section (16 chunks). For "What is imputable income?" or
  "What counts as a royalty?", search found sections that *use* the term, not the clause that *defines* it; 3 of the
  5 FBR-sourced misses were such questions (D39).
- **Rule** (`DefinitionLookup` in `backend/app/rag/lookup.py`), deterministic like the section lookup (D28): index
  every defined term (`"X" means`, `[X] means`) with its clause and chunk; when the question or one of its English
  rewrites uses a definitional phrasing (define, definition of, meaning of, what is/are, what counts as, who is) and a
  defined term follows directly and ends the phrase, pin that clause above the search results. "What is the tax rate
  on salary?" does not pin the definition of "tax". 28 definitions only point elsewhere ("taxable income ... as
  defined in section 9"); those pin the section they point to instead (found on dev: pinning the pointer pushed
  section 9 to second place for en-009).
- **Results:** dev Hit@5 98.0% and MRR 0.898, unchanged. Test: Hit@5 **94.0% → 95.8%**, FBR group **87.2% → 94.9%**
  (fbr-006, -008, -013 now found), MRR 0.878 → 0.906; no test question lost its hit. English MRR 0.940 → 0.933 (two
  "tax year" questions get the section 2 entry first and section 74 second).
- **Caveat:** the pattern was found by reading test-set misses, and the FBR questions exist only on the test split,
  so part of the FBR gain is in-sample. The rule is generic (no terms or questions from the test set are in it) and
  dev was checked for regressions. `fast-nodef` keeps the comparison.

### D58. Results on 2026-09-26 (second session of the day): judges complete, end to end 50 of 189
- **Qwen re-judge complete** (three-question prompt, D51): 168 of 169 directly judged questions pass; **248 of 249**
  are verified (30 "reviewed"). **en-092 stays unverified**: Qwen reads Division V clause (b), 15% for "company", as
  applying when a company *pays* the rent; the test set, like the FBR rate card's grouping, reads clauses (a) and (b)
  by the *landlord* (recipient). The corpus does not say which party decides, so the question waits for the
  tax-practitioner review rather than a guess either way.
- **Gemini second opinion** (current prompt): 19 of 21 agree. en-002 was fixed (the salaried exception in the
  proviso to section 4AB, checked against the text). en-005 and en-006: Gemini wants the tax-year-2022 provisos of
  section 4C / Division IIB; they do not change the answer for TY2027, so no change.
- **End to end** (current prompt, `fast` retrieval): 50 of 189 run before GPT OSS 120B's daily limit, 139 left.
  37 in-scope answered, all with a correct citation; 13 of 13 out-of-scope refused. The run started before the
  definition lookup (D57) was adopted, so the next run re-asks the few definition questions whose sources changed.
- **Answer correctness** (Qwen judge, D56) on those 37: 36 match the reference (97.3% strict, 100% lenient).
  en-029 is "partly": the app gave the 183-day test but not the other two residency tests in section 82, although
  the answer prompt asks for other routes (D51). Coverage is almost only written English so far.

### D59. Demo limits: 10 new questions per visitor a day, 60 answers a day for everyone (Hamza, 2026-09-26)
- **Rule** (`backend/app/api/ask.py`): a visitor (client IP) may ask **10 new questions per UTC day**
  (`MAHSOOL_DAILY_QUESTIONS_PER_VISITOR`, was 20 in D53); all visitors together get **60 answers per UTC day that
  call the answer model** (`MAHSOOL_DAILY_ANSWERS_GLOBAL`), sized to GPT OSS 120B's free 200k tokens/day at ~3k
  tokens an answer. Both reply with the friendly "come back tomorrow" message in the question's language, and both
  add that questions others already asked still get an answer. **Cached answers never count** against either
  limit. A question refused before the answer model (scope, tax year, Prompt Guard) counts for the visitor but not
  against the global 60, because it spends no answer quota.
- **Visitor key behind a proxy:** on the Space every request comes from the proxy's address, so the visitor is the
  entry `MAHSOOL_FORWARDED_FOR_HOPS` places from the right of `X-Forwarded-For` (proxies append; the leftmost entries
  can be forged by the client). Default 0 = the socket address (local runs). The right value for the host must be
  checked on the first deploy by looking at the header.
- Both counters live in memory (one instance): a restart resets them. Acceptable for a free demo; the global cap
  still stops at Groq's own daily limit with the same message (D53).

### D60. Prompt Guard: Llama Prompt Guard 2 (86M) on Groq, first check, fails open
- **What:** the plan's input screening. Groq serves `meta-llama/llama-prompt-guard-2-86m` on the free tier (no token
  quota counted in the responses seen); it returns the probability that a text is a prompt attack. `AskService`
  calls it before any search; at ≥ 0.5 (Meta's default, not tuned) the question is refused with
  `PROMPT_INJECTION` and a message in the question's language. If Groq fails, the question passes (logged): the
  other guardrails (scope check, grounded answer, citation check) still apply, and an outage of an add-on should not
  take the demo down. ~0.2 s per question (first call ~0.5 s), measured from this container.
- **Measured** (`python -m eval.guard_eval`, report `eval/reports/2026-09-26-prompt-guard.json`):
  **0 of 249** test-set questions flagged (149 English, 50 Urdu, 50 Roman Urdu; no false positives). On 14
  hand-written attacks (`eval/guard_attacks.jsonl`): **English 4 of 6, Urdu 1 of 4, Roman Urdu 0 of 4**. It misses
  role-play and "answer from your own knowledge" phrasings in English and nearly everything in Urdu / Roman Urdu.
  So it is a thin first filter for English only; the grounded-answer and citation checks remain the real defence.
- **Not done:** screening the English rewrite as well (would catch translated attacks but runs after the rewrite
  LLM call); a local classifier (would cost CPU on the 2-vCPU host).

### D61. Hugging Face Docker Spaces on free CPU now need PRO: test deploy blocked
- On 2026-09-26 `create_repo(..., space_sdk="docker", private=True)` for `HUZZZ/mahsool-ai` returned **402 Payment
  Required**: "Static Spaces are free for everyone, but hosting Gradio and Docker Spaces on free cpu-basic requires a
  PRO subscription." The hosting plan of D54 (free 2-vCPU Space) is therefore not free any more for this account.
  Nothing was created, no secrets were set, nothing was published.
- `scripts/deploy_space.py` now takes `--private`, `--secret NAME` (value read from the environment, never printed),
  `--variable NAME=value` and `--wait` (polls the build), so the deploy is one command once hosting is decided.
- **Options for Hamza** (none tried): (a) Hugging Face PRO (~9 USD/month) keeps D54 unchanged; (b) a host with a
  free tier big enough for BGE-M3 + a reranker in RAM (≥ 4 GB): Oracle Cloud Always Free Ampere (4 OCPU, 24 GB;
  needs a card for sign-up) or Google Cloud Run (free monthly vCPU-seconds, needs billing enabled, cold starts load
  ~3 GB of models); (c) move embedding and reranking to hosted APIs so the backend fits a 512 MB free instance
  (Render, Koyeb), at the cost of new accounts and each API's free-tier limits.

### D62. Reranker: gte-multilingual-reranker-base at 256 tokens replaces bge-reranker-v2-m3
- **Why:** reranking was ~15-30 s of every new question (D52), and the host has 2 vCPU. Hamza's rule: only models
  whose license allows commercial use; tune on dev only; keep dev Hit@5 within 1 point of 98.0% and test Hit@5
  within 1 point of 94.0%; report p50 / p95 on 4 cores and on 2 cores.
- **Compared on dev** (51 in-scope questions, `/ask` settings: 15 candidates, max score for Urdu / Roman Urdu; real
  compute, `python -m eval.latency`; "2 cores" = the process pinned to 2 of this machine's 4 cores with `taskset` and
  2 PyTorch threads, an estimate for the Space's 2 vCPU):

  | Reranker | License | Size | Tokens/pair | Dev Hit@5 | Rerank p50 / p95, 4 cores | 2 cores |
  | --- | --- | --- | --- | --- | --- | --- |
  | BAAI/bge-reranker-v2-m3 (before) | Apache-2.0 | 568M | 512 | 98.0% | 20.3 / 38.8 s (15.1 / 29.5 s in D52) | 30.6 / 33.5 s (20 English questions) |
  | BAAI/bge-reranker-v2-m3 | Apache-2.0 | 568M | 256 | 98.0% | 10.6 / 18.2 s | not run (too slow at 4 cores) |
  | Alibaba-NLP/gte-multilingual-reranker-base | Apache-2.0 | 306M | 512 | 96.1% | 6.3 / 11.5 s | 9.6 / 19.4 s |
  | **Alibaba-NLP/gte-multilingual-reranker-base** | Apache-2.0 | 306M | **256** | **98.0%** | **2.7 / 4.8 s** | **4.7 / 8.8 s** |
  | cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 | Apache-2.0 | 118M | 512 | 94.1% (Roman Urdu 83%) | 1.9 / 3.3 s | 2.3 / 4.6 s |
  | jinaai/jina-reranker-v2-base-multilingual | CC-BY-NC-4.0 | 278M | — | not run: no commercial use | | |
  | mixedbread-ai/mxbai-rerank-base-v2 | Apache-2.0 | 494M | — | not run: a 0.5B decoder, about bge's size, needs its own package | | |

  The same bge run was ~35% slower this session than in D52 (machine variance); all rows of the table were measured
  in the same session. Licenses are the `license:` tags on each model's Hugging Face page (2026-09-26).
- **Chosen:** gte at 256 tokens, the only setting that keeps dev Hit@5 at 98.0% (the 1-point margin allows no lost
  question on 51) and gets rerank p50 under ~6 s on 2 cores. **Test check, run once** (168 questions): Hit@5
  **95.8%**, the same as bge (95.8%; the bar was ≥ 93.0%); English 97.3% (bge 98.6%), FBR 97.4% (94.9%), Urdu 96.4%
  (92.9%), Roman Urdu 89.3% (92.9%); Recall@5 93.2% (92.8%). **MRR@10 falls**: test 0.906 → 0.848, dev
  0.898 → 0.809, i.e. the right section is still in the top 5 but less often first. The answer model reads the top
  6, so answers should not suffer, but the end-to-end run has to confirm it.
- **Measured live** (`uvicorn` on 4 cores, Prompt Guard on, answers from Groq): an English question 7.1-7.7 s in
  total (rerank 2.6-2.8 s, retrieval 1.3-2.2 s, guard 0.5 s, rewrite 0.7-0.8 s, answer 1.5-1.7 s); a Roman Urdu one
  9.3 s (rerank 6.0 s: Urdu and Roman Urdu are scored twice, D40); repeated questions ~8 ms from the answer cache.
  **Estimate for 2 vCPU:** search p50 5.9 s / p95 9.9 s (dev) + guard, rewrite and answer ~2.5-3 s ≈ **8-9 s p50,
  ~13 s p95** for a new question, plus whatever the host's vCPUs lose against these cores. Still above the plan's
  4 s target; no hosted reranker was needed to get under ~6 s of reranking.
- **Engineering:** `CrossEncoderReranker` (transformers) next to `BGEReranker`, picked by `reranker_model`. gte runs
  remote model code (`trust_remote_code`); both the weights and the code are pinned to reviewed revisions in
  `config.py`. transformers 5 leaves gte's non-persistent buffers uninitialised and dropped a helper the code calls,
  so the model is built from its config, the weights are loaded into it, and the old helper is restored (checked:
  all weights load, scores sensible). Reranker score caches are now per model and length
  (`eval/cache/rerank-gte-multilingual-reranker-base-256.tsv`); the bge cache stays for the old reports. The answer
  cache version includes the reranker. The Dockerfile bakes gte and its pinned code.
- **Consequence:** the 52 end-to-end answers so far were made with bge; the next `run_e2e` asks again with gte's
  sources (new answer prompts, so new quota).

### D63. Live check: a non-ATL rate claimed to be the same as the ATL rate
- "What is the withholding tax on profit on debt paid by a bank to a filer?" → 20% (correct for a filer, Division IA
  clause (a)), but the answer added that the rate applies "regardless of ATL status". The law: Tenth Schedule rule 1
  raises withholding by 100% for persons not on the ATL, and section 151 is not among rule 10's exceptions; the FBR
  rate card (source [1] of that answer) shows 20% ATL / 40% non-ATL. A Roman Urdu non-filer variant ("bank munafa par
  kitna tax katta hai agar main non filer hun?") was refused (`NOT_IN_SOURCES`).
- **Tried and reverted:** a sharper rule 7(a) in the answer prompt. The model then argued that "the Ordinance
  prevails over the rate card's higher non-ATL rate" (the card carries FBR's note that the Ordinance prevails),
  because Tenth Schedule rule 1, the Ordinance's own doubling rule, was not among the sources.
- **Proposed fix (not done, needs a dev eval and answer quota):** when a rate-card chunk whose rows cite "R.1 of
  Tenth Schedule" is among the answer sources, pin `ITO2001-sch10-1` (rule 1) as an extra source, and add a test
  question for it. Same pattern as the definition lookup (D57).
