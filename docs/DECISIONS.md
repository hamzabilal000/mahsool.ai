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

### D14. Hugging Face is blocked here, so the BGE-M3 baseline is pending
- The build environment's network policy denies `huggingface.co`, so the BGE-M3 and bge-reranker weights cannot be
  downloaded here. Everything around the model is built and tested (embedder wrapper, Qdrant store with dense +
  sparse vectors, RRF, tax-year filters, eval runner), using a deterministic fake embedder and in-memory Qdrant.
- The **BM25 keyword baseline** is measured now (no model needed). The dense / hybrid rows of the ablation table will
  be filled in as soon as the model can be downloaded, either here after the domain is allowed, or on Hamza's machine
  with `pip install -e ".[ml]" && python -m ingestion.index && python -m eval.run_eval --retriever dense`.

### D15. Embedded Qdrant by default; Docker Compose for the server
- Docker has no daemon in the build environment. `qdrant-client` has an embedded mode (same API, stored under
  `data/qdrant/`), used when `QDRANT_URL` is empty. `docker-compose.yml` runs Qdrant + Postgres for local
  development; the backend service will be added to it in Milestone 3 when it exists.
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
