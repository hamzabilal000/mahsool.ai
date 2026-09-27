import { GitHubIcon, LatticeBand } from "./Brand"

export function Footer() {
    return (
        <footer className="bg-bg">
            <LatticeBand />
            <div className="mx-auto flex max-w-[960px] flex-col gap-x-4 px-4 text-[13px] text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6">
                <p>For information only, not tax advice. Confirm with a tax practitioner or FBR.</p>
                <p>
                    <a
                        href="https://github.com/hamzabilal000/mahsool.ai"
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex min-h-11 items-center gap-1.5 font-semibold text-green hover:underline"
                    >
                        <GitHubIcon size={16} />
                        GitHub
                    </a>
                </p>
            </div>
        </footer>
    )
}
