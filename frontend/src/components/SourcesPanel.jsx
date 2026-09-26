// "Show sources": every chunk the pipeline retrieved, in rank order, with the reranker score.
export function SourcesPanel({ sources, searchQueries }) {
    return (
        <div className="rounded-xl border border-line bg-sunken p-3 text-sm">
            {searchQueries?.length > 0 && (
                <p className="mb-2 text-xs text-muted">
                    Searched for: {searchQueries.map((q) => `“${q}”`).join(", ")}
                </p>
            )}
            <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                    <thead className="text-muted">
                        <tr>
                            <th className="py-1 pr-2 font-medium">#</th>
                            <th className="py-1 pr-2 font-medium">Section</th>
                            <th className="py-1 pr-2 font-medium">Found by</th>
                            <th className="py-1 text-right font-medium">Reranker score</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sources.map((s) => (
                            <tr key={s.chunk_id} className="border-t border-line">
                                <td className="py-1 pr-2 tabular-nums">{s.rank}</td>
                                <td className="py-1 pr-2">{s.label}</td>
                                <td className="py-1 pr-2 text-muted">{s.via === "lookup" ? "section named" : "search"}</td>
                                <td className="py-1 text-right tabular-nums">{s.rerank_score == null ? "–" : s.rerank_score.toFixed(3)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
