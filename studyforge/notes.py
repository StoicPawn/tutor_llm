from __future__ import annotations
from datetime import datetime, timezone
from .db import connect, document_belongs_to_workspace


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_note(workspace_id: int, title: str, content: str = "", *, kind: str = "text", document_id: int | None = None, page: int | None = None) -> int:
    title = title.strip()[:240] or "Nota senza titolo"
    if document_id is not None and not document_belongs_to_workspace(document_id, workspace_id):
        raise ValueError("Il documento non appartiene al workspace.")
    now = _now()
    with connect() as con:
        cur = con.execute(
            "INSERT INTO notes(workspace_id,title,content,kind,document_id,page,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (workspace_id, title, content, kind[:40], document_id, page, now, now),
        )
        return int(cur.lastrowid)


def update_note(workspace_id: int, note_id: int, *, title: str | None = None, content: str | None = None):
    fields, values = [], []
    if title is not None:
        fields.append("title=?"); values.append(title.strip()[:240] or "Nota senza titolo")
    if content is not None:
        fields.append("content=?"); values.append(content)
    fields.append("updated_at=?"); values.append(_now())
    values.extend([note_id, workspace_id])
    with connect() as con:
        con.execute(f"UPDATE notes SET {', '.join(fields)} WHERE id=? AND workspace_id=?", values)


def list_notes(workspace_id: int, limit: int = 100):
    with connect() as con:
        return con.execute(
            "SELECT n.*, d.name document_name FROM notes n LEFT JOIN documents d ON d.id=n.document_id "
            "WHERE n.workspace_id=? ORDER BY n.updated_at DESC LIMIT ?",
            (workspace_id, limit),
        ).fetchall()


def delete_note(workspace_id: int, note_id: int):
    with connect() as con:
        con.execute("DELETE FROM notes WHERE id=? AND workspace_id=?", (note_id, workspace_id))
