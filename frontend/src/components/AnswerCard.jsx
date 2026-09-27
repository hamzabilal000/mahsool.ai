import { useEffect, useState } from "react"
import { CitationCard } from "./CitationCard"
import { FeedbackButtons } from "./FeedbackButtons"
import { SourcesPanel } from "./SourcesPanel"
import { Banner, Diamond, Divider, InfoIcon } from "./Brand"
import { REFUSAL_LABELS, STEPS, currentStep, isUrduScript, splitCitations } from "../lib/text"

function AnswerText({ text, onCite }) {
    return splitCitations(text).map((part, i) =>
        typeof part === "number" ? (
            <button
                key={i}
                type="button"
                onClick={() => onCite(part)}
                className="mx-0.5 inline-grid min-h-6 min-w-7 place-items-center rounded bg-surface-2 px-1 align-baseline font-sans text-[13px] font-semibold leading-none text-indigo hover:underline"
                aria-label={`Source ${part}`}
            >
                [{part}]
            </button>
        ) : (
            <span key={i}>{part}</span>
        ),
    )
}

// Five diamond markers: done ones indigo, the current one green, upcoming ones outlined.
export function Progress({ stage }) {
    // Milliseconds since the "search" stage began, ticking while it lasts.
    let [elapsed, setElapsed] = useState(0)
    useEffect(() => {
        if (stage !== "search") return
        let start = Date.now()
        let id = setInterval(() => setElapsed(Date.now() - start), 250)
        return () => clearInterval(id)
    }, [stage])
    let step = currentStep(stage, stage === "search" ? elapsed : 0)
    return (
        <div role="status" aria-live="polite" data-progress>
            <ol className="flex items-center" aria-label="Progress">
                {STEPS.map((label, i) => (
                    <li key={label} className="flex flex-1 items-center last:flex-none" aria-current={i === step ? "step" : undefined}>
                        <Diamond n={i + 1} state={i < step ? "done" : i === step ? "current" : "upcoming"} size={24} />
                        <span className="sr-only">{label}</span>
                        {i < STEPS.length - 1 && <span className={`h-[1.5px] flex-1 ${i < step ? "bg-indigo" : "bg-line"}`} />}
                    </li>
                ))}
            </ol>
            <p className="mt-2 text-[15px] text-muted">{STEPS[step]}…</p>
        </div>
    )
}

// One question and its answer: streamed text, citation cards, sources, feedback.
export function AnswerCard({ turn }) {
    let [showSources, setShowSources] = useState(false)
    let [highlight, setHighlight] = useState(null)
    let { question, stage, text, result, error, errorCode } = turn
    // Quota limits of the free demo are expected, not failures: show them as a notice.
    // So is the backend being offline (the free server rests sometimes).
    let quota = errorCode === "DAILY_LIMIT" || errorCode === "VISITOR_DAILY_LIMIT" || errorCode === "OFFLINE"
    let data = result?.data
    let urdu = isUrduScript(question)

    function onCite(n) {
        setHighlight(n)
        document.getElementById(`cite-${n}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" })
    }

    let refused = data?.refused
    return (
        <div className="space-y-3">
            <div className="flex justify-end">
                <p
                    dir="auto"
                    lang={urdu ? "ur" : undefined}
                    className={`max-w-[85%] rounded-md bg-band px-4 py-2.5 text-[17px] text-button-ink ${urdu ? "urdu" : ""}`}
                >
                    {question}
                </p>
            </div>

            {error && quota && <Banner urdu={isUrduScript(error)}>{error}</Banner>}
            {error && !quota && (
                <p dir="auto" role="alert" className={`rounded-md border-[1.5px] border-terracotta bg-surface px-4 py-3 text-terracotta ${isUrduScript(error) ? "urdu" : ""}`}>
                    {error}
                </p>
            )}

            {!error && (
                <article className="rounded-lg border-[1.5px] border-indigo bg-surface p-5 sm:p-6">
                    {!text && !data && <Progress stage={stage} />}
                    {(text || data) && (
                        <p className={`eyebrow mb-2 ${refused ? "text-terracotta" : "text-green"}`}>
                            {refused ? "Not in the law I cover" : "Answer"}
                        </p>
                    )}
                    {refused && (
                        <p className="mb-2 text-sm text-muted">{REFUSAL_LABELS[data.refusal_reason] || "Not answered"}</p>
                    )}
                    {(text || data) && (
                        <div
                            dir="auto"
                            className={`whitespace-pre-line text-[18px] leading-[1.6] text-ink ${isUrduScript(text || data?.answer) ? "urdu" : ""}`}
                        >
                            <AnswerText text={data ? data.answer : text} onCite={onCite} />
                        </div>
                    )}

                    {data && (
                        <div className="mt-4 space-y-4">
                            <p className="text-sm text-muted">
                                Tax year {data.tax_year}
                                {data.tax_year_assumed ? " (assumed: current year)" : ""}
                                {data.confidence ? ` · confidence: ${data.confidence}` : ""}
                                {data.timings_ms?.total ? ` · ${(data.timings_ms.total / 1000).toFixed(1)} s` : ""}
                            </p>
                            {data.warnings?.length > 0 && (
                                <ul className="rounded-md border border-line bg-surface-2 px-3 py-2 text-sm text-ink-2">
                                    {data.warnings.map((w) => <li key={w}>{w}</li>)}
                                </ul>
                            )}
                            {data.citations.length > 0 && (
                                <section className="space-y-3" aria-label="Sources cited">
                                    <Divider />
                                    <h3 className="eyebrow text-green">Sources</h3>
                                    {data.citations.map((c) => (
                                        <CitationCard key={c.n} citation={c} highlighted={highlight === c.n} />
                                    ))}
                                </section>
                            )}
                            {data.sources.length > 0 && (
                                <div>
                                    <button
                                        type="button"
                                        onClick={() => setShowSources(!showSources)}
                                        aria-expanded={showSources}
                                        className="min-h-11 text-[15px] font-semibold text-green hover:underline"
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
                            <p dir="auto" className={`flex items-start gap-2 text-sm text-muted ${isUrduScript(data.disclaimer) ? "urdu" : ""}`}>
                                <InfoIcon size={16} className="mt-1" />
                                <span>{data.disclaimer}</span>
                            </p>
                            <FeedbackButtons askId={data.id} />
                        </div>
                    )}
                </article>
            )}
        </div>
    )
}
