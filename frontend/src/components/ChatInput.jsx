import { useRef } from "react"
import { PLACEHOLDER } from "../lib/text"
import { autoGrow } from "../lib/autogrow"

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
        autoGrow(ref.current)
    }

    // Two rows to start; grows with the text up to six rows, then scrolls.
    function grow(e) {
        autoGrow(e.target)
    }

    function onKeyDown(e) {
        if (e.key === "Enter" && !e.shiftKey) submit(e)
    }

    return (
        <form
            onSubmit={submit}
            className="rounded-xl border-[1.5px] border-indigo bg-surface p-2 focus-within:border-green"
        >
            <label htmlFor="question" className="sr-only">Your question</label>
            <textarea
                id="question"
                ref={ref}
                rows={2}
                dir="auto"
                maxLength={1000}
                onKeyDown={onKeyDown}
                onInput={grow}
                placeholder={PLACEHOLDER}
                className="block w-full resize-none bg-transparent px-2 py-1 text-[17px] leading-[1.75] text-ink outline-none placeholder:text-muted"
            />
            <div className="flex items-center justify-between gap-2 pl-1">
                <label className="flex items-center gap-1.5 text-sm text-muted">
                    <span className="hidden sm:inline">Tax year</span>
                    <select
                        ref={yearref}
                        aria-label="Tax year"
                        defaultValue={String(CURRENT_TAX_YEAR)}
                        className="min-h-11 cursor-pointer rounded-md bg-transparent px-1.5 text-sm text-ink-2 hover:bg-surface-2"
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
                    className="min-h-11 rounded-lg bg-button px-6 text-base font-semibold text-button-ink hover:opacity-90 disabled:opacity-60"
                >
                    {busy ? "Answering…" : "Ask"}
                </button>
            </div>
        </form>
    )
}
