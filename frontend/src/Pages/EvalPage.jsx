import { useEffect, useState } from "react"
import axios from "axios"
import { getAblationChart, getEvalSummary } from "../api/client"
import { Header } from "../components/Header"
import { Footer } from "../components/Footer"
import { Divider, StarTile } from "../components/Brand"
axios.defaults.withCredentials = true

const GROUPS = [
    ["english", "English (written)"],
    ["fbr", "English (FBR pages)"],
    ["urdu", "Urdu script"],
    ["roman_urdu", "Roman Urdu"],
    ["all", "All"],
]

// The carousel's order: the target groups first.
const BAR_ORDER = ["roman_urdu", "urdu", "all", "english", "fbr"]

function fmt(x) {
    return x == null ? "–" : `${x.toFixed(1)}%`
}

function Stat({ label, value, note }) {
    return (
        <div className="rounded-md border-[1.5px] border-indigo bg-surface p-4">
            <p className="eyebrow text-green">{label}</p>
            <p className="mt-1 font-display text-[30px] leading-tight tabular-nums text-ink">{value}</p>
            {note && <p className="mt-1 text-sm text-muted">{note}</p>}
        </div>
    )
}

// One group as on the carousel's results slide: a "before" bar and an "after" bar, 0-100%.
function BarPair({ label, before, after }) {
    return (
        <div className="space-y-1" data-bar-pair>
            <h3 className="text-base font-semibold leading-snug text-ink">{label}</h3>
            {[
                [before, "bg-bar-muted", "text-ink-2", "Search alone"],
                [after, "bg-green", "text-green font-semibold", "With rewrite, glossary and re-ranking"],
            ].map(([value, bar, text, name]) => (
                <div key={name} className="flex items-center gap-3">
                    <div className="h-5 flex-1 bg-bar-track">
                        <div className={`h-full ${bar}`} style={{ width: `${value ?? 0}%` }} />
                    </div>
                    <span className={`w-14 shrink-0 text-right text-[15px] leading-5 tabular-nums ${text}`}>
                        <span className="sr-only">{name}: </span>
                        {fmt(value)}
                    </span>
                </div>
            ))}
        </div>
    )
}

