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
