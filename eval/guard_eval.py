"""Prompt Guard on the test set and on hand-written attacks (D60).

False positives: every question of eval/testset.jsonl (all splits, in scope and out of scope) is
a normal question and should pass. Detection: eval/guard_attacks.jsonl holds 14 hand-written
injection / jailbreak attempts in English, Urdu and Roman Urdu. Scores are cached in
eval/cache/guard.jsonl, so a re-run costs no quota. The threshold is fixed in config (0.5, Meta's
default), not tuned on these questions.

Usage:
    python -m eval.guard_eval
"""

import json
import time
from datetime import date
from pathlib import Path

from backend.app.config import get_settings
from backend.app.guard import PromptGuard
from eval.run_eval import REPORTS
from eval.validate_testset import load_testset

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache" / "guard.jsonl"
ATTACKS = HERE / "guard_attacks.jsonl"


def main() -> None:
    s = get_settings()
    guard = PromptGuard(s.groq_api_key.get_secret_value(), s.prompt_guard_model,
                        s.prompt_guard_threshold, s.groq_base_url, timeout=15)  # fmt: skip
    cache = {}
    if CACHE.exists():
        for line in CACHE.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            cache[(row["model"], row["text"])] = row["score"]

    def score(text: str) -> float | None:
        key = (s.prompt_guard_model, text)
        if key not in cache:
            time.sleep(2.2)  # Groq free tier: 30 requests a minute
            value = guard.score(text)
            if value is None:
                return None
            cache[key] = value
            with CACHE.open("a", encoding="utf-8") as fh:
                row = {"model": s.prompt_guard_model, "text": text, "score": value}
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        return cache[key]

    rows = [{"id": i.id, "kind": "question", "language": i.language, "text": i.question}
            for i in load_testset()]  # fmt: skip
    for line in ATTACKS.read_text(encoding="utf-8").splitlines():
        a = json.loads(line)
        rows.append({"id": a["id"], "kind": "attack", "language": a["language"], "text": a["text"]})
    for r in rows:
        r["score"] = score(r["text"])
        r["flagged"] = r["score"] is not None and r["score"] >= s.prompt_guard_threshold
    summary = {"model": s.prompt_guard_model, "threshold": s.prompt_guard_threshold}
    for kind in ("question", "attack"):
        for lang in ("en", "ur", "roman_ur", "all"):
            sel = [r for r in rows if r["kind"] == kind and lang in ("all", r["language"])]
            summary[f"{kind}_{lang}"] = {
                "n": len(sel),
                "flagged": sum(r["flagged"] for r in sel),
                "not_scored": sum(r["score"] is None for r in sel),
            }
    out = REPORTS / f"{date.today().isoformat()}-prompt-guard.json"
    out.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1),
                   encoding="utf-8")  # fmt: skip
    print(json.dumps(summary, indent=1))
    for r in rows:
        if r["flagged"] != (r["kind"] == "attack"):
            print("WRONG", r["id"], r["score"], r["text"][:100])


if __name__ == "__main__":
    main()
