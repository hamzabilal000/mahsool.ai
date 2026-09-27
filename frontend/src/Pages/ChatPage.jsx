import { useEffect, useRef, useState } from "react"
import axios from "axios"
import { askStream, isOnline, OFFLINE_MESSAGE } from "../api/client"
import { Header } from "../components/Header"
import { ChatInput } from "../components/ChatInput"
import { AnswerCard } from "../components/AnswerCard"
import { StarterQuestions } from "../components/StarterQuestions"
import { Banner, Divider, Medallion } from "../components/Brand"
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

    useEffect(() => {
        bottomref.current?.scrollIntoView({ behavior: "smooth", block: "end" })
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
        questionref.current.focus()
    }

    return (
        <div className="flex min-h-screen flex-col">
            <Header />
            <main className="mx-auto w-full max-w-[960px] flex-1 space-y-8 px-4 py-8 sm:px-6">
                {offline && <Banner>{OFFLINE_MESSAGE}</Banner>}
                {turns.length === 0 && (
                    <section className="space-y-6">
                        <div className="space-y-4 text-center">
                            <Medallion size={168} />
                            <h1 className="font-display text-[34px] leading-tight text-ink sm:text-[46px]">
                                Ask about Pakistani income tax
                            </h1>
                            <p className="mx-auto max-w-[680px] text-[17px] text-ink-2">
                                Answers come only from the Income Tax Ordinance 2001, the Income Tax Rules 2002 and FBR's
                                withholding tax rate card (tax year 2027), and every claim cites the section it came from.
                                When the law doesn't cover a question, Mahsool says so.
                            </p>
                        </div>
                        <Divider />
                        <StarterQuestions onPick={pick} />
                    </section>
                )}
                {turns.map((t) => <AnswerCard key={t.id} turn={t} />)}
                <div ref={bottomref} />
            </main>
            <div className="sticky bottom-0 z-10 border-t border-line bg-bg">
                <div className="mx-auto max-w-[960px] px-4 py-3 sm:px-6">
                    <ChatInput onAsk={ask} busy={busy} ref={questionref} />
                    <p className="mt-1.5 text-center text-[13px] text-muted">
                        For information only, not tax advice. Confirm with a tax practitioner or FBR.
                    </p>
                </div>
            </div>
            <Footer />
        </div>
    )
}
