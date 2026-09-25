# Learning notes

Plain-English explanations of the concepts and design decisions in Mahsool AI, one section per milestone.
Each section ends with interview-style questions and short answers.

---

## Milestone 1 — Turning the Income Tax Ordinance into clean, citable chunks

### 1. The big picture: why ingestion matters in RAG

RAG (Retrieval-Augmented Generation) has two halves:

1. **Retrieval:** find the few pieces of text that answer the question.
2. **Generation:** an LLM writes the answer using *only* those pieces, and cites them.

The LLM can only be as good as the pieces it's given. If a piece is cut in the middle of a sentence, mixes two
sections, or contains repealed law, the answer is wrong no matter how good the model is. That's why Milestone 1 is
entirely about producing good pieces, called **chunks**.

```
FBR PDF ──download──▶ PDF + checksum ──parse──▶ clean lines, footnotes, tables ──chunk──▶ chunks.jsonl
```

### 2. Section-aware chunking (vs fixed-size windows)

Most tutorials split text into fixed windows, for example 500 tokens with 50 tokens of overlap. For law that's a bad
idea:

- A window can start in the middle of section 148 and end in the middle of section 149. Which section do you cite?
- Retrieval would return half a rule, e.g. the rate without the conditions.

The law already has perfect boundaries, so we use them:

| Part of the Ordinance | One chunk = |
| --- | --- |
| Chapters (sections 1–242) | one section, e.g. `149. Salary` |
| Second Schedule (exemptions) | one clause, e.g. clause (13), gratuity |
| First Schedule (rates) | one Division of a Part, and each rate table as its own chunk |
| Other schedules | one Part / Division |

**Long sections** (section 2 "Definitions" is about 30 pages) are split at **sub-section boundaries** — `(1)`, `(2)`,
... — never mid-sentence. Each piece after the first starts with `Section 2. Definitions (continued)`, so a piece still
makes sense on its own when retrieved. That line is the "title repeated" rule from the plan.

**Why ~800 tokens?** Big enough for most sections (average chunk is ~315 tokens), small enough that the embedding
represents *one* idea. The embedding of a 5,000-token chunk is a blurry average of many topics, which hurts retrieval.

**How packing works** (`chunk.pack`): group paragraphs into sub-section "units", then greedily fill pieces up to the
budget. If a single sub-section is too big, fall back to paragraphs, and then to sentences. It's the same idea as
packing boxes: keep things that belong together in the same box whenever they fit.

### 3. How the parser reads an FBR PDF

A PDF has no paragraphs, only positioned text fragments ("spans") with a font, size and x/y coordinates. PyMuPDF gives
us those spans, and the parser rebuilds the structure from layout clues:

| Clue | Meaning |
| --- | --- |
| 12 pt bold text at the top | running header, e.g. `Chapter X – Procedure`, which tells us where we are |
| 12 pt number at the bottom | printed page number (dropped from the text) |
| bold `149.` at the left margin followed by a title and `.—` | a section heading |
| tiny digit (≈ 6.5 pt) followed by `[` | an amendment marker: `³[text]` means "text was inserted by the law in footnote 3" |
| a 144 pt-wide horizontal line at the left margin | the footnote separator |

**Baseline merging.** The section number `149.` and its title are separate spans at the same height. The parser groups
spans on the same baseline (±3 pt) into one visual line, sorted left to right.

**A bug worth remembering.** Some pages have big decorative `..` glyphs that share a baseline with a heading. The first
version dropped any line containing a huge glyph, and silently lost sections 78, 143, 148, 192, 194 and 241. The fix
was to drop the *glyph span*, not the whole line. We only found it because the output is checked against the table of
contents (see §7).

### 4. Footnotes: the most dangerous part of FBR PDFs

FBR footnotes record amendment history, like this:

> ¹ Table substituted by the Finance Act, 2024. The substituted Table read as follows: "[old table]"

So footnotes **contain repealed law**, sometimes whole old sections or rate tables running across several pages. If
that text gets into the index, a user asking "what's the top tax rate?" could get last year's rate with a confident
citation. That's the worst failure a tax assistant can have.

**The rule we ended with:** everything below the footnote separator is footnote material, full stop.

- Lines with a marker start a new footnote. Lines without a marker continue the previous footnote, including a
  footnote carried over from the previous page.
- Footnotes become metadata, never chunk text: `amended_by` (e.g. `["Finance Act, 2025"]`) and short
  `amendment_notes`.
- Laws named *inside* the quoted old text ("…read as follows: …inserted by Finance Act, 2015…") are ignored, because
  they describe the old text, not the current one.

**The story (good for interviews):** the first rule was "the footnote area starts at the first footnote marker below
the separator". On pages 523–528 (the individual income tax rates) FBR's layout is unusual: the old pre-2019 rate
tables continue from a footnote on the previous page, so there's no marker. The first version indexed the **repealed
29% and 35% rate tables as current law**. Looking at font sizes showed the pattern: current law is 10 pt, quoted old
text is 7–8 pt, and it is always below the separator. After the fix, a regression test asserts the repealed tables
are absent and the current table (e.g. "Rs. 1,424,000 + 35% above Rs. 7,000,000" for salaried individuals) is present.

### 5. Tables → markdown chunks

Rate tables (First Schedule) are the answer to "how much tax?" questions. PyMuPDF's table finder returns a grid of
cells, but FBR's merged cells confuse it, so `parse._table_markdown` cleans it up:

1. **Compact rows.** Drop empty cells from each row, which fixes misaligned columns when two stacked tables were
   detected as one grid.
