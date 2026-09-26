"""Bar chart of the retrieval ablation (Hit@5 on the test split, per language group).

Reads the latest report of each setup from eval/reports/ and writes
eval/reports/ablation-test.png (the README embeds it).

Usage:
    python -m eval.plot_ablation
"""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from eval.run_eval import REPORTS

# (report name, label) in ablation order. From the hybrid baseline on, every setup includes
# section lookup; the reranker and the rewrite are added separately, then together.
SETUPS = [
    ("bm25-test", "BM25"),
    ("sparse-test", "Sparse"),
    ("dense-test", "Dense"),
    ("hybrid-test", "Hybrid\n(baseline)"),
    ("pipeline-lookup-test", "+ section\nlookup"),
    ("pipeline-lookup-rerank-test", "+ reranker\n(no rewrite)"),
    ("pipeline-rewrite-test", "+ rewrite\n(no reranker)"),
    ("pipeline-rewrite-rerank-test", "+ rewrite\n+ reranker"),
    ("pipeline-full-test", "+ glossary\n= full pipeline"),
    ("pipeline-full-max-test", "full, rerank\nmax*"),
    ("pipeline-fast-test", "15 candidates,\nmax* for Urdu\n= /ask default"),
]
GROUPS = [
    ("english", "English (written)"),
    ("urdu", "Urdu script"),
    ("roman_urdu", "Roman Urdu"),
    ("fbr", "English (from FBR pages)"),
]
# Validated categorical slots 1-4 (FBR last: yellow next to orange fails the normal-vision check).
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"


def latest(name: str) -> dict:
    files = sorted(REPORTS.glob(f"*-{name}.json"))
    if not files:
        raise SystemExit(f"no report for {name}; run eval.run_eval first")
    return json.loads(files[-1].read_text())["summary"]


def main() -> None:
    rows = [(label, latest(name)) for name, label in SETUPS]
    fig, ax = plt.subplots(figsize=(12, 4.6), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    width = 0.2
    for g, ((key, name), color) in enumerate(zip(GROUPS, COLORS, strict=True)):
        xs = [i + (g - 1.5) * (width + 0.02) for i in range(len(rows))]
        ys = [100 * s[key]["hit@5"] for _, s in rows]
        ax.bar(xs, ys, width, color=color, label=name, zorder=2)
        # Label only the two full-pipeline variants.
        for i in (-2, -1):
            ax.text(xs[i], ys[i] + 1.5, f"{ys[i]:.0f}", ha="center", color=INK, fontsize=7)
    ax.axhline(80, color=MUTED, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.text(len(rows) - 0.5, 80, " target 80%", color=MUTED, fontsize=8, va="center")
    ax.set_xlim(-0.6, len(rows) - 0.5)
    ax.set_xticks(range(len(rows)), [label for label, _ in rows], fontsize=8, color=INK)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Hit@5, test split (%)", color=MUTED, fontsize=9)
    ax.tick_params(axis="y", colors=MUTED, labelsize=8)
    ax.tick_params(axis="x", length=0)
    ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.set_title(
        "Retrieval Hit@5 on the held-out test split, by setup and question language",
        loc="left",
        fontsize=11,
        color=INK,
        pad=24,
    )
    ax.legend(frameon=False, fontsize=8, ncols=4, loc="lower left", bbox_to_anchor=(0, 1.0))
    fig.text(
        0.01,
        0.01,
        "* the reranker also scores the English rewrite and keeps the higher score (D40); "
        "the /ask default does this only for Urdu / Roman Urdu and reranks 15 candidates, "
        "tuned on dev for speed (D52)",
        color=MUTED,
        fontsize=7,
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.subplots_adjust(right=0.93)
    out = REPORTS / "ablation-test.png"
    fig.savefig(out, facecolor=SURFACE)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
