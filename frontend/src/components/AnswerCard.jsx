import { useState } from "react"
import { CitationCard } from "./CitationCard"
import { FeedbackButtons } from "./FeedbackButtons"
import { SourcesPanel } from "./SourcesPanel"
import { REFUSAL_LABELS, STAGE_LABELS, isUrduScript, splitCitations } from "../lib/text"

function AnswerText({ text, onCite }) {
    return splitCitations(text).map((part, i) =>
        typeof part === "number" ? (
            <button
                key={i}
                type="button"
                onClick={() => onCite(part)}
                className="mx-0.5 inline-grid h-5 min-w-5 place-items-center rounded bg-accent-soft px-1 align-text-top text-[11px] font-semibold text-accent"
                aria-label={`Source ${part}`}
            >
                {part}
            </button>
        ) : (
            <span key={i}>{part}</span>
        ),
    )
}

// One question and its answer: streamed text, citation cards, sources, feedback.
export function AnswerCard({ turn }) {
    let [showSources, setShowSources] = useState(false)
    let [highlight, setHighlight] = useState(null)
    let { question, stage, text, result, error, errorCode } = turn
    // Quota limits of the free demo are expected, not failures: show them as a notice.
    let quota = errorCode === "DAILY_LIMIT" || errorCode === "VISITOR_DAILY_LIMIT"
    let data = result?.data
    let urdu = isUrduScript(question)

    function onCite(n) {
        setHighlight(n)
        document.getElementById(`cite-${n}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" })
    }

    return (
        <div className="space-y-3">
            <div className="flex justify-end">
                <p dir="auto" className={`max-w-[85%] rounded-2xl rounded-br-sm bg-accent px-4 py-2 text-accent-ink ${urdu ? "urdu" : ""}`}>
                    {question}
                </p>
            </div>

            <div className="rounded-2xl rounded-bl-sm border border-line bg-panel p-4">
                {error && (
                    <p
                        dir="auto"
                        role={quota ? "status" : "alert"}
                        className={`text-sm ${quota ? "rounded-md bg-warn-soft px-3 py-2 text-ink" : "text-warn"} ${isUrduScript(error) ? "urdu" : ""}`}
                    >
                        {quota ? "⏳ " : ""}
                        {error}
                    </p>
                )}
                {!error && !text && !data && (
                    <p className="flex items-center gap-2 text-sm text-muted" role="status">
                        <span className="h-2 w-2 animate-pulse rounded-full bg-accent" />
                        {STAGE_LABELS[stage] || "Starting…"}
                    </p>
                )}
                {data?.refused && (
                    <p className="mb-2 inline-block rounded-md bg-warn-soft px-2 py-0.5 text-xs font-medium text-warn">
                        {REFUSAL_LABELS[data.refusal_reason] || "Not answered"}
                    </p>
                )}
                {(text || data) && (
                    <div dir="auto" className={`whitespace-pre-line text-[15px] leading-relaxed ${isUrduScript(text) ? "urdu" : ""}`}>
                        <AnswerText text={data ? data.answer : text} onCite={onCite} />
                    </div>
                )}

                {data && (
                    <div className="mt-3 space-y-3">
                        <p className="text-xs text-muted">
                            Tax year {data.tax_year}
                            {data.tax_year_assumed ? " (assumed: current year)" : ""}
                            {data.confidence ? ` · confidence: ${data.confidence}` : ""}
                            {data.timings_ms?.total ? ` · ${(data.timings_ms.total / 1000).toFixed(1)} s` : ""}
                        </p>
                        {data.warnings?.length > 0 && (
                            <ul className="rounded-md bg-warn-soft px-3 py-2 text-xs text-warn">
                                {data.warnings.map((w) => <li key={w}>{w}</li>)}
                            </ul>
                        )}
                        {data.citations.length > 0 && (
                            <div className="grid gap-2">
                                {data.citations.map((c) => (
                                    <CitationCard key={c.n} citation={c} highlighted={highlight === c.n} />
                                ))}
                            </div>
                        )}
                        {data.sources.length > 0 && (
                            <div>
                                <button
                                    type="button"
                                    onClick={() => setShowSources(!showSources)}
                                    aria-expanded={showSources}
                                    className="text-xs font-medium text-accent"
                                >
                                    {showSources ? "Hide sources" : `Show sources (${data.sources.length})`}
                                </button>
                                {showSources && (
                                    <div className="mt-2">
                                        <SourcesPanel sources={data.sources} searchQueries={data.search_queries} />
                                    </div>
                                )}
                            </div>
                        )}
                        <p dir="auto" className={`text-xs text-muted ${isUrduScript(data.disclaimer) ? "urdu" : ""}`}>⚠️ {data.disclaimer}</p>
                        <FeedbackButtons askId={data.id} />
                    </div>
                )}
            </div>
        </div>
    )
}
