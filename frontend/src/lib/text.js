// Urdu script (Arabic block) in the text → render right-to-left with the Nastaliq font.
export function isUrduScript(text) {
    return /[؀-ۿ]/.test(text || "")
}

// Split an answer into text and citation markers: "tax is 5% [1]." → ["tax is 5% ", 1, "."];
// a group "[1, 7]" gives one marker per source.
export function splitCitations(text) {
    let parts = []
    let last = 0
    for (let m of (text || "").matchAll(/\[(\d+(?:\s*,\s*\d+)*)\]/g)) {
        if (m.index > last) parts.push(text.slice(last, m.index))
        for (let n of m[1].split(",")) parts.push(Number(n))
        last = m.index + m[0].length
    }
    if (last < (text || "").length) parts.push(text.slice(last))
    return parts
}

export const REFUSAL_LABELS = {
    OUT_OF_SCOPE: "Outside the laws Mahsool covers",
    TAX_YEAR_NOT_COVERED: "Tax year not covered",
    SECTION_NOT_FOUND: "Section not found",
    NO_RELEVANT_SOURCES: "No relevant law text found",
    NOT_IN_SOURCES: "Not answered by the law text found",
    NO_VALID_CITATIONS: "Answer could not be backed by a citation",
    PROMPT_INJECTION: "Looks like an instruction to the assistant, not a tax question",
}

export const STAGE_LABELS = {
    search: "Searching the Ordinance, Rules and rate card…",
    answer: "Writing a cited answer…",
}

// The question box placeholder. The Urdu word renders in Gulzar through the font stack
// (Hanken Grotesk has no Urdu glyphs), so it is never blank.
export const PLACEHOLDER = "Ask in English, اردو, or Roman Urdu — e.g. “filer na hon to kya hoga?”"

// The five progress steps shown while answering (the carousel's "How it works").
export const STEPS = ["Understanding", "Rewriting", "Searching the law", "Re-ranking", "Writing the answer"]

// The API streams two stages ("search", then "answer"). Search covers rewriting, searching and
// re-ranking, so within it the markers move on at typical times (rewrite ~0.8 s, search ~1.5 s,
// then re-ranking; D52, D62). Returns the 0-based index of the current step.
export function currentStep(stage, msInSearch = 0) {
    if (stage === "answer") return 4
    if (stage !== "search") return 0
    if (msInSearch < 800) return 1
    if (msInSearch < 2300) return 2
    return 3
}

// Law text with markdown rate tables → blocks: {type: "text", text} or {type: "table", rows}.
// Chunk text marks tables with "[TABLE" and pipe rows ("| S. No. | Rate |"); separator rows
// ("|---|") and "[Table 1: see …]" placeholders are dropped.
export function splitTables(text) {
    let blocks = []
    let lines = []
    let rows = []
    function flushText() {
        let t = lines.join("\n").trim()
        if (t) blocks.push({ type: "text", text: t })
        lines = []
    }
    function flushTable() {
        if (rows.length) blocks.push({ type: "table", rows })
        rows = []
    }
    for (let raw of (text || "").split("\n")) {
        let line = raw.replace(/\[TABLE\b/g, "").replace(/\[Table \d+: see [^\]]*\]/g, "")
        let t = line.trim()
        if (t.startsWith("|") && t.endsWith("|") && t.length > 1) {
            if (/^\|[\s|:-]+\|$/.test(t)) continue // separator row
            flushText()
            rows.push(t.slice(1, -1).split("|").map((cell) => cell.trim()))
        } else {
            flushTable()
            if (t) lines.push(line)
        }
    }
    flushTable()
    flushText()
    return blocks
}
