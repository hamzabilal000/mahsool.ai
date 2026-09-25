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

---

## Milestone 2 — More laws, the retrieval machinery, and the first baseline

### 1. One pipeline, three documents

The same parser and chunker now handle the **Income Tax Rules, 2002** by changing *configuration*, not code
(`ingestion/laws/itr2002.py`). The Rules use US Letter pages, 9.5 pt text, and a footnote line at x=126 instead of
x=72, so these became `LawConfig` fields (`separator_x`, `heading_max_x`, `unit_name="Rule"`, …). This is what
the plan meant by "each new law is mostly a data job".

Two lessons:

- **Define the body as a range, not by matching every page header.** Some Rules pages have a continuation title as
  their header ("RECOVERY OF TAX FROM PERSONS HOLDING…"). Matching every header against `CHAPTER -` skipped them.
  The fix: the body starts at the first chapter header and ends where the appendix starts.
- **Normalise before comparing.** The Rules' table of contents writes `01`, `02`; the body writes `1.`, `2.`.
  Stripping leading zeros turned a scary "70 rules missing" into 0 missing.

### 2. Parsing a table without trusting the table finder (the rate card)

FBR's withholding rate card is an Excel sheet saved as PDF. Merged cells confuse automatic table extraction, which
put rates in the wrong columns. Rather than guess, the parser rebuilds the grid from geometry:

1. **Columns:** each cell draws its own border segment, so the x-positions where segments start are the column
   edges. Snap them to the header words, because some pages have extra segments.
