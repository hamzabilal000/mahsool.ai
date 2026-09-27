// Brand ornament and icons (docs/brand/BRAND.md §3). Ornament goes in the header, footer,
// dividers and empty state only, never behind text. Icons are inline SVG (no emoji).
import logoMark from "../assets/brand/logo-mark.svg"
import medallion from "../assets/brand/medallion.svg"
import divider from "../assets/brand/divider.svg"
import starTile from "../assets/brand/star-tile.svg"

export function LogoMark({ size = 40 }) {
    return <img src={logoMark} width={size} height={size} alt="" aria-hidden="true" className="shrink-0" />
}

export function Medallion({ size = 176 }) {
    return <img src={medallion} width={size} height={size} alt="" aria-hidden="true" className="mx-auto h-auto max-w-full" />
}

export function StarTile({ size = 16, className = "" }) {
    return <img src={starTile} width={size} height={size} alt="" aria-hidden="true" className={`shrink-0 ${className}`} />
}

// The indigo lattice band with a terracotta star tile at each end.
export function LatticeBand() {
    return (
        <div className="flex" aria-hidden="true" data-ornament="lattice">
            <StarTile size={12} />
            <div className="lattice-band flex-1" />
            <StarTile size={12} />
        </div>
    )
}

export function Divider({ className = "", small = false }) {
    return (
        <div className={`flex justify-center ${className}`} aria-hidden="true" data-ornament="divider">
            <img src={divider} alt="" className={`${small ? "h-2" : "h-[18px]"} w-full max-w-[820px] object-contain`} />
        </div>
    )
}

// A small rotated square with a numeral, as on the carousel's "How it works" slide.
export function Diamond({ n, state = "upcoming", size = 30 }) {
    // Fills use the fixed deep indigo and green (as the lattice band and the Ask button), so the
    // numerals keep their contrast in dark mode too.
    let fill = { current: "bg-button border-button", done: "bg-band border-indigo", upcoming: "bg-surface border-indigo" }[state]
    let digit = state === "upcoming" ? "text-indigo" : state === "current" ? "text-button-ink" : "text-ochre"
    return (
        <span className="grid shrink-0 place-items-center" style={{ width: size * 1.42, height: size * 1.42 }} aria-hidden="true">
            <span className={`grid rotate-45 place-items-center border-[1.5px] ${fill}`} style={{ width: size, height: size }}>
                <span className={`-rotate-45 font-display text-[15px] leading-none ${digit}`}>{n}</span>
            </span>
        </span>
    )
}

function Svg({ children, size = 18, label, className = "" }) {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={`shrink-0 ${className}`}
            role={label ? "img" : undefined}
            aria-label={label}
            aria-hidden={label ? undefined : "true"}
        >
            {children}
        </svg>
    )
}

export const InfoIcon = (p) => (
    <Svg {...p}>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 11v5M12 8h.01" />
    </Svg>
)

export const ThumbUpIcon = (p) => (
    <Svg {...p}>
        <path d="M7 11v9H4v-9h3Z" />
        <path d="M7 11l4-7a2 2 0 0 1 3 2l-1 4h5a2 2 0 0 1 2 2.3l-1.2 6A2 2 0 0 1 16.8 20H7" />
    </Svg>
)

export const ThumbDownIcon = (p) => (
    <Svg {...p}>
        <path d="M7 13V4H4v9h3Z" />
        <path d="M7 13l4 7a2 2 0 0 0 3-2l-1-4h5a2 2 0 0 0 2-2.3l-1.2-6A2 2 0 0 0 16.8 4H7" />
    </Svg>
)

export const ExternalIcon = (p) => (
    <Svg {...p}>
        <path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" />
    </Svg>
)

export const GitHubIcon = (p) => (
    <Svg {...p}>
        <path d="M9 19c-4 1.3-4-2-6-2.5M15 21v-3.5a3 3 0 0 0-.9-2.4c3-.3 6-1.5 6-6.5a5 5 0 0 0-1.4-3.6 4.7 4.7 0 0 0-.1-3.5s-1.1-.3-3.7 1.4a12.7 12.7 0 0 0-6.6 0C5.7 1.2 4.6 1.5 4.6 1.5a4.7 4.7 0 0 0-.1 3.5A5 5 0 0 0 3 8.6c0 5 3 6.2 6 6.5a3 3 0 0 0-.9 2.4V21" />
    </Svg>
)

// Calm notice with a star tile: the "resting" (offline) and daily-limit messages.
export function Banner({ children, urdu = false }) {
    return (
        <div role="status" className="flex items-start gap-3 rounded-md border border-line bg-surface-2 px-4 py-3 text-ink" data-banner>
            <StarTile size={22} className="mt-0.5" />
            <p dir="auto" className={urdu ? "urdu" : ""}>{children}</p>
        </div>
    )
}
