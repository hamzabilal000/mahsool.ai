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
