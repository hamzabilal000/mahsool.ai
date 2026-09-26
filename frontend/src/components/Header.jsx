import { NavLink } from "react-router-dom"

function navClass({ isActive }) {
    return `rounded-md px-3 py-1.5 text-sm font-medium ${isActive ? "bg-accent-soft text-accent" : "text-muted hover:text-ink"}`
}

export function Header() {
    return (
        <header className="border-b border-line bg-panel">
            <div className="mx-auto flex max-w-4xl items-center justify-between gap-4 px-4 py-3">
                <NavLink to="/" className="flex items-center gap-2">
                    <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent font-serif text-lg text-accent-ink">م</span>
                    <span className="leading-tight">
                        <span className="block font-semibold">Mahsool AI</span>
                        <span className="block text-xs text-muted">Pakistani income tax law, with citations</span>
                    </span>
                </NavLink>
                <nav className="flex gap-1">
                    <NavLink to="/" end className={navClass}>Ask</NavLink>
                    <NavLink to="/eval" className={navClass}>Evaluation</NavLink>
                </nav>
            </div>
        </header>
    )
}
