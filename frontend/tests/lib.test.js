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
})

test("isUrduScript detects Urdu script but not Roman Urdu", () => {
    assert.equal(isUrduScript("کیا زرعی آمدنی پر ٹیکس ہے؟"), true)
    assert.equal(isUrduScript("salary pe kitna tax hai"), false)
})