2. **Lift captions.** A first row with one long cell is really the sentence *introducing* the table ("(2) Where the
   income of an individual chargeable under the head salary exceeds seventy-five per cent…"). It becomes the caption.
3. **Split stacked tables.** A repeated header row means a new table starts.
4. **Merge page-break continuations.** A table continued on the next page is joined back into one.

Each table becomes its own chunk: `Schedule/Part/Division title + caption + markdown table`. The caption matters
because it's what separates the *salaried* table from the *non-salaried* one. Without it, both tables look almost
identical to the retriever.

### 6. Metadata and IDs

Every chunk carries metadata used later for filtering and citations:

- `law`, `law_code`: for the law filter (Income Tax / Sales Tax / …) in later phases.
- `section`, `subsection`, `schedule`, `clause`, `chapter`, `part`: what the citation card shows.
- `page`, `page_end`, `source_url`, `version_date`: the "open the FBR PDF at this page" link.
- `tax_year_from` / `tax_year_to`: which tax years this text governs (see below).
- `needs_review`: schedule chunks waiting for a manual spot check.

**Two IDs, on purpose:**

- `chunk_id` is unique per piece: `ITO2001-s2-5` is the 5th piece of section 2.
- `section_id` is the thing you cite and grade against: `ITO2001-s2`.

The eval set stores `section_id`s, so if we later change the chunk size, the test set is still valid.

**Tax-year arithmetic** (section 74): a tax year ends on 30 June and is named after the calendar year it ends in, so
TY2027 = 1 Jul 2026 – 30 Jun 2027. A consolidated text "amended up to 30.06.2026" governs the tax year that starts
the next day, which is TY2027. See `ingestion/tax_year.py`.

### 7. How we know the output is right

1. **Table of contents as an oracle.** The PDF's TOC lists every section. We parse it separately (from the raw text
   stream) and compare: 380 live sections in the TOC, 380 in our chunks, none missing, none extra. This caught the
   lost-heading bug and an FBR typo (`[230E Directorate…` has no full stop after the number).
2. **Unit tests on tiny synthetic pages** (`tests/ingestion/test_chunk.py`): heading detection, sub-section
   splitting, amendment parsing, table clean-up. They are fast and don't need the PDF.
3. **Regression tests on the real output** (`test_ito2001_output.py`): unique IDs, the token budget, section 149's
   title and amendments, and above all *repealed tables are not indexed*.
4. **Reproducible spot check.** `python -m ingestion.spot_check` samples 20 random chunks with a fixed seed and writes a
   checklist with links to the exact PDF page, for a human to tick.

### 8. Downloads you can trust

`ingestion/download.py`:

- saves the PDF with its **SHA-256 checksum** in `data/sources.manifest.json` (committed), so anyone can check they
  are using the same file;
- on re-run it sends a cheap `HEAD` request and **skips the download** if the ETag, Last-Modified and size are
  unchanged (idempotent);
- `--check-latest` reads FBR's index page, parses every "Amended upto DD.MM.YYYY" link, and exits with an error if a
  newer consolidated version exists. That's how we found the 30.06.2026 version the plan didn't know about.

### 9. The evaluation set (built before any tuning)

`eval/testset.jsonl` has one question per line: question, language, **gold section IDs**, a short reference answer
written only from the law text, difficulty, type (lookup / rate / numeric / conditions / multi-section), and a fixed
`split`.

- **Why build it first?** If you tune the system while looking at the test questions, you overfit to them and your
  numbers lie. The test set is the ruler, so you make it before you start measuring.
- **Dev vs test split (30/70).** We tune only on dev and report only on test. The split is random with a fixed seed.
  Translations will inherit the split of their English source, so the same question can't appear in both.
- **`verified: false`.** Questions and answers were drafted from the chunk text but must be checked by a human
  against the PDF. Only verified questions should back published numbers.
- **Multi-section questions** such as "how much tax is deducted on PSEB IT exports?" need the *rule* (section 154A)
  and the *rate* (First Schedule, Part III, Division IVA). They test whether retrieval can find both.

### Interview questions you should be able to answer

**Q: Why not just use LangChain's RecursiveCharacterTextSplitter?**
A: Law has explicit structure (sections, sub-sections, clauses), and citations must point to exactly one of them.
Fixed windows cut rules in half and mix sections, so a citation becomes ambiguous. We split on the law's own
boundaries and only fall back to sub-sections when a section is too long.

**Q: What was the hardest bug?**
A: Repealed rate tables quoted in footnotes were being indexed as current law, because the footnote continued from the
previous page with no marker. I found it by reading the actual rate chunks, then used font size and the separator line
to define the footnote zone, and added a regression test that fails if the old tables ever reappear.

**Q: How do you know you didn't miss sections?**
A: I parse the PDF's table of contents independently and diff it against the sections the chunker found. The report
has to show zero missing and zero extra, and that's asserted in CI.

**Q: How do you handle law that changes every year?**
A: Each consolidated version is a snapshot (`snapshot_id = ITO2001@2026-06-30`) with `tax_year_from/to`, and each chunk
records which Finance Acts amended it. New versions are added alongside old ones, not over them, so a question about
TY2025 can later be filtered to TY2025 text.

**Q: Why keep `section_id` separate from `chunk_id`?**
A: Graders and users care about the section, not how I happened to split it. Grading on `section_id` means I can
re-chunk without re-labelling the test set.

**Q: Why not Docling for tables?**
A: Docling brings in PyTorch and layout models (several GB) for about 70 tables. PyMuPDF plus targeted clean-up
handled FBR's quirks, and regression tests pin the important tables. I'll re-evaluate when the rate card (mostly
tables) arrives.
