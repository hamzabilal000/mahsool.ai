"""Download consolidated FBR law PDFs, record checksums, and flag newer versions.

Re-running is cheap: if the manifest says we already have the file and the server's
ETag / Last-Modified / size are unchanged, nothing is downloaded.

Usage:
    python -m ingestion.download --law ITO2001            # download if changed
    python -m ingestion.download --law ITO2001 --check-latest
"""

import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
from pydantic import BaseModel

from ingestion.laws import LAWS, LawConfig
from ingestion.parse import raw_pdf_path
from ingestion.settings import get_settings

log = logging.getLogger(__name__)

# "Income Tax Ordinance, 2001 Amended upto 30.06.2026" (FBR spells it "upto" / "up to").
VERSION_LINK_RE = re.compile(
    r'<a[^>]+href="(?P<href>[^"]+\.pdf)"[^>]*>(?P<label>[^<]*?amended\s+up\s*to\s*'
    r"(?P<d>\d{1,2})[.\-/](?P<m>\d{1,2})[.\-/](?P<y>\d{4})[^<]*)</a>",
    re.I,
)


class ManifestEntry(BaseModel):
    law: str
    version_date: date
    url: str
    path: str
    sha256: str
    bytes: int
    etag: str | None = None
    last_modified: str | None = None
    downloaded_at: datetime


class NewerVersion(BaseModel):
    version_date: date
    url: str
    label: str


def manifest_path() -> Path:
    """Committed to git (unlike the PDFs) so anyone can verify they have the same source."""
    return get_settings().data_dir / "sources.manifest.json"


def load_manifest() -> dict[str, ManifestEntry]:
    path = manifest_path()
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {k: ManifestEntry.model_validate(v) for k, v in raw.items()}


def save_manifest(manifest: dict[str, ManifestEntry]) -> None:
    path = manifest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {k: v.model_dump(mode="json") for k, v in sorted(manifest.items())}
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _client() -> httpx.Client:
    s = get_settings()
    return httpx.Client(
        timeout=s.http_timeout_s, follow_redirects=True, headers={"User-Agent": s.user_agent}
    )


def download(cfg: LawConfig, force: bool = False) -> ManifestEntry:
    manifest = load_manifest()
    key = cfg.snapshot_id
    dest = raw_pdf_path(cfg)
    known = manifest.get(key)

    with _client() as client:
        if known and dest.exists() and not force and sha256_of(dest) == known.sha256:
            head = client.head(cfg.source_url)
            head.raise_for_status()
            same = (
                head.headers.get("etag") == known.etag
                and head.headers.get("last-modified") == known.last_modified
                and int(head.headers.get("content-length", known.bytes)) == known.bytes
            )
            if same:
                log.info("%s unchanged on FBR (sha256 %s…) — skipping", key, known.sha256[:12])
                return known
            log.warning("%s changed on the server since the last download", key)

        log.info("downloading %s", cfg.source_url)
        resp = client.get(cfg.source_url)
        resp.raise_for_status()
        if not resp.content.startswith(b"%PDF"):
            raise RuntimeError(f"{cfg.source_url} did not return a PDF")

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    entry = ManifestEntry(
        law=cfg.law,
        version_date=cfg.version_date,
        url=cfg.source_url,
        path=str(dest),
        sha256=sha256_of(dest),
        bytes=len(resp.content),
        etag=resp.headers.get("etag"),
        last_modified=resp.headers.get("last-modified"),
        downloaded_at=datetime.now(UTC),
    )
    if known and known.sha256 != entry.sha256:
        log.warning("%s content changed: %s… → %s…", key, known.sha256[:12], entry.sha256[:12])
    manifest[key] = entry
    save_manifest(manifest)
    log.info("saved %s (%d bytes, sha256 %s…)", dest, entry.bytes, entry.sha256[:12])
    return entry


def find_versions(html: str) -> list[NewerVersion]:
    """All 'Amended upto DD.MM.YYYY' links on an FBR index page, newest first."""
    versions = []
    for m in VERSION_LINK_RE.finditer(html):
        try:
            d = date(int(m.group("y")), int(m.group("m")), int(m.group("d")))
        except ValueError:
            continue
        label = re.sub(r"\s+", " ", m.group("label")).strip()
        versions.append(NewerVersion(version_date=d, url=m.group("href"), label=label))
    return sorted(versions, key=lambda v: v.version_date, reverse=True)


def check_latest(cfg: LawConfig) -> NewerVersion | None:
    """Return the newest version on FBR's index page if it is newer than our config."""
    if not cfg.index_page_url:
        return None
    with _client() as client:
        resp = client.get(cfg.index_page_url)
        resp.raise_for_status()
    versions = find_versions(resp.text)
    if not versions:
        log.warning(
            "no versioned links found on %s — page layout may have changed", cfg.index_page_url
        )
        return None
    newest = versions[0]
    if newest.version_date > cfg.version_date:
        return newest
    log.info("%s is the latest version on FBR (%s)", cfg.snapshot_id, newest.label)
    return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--law", default="ITO2001", choices=sorted(LAWS))
    ap.add_argument("--force", action="store_true", help="download even if unchanged")
    ap.add_argument(
        "--check-latest",
        action="store_true",
        help="only check FBR for a newer consolidated version",
    )
    args = ap.parse_args()
    cfg = LAWS[args.law]

    if args.check_latest:
        newer = check_latest(cfg)
        if newer:
            log.warning(
                "NEWER VERSION on FBR: %s (%s) — update ingestion/laws/ and re-ingest",
                newer.label,
                newer.url,
            )
            sys.exit(2)
        return
    download(cfg, force=args.force)


if __name__ == "__main__":
    main()
