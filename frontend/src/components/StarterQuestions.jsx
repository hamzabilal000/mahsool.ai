import { useState } from "react"
import { isUrduScript } from "../lib/text"
import { STARTERS } from "../lib/starters"

// Example questions as quiet chips: the shortest one of each audience (salaried, freelancers,
// businesses) is shown; the rest open with "More examples". The audience is in the tooltip.
const ALL = STARTERS.flatMap(({ group, questions }) => questions.map((q) => ({ group, q })))
const FEATURED = STARTERS.map(({ group, questions }) => ({
    group,
    q: [...questions].sort((a, b) => a.length - b.length)[0],
}))
const REST = ALL.filter(({ q }) => !FEATURED.some((f) => f.q === q))

function Chip({ group, q, onPick }) {
    let urdu = isUrduScript(q)
    return (
        <li className="min-w-0 max-w-full">
            <button
                type="button"
                onClick={() => onPick(q)}
                title={`${group}: ${q}`}
                dir="auto"
                lang={urdu ? "ur" : undefined}
                // Urdu at 15px keeps the chip as low as the others.
                style={urdu ? { fontSize: 15, lineHeight: 1.9 } : undefined}
                className={`min-h-10 max-w-full truncate rounded-full border border-line px-4 text-[15px] text-ink-2 transition-colors hover:border-indigo hover:bg-surface hover:text-ink ${urdu ? "urdu" : ""}`}
            >
                {q}
            </button>
        </li>
    )
}

export function StarterQuestions({ onPick }) {
    let [more, setMore] = useState(false)
    return (
        <section aria-label="Starter questions" className="text-center">
            <ul className="flex flex-wrap items-center justify-center gap-2">
                {(more ? [...FEATURED, ...REST] : FEATURED).map((item) => (
                    <Chip key={item.q} {...item} onPick={onPick} />
                ))}
                {REST.length > 0 && (
                    <li>
                        <button
                            type="button"
                            onClick={() => setMore(!more)}
                            aria-expanded={more}
                            className="min-h-10 px-2 text-sm font-semibold text-green hover:underline"
                        >
                            {more ? "Fewer examples" : "More examples"}
                        </button>
                    </li>
                )}
            </ul>
        </section>
    )
}
