from __future__ import annotations
import json
import numpy as np
from .db import iter_chunks
from .ollama_client import embed

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    den = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / den) if den else 0.0

def retrieve(query: str, document_ids: list[int] | None, top_k: int) -> list[dict]:
    rows = iter_chunks(document_ids)
    if not rows:
        return []
    q = np.asarray(embed([query])[0], dtype=np.float32)
    scored = []
    for r in rows:
        e = np.asarray(json.loads(r["embedding"]), dtype=np.float32)
        scored.append((_cosine(q, e), r))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for score, r in scored[:top_k]:
        out.append({
            "score": score,
            "document_id": r["document_id"],
            "document_name": r["document_name"],
            "page": r["page"],
            "chunk_index": r["chunk_index"],
            "text": r["text"],
        })
    return out
