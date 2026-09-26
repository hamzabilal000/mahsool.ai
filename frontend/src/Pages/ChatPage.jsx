import { useEffect, useRef, useState } from "react"
import axios from "axios"
import { askStream } from "../api/client"
import { Header } from "../components/Header"
import { ChatInput } from "../components/ChatInput"
import { AnswerCard } from "../components/AnswerCard"
import { StarterQuestions } from "../components/StarterQuestions"
axios.defaults.withCredentials = true

export function ChatPage() {
    let questionref = useRef()
    let bottomref = useRef()
    let [turns, setTurns] = useState([])
    let [busy, setBusy] = useState(false)

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
        if (res.data) update(id, { result: res })
        else update(id, { error: res.error || "Something went wrong." })
        setBusy(false)
    }

    function pick(question) {
        questionref.current.value = question
        questionref.current.focus()
    }

    return (
        <div className="flex min-h-screen flex-col">
            <Header />
            <main className="mx-auto w-full max-w-4xl flex-1 space-y-6 px-4 py-6">
                {turns.length === 0 && (
                    <section className="space-y-4">
                        <div>
                            <h1 className="text-2xl font-semibold">Ask about Pakistani income tax</h1>
                            <p className="mt-1 text-sm text-muted">
                                Answers come only from the Income Tax Ordinance 2001, the Income Tax Rules 2002 and FBR's
                                withholding tax rate card (tax year 2027), and every claim cites the section it came from.
                                When the law doesn't cover a question, Mahsool says so.
                            </p>
                        </div>
                        <StarterQuestions onPick={pick} />
                    </section>
                )}
                {turns.map((t) => <AnswerCard key={t.id} turn={t} />)}
                <div ref={bottomref} />
            </main>
            <div className="sticky bottom-0 border-t border-line bg-page/95 backdrop-blur">
                <div className="mx-auto max-w-4xl px-4 py-3">
                    <ChatInput onAsk={ask} busy={busy} ref={questionref} />
                    <p className="mt-1.5 text-center text-[11px] text-muted">
                        For information only, not tax advice. Confirm with a tax practitioner or FBR.
                    </p>
                </div>
            </div>
        </div>
    )
}
