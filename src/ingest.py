"""Step 1 of the pipeline: read documents and cut them into small chunks.

Run from the project folder:
    py -m src.ingest

Why chunks? Search works better on small pieces than on a 100-page PDF.
"""
import csv
import json
import logging
import re
from pathlib import Path

from pypdf import PdfReader

logging.getLogger("pypdf").setLevel(logging.CRITICAL)  # hide harmless font warnings

from . import config


def load_friendly_names(csv_path=config.SOURCES_CSV):
    """Read data/sources.csv -> {file name: simple name}. Used so answers say
    'WHO diarrhoea guide' instead of 'pnadk428.pdf'."""
    names = {}
    path = Path(csv_path)
    if not path.exists():
        return names
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("file") and row.get("friendly_name"):
                names[row["file"].strip()] = row["friendly_name"].strip()
    return names


def clean_text(text):
    """Fix common PDF mess: broken words at line ends, many spaces, new lines."""
    text = re.sub(r"-\s*\n\s*", "", text)      # "treat-\nment" -> "treatment"
    text = re.sub(r"\s+", " ", text)           # many spaces/new lines -> one space
    return text.strip()


def read_pages(path):
    """Return a list of (page_number, text) for a .pdf or .txt file."""
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        return [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]
    if path.suffix.lower() == ".txt":
        return [(1, path.read_text(encoding="utf-8", errors="ignore"))]
    return []


def split_words(text, size=config.CHUNK_WORDS, overlap=config.CHUNK_OVERLAP):
    """Cut text into pieces of about `size` words. Pieces overlap a little so
    a sentence at the edge is not lost."""
    words = text.split()
    step = max(size - overlap, 1)
    pieces = []
    for start in range(0, len(words), step):
        piece = words[start:start + size]
        if len(piece) >= config.MIN_CHUNK_WORDS:
            pieces.append(" ".join(piece))
        if start + size >= len(words):
            break
    return pieces


def _file_chunks(path, source_name):
    """Read ONE file and return its chunks (ids are added later)."""
    pages = read_pages(path)
    out = []
    for page_no, raw in pages:
        if page_no % 50 == 0:
            print(f"   ...page {page_no} of {len(pages)}", flush=True)
        for piece in split_words(clean_text(raw)):
            out.append({"source_file": path.name, "source_name": source_name,
                        "page": page_no, "text": piece})
    return out


def ingest(sources_dir=config.SOURCES_DIR, csv_path=config.SOURCES_CSV,
           out_path=config.CHUNKS_FILE, cache_dir=None):
    """Each file is saved in data/cache when it finishes.
    If you stop and run again, finished files are skipped (fast)."""
    sources_dir = Path(sources_dir)
    out_path = Path(out_path)
    cache_dir = Path(cache_dir) if cache_dir else out_path.parent / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    names = load_friendly_names(csv_path)
    files = sorted(p for p in sources_dir.glob("*") if p.suffix.lower() in (".pdf", ".txt"))

    chunks = []
    for path in files:
        source_name = names.get(path.name, path.stem)
        stamp = f"{path.stat().st_size}-{int(path.stat().st_mtime)}-{source_name}"
        cache_file = cache_dir / (path.name + ".json")
        cached = None
        if cache_file.exists():
            saved = json.loads(cache_file.read_text(encoding="utf-8"))
            if saved.get("stamp") == stamp:
                cached = saved["chunks"]
        if cached is None:
            print(f"Reading {path.name} ...", flush=True)
            cached = _file_chunks(path, source_name)
            cache_file.write_text(
                json.dumps({"stamp": stamp, "chunks": cached}, ensure_ascii=False),
                encoding="utf-8")
            print(f"{path.name}: {len(cached)} chunks", flush=True)
        else:
            print(f"{path.name}: {len(cached)} chunks (already done)", flush=True)
        chunks.extend(cached)

    for i, chunk in enumerate(chunks):
        chunk["id"] = i
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(chunks, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Total: {len(chunks)} chunks from {len(files)} files -> {out_path}")
    return chunks


if __name__ == "__main__":
    ingest()
