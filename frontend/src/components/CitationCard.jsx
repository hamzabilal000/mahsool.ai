import { useState } from "react"

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
            <p className={`mt-2 whitespace-pre-line text-sm text-muted ${open || !long ? "" : "line-clamp-5"}`}>{citation.text}</p>
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
