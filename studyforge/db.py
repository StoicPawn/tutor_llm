from __future__ import annotations
import json, os, sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  path TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chunks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id INTEGER NOT NULL,
  page INTEGER,
  chunk_index INTEGER NOT NULL,
  text TEXT NOT NULL,
  embedding TEXT NOT NULL,
  FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
CREATE TABLE IF NOT EXISTS lessons (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic TEXT NOT NULL,
  mode TEXT NOT NULL,
  content TEXT NOT NULL,
  sources_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  rating INTEGER,
  feedback TEXT
);
"""

@contextmanager
def connect():
    os.makedirs(os.path.dirname(settings.db_path) or ".", exist_ok=True)
    con = sqlite3.connect(settings.db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(SCHEMA)
    try:
        yield con
        con.commit()
    finally:
        con.close()

def add_document(name: str, path: str) -> int:
    with connect() as con:
        cur = con.execute("INSERT INTO documents(name,path,created_at) VALUES(?,?,?)", (name, path, datetime.now(timezone.utc).isoformat()))
        return int(cur.lastrowid)

def add_chunks(document_id: int, chunks: list[dict], embeddings: list[list[float]]):
    with connect() as con:
        con.executemany(
            "INSERT INTO chunks(document_id,page,chunk_index,text,embedding) VALUES(?,?,?,?,?)",
            [(document_id, c.get("page"), c["chunk_index"], c["text"], json.dumps(e)) for c, e in zip(chunks, embeddings)]
        )

def list_documents():
    with connect() as con:
        return con.execute("SELECT id,name,created_at FROM documents ORDER BY id DESC").fetchall()

def iter_chunks(document_ids: list[int] | None = None):
    with connect() as con:
        if document_ids:
            marks = ",".join("?" for _ in document_ids)
            q = f"SELECT c.*, d.name document_name FROM chunks c JOIN documents d ON d.id=c.document_id WHERE c.document_id IN ({marks})"
            return con.execute(q, document_ids).fetchall()
        return con.execute("SELECT c.*, d.name document_name FROM chunks c JOIN documents d ON d.id=c.document_id").fetchall()

def save_lesson(topic: str, mode: str, content: str, sources: list[dict]) -> int:
    with connect() as con:
        cur = con.execute("INSERT INTO lessons(topic,mode,content,sources_json,created_at) VALUES(?,?,?,?,?)", (topic, mode, content, json.dumps(sources, ensure_ascii=False), datetime.now(timezone.utc).isoformat()))
        return int(cur.lastrowid)

def rate_lesson(lesson_id: int, rating: int, feedback: str):
    with connect() as con:
        con.execute("UPDATE lessons SET rating=?, feedback=? WHERE id=?", (rating, feedback, lesson_id))

def rated_lessons():
    with connect() as con:
        return con.execute("SELECT * FROM lessons WHERE rating IS NOT NULL ORDER BY id").fetchall()

def delete_document(document_id: int):
    with connect() as con:
        row = con.execute("SELECT path FROM documents WHERE id=?", (document_id,)).fetchone()
        con.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
        con.execute("DELETE FROM documents WHERE id=?", (document_id,))
    if row:
        try: os.remove(row["path"])
        except OSError: pass

def recent_lessons(limit: int = 20):
    with connect() as con:
        return con.execute("SELECT id,topic,mode,created_at,rating FROM lessons ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
