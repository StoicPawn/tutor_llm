from __future__ import annotations
import os, shutil
from pathlib import Path
from .config import settings
from .db import add_document, add_chunks, add_pages
from .ingest import extract, chunk_pages
from .inference import embed
from .source_map import store_chunk_spans
from .structure import rebuild_structure


def ingest_file(workspace_id: int, src_path: str, original_name: str | None = None) -> dict:
    workspace_dir = Path(settings.upload_dir) / str(workspace_id)
    os.makedirs(workspace_dir, exist_ok=True)
    name = original_name or Path(src_path).name
    safe = Path(name).name
    dst = workspace_dir / safe
    if Path(src_path).resolve() != dst.resolve():
        shutil.copy2(src_path, dst)
    pages = extract(str(dst))
    chunks = chunk_pages(pages)
    if not chunks:
        raise ValueError('Non è stato possibile estrarre testo dal documento.')
    embeddings=[]; batch=16
    for i in range(0,len(chunks),batch):
        embeddings.extend(embed([c['text'] for c in chunks[i:i+batch]]))
    doc_id=add_document(workspace_id,name,str(dst))
    add_pages(doc_id,pages)
    add_chunks(doc_id,chunks,embeddings)
    store_chunk_spans(doc_id,chunks)
    sections=[]
    if any(p.get('page') is not None for p in pages):
        sections=rebuild_structure(workspace_id,doc_id)
    return {
        'document_id':doc_id,'workspace_id':workspace_id,'name':name,
        'pages':len(pages),'chunks':len(chunks),'sections':len(sections),
        'layout_pages':sum(1 for p in pages if p.get('blocks')),
        'ocr_pages':sum(1 for p in pages if p.get('ocr_used')),
    }
