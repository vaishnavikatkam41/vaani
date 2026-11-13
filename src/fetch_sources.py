"""Download the official health PDFs listed in data/sources.csv.

Run from the project folder:
    python -m src.fetch_sources          # download missing files
    python -m src.fetch_sources --force  # download everything again

Every file is checked: it must really be a PDF (not an error page).
A small record (size + SHA-256) is written to data/sources/manifest.json,
so you can prove later exactly which version of each document Vaani used.
"""
import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import config

USER_AGENT = "Mozilla/5.0 (Vaani health-awareness research project)"


def read_sources(csv_path=config.SOURCES_CSV):
    with open(csv_path, newline="", encoding="utf-8") as f:
        return [row for row in csv.DictReader(f) if row.get("file") and row.get("url")]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _python_get(url, tmp, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp, "wb") as out:
        while block := resp.read(1 << 16):
            out.write(block)


def download(url, dest, timeout=120):
    """Download to a temp file, check it is a PDF, then move into place.

    Some government sites send an incomplete certificate chain that Python rejects
    but the system's curl accepts (it uses the OS certificate store). In that case we
    retry with curl. Certificate checking is never switched off."""
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        _python_get(url, tmp, timeout)
    except urllib.error.URLError as err:
        if "CERTIFICATE_VERIFY_FAILED" not in str(err) or not shutil.which("curl"):
            raise
        subprocess.run(["curl", "-sSfL", "--max-time", str(timeout), "-A", USER_AGENT,
                        "-o", str(tmp), url], check=True)
    with open(tmp, "rb") as f:
        if f.read(5) != b"%PDF-":
            tmp.unlink()
            raise ValueError("not a PDF (the site probably returned an error page)")
    tmp.replace(dest)


def fetch_all(sources_dir=config.SOURCES_DIR, csv_path=config.SOURCES_CSV, force=False):
    sources_dir = Path(sources_dir)
    sources_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = sources_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    failed = []

    for row in read_sources(csv_path):
        dest = sources_dir / row["file"]
        if dest.exists() and not force:
            print(f"ok    {row['file']} (already here)")
        else:
            try:
                print(f"get   {row['file']} ...", flush=True)
                download(row["url"], dest)
            except Exception as err:  # network errors, 404s, non-PDF pages
                print(f"FAIL  {row['file']}: {err}")
                failed.append(row["file"])
                continue
        manifest[row["file"]] = {"url": row["url"], "bytes": dest.stat().st_size,
                                 "sha256": sha256(dest),
                                 "checked": time.strftime("%Y-%m-%d")}

    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"\n{len(manifest)} files ready, {len(failed)} failed: {', '.join(failed) or '-'}")
    print("Next:  python -m src.ingest")
    return failed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="download again even if present")
    fetch_all(force=parser.parse_args().force)
