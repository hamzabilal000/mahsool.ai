import { isUrduScript } from "../lib/text"
import { STARTERS } from "../lib/starters"

export function StarterQuestions({ onPick }) {
    return (
        <section aria-label="Starter questions" className="grid gap-4 md:grid-cols-3">
            {STARTERS.map(({ group, questions }) => (
                <div key={group} className="rounded-md border-[1.5px] border-indigo bg-surface p-5">
                    <h2 className="eyebrow mb-3 text-green">{group}</h2>
                    <ul className="space-y-2">
                        {questions.map((q) => (
                            <li key={q}>
                                <button
                                    type="button"
                                    onClick={() => onPick(q)}
                                    dir="auto"
                                    lang={isUrduScript(q) ? "ur" : undefined}
                                    className={`min-h-11 w-full rounded-md border border-line px-3 py-2 text-start text-base text-ink transition-colors hover:bg-surface-2 ${isUrduScript(q) ? "urdu" : ""}`}
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
