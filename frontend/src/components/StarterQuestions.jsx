import { useState } from "react"
import { isUrduScript } from "../lib/text"
import { STARTERS } from "../lib/starters"

// Compact starter cards: two questions per group on wide screens, one on phones; the rest open
// inline with "More examples".
export function StarterQuestions({ onPick }) {
    let [more, setMore] = useState(false)
    // On wide screens the link is needed only when a group has more than two questions.
    let hiddenOnWide = STARTERS.some(({ questions }) => questions.length > 2)

    return (
        <section aria-label="Starter questions" className="space-y-2">
            <div className="grid gap-3 sm:grid-cols-3">
                {STARTERS.map(({ group, questions }) => (
                    <div key={group} className="rounded-md border-[1.5px] border-indigo bg-surface px-3 py-2.5">
                        <h2 className="eyebrow mb-1.5 text-[12px] text-green">{group}</h2>
                        <ul className="space-y-1.5">
                            {questions.map((q, i) => (
                                <li key={q} className={more ? "" : i === 0 ? "" : i === 1 ? "hidden sm:block" : "hidden"}>
                                    <button
                                        type="button"
                                        onClick={() => onPick(q)}
                                        title={q}
                                        dir="auto"
                                        lang={isUrduScript(q) ? "ur" : undefined}
                                        // Urdu at 15px on one line keeps the card as low as the others.
                                        style={isUrduScript(q) ? { fontSize: 15, lineHeight: 1.9 } : undefined}
                                        className={`min-h-10 w-full rounded-md border border-line px-2.5 py-1 text-start text-[15px] leading-snug text-ink transition-colors hover:bg-surface-2 ${more ? "" : "line-clamp-2"} ${isUrduScript(q) ? "urdu" : ""}`}
                                    >
                                        {q}
                                    </button>
                                </li>
                            ))}
                        </ul>
                    </div>
                ))}
            </div>
            <button
                type="button"
                onClick={() => setMore(!more)}
                aria-expanded={more}
                className={`min-h-10 text-[15px] font-semibold text-green hover:underline ${hiddenOnWide || more ? "" : "sm:hidden"}`}
            >
                {more ? "Fewer examples" : "More examples"}
            </button>
        </section>
    )
}