2. **Rows:** many rows have no border, but cells are top-aligned. Inside a cell, lines are 2–3 pt apart; between
   cells, 8 pt or more. So a row starts where a description cell starts, or where a new rate starts (a line beginning
   with `%`, `Rs`, `Nil`… that isn't the wrapped tail of a line ending in "exceeding Rs.").
3. **Sections:** the label ("236K Purchase of Immovable Property") sits on its first row, so every row belongs to the
   last label at or above it.

The general lesson: when a tool fails on a specific document, measure the document (spacing, alignment, line
positions) and write down the rule the layout actually follows.

### 3. Three ways to search

| Method | What it matches | Good at | Bad at |
| --- | --- | --- | --- |
| **BM25** (keyword) | exact words, weighted by rarity (IDF) and frequency (TF) | section numbers, legal terms | synonyms, other languages |
| **Dense** (BGE-M3 vector) | meaning: the question and chunk become 1,024-number vectors; closeness = cosine similarity | paraphrases, Urdu → English | exact numbers, rare terms |
| **Sparse** (BGE-M3 lexical weights) | learned keyword weights per token, from the same model | exact terms, with better weighting than BM25 | cross-language |

**BM25 in one line:** a chunk scores high if it contains the query's *rare* words, many times, relative to its length.
`idf = log(1 + (N − df + 0.5)/(df + 0.5))`; the `k1` and `b` parameters stop long chunks from winning just by being
long.

**BGE-M3** gives *both* a dense vector and sparse weights in one forward pass, which is why the plan picked it. It
reads 100+ languages, so an Urdu question and the English section about the same thing land close together.

### 4. Hybrid search and Reciprocal Rank Fusion (RRF)

Hybrid search runs dense and sparse search separately and merges the two ranked lists. You can't add their scores:
cosine similarity (0–1) and sparse dot products (any size) aren't on the same scale. RRF uses **ranks only**:

```
score(chunk) = Σ over lists  1 / (k + rank)        k = 60
```

A chunk ranked 1st by dense and 3rd by sparse scores 1/61 + 1/63; a chunk only ranked 1st by one list scores 1/61.
Agreement wins. `k = 60` (from the original 2009 paper) keeps rank 1 from dominating. The same function also fuses
the results of *several phrasings* of one question (original + English rewrite), which is how Milestone 3's query
rewriting will plug in (`Retriever.retrieve_many`).

### 5. Qdrant: one collection, named vectors, filters

- Each chunk is one **point** with two **named vectors** (`dense`, `sparse`) and the whole chunk as its **payload**.
- Point ids are `uuid5(chunk_id@version_date)`: stable across re-indexing, and different for a new snapshot of
  the same section, so old and new law can coexist.
- **Tax-year filter:** `tax_year_from ≤ Y` and (`tax_year_to` is null or `≥ Y`). A test indexes an "old" (TY2020–2026)
  and a "new" (TY2027+) chunk and checks that each tax year sees only the right one.
- Embedded mode (`QdrantClient(path=…)`) runs in-process with the same API as the server, which is handy for tests
  and laptops (no Docker needed). A Qdrant server (Docker or Qdrant Cloud) is only needed later, for deployment.

### 6. Measuring retrieval

- **Hit@5**: did any correct section appear in the top 5? (the plan's Recall@5)
- **Recall@5 (all gold)**: for questions needing two sections (the rule + the rate table), what share was found?
- **MRR@10**: 1 / rank of the first correct section, averaged. Rank 1 → 1.0, rank 2 → 0.5, not found → 0.
- Scored on **section ids**, so three pieces of section 2 in the top 5 count as one section.
- Reported on the **test split only**; the dev split is for tuning.

### 7. The first (BM25) baseline, and what it teaches

BM25 on the held-out test split:

| Group | Hit@5 |
| --- | --- |
| English | 87.3% |
| Roman Urdu | 50.0% |
| Urdu script | 3.6% |

- **Urdu script ≈ 4%:** the words share no characters with English legal text, so keyword search has nothing to
  match. That's the whole case for the cross-lingual design (multilingual embeddings + English query rewriting).
- **Roman Urdu 50%:** people mix English terms into Roman Urdu ("salary", "return", "ATL", "advance tax"), and those
  still match. The half that fails uses Urdu words ("kiraya", "makan", "zakat di hai").
- **English 87% is optimistic:** the questions were written while reading the sections, so they share wording with
  the law. Real users won't. This is why numbers from hand-written test sets need a caveat.

### 8. Embedding the corpus with BGE-M3

`python -m ingestion.index` loads every chunk, prepends a one-line **context header** ("Income Tax Ordinance, 2001
— Section 149: Salary"), and passes batches through BGE-M3. One forward pass returns:

- a **dense vector**: 1,024 numbers that capture meaning (the CLS token's final state, normalised);
- **sparse weights**: for each token in the text, a learned importance score (e.g. "withholding" 0.21, "the" ≈ 0).

Both go into one Qdrant point with the whole chunk as payload. 1,416 chunks took 28 minutes on a 4-core CPU. That's a
one-time cost, redone only when the chunks change. Answering a question only encodes the *query* (a few words),
which takes well under a second.

**Measure, don't assume (token counts).** Milestone 1 guessed "4 characters ≈ 1 token". The real tokenizer gave 4.02:
the guess was right on average, but 19 chunks (mostly tables) were over the encoder's 1,024-token setting, and the
encoder would have **silently cut off their ends**. Truncation raises no error, so the fix (max length 2,048) only
came from counting. Lesson: check averages *and* the tail.

### 9. The BGE-M3 baseline, and what each method is good at

Test split, Hit@5:

| Retriever | English | Urdu script | Roman Urdu |
| --- | --- | --- | --- |
| BM25 | 87.3% | 3.6% | 50.0% |
| BGE-M3 sparse | 92.1% | 7.1% | 60.7% |
| BGE-M3 dense | 98.4% | 78.6% | 57.1% |
| **Hybrid (dense + sparse, RRF)** | 95.2% | 78.6% | **67.9%** |

All-language hybrid: **Hit@5 84.9%, Recall@5 (all gold) 81.9%, MRR@10 0.764**.

How to read this:

- **Urdu script jumps from 4% to 79% with dense.** This is cross-lingual retrieval working: an Urdu question and
  the English section land close together in vector space. Sparse stays at 7% because it's still word matching,
  just with learned weights.
- **Roman Urdu is the hardest group.** Dense is *worse* than sparse here (57% vs 61%). BGE-M3 was trained on Urdu in
  Urdu script, and hardly any romanized Urdu, so "gaari", "fasal" or "jama karwana" aren't meaningful to it. The
  English words people mix in ("salary", "tax", "return") are what sparse catches.
- **Hybrid wins because the two methods fail on different questions.** RRF rewards chunks both lists agree on, and
  lets a chunk that only one method finds still reach the top 10. Roman Urdu gains 11 points over dense alone.
- **Hybrid isn't free:** English drops from 98.4% to 95.2%, because sparse sometimes pushes a lexically similar but
  wrong section up. On Urdu script sparse has nothing useful to add.
- **MRR vs Hit@5:** MRR 0.76 means the right section is usually ranked 1st or 2nd, not just somewhere in the top 5.
  That matters because the LLM pays most attention to the first few passages.

**What the misses look like** (see `eval/reports/*-hybrid-test.md`): "tax deducted at source on salary" in Roman Urdu
returns the Second Schedule salary *exemptions* instead of section 149 (right topic, wrong rule); "when do I have to
pay the tax" returns sections about tax on specific incomes instead of section 137 (due date). These are
vocabulary gaps, which is what Milestone 3's step (rewrite the question into formal English legal terms, then search
with both phrasings and fuse with RRF) is for.

### Interview questions you should be able to answer

**Q: Your Urdu recall went from 4% to 79%. What changed?**
A: I replaced keyword matching with a multilingual embedding model. BM25 needs shared tokens, and Urdu script shares
none with English law. BGE-M3 maps a sentence and its translation to nearby vectors, so the Urdu question finds
the English section.

**Q: Why is Roman Urdu worse than Urdu script, if Roman Urdu has English words in it?**
A: The embedding model barely saw romanized Urdu in training, so the Urdu words in it are close to noise, while
Urdu script was well covered. Sparse and keyword signals pick up the mixed-in English terms, which is why hybrid
helps Roman Urdu most. The next step is an LLM rewrite of the question into English.

**Q: Hybrid lowered your English score. Why keep it?**
A: It's 3 points lower on English, 11 points higher on Roman Urdu, and best overall on every metric. The target users
write Urdu and Roman Urdu. I chose it on the aggregate and confirmed the same ranking on the dev split, so it
isn't tuned to the test set.

**Q: How long does indexing take, and does that matter?**
A: About 28 minutes on a laptop CPU for 1,416 chunks, and it only reruns when the law changes (once or twice a year).
Query-time cost is encoding one short question.

### More interview questions

**Q: Why not just add the dense and sparse scores?**
A: They're on different scales and distributions. RRF only uses ranks, needs no score normalisation, has one
parameter, and is hard to beat in practice.

**Q: Why does BM25 fail on Urdu when BGE-M3 shouldn't?**
A: BM25 compares exact tokens, and Urdu and English share none. BGE-M3 is trained on parallel and multilingual data,
so it maps a sentence and its translation to nearby vectors: similarity is about meaning, not spelling.

**Q: Why keep a keyword method at all if embeddings understand meaning?**
A: Embeddings are fuzzy about exact strings like "236K", "Division XVIII" or "Rs. 50 million". Sparse or keyword
signals catch those. Hybrid gets both.

**Q: How do you stop a translated test question leaking into tuning?**
A: Every translation stores `source_id`, and the validator enforces that it has the same split (and gold) as its
source. The whole question family is either dev or test.

**Q: The rate card and the Ordinance both give the rent rate. Which one is gold?**
A: The Ordinance; the card says itself that the statute prevails. The card is listed as an *acceptable* source: it
counts as a hit, but the answer should cite the law.

---

## Milestone 3 — From "find the section" to "answer with a citation"

### 1. The full question path

```
question ─▶ understand ─▶ search ─▶ pin named sections ─▶ rerank ─▶ guardrails ─▶ answer ─▶ citation check
            language,       hybrid       "section 149"        top 30      scope,        GPT OSS    drop invented
            tax year,       (original    → put on top          → best 6    tax year,     120B       sources, refuse
            English         + rewrites,                                    score                   if none left
            rewrites        RRF)
```

Each box is a switch in `PipelineConfig`, which is how the ablation table measures what each step adds.

### 2. Query rewriting (and why the glossary exists)

Embeddings put an Urdu question near the English section with the same *meaning*, but Roman Urdu is hard for them
(Milestone 2: 57% dense). A small, fast LLM (GPT OSS 20B) rewrites the question into 1–3 **English legal search
queries**: "non filer hun, cash nikalwaun to kitna tax katega?" → "advance tax on cash withdrawal for persons not
in the active taxpayers' list". We then search with the original *and* the rewrites and fuse all rankings with RRF,
so a bad rewrite can't sink a good original.

The **glossary** (`data/glossary_ur.csv`) is the domain knowledge a general model lacks: *katoti* = withholding,
*filer* = on the Active Taxpayers' List, *gosh wara* = return of income. Only the entries that appear in the
question are put into the prompt, which keeps it short and focused.

The rewrite also returns the question's **scope** (income tax / other federal tax / provincial / not tax), which is
the cheapest way to refuse "What's PRA's tax on restaurants?".

### 3. Rules first, LLM second

Language and tax year are detected with plain rules: Urdu-script character counts, a list of Roman Urdu function
words (*hai, ka, ki, kitna, kya*), and regexes for "tax year 2025", "TY2025", "2024-25". That's free, instant
and predictable (200/200 correct on the test set's language labels). The LLM's tax year is used only if that
year is actually written in the question, because models like to "helpfully" fill in a year.

### 4. Direct section lookup

If the user names a section ("dafa 236K", "u/s 149", "دفعہ ۱۴۹"), searching for it is silly: we fetch it by id
and pin it on top. It's a regex plus a dictionary lookup. If the section doesn't exist ("section 999Z"), that's a
strong signal to refuse instead of guessing.

### 5. Bi-encoder vs cross-encoder (why reranking works)

- **Bi-encoder** (BGE-M3): question and chunk are embedded *separately*; similarity is a dot product. You can
  pre-compute all chunk vectors, so it searches millions of chunks in milliseconds, but it never sees question and
  chunk together.
- **Cross-encoder** (bge-reranker-v2-m3): question and chunk go through the model *together*, so every question
  word can attend to every chunk word. Much more accurate, but it needs one full model run per (question, chunk)
  pair, so you can only afford it on a short list.

Hence "retrieve 30 cheaply, rerank 30 precisely". Result on the test split: **Urdu Hit@5 78.6% → 92.9%**, MRR
0.781 → 0.805 overall. Roman Urdu slipped 67.9% → 64.3% (one question): the reranker reads Roman Urdu no better
than the embedder, which is exactly what the English rewrite is for.

**The cost:** on a 4-core CPU the reranker needs ~27 s per question. Quality and latency pull in opposite
directions; for deployment we'll need a quantised model, fewer candidates or a GPU (DECISIONS D26).

### 6. Guardrails: refuse early, refuse cheaply

The answer is refused at the first failed check, cheapest first: scope → tax year → non-existent section → reranker
score → the answer model says "not in the sources" → no valid citation. Most out-of-scope questions never reach the
expensive model.

**A lesson from the data:** a "refuse if the best reranker score is low" rule sounds right, but on the dev split
answerable Roman Urdu questions score as low as out-of-scope ones. A threshold that catches most out-of-scope
questions would also refuse 1 in 5 real Roman Urdu questions. So the threshold is almost off, and the scope check
and the answer model do the work. Always check a guardrail's false-positive rate, not just its catch rate.

### 7. Grounded generation and the citation check

The answer model sees sources numbered `[1]`…`[6]` and must end every sentence with one. It returns JSON
(`answerable`, `answer`, `citations`, `confidence`). Then **code**, not the model, verifies:

- markers pointing outside 1…6 are deleted (the model invented a source);
- if no valid citation is left, the user gets a refusal, never an uncited answer;
- uncited sentences and "section N" mentions that no cited source contains become warnings.

Why not trust the model? Because LLMs produce confident, well-formatted citations to things they never read. The
check is ten lines of code and removes a whole class of failure.

### 8. Tuning a prompt: read the outputs, on dev only

The first rewrite prompt looked fine until I read what it produced for the 60 dev questions. In 67 of 240
queries it added a section number the user never wrote, usually "section 236K", which was the example in the
prompt itself. Models copy examples. It also called "stamp duty in Punjab" income tax as soon as the glossary said
"jaidad = immovable property".

The fix was three plain rules in the prompt (never add a section number; convert lakh / crore; decide scope from
what is asked, with lists of what counts as what). Invented numbers fell from 67 to 7. All of this was done on
**dev**. The test split was run once, with the final prompt. If you tune on test, your test number stops meaning
anything.

### 9. What the ablation showed: one step can undo another

Test split, Hit@5 for English / Urdu / Roman Urdu:

- hybrid + lookup: 96.8 / 78.6 / 67.9
- \+ rewrite: **98.4 / 100 / 89.3**. Searching with the law's own English words fixes most of the language gap.
- \+ rewrite + reranker: 96.8 / 89.3 / 71.4. **Worse.**

Why: the reranker still scores each chunk against the *original* question. It reads English well, Urdu script
reasonably, Roman Urdu badly, so for Roman Urdu it demotes the right chunks that the rewrite had found. Each
component is fine on its own; together, the later step overrides the better signal from the earlier one.

Two lessons:
1. **Always run the ablation.** "Add a reranker" is standard advice; here it costs 18 points on Roman Urdu.
2. **Dev and test can disagree.** On dev (51 questions) the full pipeline was best overall, so it's still the
   default. The test result goes into the decisions log as a problem to solve on dev next time, not a reason to
   quietly switch defaults. Small splits are noisy: one question is 8 points of Roman Urdu on dev.

The obvious fix is to let the reranker read the English rewrite too, keeping the higher of the two scores. On dev
it gained one Roman Urdu question and doubled the reranker time, so I didn't adopt it. Run once on test for the
record, it lifts Roman Urdu from 75.0% to 92.9%. That's the first decision for Milestone 5, with a faster reranker.

### 10. End-to-end numbers, and a free tier's real limits

`eval/run_e2e.py` runs `/ask` itself on every test question: is an in-scope question answered with a citation to a
gold section, and is an out-of-scope question refused? On the 85 questions that ran, 68 of 69 answers cited a
correct section, and all 13 out-of-scope questions were refused.

Then Groq said no: the free tier allows **200,000 tokens a day** on the 120B model, and one grounded answer
(six sources) is ~3,000 tokens, so ~65 answers a day. Two practical changes followed:

- the client **fails fast** on a daily limit (retrying for hours helps nobody; the API returns 503 at once);
- the eval **records "not run"** instead of crashing, and resumes from the cache the next day.

And a warning about partial results: the questions that didn't run aren't random. Out-of-scope questions refused
by the cheap checks never call the big model, so they all ran; the 8 that didn't run are exactly the ones that got
past those checks. "13 / 13 refused" is therefore an optimistic number until the rest run.

### Interview questions you should be able to answer

**Q: Why rewrite the query instead of translating it?**
A: Translation gives everyday English ("how much tax will be cut if I take out cash"). Search needs the *law's*
words ("advance tax on cash withdrawal, persons not in the active taxpayers' list"). The rewrite targets that
vocabulary, and the glossary tells the model what colloquial terms mean legally.

**Q: What does a reranker add if you already have hybrid search?**
A: Precision at the top. Hybrid search is good at getting the right chunk into the top 30; a cross-encoder reads
question and chunk together and is much better at putting it at rank 1. Urdu Hit@5 went from 79% to 93%.

**Q: How do you stop the model citing things it didn't see?**
A: Sources are numbered, the model must cite numbers, and code checks every number against what was retrieved.
Invalid ones are removed; if none remain, the app refuses.

**Q: Your reranker takes 27 s on CPU. Would you ship it?**
A: Not as is. I'd measure how much of the gain survives with fewer candidates (10–15) and a quantised ONNX model,
or run it on a GPU. Quality numbers come from the eval; the latency budget decides the serving setup.

**Q: Your ablation shows the reranker hurting Roman Urdu. Why not just remove it?**
A: Because the decision has to come from dev, not test, and on dev the reranker helped English ranking a lot
(MRR 0.80 → 0.91). The next step is to test on dev whether reranking against the English rewrite (or skipping the
reranker for Roman Urdu) keeps the English gain without the Roman Urdu loss.

**Q: How did you tune the rewrite prompt without overfitting?**
A: Only on the dev split, by reading every output, and fixing patterns (invented section numbers, scope mistakes),
not individual questions. The test split was run once at the end.

**Q: Your end-to-end run stopped halfway. How do you report that?**
A: With the coverage next to the number (85 of 140), and saying which way the missing part biases it. The eval
lists what didn't run and resumes from the cache, so the rest runs when the quota resets.

