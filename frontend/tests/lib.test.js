import { test } from "node:test"
import assert from "node:assert/strict"
import { parseEvents } from "../src/lib/sse.js"
import { isUrduScript, splitCitations } from "../src/lib/text.js"

test("parseEvents reads complete events and keeps the offset for the next chunk", () => {
    let first = 'event: stage\ndata: {"stage": "search"}\n\nevent: delta\ndata: {"text": "Tax '
    let r1 = parseEvents(first, 0)
    assert.deepEqual(r1.events, [{ event: "stage", data: { stage: "search" } }])
    let full = first + 'is 5% [1]."}\n\n'
    let r2 = parseEvents(full, r1.offset)
    assert.deepEqual(r2.events, [{ event: "delta", data: { text: "Tax is 5% [1]." } }])
    assert.equal(r2.offset, full.length)
})

test("splitCitations separates [n] markers from the text", () => {
    assert.deepEqual(splitCitations("Rate is 5% [1] and [12]."), ["Rate is 5% ", 1, " and ", 12, "."])
    assert.deepEqual(splitCitations("no markers"), ["no markers"])
    assert.deepEqual(splitCitations("40% [1, 7]."), ["40% ", 1, 7, "."])
})

test("isUrduScript detects Urdu script but not Roman Urdu", () => {
    assert.equal(isUrduScript("کیا زرعی آمدنی پر ٹیکس ہے؟"), true)
    assert.equal(isUrduScript("salary pe kitna tax hai"), false)
})

test("splitTables turns pipe rows into a table and drops markers and separators", async () => {
    let { splitTables } = await import("../src/lib/text.js")
    let text = "Division V Income from Property\n(a) The rate shall be— [TABLE\n| S. No. | Rent | Rate |\n|---|---|---|\n| 1. | up to Rs.300,000 | Nil |\n(b) company 15%\n[Table 1: see ITO-x]"
    let blocks = splitTables(text)
    assert.deepEqual(blocks.map((b) => b.type), ["text", "table", "text"])
    assert.deepEqual(blocks[1].rows, [["S. No.", "Rent", "Rate"], ["1.", "up to Rs.300,000", "Nil"]])
    assert.ok(!blocks[0].text.includes("[TABLE"))
    assert.equal(blocks[2].text, "(b) company 15%")
})

test("an unreachable backend gives the friendly offline message, API errors pass through", async () => {
    let { envelopeOf, OFFLINE_MESSAGE, API_HEADERS } = await import("../src/api/client.js")
    let offline = { success: false, data: null, error: OFFLINE_MESSAGE, code: "OFFLINE" }
    assert.deepEqual(envelopeOf(new Error("Network Error")), offline)
    // ngrok's "endpoint offline" page or a 502 while the server restarts: HTML, not the envelope.
    assert.deepEqual(envelopeOf({ response: { status: 404, data: "<html>ERR_NGROK_3200</html>" } }), offline)
    let limit = { success: false, data: null, error: "Try tomorrow", code: "DAILY_LIMIT" }
    assert.deepEqual(envelopeOf({ response: { status: 429, data: limit } }), limit)
    assert.equal(API_HEADERS["ngrok-skip-browser-warning"], "true")
})
