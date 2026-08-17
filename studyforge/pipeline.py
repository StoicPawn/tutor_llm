from __future__ import annotations
import os, shutil
from pathlib import Path
from .config import settings
from .db import add_document, add_chunks
from .ingest import extract, chunk_pages
from .ollama_client import embed

def ingest_file(src_path: str, original_name: str | None = None) -> dict:
    os.makedirs(settings.upload_dir, exist_ok=True)
    name = original_name or Path(src_path).name
    safe = Path(name).name
    dst = Path(settings.upload_dir) / safe
    if Path(src_path).resolve() != dst.resolve():
        shutil.copy2(src_path, dst)
    pages = extract(str(dst))
    chunks = chunk_pages(pages)
    if not chunks:
        raise ValueError("Non è stato possibile estrarre testo dal documento.")
    embeddings = []
    batch = 16
    for i in range(0, len(chunks), batch):
        embeddings.extend(embed([c["text"] for c in chunks[i:i+batch]]))
    doc_id = add_document(name, str(dst))
    add_chunks(doc_id, chunks, embeddings)
    return {"document_id": doc_id, "name": name, "pages": len(pages), "chunks": len(chunks)}
