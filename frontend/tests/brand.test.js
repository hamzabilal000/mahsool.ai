import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync, statSync } from "node:fs"
import { join } from "node:path"
import { PLACEHOLDER, STEPS, currentStep } from "../src/lib/text.js"

function sourceFiles(dir) {
    return readdirSync(dir).flatMap((name) => {
        let path = join(dir, name)
        return statSync(path).isDirectory() ? sourceFiles(path) : /\.(jsx?|css|html)$/.test(name) ? [path] : []
    })
}
const FILES = [...sourceFiles("src"), "index.html"]

test("the question box placeholder has the Urdu word and the Roman Urdu example", () => {
    assert.ok(PLACEHOLDER.includes("اردو"))
    assert.ok(PLACEHOLDER.includes("filer na hon to kya hoga?"))
})

test("progress shows five steps, in the carousel's order", () => {
    assert.deepEqual(STEPS, ["Understanding", "Rewriting", "Searching the law", "Re-ranking", "Writing the answer"])
    assert.equal(currentStep(null), 0)
    assert.equal(currentStep("search", 0), 1)
    assert.equal(currentStep("search", 1500), 2)
    assert.equal(currentStep("search", 5000), 3)
    assert.equal(currentStep("answer"), 4)
})

test("no emoji anywhere in the UI", () => {
    let emoji = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B00}-\u{2BFF}]|\u{FE0F}/u
    for (let file of FILES) {
        let text = readFileSync(file, "utf8")
        assert.ok(!emoji.test(text), `${file} contains an emoji: ${text.match(emoji)?.[0]}`)
    }
})

test("components use colour tokens, not raw hex", () => {
    for (let file of FILES.filter((f) => f.endsWith(".jsx"))) {
        assert.ok(!/#[0-9a-fA-F]{3,8}\b/.test(readFileSync(file, "utf8")), `${file} has a raw hex colour`)
    }
})

test("brand fonts are loaded and the page title is set", () => {
    let html = readFileSync("index.html", "utf8")
    for (let family of ["Young+Serif", "Hanken+Grotesk", "Gulzar", "display=swap"]) assert.ok(html.includes(family), family)
    assert.ok(html.includes("<title>Mahsool AI · Pakistan tax Q&amp;A</title>"))
    let css = readFileSync("src/index.css", "utf8")
    assert.match(css, /--font-sans: "Hanken Grotesk", "Gulzar"/)
    assert.match(css, /prefers-reduced-motion/)
})
