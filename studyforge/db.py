from __future__ import annotations
import json, os, sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS workspaces (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  description TEXT NOT NULL DEFAULT '',
  goal TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  workspace_id INTEGER,
  name TEXT NOT NULL,
  path TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
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
  workspace_id INTEGER,
  topic TEXT NOT NULL,
  mode TEXT NOT NULL,
  epistemic_mode TEXT NOT NULL DEFAULT 'Grounded',
  content TEXT NOT NULL,
  sources_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  rating INTEGER,
  feedback TEXT,
  FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS notes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  workspace_id INTEGER NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL DEFAULT '',
  kind TEXT NOT NULL DEFAULT 'text',
  document_id INTEGER,
  page INTEGER,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
  FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS study_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  workspace_id INTEGER NOT NULL,
  current_document_id INTEGER,
  current_page INTEGER,
  selected_text TEXT NOT NULL DEFAULT '',
  current_concept TEXT NOT NULL DEFAULT '',
  learning_goal TEXT NOT NULL DEFAULT '',
  state_json TEXT NOT NULL DEFAULT '{}',
  started_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  ended_at TEXT,
  FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
  FOREIGN KEY(current_document_id) REFERENCES documents(id) ON DELETE SET NULL
);
"""


def _column_names(con: sqlite3.Connection, table: str) -> set[str]:
    return {r["name"] for r in con.execute(f"PRAGMA table_info({table})").fetchall()}


def _ensure_column(con: sqlite3.Connection, table: str, name: str, ddl: str):
    if name not in _column_names(con, table):
        con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def _migrate(con: sqlite3.Connection):
    now = datetime.now(timezone.utc).isoformat()
    row = con.execute("SELECT id FROM workspaces ORDER BY id LIMIT 1").fetchone()
    if row:
        default_id = int(row["id"])
    else:
        default_id = int(con.execute(
            "INSERT INTO workspaces(name,description,goal,created_at) VALUES(?,?,?,?)",
            ("General", "Workspace creato automaticamente per i dati esistenti.", "", now),
        ).lastrowid)

    _ensure_column(con, "documents", "workspace_id", "INTEGER")
    _ensure_column(con, "lessons", "workspace_id", "INTEGER")
    _ensure_column(con, "lessons", "epistemic_mode", "TEXT NOT NULL DEFAULT 'Grounded'")
    con.execute("UPDATE documents SET workspace_id=? WHERE workspace_id IS NULL", (default_id,))
    con.execute("UPDATE lessons SET workspace_id=? WHERE workspace_id IS NULL", (default_id,))
    # Create indexes only after legacy tables have been upgraded.
    con.execute("CREATE INDEX IF NOT EXISTS idx_documents_workspace ON documents(workspace_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_lessons_workspace ON lessons(workspace_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_notes_workspace ON notes(workspace_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_sessions_workspace ON study_sessions(workspace_id)")


@contextmanager
def connect():
    os.makedirs(os.path.dirname(settings.db_path) or ".", exist_ok=True)
    con = sqlite3.connect(settings.db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(SCHEMA)
    _migrate(con)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def add_document(workspace_id: int, name: str, path: str) -> int:
    with connect() as con:
        cur = con.execute(
            "INSERT INTO documents(workspace_id,name,path,created_at) VALUES(?,?,?,?)",
            (workspace_id, name, path, datetime.now(timezone.utc).isoformat()),
        )
        return int(cur.lastrowid)


def add_chunks(document_id: int, chunks: list[dict], embeddings: list[list[float]]):
    with connect() as con:
        con.executemany(
            "INSERT INTO chunks(document_id,page,chunk_index,text,embedding) VALUES(?,?,?,?,?)",
            [(document_id, c.get("page"), c["chunk_index"], c["text"], json.dumps(e)) for c, e in zip(chunks, embeddings)],
        )


def list_documents(workspace_id: int):
    with connect() as con:
        return con.execute(
            "SELECT id,name,created_at FROM documents WHERE workspace_id=? ORDER BY id DESC", (workspace_id,)
        ).fetchall()


def document_belongs_to_workspace(document_id: int, workspace_id: int) -> bool:
    with connect() as con:
        return con.execute(
            "SELECT 1 FROM documents WHERE id=? AND workspace_id=?", (document_id, workspace_id)
        ).fetchone() is not None


def iter_chunks(workspace_id: int, document_ids: list[int] | None = None):
    with connect() as con:
        params: list[object] = [workspace_id]
        where = "d.workspace_id=?"
        if document_ids:
            marks = ",".join("?" for _ in document_ids)
            where += f" AND c.document_id IN ({marks})"
            params.extend(document_ids)
        q = (
            "SELECT c.*, d.name document_name, d.workspace_id FROM chunks c "
            "JOIN documents d ON d.id=c.document_id WHERE " + where
        )
        return con.execute(q, params).fetchall()


def save_lesson(workspace_id: int, topic: str, mode: str, content: str, sources: list[dict], epistemic_mode: str = "Grounded") -> int:
    with connect() as con:
        cur = con.execute(
            "INSERT INTO lessons(workspace_id,topic,mode,epistemic_mode,content,sources_json,created_at) VALUES(?,?,?,?,?,?,?)",
            (workspace_id, topic, mode, epistemic_mode, content, json.dumps(sources, ensure_ascii=False), datetime.now(timezone.utc).isoformat()),
        )
        return int(cur.lastrowid)


def rate_lesson(lesson_id: int, rating: int, feedback: str):
    with connect() as con:
        con.execute("UPDATE lessons SET rating=?, feedback=? WHERE id=?", (rating, feedback, lesson_id))


def rated_lessons(workspace_id: int | None = None):
    with connect() as con:
        if workspace_id is None:
            return con.execute("SELECT * FROM lessons WHERE rating IS NOT NULL ORDER BY id").fetchall()
        return con.execute(
            "SELECT * FROM lessons WHERE workspace_id=? AND rating IS NOT NULL ORDER BY id", (workspace_id,)
        ).fetchall()


def delete_document(workspace_id: int, document_id: int):
    with connect() as con:
        row = con.execute(
            "SELECT path FROM documents WHERE id=? AND workspace_id=?", (document_id, workspace_id)
        ).fetchone()
        if not row:
            return
        con.execute("DELETE FROM chunks WHERE document_id=?", (document_id,))
        con.execute("DELETE FROM documents WHERE id=? AND workspace_id=?", (document_id, workspace_id))
    try:
        os.remove(row["path"])
    except OSError:
        pass


def recent_lessons(workspace_id: int, limit: int = 20):
    with connect() as con:
        return con.execute(
            "SELECT id,topic,mode,epistemic_mode,created_at,rating FROM lessons WHERE workspace_id=? ORDER BY id DESC LIMIT ?",
            (workspace_id, limit),
        ).fetchall()
