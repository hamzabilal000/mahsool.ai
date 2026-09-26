"""Stage the backend for a Hugging Face Docker Space and upload it (README "Deploy").

Copies only what the container needs: Dockerfile, the Space card (deploy/space/README.md as
README.md), pyproject.toml, backend/, ingestion/, eval/ (code plus the eval page's summary.json
and chart), data/processed/, the glossary and the prebuilt vector index (data/qdrant, build it
first with `python -m ingestion.index`). The upload goes through huggingface_hub, which stores
large files (the 19 MB index) with LFS, so git-lfs is not needed.

Usage:
    python scripts/deploy_space.py --dry-run                     # stage and list files only
    HF_TOKEN=hf_... python scripts/deploy_space.py --space <user>/mahsool-api
"""

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE_DIRS = ["backend", "ingestion"]
EVAL_FILES = ["eval/reports/summary.json", "eval/reports/ablation-test.png"]
DATA = ["data/processed", "data/glossary_ur.csv", "data/sources.manifest.json", "data/qdrant"]
SKIP = shutil.ignore_patterns("__pycache__", "*.pyc", ".lock", "*.db")


def stage(dest: Path) -> list[Path]:
    if not (ROOT / "data/qdrant/collection").exists():
        sys.exit("data/qdrant is missing: run `python -m ingestion.index` first")
    shutil.copy(ROOT / "Dockerfile", dest / "Dockerfile")
    shutil.copy(ROOT / "deploy/space/README.md", dest / "README.md")
    shutil.copy(ROOT / "pyproject.toml", dest / "pyproject.toml")
    for d in CODE_DIRS:
        shutil.copytree(ROOT / d, dest / d, ignore=SKIP)
    # eval/ code is imported by nothing at runtime, but the package list includes it; ship the
    # modules (small) and the two files the eval page reads.
    shutil.copytree(ROOT / "eval", dest / "eval",
                    ignore=shutil.ignore_patterns("__pycache__", "cache", "reports", "review",
                                                  "*.jsonl", "*.json", "*.md"))  # fmt: skip
    for f in EVAL_FILES:
        (dest / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / f, dest / f)
    for p in DATA:
        src, dst = ROOT / p, dest / p
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, ignore=SKIP)
        else:
            shutil.copy(src, dst)
    return sorted(p for p in dest.rglob("*") if p.is_file())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--space", help="Hugging Face Space id, e.g. hamzabilal000/mahsool-api")
    ap.add_argument("--dry-run", action="store_true", help="stage and list files, no upload")
    ap.add_argument("--keep", type=Path, help="stage into this folder and keep it")
    args = ap.parse_args()

    dest = args.keep or Path(tempfile.mkdtemp(prefix="mahsool-space-"))
    dest.mkdir(parents=True, exist_ok=True)
    files = stage(dest)
    size = sum(f.stat().st_size for f in files) / 1e6
    print(f"staged {len(files)} files, {size:.1f} MB, in {dest}")
    if args.dry_run:
        return
    if not args.space:
        sys.exit("--space is required to upload")
    token = os.environ.get("HF_TOKEN")
    if not token:
        sys.exit("set HF_TOKEN to a Hugging Face token with write access")
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    api.create_repo(args.space, repo_type="space", space_sdk="docker", exist_ok=True)
    api.upload_folder(folder_path=str(dest), repo_id=args.space, repo_type="space",
                      commit_message="Deploy from GitHub main")  # fmt: skip
    print(f"uploaded; the Space builds at https://huggingface.co/spaces/{args.space}")


if __name__ == "__main__":
    main()
