// Layout check in a real browser: the empty Ask page fits one screen, nothing overlaps.
//   npm run test:layout      (builds, serves dist/ with vite preview, drives Chromium)
// Chromium: $CHROMIUM_PATH, else /opt/pw-browsers/chromium, else Playwright's own install. The
// API is mocked (online /health, eval summary from eval/reports/summary.json). Google Fonts load
// when the network allows; otherwise the fallback fonts are used, which are not smaller.
import { after, before, test } from "node:test"
import assert from "node:assert/strict"
import { existsSync, readFileSync } from "node:fs"
import { preview } from "vite"
import { chromium } from "playwright-core"

const DESKTOP = [
    [1920, 815],
    [1366, 650],
    [1280, 620],
]
const SCHEMES = ["light", "dark"]
const SUMMARY = JSON.parse(readFileSync(new URL("../../eval/reports/summary.json", import.meta.url)))

// A long answer, so the page scrolls under the fixed question box.
const ANSWER = {
    success: true,
    error: null,
    code: "OK",
    data: {
        id: "layout-1",
        answer: "The employer deducts tax from salary every month at the average rate [1]. ".repeat(12),
        refused: false,
        language: "en",
        tax_year: 2027,
        tax_year_assumed: true,
        confidence: "high",
        citations: [],
        sources: [],
        search_queries: [],
        warnings: [],
        disclaimer: "For information only, not tax advice. Confirm with a tax practitioner or FBR.",
        timings_ms: { total: 7400 },
    },
}

let server, browser, base, skip
before(async () => {
    let executablePath = process.env.CHROMIUM_PATH || (existsSync("/opt/pw-browsers/chromium") ? "/opt/pw-browsers/chromium" : undefined)
    try {
        browser = await chromium.launch({ executablePath })
    } catch (e) {
        skip = `no Chromium to drive (${e.message.split("\n")[0]})`
        return
    }
    server = await preview({ preview: { port: 0, strictPort: false }, logLevel: "silent" })
    base = server.resolvedUrls.local[0].replace(/\/$/, "")
})
after(async () => {
    await browser?.close()
    await server?.close()
})

async function open(path, { width, height, colorScheme = "light" }) {
    let page = await browser.newPage({ viewport: { width, height }, colorScheme })
    let cors = { "access-control-allow-origin": base, "access-control-allow-credentials": "true", "access-control-allow-headers": "content-type,ngrok-skip-browser-warning" }
    // Every API call (whatever VITE_API_URL the build used) is answered here.
    await page.route(/\/(health|eval\/summary|eval\/ablation\.png|ask\/stream)$/, (route) => {
        let url = route.request().url()
        if (route.request().method() === "OPTIONS") return route.fulfill({ status: 204, headers: cors })
        if (url.endsWith("/ask/stream")) return route.fulfill({ body: `event: done\ndata: ${JSON.stringify(ANSWER)}\n\n`, contentType: "text/event-stream", headers: cors })
        if (url.endsWith("/eval/summary")) return route.fulfill({ json: { success: true, data: SUMMARY, error: null, code: "OK" }, headers: cors })
        if (url.endsWith(".png")) return route.fulfill({ status: 404, headers: cors })
        return route.fulfill({ json: { success: true, data: { status: "ok" }, error: null, code: "OK" }, headers: cors })
    })
    await page.goto(base + path)
    await page.evaluate(() => Promise.race([document.fonts.ready, new Promise((r) => setTimeout(r, 3000))]))
    await page.waitForTimeout(300)
    return page
}

// Top and bottom of the first element matching each selector.
function boxes(page, selectors) {
    return page.evaluate((sels) => Object.fromEntries(Object.entries(sels).map(([k, s]) => {
        let r = document.querySelector(s).getBoundingClientRect()
        return [k, { top: r.top, bottom: r.bottom }]
    })), selectors)
}

for (let [width, height] of DESKTOP) {
    for (let colorScheme of SCHEMES) {
        test(`empty Ask page fits ${width}x${height} (${colorScheme}) with nothing overlapping`, async (t) => {
            if (skip) return t.skip(skip)
            let page = await open("/", { width, height, colorScheme })
            let { scrollHeight, innerHeight } = await page.evaluate(() => ({ scrollHeight: document.documentElement.scrollHeight, innerHeight: window.innerHeight }))
            assert.ok(scrollHeight <= innerHeight, `page scrolls: ${scrollHeight}px of content in a ${innerHeight}px window`)
            let b = await boxes(page, { title: "h1", intro: "h1 + p", box: "form", starters: "[aria-label='Starter questions']", footer: "#root > div > footer" })
            assert.ok(b.title.bottom <= b.intro.top + 1, "title overlaps the intro line")
            assert.ok(b.intro.bottom <= b.box.top, "the question box covers the hero")
            assert.ok(b.box.bottom <= b.starters.top, "the question box covers the starter questions")
            assert.ok(b.starters.bottom <= b.footer.top, "the starter questions run into the footer")
            assert.ok(b.footer.bottom <= innerHeight + 0.5, "the footer is cut off")
            await page.close()
        })
    }
}

test("on a phone (390x844) the question box is visible without scrolling", async (t) => {
    if (skip) return t.skip(skip)
    let page = await open("/", { width: 390, height: 844 })
    let b = await boxes(page, { intro: "h1 + p", box: "form" })
    let { scrollWidth, innerWidth } = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth }))
    assert.ok(b.box.bottom <= 844, `question box ends at ${b.box.bottom}px`)
    assert.ok(b.intro.bottom <= b.box.top, "the question box covers the hero")
    assert.ok(scrollWidth <= innerWidth, "horizontal scroll on a phone")
    await page.close()
})

test("Evaluation page: title and the Hit@5 chart are visible at 1366x650", async (t) => {
    if (skip) return t.skip(skip)
    let page = await open("/eval", { width: 1366, height: 650 })
    await page.waitForSelector("[aria-labelledby='bars-title']")
    let b = await boxes(page, { title: "h1", chart: "[aria-labelledby='bars-title']" })
    assert.ok(b.title.top >= 0 && b.chart.bottom <= 650, `chart ends at ${b.chart.bottom}px`)
    await page.close()
})

test("after an answer the fixed question box never covers the page (bottom padding)", async (t) => {
    if (skip) return t.skip(skip)
    for (let [width, height] of [[1366, 650], [390, 844]]) {
        let page = await open("/", { width, height })
        await page.locator("#question").fill("Who deducts tax from salary?")
        await page.locator("form button[type=submit]").click()
        await page.waitForSelector("[aria-label='Helpful']")
        await page.waitForTimeout(800) // the smooth scroll to the answer
        await page.evaluate(() => window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "instant" }))
        await page.waitForTimeout(200)
        let b = await boxes(page, { box: "form", footer: "#root > div > footer", feedback: "[aria-label='Helpful']" })
        let fixedTop = await page.evaluate(() => document.querySelector("form").closest(".fixed").getBoundingClientRect().top)
        assert.ok(b.footer.bottom <= fixedTop, `${width}px: the box covers the footer (footer ends ${b.footer.bottom}px, box starts ${fixedTop}px)`)
        assert.ok(b.feedback.bottom <= fixedTop, `${width}px: the box covers the answer`)
        await page.close()
    }
})