export function EvalPage() {
    let [summary, setSummary] = useState(null)
    let [error, setError] = useState(null)
    let [chart, setChart] = useState(null)

    useEffect(() => {
        async function load() {
            let res = await getEvalSummary()
            if (res.success == true) {
                setSummary(res.data)
                setChart(await getAblationChart())
            } else setError(res.error)
        }
        load()
    }, [])

    let ts = summary?.testset
    let rows = summary?.retrieval_ablation || []
    let best = rows[rows.length - 1]
    let e2e = summary?.end_to_end

    // "Before" is plain hybrid search (the baseline); "after" is the /ask default (last row).
    let base = rows.find((r) => r.setup === "Hybrid")

    return (
        <div className="flex min-h-dvh flex-col">
            <Header />
            <main className="mx-auto w-full max-w-[960px] flex-1 space-y-8 px-4 py-4 sm:px-6">
                <div className="space-y-4">
                    <section className="space-y-1.5">
                        <p className="eyebrow text-green">Evaluation</p>
                        <h1 className="font-display text-[28px] leading-tight text-ink sm:text-[36px]">How well does Mahsool find the law?</h1>
                        <p className="text-base leading-snug text-ink-2">
                            Scores on the held-out test split, straight from the committed reports in{" "}
                            <code className="rounded bg-surface-2 px-1 text-[15px]">eval/reports/</code>.
                            {summary && ` Updated ${summary.generated}.`}
                        </p>
                        {error && <p className="text-terracotta">{error}</p>}
                        <Divider small className="pt-2" />
                    </section>

                    {best && base && (
                        <section className="space-y-3" aria-labelledby="bars-title">
                            <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-1">
                                <div>
                                    <h2 id="bars-title" className="font-display text-[22px] leading-snug text-ink sm:text-[24px]">
                                        Is the right section in the top 5? (Hit@5)
                                    </h2>
                                    <p className="text-[15px] text-muted">on {best.n.all} held-out test questions</p>
                                </div>
                                <div className="flex flex-wrap gap-x-5 gap-y-1 text-[15px] text-ink-2" aria-hidden="true">
                                    <span className="flex items-center gap-2"><span className="h-4 w-6 bg-bar-muted" />Search alone</span>
                                    <span className="flex items-center gap-2"><span className="h-4 w-6 bg-green" />+ rewrite, glossary, re-ranking</span>
                                </div>
                            </div>
                            <div className="grid gap-x-10 gap-y-3 md:grid-cols-2">
                                {BAR_ORDER.map((key) => GROUPS.find(([k]) => k === key)).filter(([key]) => base.hit_at_5[key] != null).map(([key, label]) => (
                                    <BarPair key={key} label={label} before={base.hit_at_5[key]} after={best.hit_at_5[key]} />
                                ))}
                            </div>
                            <p className="text-sm text-muted">Bars run from 0 to 100%. Targets: Urdu and Roman Urdu ≥ 80%.</p>
                        </section>
                    )}
                </div>

                {ts && (
                    <section className="rounded-md border-[1.5px] border-indigo bg-surface p-5 text-[15px]">
                        <h2 className="mb-2 font-display text-[22px] text-ink">Test set</h2>
                        <p className="text-ink-2">
                            {ts.questions} questions ({ts.test_split} on the test split). {ts.machine_verified} are
                            machine-verified by an independent LLM judge (Qwen) plus an automatic number check
                            {ts.not_verified_yet ? `; ${ts.not_verified_yet} wait for the judge's re-check with its new completeness question` : ""}.
                            A second judge (Gemini) agreed on {ts.second_opinion_agreed} of {ts.second_opinion_checked} it checked.
                        </p>
                        {ts.review_by && ts.review_result && (
                            <p className="mt-2 text-ink-2">
                                Legal review of a {ts.review_sample}-question sample by {ts.review_by}:{" "}
                                {ts.review_result.correct} correct, {ts.review_result.partly_correct} partly correct,{" "}
                                {ts.review_result.wrong} wrong; all fixed and a completeness sweep applied to the full set.
                                This is an AI tool, not a human review. Review by a tax professional: {ts.tax_professional_review}.
                            </p>
                        )}
                    </section>
                )}

                {best && (
                    <section className="space-y-3">
                        <h2 className="font-display text-[26px] leading-snug text-ink">Every setup we tried</h2>
                        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                            <Stat label="All questions" value={fmt(best.hit_at_5.all)} note={`${best.n.all} questions`} />
                            <Stat label="Urdu script" value={fmt(best.hit_at_5.urdu)} note="target ≥ 80%" />
                            <Stat label="Roman Urdu" value={fmt(best.hit_at_5.roman_urdu)} note="target ≥ 80%" />
                            <Stat label="From FBR pages" value={fmt(best.hit_at_5.fbr)} note={`${best.n.fbr} questions`} />
                        </div>
                        <div className="overflow-x-auto rounded-md border border-line bg-surface">
                            <table className="w-full text-left text-sm">
                                <thead className="bg-surface-2 text-sm text-muted">
                                    <tr>
                                        <th className="px-3 py-2 font-semibold">Setup</th>
                                        {GROUPS.map(([, label]) => (
                                            <th key={label} className="px-3 py-2 text-right font-semibold">{label}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {rows.map((r, i) => (
                                        <tr key={r.setup} className={`border-t border-line ${i === rows.length - 1 ? "bg-green-soft font-semibold" : ""}`}>
                                            <td className="px-3 py-2">
                                                {r.setup}
                                                <span className="block text-sm font-normal text-muted">{r.description}</span>
                                            </td>
                                            {GROUPS.map(([key]) => (
                                                <td key={key} className="px-3 py-2 text-right tabular-nums">{fmt(r.hit_at_5[key])}</td>
                                            ))}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        {chart && (
                            <figure className="rounded-md border border-line bg-surface p-2">
                                <img
                                    src={chart}
                                    alt="Bar chart of Hit@5 per setup and question group; the same numbers are in the table above."
                                    className="w-full rounded bg-white"
                                />
                            </figure>
                        )}
                    </section>
                )}

                {e2e && (
                    <section className="space-y-3">
                        <h2 className="font-display text-[26px] leading-snug text-ink">End to end: answers and refusals</h2>
                        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                            {summary.answer_correctness && (
                                <Stat
                                    label="Answer matches reference"
                                    value={fmt(summary.answer_correctness.correct_strict)}
                                    note={`${summary.answer_correctness.judged} judged by an LLM · target ≥ 85%`}
                                />
                            )}
                            <Stat label="Correct citation (answered)" value={fmt(e2e.correct_citation_answered)} note="target ≥ 90%" />
                            <Stat label="Out-of-scope refused" value={fmt(e2e.out_of_scope_refused)} note={`${e2e.out_of_scope_run} run · target ≥ 90%`} />
                            <Stat label="Questions run" value={`${e2e.run} / ${e2e.questions}`} note={e2e.not_run ? `${e2e.not_run} wait for the LLM's daily quota` : "complete"} />
                        </div>
                        {e2e.not_run > 0 && (
                            <p className="flex items-start gap-3 rounded-md border border-line bg-surface-2 px-4 py-3 text-[15px] text-ink">
                                <StarTile size={18} className="mt-1" />
                                <span>
                                    Partial: the free LLM tier allows about 65 answers a day, so these scores cover {e2e.run} of{" "}
                                    {e2e.questions} test questions and will change as the rest run.
                                </span>
                            </p>
                        )}
                        <p className="text-sm text-muted">
                            Answer correctness: an LLM judge (Qwen) compares each answer with the reference answer; a
                            hand check of 50 answers is pending.
                        </p>
                    </section>
                )}
            </main>
            <Footer />
        </div>
    )
}
