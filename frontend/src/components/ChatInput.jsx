import { useRef } from "react"

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
        <form onSubmit={submit} className="rounded-2xl border border-line bg-panel p-2 shadow-sm">
            <label htmlFor="question" className="sr-only">Your question</label>
            <textarea
                id="question"
                ref={ref}
                rows={2}
                dir="auto"
                maxLength={1000}
                onKeyDown={onKeyDown}
                placeholder="Ask in English, اردو or Roman Urdu — e.g. “filer na hon to kya hoga?”"
                className="w-full resize-none bg-transparent px-2 py-1.5 text-[15px] outline-none placeholder:text-muted"
            />
            <div className="flex flex-wrap items-center justify-between gap-2 px-1">
                <label className="flex items-center gap-2 text-xs text-muted">
                    Tax year
                    <select
                        ref={yearref}
                        defaultValue={String(CURRENT_TAX_YEAR)}
                        className="rounded-md border border-line bg-panel px-2 py-1 text-xs text-ink"
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
                    className="rounded-lg bg-accent px-4 py-1.5 text-sm font-medium text-accent-ink disabled:opacity-50"
                >
                    {busy ? "Answering…" : "Ask"}
                </button>
            </div>
        </form>
    )
}
