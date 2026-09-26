import { isUrduScript } from "../lib/text"
import { STARTERS } from "../lib/starters"

export function StarterQuestions({ onPick }) {
    return (
        <section aria-label="Starter questions" className="grid gap-3 sm:grid-cols-3">
            {STARTERS.map(({ group, questions }) => (
                <div key={group} className="rounded-xl border border-line bg-panel p-3">
                    <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">{group}</h3>
                    <ul className="space-y-2">
                        {questions.map((q) => (
                            <li key={q}>
                                <button
                                    type="button"
                                    onClick={() => onPick(q)}
                                    dir="auto"
                                    className={`w-full rounded-lg bg-sunken px-3 py-2 text-left text-sm hover:bg-accent-soft ${isUrduScript(q) ? "urdu text-right" : ""}`}
                                >
                                    {q}
                                </button>
                            </li>
                        ))}
                    </ul>
                </div>
            ))}
        </section>
    )
}
