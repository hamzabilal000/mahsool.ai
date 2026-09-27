// "Show sources": every chunk the pipeline retrieved, in rank order, with the reranker score.
export function SourcesPanel({ sources, searchQueries }) {
    return (
        <div className="rounded-md border border-line bg-surface">
            {searchQueries?.length > 0 && (
                <p className="border-b border-line px-3 py-2 text-sm text-muted">
                    Searched for: {searchQueries.map((q) => `“${q}”`).join(", ")}
                </p>
            )}
            <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                    <thead className="bg-surface-2 text-muted">
                        <tr>
                            <th className="px-3 py-2 font-semibold">#</th>
                            <th className="px-3 py-2 font-semibold">Section</th>
                            <th className="px-3 py-2 font-semibold">Found by</th>
                            <th className="px-3 py-2 text-right font-semibold">Score</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sources.map((s) => (
                            <tr key={s.chunk_id} className="border-t border-line">
                                <td className="px-3 py-2 tabular-nums">{s.rank}</td>
                                <td className="px-3 py-2">{s.label}</td>
                                <td className="px-3 py-2 text-muted">{s.via === "lookup" ? "section named" : "search"}</td>
                                <td className="px-3 py-2">
                                    <span className="flex items-center justify-end gap-2">
                                        {s.rerank_score != null && (
                                            <span className="h-2 w-16 shrink-0 bg-bar-track" aria-hidden="true">
                                                <span
                                                    className="block h-full bg-green"
                                                    style={{ width: `${Math.max(0, Math.min(1, s.rerank_score)) * 100}%` }}
                                                />
                                            </span>
                                        )}
                                        <span className="w-12 text-right tabular-nums">
                                            {s.rerank_score == null ? "–" : s.rerank_score.toFixed(3)}
                                        </span>
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
