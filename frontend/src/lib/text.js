// Urdu script (Arabic block) in the text → render right-to-left with the Nastaliq font.
export function isUrduScript(text) {
    return /[؀-ۿ]/.test(text || "")
}

// Split an answer into text and citation markers: "tax is 5% [1]." → ["tax is 5% ", 1, "."].
export function splitCitations(text) {
    let parts = []
    let last = 0
    for (let m of (text || "").matchAll(/\[(\d+)\]/g)) {
        if (m.index > last) parts.push(text.slice(last, m.index))
        parts.push(Number(m[1]))
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
}

export const STAGE_LABELS = {
    search: "Searching the Ordinance, Rules and rate card…",
    answer: "Writing a cited answer…",
}
