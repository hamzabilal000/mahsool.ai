import { useEffect, useState } from "react"
import axios from "axios"
import { ABLATION_CHART_URL, getEvalSummary } from "../api/client"
import { Header } from "../components/Header"
axios.defaults.withCredentials = true

const GROUPS = [
    ["english", "English (written)"],
    ["fbr", "English (FBR pages)"],
    ["urdu", "Urdu script"],
    ["roman_urdu", "Roman Urdu"],
    ["all", "All"],
]

function fmt(x) {
    return x == null ? "–" : `${x.toFixed(1)}%`
}

function Stat({ label, value, note }) {
    return (
        <div className="rounded-xl border border-line bg-panel p-3">
            <p className="text-xs text-muted">{label}</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
            {note && <p className="mt-0.5 text-xs text-muted">{note}</p>}
        </div>
    )
}

export function EvalPage() {
    let [summary, setSummary] = useState(null)
    let [error, setError] = useState(null)

    useEffect(() => {
        async function load() {
            let res = await getEvalSummary()
            if (res.success == true) setSummary(res.data)
            else setError(res.error)
        }
        load()
    }, [])

    let ts = summary?.testset
    let rows = summary?.retrieval_ablation || []
    let best = rows[rows.length - 1]
    let e2e = summary?.end_to_end

    return (
        <div className="min-h-screen">
            <Header />
            <main className="mx-auto max-w-4xl space-y-8 px-4 py-6">
                <section>
                    <h1 className="text-2xl font-semibold">Evaluation</h1>
                    <p className="mt-1 text-sm text-muted">
                        Scores on the held-out test split, straight from the committed reports in{" "}
                        <code className="rounded bg-sunken px-1">eval/reports/</code>.
                        {summary && ` Updated ${summary.generated}.`}
                    </p>
                    {error && <p className="mt-3 text-sm text-warn">{error}</p>}
                </section>

                {ts && (
                    <section className="rounded-xl border border-line bg-panel p-4 text-sm">
                        <h2 className="mb-1 font-semibold">Test set</h2>
                        <p className="text-muted">
                            {ts.questions} questions ({ts.test_split} on the test split). {ts.machine_verified} are
                            machine-verified by an independent LLM judge (Qwen) plus an automatic number check
                            {ts.not_verified_yet ? `; ${ts.not_verified_yet} wait for the judge's re-check with its new completeness question` : ""}.
                            A second judge (Gemini) agreed on {ts.second_opinion_agreed} of {ts.second_opinion_checked} it checked.
                        </p>
                        {ts.review_by && ts.review_result && (
                            <p className="mt-2 text-muted">
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
                        <h2 className="font-semibold">Retrieval: is the right section in the top 5? (Hit@5)</h2>
                        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                            <Stat label="All questions" value={fmt(best.hit_at_5.all)} note={`${best.n.all} questions`} />
                            <Stat label="Urdu script" value={fmt(best.hit_at_5.urdu)} note="target ≥ 80%" />
                            <Stat label="Roman Urdu" value={fmt(best.hit_at_5.roman_urdu)} note="target ≥ 80%" />
                            <Stat label="From FBR pages" value={fmt(best.hit_at_5.fbr)} note={`${best.n.fbr} questions`} />
                        </div>
                        <figure className="rounded-xl border border-line bg-panel p-2">
                            <img
                                src={ABLATION_CHART_URL}
                                alt="Bar chart of Hit@5 per setup and question group; the same numbers are in the table below."
                                className="w-full rounded-lg bg-white"
                            />
                        </figure>
                        <div className="overflow-x-auto rounded-xl border border-line bg-panel">
                            <table className="w-full text-left text-sm">
                                <thead className="bg-sunken text-xs text-muted">
                                    <tr>
                                        <th className="px-3 py-2 font-medium">Setup</th>
                                        {GROUPS.map(([, label]) => (
                                            <th key={label} className="px-3 py-2 text-right font-medium">{label}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {rows.map((r, i) => (
                                        <tr key={r.setup} className={`border-t border-line ${i === rows.length - 1 ? "font-semibold" : ""}`}>
                                            <td className="px-3 py-2">
                                                {r.setup}
                                                <span className="block text-xs font-normal text-muted">{r.description}</span>
                                            </td>
                                            {GROUPS.map(([key]) => (
                                                <td key={key} className="px-3 py-2 text-right tabular-nums">{fmt(r.hit_at_5[key])}</td>
                                            ))}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </section>
                )}

                {e2e && (
                    <section className="space-y-3">
                        <h2 className="font-semibold">End to end: answers and refusals</h2>
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
                            <p className="rounded-md bg-warn-soft px-3 py-2 text-xs text-warn">
                                Partial: the free LLM tier allows about 65 answers a day, so these scores cover {e2e.run} of{" "}
                                {e2e.questions} test questions and will change as the rest run.
                            </p>
                        )}
                        <p className="text-xs text-muted">
                            Answer correctness: an LLM judge (Qwen) compares each answer with the reference answer; a
                            hand check of 50 answers is pending.
                        </p>
                    </section>
                )}
            </main>
        </div>
    )
}
