import { useState } from "react"
import { splitTables } from "../lib/text"

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
            className={`rounded-xl border bg-panel p-3 transition-colors ${highlighted ? "border-accent ring-2 ring-accent/30" : "border-line"}`}
        >
            <header className="flex items-start gap-2">
                <span className="mt-0.5 grid h-6 min-w-6 place-items-center rounded-md bg-accent-soft text-xs font-semibold text-accent">
                    {citation.n}
                </span>
                <div className="min-w-0 flex-1">
                    <p className="text-xs text-muted">{law} · as amended to {citation.version_date}</p>
                    <h4 className="text-sm font-semibold">{title}</h4>
                </div>
            </header>
            <div className={`relative mt-2 space-y-2 text-sm text-muted ${open || !long ? "" : "max-h-32 overflow-hidden"}`}>
                {splitTables(citation.text).map((block, i) =>
                    block.type === "table" ? (
                        <div key={i} className="overflow-x-auto">
                            <table className="w-full border-collapse text-left text-xs">
                                <tbody>
                                    {block.rows.map((row, r) => (
                                        <tr key={r} className={r === 0 ? "bg-sunken font-medium text-ink" : "border-t border-line"}>
                                            {row.map((cell, c) => (
                                                <td key={c} className="px-2 py-1 align-top">{cell}</td>
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
                {long && !open && <div className="pointer-events-none absolute inset-x-0 bottom-0 h-8 bg-gradient-to-t from-panel" />}
            </div>
            <footer className="mt-2 flex flex-wrap items-center gap-3 text-xs">
                {long && (
                    <button type="button" onClick={() => setOpen(!open)} className="font-medium text-accent">
                        {open ? "Show less" : "Show full text"}
                    </button>
                )}
                <a href={citation.url} target="_blank" rel="noreferrer" className="font-medium text-accent underline-offset-2 hover:underline">
                    FBR PDF, page {citation.page} ↗
                </a>
            </footer>
        </article>
    )
}
