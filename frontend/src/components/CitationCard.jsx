import { useState } from "react"
import { splitTables } from "../lib/text"
import { Diamond, ExternalIcon } from "./Brand"

const LAW_NAMES = {
    ITO: "Income Tax Ordinance, 2001",
    ITR: "Income Tax Rules, 2002",
    WHT: "FBR withholding tax rate card",
}

// One cited source: law, section and title, the law text, and the FBR PDF at that page.
export function CitationCard({ citation, highlighted }) {
    let [open, setOpen] = useState(false)
    let [lawCode] = citation.chunk_id.match(/^[A-Z]+/) || [""]
    let law = LAW_NAMES[lawCode] || citation.law
    // label: "Income Tax Ordinance, 2001 — Section 149: Salary" → "Section 149: Salary"
    let title = citation.label.includes(" — ") ? citation.label.split(" — ").slice(1).join(" — ") : citation.label
    let long = citation.text.length > 420

    return (
        <article
            id={`cite-${citation.n}`}
            className={`overflow-hidden rounded-md bg-surface transition-colors ${highlighted ? "border-2 border-indigo" : "border border-line"}`}
        >
            <header className="flex items-start gap-3 bg-surface-2 px-4 py-3">
                <Diamond n={citation.n} state="done" size={20} />
                <div className="min-w-0 flex-1">
                    <p className="text-sm text-muted">{law} · as amended to {citation.version_date}</p>
                    <h4 className="font-display text-[20px] leading-snug text-ink">{title}</h4>
                </div>
            </header>
            <div className={`space-y-3 px-4 pt-3 text-base leading-[1.6] text-ink-2 ${open || !long ? "" : "max-h-40 overflow-hidden"}`}>
                {splitTables(citation.text).map((block, i) =>
                    block.type === "table" ? (
                        <div key={i} className="overflow-x-auto">
                            <table className="w-full border-collapse text-left text-sm tabular-nums">
                                <tbody>
                                    {block.rows.map((row, r) => (
                                        <tr key={r} className={r === 0 ? "bg-surface-2 font-semibold text-ink" : "border-t border-line"}>
                                            {row.map((cell, c) => (
                                                <td key={c} className="px-2 py-1.5 align-top">{cell}</td>
                                            ))}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <p key={i} className="whitespace-pre-line">{block.text}</p>
                    ),
                )}
            </div>
            <footer className="flex flex-wrap items-center gap-x-5 px-4 pb-2 text-[15px]">
                {long && (
                    <button type="button" onClick={() => setOpen(!open)} className="min-h-11 font-semibold text-green hover:underline">
                        {open ? "Show less" : "Show full text"}
                    </button>
                )}
                <a
                    href={citation.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex min-h-11 items-center gap-1.5 font-semibold text-green underline-offset-2 hover:underline"
                >
                    Open FBR PDF, p. {citation.page}
                    <ExternalIcon size={15} />
                </a>
            </footer>
        </article>
    )
}
