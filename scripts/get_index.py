"""Install the prebuilt vector index, so a new machine skips the ~30-minute re-index.

    python scripts/get_index.py          # install data/index/ into data/qdrant (or download it)
    python scripts/get_index.py --pack   # after `python -m ingestion.index`: pack data/qdrant

The archive (embedded Qdrant folder, ~1,400 BGE-M3 dense + sparse points) is committed under
data/index/ with a manifest: the SHA-256 of the archive, of every chunks.jsonl it was built from,
the embedding model and the qdrant-client version. Installing checks the archive's hash, and warns
when the chunks changed since it was built (then run `python -m ingestion.index` and `--pack`).
When the archive is not in the checkout (a sparse clone), it is downloaded: first from the GitHub
Release "index-v1" (asset qdrant-index.tar.gz), else from the file committed on main.
Standard library only, so it runs before the heavy dependencies are installed.
"""

import argparse
import hashlib
import json
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QDRANT = ROOT / "data" / "qdrant"
INDEX_DIR = ROOT / "data" / "index"
ARCHIVE = INDEX_DIR / "qdrant-index.tar.gz"
MANIFEST = INDEX_DIR / "manifest.json"
STAMP = QDRANT / ".index-manifest.json"  # the manifest of the installed index
RAW_URL = "https://raw.githubusercontent.com/hamzabilal000/mahsool.ai/main/data/index/"
RELEASE_URL = "https://github.com/hamzabilal000/mahsool.ai/releases/download/index-v1/"


def download(name: str, dest: Path) -> None:
    for base in (RELEASE_URL, RAW_URL):
        try:
            print(f"downloading {base + name}")
            urllib.request.urlretrieve(base + name, dest)
            return
        except OSError as e:  # urllib's HTTPError / URLError are OSErrors
            print(f"  not available there ({e})")
    sys.exit(f"could not download {name}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def chunk_hashes() -> dict[str, str]:
    files = sorted((ROOT / "data" / "processed").glob("*/*/chunks.jsonl"))
    return {str(p.relative_to(ROOT)): sha256(p) for p in files}


def pack() -> None:
    if not QDRANT.is_dir():
        sys.exit("data/qdrant not found: run `python -m ingestion.index` first.")
    sys.path.insert(0, str(ROOT))
    from backend.app.config import get_settings

    s = get_settings()
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    with tarfile.open(ARCHIVE, "w:gz", compresslevel=9) as tar:
        for p in sorted(QDRANT.rglob("*")):
            if p.is_file() and p.name != STAMP.name and not p.name.endswith(".lock"):
                tar.add(p, arcname=str(p.relative_to(QDRANT.parent)))
    manifest = {
        "archive": ARCHIVE.name,
        "archive_sha256": sha256(ARCHIVE),
        "archive_bytes": ARCHIVE.stat().st_size,
        "collection": s.qdrant_collection,
        "embedding_model": s.embedding_model,
        "embedding_max_length": s.embedding_max_length,
        "qdrant_client": version("qdrant-client"),
        "chunks": chunk_hashes(),
        "packed": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"packed {ARCHIVE.relative_to(ROOT)}: {manifest['archive_bytes'] / 1e6:.1f} MB")


def install(force: bool = False) -> None:
    if not MANIFEST.exists():
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        download(MANIFEST.name, MANIFEST)
    manifest = json.loads(MANIFEST.read_text())
    if not force and STAMP.exists() and json.loads(STAMP.read_text()) == manifest:
        print("index already installed and current: nothing to do")
        return
    if not ARCHIVE.exists() or sha256(ARCHIVE) != manifest["archive_sha256"]:
        download(ARCHIVE.name, ARCHIVE)
    if sha256(ARCHIVE) != manifest["archive_sha256"]:
        sys.exit(f"{ARCHIVE.name}: checksum does not match the manifest; not installed.")

    with tempfile.TemporaryDirectory(dir=QDRANT.parent) as tmp, tarfile.open(ARCHIVE) as tar:
        # The "data" filter (no absolute paths, no links out) exists from Python 3.11.4.
        kwargs = {"filter": "data"} if hasattr(tarfile, "data_filter") else {}
        tar.extractall(tmp, **kwargs)
        if QDRANT.exists():
            shutil.rmtree(QDRANT)
        shutil.move(Path(tmp) / "qdrant", QDRANT)
    STAMP.write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"installed the index into {QDRANT.relative_to(ROOT)} (packed {manifest['packed']})")

    stale = [f for f, h in manifest["chunks"].items() if chunk_hashes().get(f) != h]
    stale += [f for f in chunk_hashes() if f not in manifest["chunks"]]
    if stale:
        print("WARNING: these chunk files changed after the index was built, so search may miss "
              f"new text: {', '.join(sorted(set(stale)))}. Rebuild: python -m ingestion.index, "
              "then python scripts/get_index.py --pack")  # fmt: skip
    try:
        if version("qdrant-client") != manifest["qdrant_client"]:
            print(f"note: built with qdrant-client {manifest['qdrant_client']}, "
                  f"installed {version('qdrant-client')}")  # fmt: skip
    except PackageNotFoundError:
        pass


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pack", action="store_true", help="pack data/qdrant into data/index/")
    ap.add_argument("--force", action="store_true", help="reinstall even if current")
    args = ap.parse_args()
    pack() if args.pack else install(args.force)


if __name__ == "__main__":
    main()
