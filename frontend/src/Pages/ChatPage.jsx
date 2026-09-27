import { useEffect, useRef, useState } from "react"
import axios from "axios"
import { askStream, isOnline, OFFLINE_MESSAGE } from "../api/client"
import { Header } from "../components/Header"
import { ChatInput } from "../components/ChatInput"
import { autoGrow } from "../lib/autogrow"
import { AnswerCard } from "../components/AnswerCard"
import { StarterQuestions } from "../components/StarterQuestions"
import { Banner, Medallion } from "../components/Brand"
import { Footer } from "../components/Footer"
axios.defaults.withCredentials = true

export function ChatPage() {
    let questionref = useRef()
    let bottomref = useRef()
    let [turns, setTurns] = useState([])
    let [busy, setBusy] = useState(false)
    let [offline, setOffline] = useState(false)

    // Say it before the visitor types a question, not after.
    useEffect(() => {
        isOnline().then((up) => setOffline(!up))
    }, [])

    // Follow the newest answer (not on the empty page, which must stay at the top).
    useEffect(() => {
        if (turns.length) bottomref.current?.scrollIntoView({ behavior: "smooth", block: "end" })
    }, [turns])

    function update(id, patch) {
        setTurns((all) => all.map((t) => (t.id === id ? { ...t, ...(typeof patch === "function" ? patch(t) : patch) } : t)))
    }

    async function ask({ question, taxYear }) {
        let id = crypto.randomUUID()
        setTurns((all) => [...all, { id, question, stage: null, text: "", result: null, error: null }])
        setBusy(true)
        let res = await askStream(
            { question, taxYear },
            {
                onStage: (stage) => update(id, { stage }),
                onDelta: (piece) => update(id, (t) => ({ text: t.text + piece })),
            },
        )
        setOffline(res.code === "OFFLINE")
        if (res.data) update(id, { result: res })
        else update(id, { error: res.error || "Something went wrong.", errorCode: res.code })
        setBusy(false)
    }

    function pick(question) {
        questionref.current.value = question
        autoGrow(questionref.current)
        questionref.current.focus()
    }

    // After the first question the box is fixed to the bottom of the window; the page gets bottom
    // padding of the box's height (kept in sync as the textarea grows), so it never covers text.
    let started = turns.length > 0
    let boxref = useRef()
    let [boxHeight, setBoxHeight] = useState(0)
    useEffect(() => {
        if (!started || !boxref.current) return
        // Rounded up: a fractional height (e.g. 174.4px) must not overlap by a pixel.
        let observer = new ResizeObserver(([entry]) => setBoxHeight(Math.ceil(entry.target.getBoundingClientRect().height)))
        observer.observe(boxref.current)
        return () => observer.disconnect()
    }, [started])

    let input = (
        <>
            <ChatInput onAsk={ask} busy={busy} ref={questionref} />
            <p className="mt-1 text-center text-[13px] leading-snug text-muted">
                For information only, not tax advice. Confirm with a tax practitioner or FBR.
            </p>
        </>
    )

    return (
        <div className="flex min-h-dvh flex-col" style={started ? { paddingBottom: boxHeight } : undefined}>
            <Header />
            <main
                className="mx-auto flex w-full max-w-[960px] flex-1 flex-col gap-4 px-4 py-3 sm:px-6"
                style={started ? { scrollPaddingBottom: boxHeight } : undefined}
            >
                {offline && <Banner>{OFFLINE_MESSAGE}</Banner>}
                {!started && (
                    <>
                        <section className="flex items-start gap-3 sm:items-center sm:gap-4">
                            <span className="w-12 shrink-0 sm:w-16">
                                <Medallion size={64} />
                            </span>
                            <div className="min-w-0">
                                <h1 className="font-display text-[28px] leading-tight text-ink sm:text-[36px]">
                                    Ask about Pakistani income tax
                                </h1>
                                <p className="mt-0.5 text-[15px] leading-snug text-muted sm:text-base">
                                    Answers only from the Income Tax Ordinance 2001, Rules 2002 and FBR's TY2027 rate card,
                                    with the section cited. If the law doesn't cover it, Mahsool says so.
                                </p>
                            </div>
                        </section>
                        <section aria-label="Ask a question">{input}</section>
                        <StarterQuestions onPick={pick} />
                    </>
                )}
                {turns.map((t) => <AnswerCard key={t.id} turn={t} />)}
                <div ref={bottomref} style={{ scrollMarginBottom: boxHeight }} />
            </main>
            <Footer />
            {started && (
                <div ref={boxref} className="fixed inset-x-0 bottom-0 z-10 border-t border-line bg-bg">
                    <div className="mx-auto max-w-[960px] px-4 py-2 sm:px-6">{input}</div>
                </div>
            )}
        </div>
    )
}
