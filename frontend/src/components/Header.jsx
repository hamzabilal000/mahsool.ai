import { NavLink } from "react-router-dom"
import { LatticeBand, LogoMark } from "./Brand"

function navClass({ isActive }) {
    return `inline-flex min-h-11 items-center border-b-2 px-1.5 text-[15px] font-semibold sm:px-2 ${isActive ? "border-green text-green" : "border-transparent text-ink-2 hover:text-ink"}`
}

export function Header() {
    return (
        <header className="bg-bg">
            <div className="mx-auto flex max-w-[960px] items-center justify-between gap-3 px-4 py-3 sm:px-6">
                <NavLink to="/" className="flex min-w-0 items-center gap-3" aria-label="Mahsool AI, home">
                    <LogoMark size={40} />
                    <span className="flex items-baseline gap-2 whitespace-nowrap">
                        <span className="font-display text-[19px] leading-none text-ink sm:text-[22px]">Mahsool AI</span>
                        <span lang="ur" dir="rtl" className="urdu text-[17px] leading-none text-green sm:text-[20px]">محصول</span>
                    </span>
                </NavLink>
                <nav className="flex gap-1 sm:gap-2" aria-label="Main">
                    <NavLink to="/" end className={navClass}>Ask</NavLink>
                    <NavLink to="/eval" className={navClass}>Evaluation</NavLink>
                </nav>
            </div>
            <LatticeBand />
        </header>
    )
}
