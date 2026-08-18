from __future__ import annotations
import os, shutil, uuid
from pathlib import Path
from .config import settings
from .db import add_document, add_chunks
from .ingest import extract, chunk_pages
from .ollama_client import embed


def ingest_file(workspace_id: int, src_path: str, original_name: str | None = None) -> dict:
    workspace_dir = Path(settings.upload_dir) / str(workspace_id)
    os.makedirs(workspace_dir, exist_ok=True)
    name = original_name or Path(src_path).name
    safe = Path(name).name
    # Avoid collisions between two books with the same filename.
    dst = workspace_dir / f"{uuid.uuid4().hex[:10]}_{safe}"
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
    doc_id = add_document(workspace_id, name, str(dst))
    add_chunks(doc_id, chunks, embeddings)
    return {"workspace_id": workspace_id, "document_id": doc_id, "name": name, "pages": len(pages), "chunks": len(chunks)}
