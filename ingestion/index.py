"""Embed every processed chunk with BGE-M3 (dense + sparse) and load it into Qdrant.

Usage:
    python -m ingestion.index                 # all laws in data/processed
    python -m ingestion.index --laws ITO2001  # one law
    python -m ingestion.index --only ITR2002-r5   # re-embed these chunks in place (no recreate)
"""

import argparse
import logging
import time

from backend.app.config import get_settings
from backend.app.rag.corpus import embedding_text, load_chunks
from backend.app.rag.embedder import BGEM3Embedder, Embedder
from backend.app.rag.store import VectorStore, make_client
from ingestion.models import Chunk

log = logging.getLogger(__name__)


def index_chunks(
    chunks: list[Chunk], embedder: Embedder, store: VectorStore, batch_size: int = 32
) -> None:
    store.recreate()
    start = time.perf_counter()
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        store.upsert(batch, embedder.encode([embedding_text(c) for c in batch]))
        log.info(
            "indexed %d/%d chunks (%.0fs)", i + len(batch), len(chunks), time.perf_counter() - start
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--laws", nargs="*", help="law ids, e.g. ITO2001 ITR2002 (default: all)")
    ap.add_argument("--only", nargs="*", help="chunk ids to re-embed and update in place")
    args = ap.parse_args()
    settings = get_settings()

    chunks = load_chunks(laws=args.laws)
    store = VectorStore(make_client(settings), settings.qdrant_collection, settings.embedding_dim)
    if args.only:
        picked = [c for c in chunks if c.chunk_id in set(args.only)]
        if len(picked) != len(set(args.only)):
            raise SystemExit(f"unknown chunk ids: {set(args.only) - {c.chunk_id for c in picked}}")
        store.upsert(picked, BGEM3Embedder(settings).encode([embedding_text(c) for c in picked]))
        log.info("re-embedded %s", [c.chunk_id for c in picked])
    else:
        index_chunks(chunks, BGEM3Embedder(settings), store)
    log.info("collection %s now holds %d points", settings.qdrant_collection, store.count())


if __name__ == "__main__":
    main()
