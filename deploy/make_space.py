"""Builds a clean folder for Hugging Face Spaces: ../vaani-space

Run from the project folder:   py deploy\make_space.py

It copies only what the live app needs (code, chunks, saved embeddings).
It does NOT copy your PDFs, venv, tests or eval files.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT.parent / "vaani-space"


def copy_code(folder):
    shutil.copytree(ROOT / folder, OUT / folder,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def main():
    chunks = ROOT / "data" / "chunks.json"
    embeddings = sorted((ROOT / "data" / "cache").glob("embeddings_*.npy"))
    if not chunks.exists() or not embeddings:
        sys.exit("Missing data/chunks.json or data/cache/embeddings_*.npy.\n"
                 "Run:  py -m src.ingest   and   py -m eval.run_eval --retriever embedding")

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()

    copy_code("src")
    copy_code("app")
    (OUT / "data" / "cache").mkdir(parents=True)
    shutil.copy2(chunks, OUT / "data" / "chunks.json")
    if (ROOT / "data" / "sources.csv").exists():
        shutil.copy2(ROOT / "data" / "sources.csv", OUT / "data" / "sources.csv")
    for file in embeddings:
        shutil.copy2(file, OUT / "data" / "cache" / file.name)

    shutil.copy2(ROOT / "Dockerfile", OUT / "Dockerfile")
    shutil.copy2(ROOT / "deploy" / "requirements-deploy.txt", OUT / "requirements.txt")
    shutil.copy2(ROOT / "deploy" / "space_README.md", OUT / "README.md")

    total = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"Done. Folder: {OUT}")
    print(f"Files: {sum(1 for p in OUT.rglob('*') if p.is_file())}, size: {total / 1e6:.1f} MB")
    print("Embedding files copied:", ", ".join(f.name for f in embeddings))


if __name__ == "__main__":
    main()
