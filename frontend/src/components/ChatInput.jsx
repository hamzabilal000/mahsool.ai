import { useRef } from "react"
import { PLACEHOLDER } from "../lib/text"

// Tax years: only TY2027 law is loaded; earlier years are listed but not selectable yet.
const CURRENT_TAX_YEAR = 2027
const NOT_LOADED = [2026, 2025]

// `ref` (React 19 ref prop) lets the page fill the textarea from a starter question.
export function ChatInput({ onAsk, busy, ref }) {
    let yearref = useRef()

    function submit(e) {
        e.preventDefault()
        let question = ref.current.value.trim()
        if (question.length < 3 || busy) return
        let year = yearref.current.value
        onAsk({ question, taxYear: year === "auto" ? null : Number(year) })
        ref.current.value = ""
    }

    function onKeyDown(e) {
        if (e.key === "Enter" && !e.shiftKey) submit(e)
    }

    return (
        <form onSubmit={submit} className="rounded-lg border-2 border-indigo bg-surface p-2">
            <label htmlFor="question" className="sr-only">Your question</label>
            <textarea
                id="question"
                ref={ref}
                rows={2}
                dir="auto"
                maxLength={1000}
                onKeyDown={onKeyDown}
                placeholder={PLACEHOLDER}
                className="w-full resize-none bg-transparent px-2 py-1.5 text-[17px] leading-[2] text-ink outline-none placeholder:text-muted"
            />
            <div className="flex flex-wrap items-center justify-between gap-2 px-1">
                <label className="flex items-center gap-2 text-sm text-muted">
                    Tax year
                    <select
                        ref={yearref}
                        defaultValue={String(CURRENT_TAX_YEAR)}
                        className="min-h-11 rounded-md border border-line bg-surface px-2 text-sm text-ink"
                    >
                        <option value={CURRENT_TAX_YEAR}>TY{CURRENT_TAX_YEAR} (current)</option>
                        <option value="auto">From my question</option>
                        {NOT_LOADED.map((y) => (
                            <option key={y} value={y} disabled>TY{y} (not loaded yet)</option>
                        ))}
                    </select>
                </label>
                <button
                    type="submit"
                    disabled={busy}
                    className="min-h-11 rounded-md bg-button px-6 text-base font-semibold text-button-ink hover:opacity-90 disabled:opacity-60"
                >
                    {busy ? "Answering…" : "Ask"}
                </button>
            </div>
        </form>
    )
}
