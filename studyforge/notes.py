from __future__ import annotations
from datetime import datetime, timezone
from .db import connect, document_belongs_to_workspace


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _note_payload(row)->dict:
    d=dict(row)
    return {
        'title':d.get('title',''),
        'content':d.get('content',''),
        'kind':d.get('kind','text'),
        'document_id':d.get('document_id'),
        'page':d.get('page'),
        'created_at':d.get('created_at'),
        'updated_at':d.get('updated_at'),
    }


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
        note_id=int(cur.lastrowid)
        row=con.execute('SELECT * FROM notes WHERE id=? AND workspace_id=?',(note_id,workspace_id)).fetchone()
    from .offline_sync import sync_server_upsert
    sync_server_upsert(workspace_id,'note',note_id,_note_payload(row))
    return note_id


def update_note(workspace_id: int, note_id: int, *, title: str | None = None, content: str | None = None):
    fields, values = [], []
    if title is not None:
        fields.append("title=?"); values.append(title.strip()[:240] or "Nota senza titolo")
    if content is not None:
        fields.append("content=?"); values.append(content)
    fields.append("updated_at=?"); values.append(_now())
    values.extend([note_id, workspace_id])
    with connect() as con:
        cur=con.execute(f"UPDATE notes SET {', '.join(fields)} WHERE id=? AND workspace_id=?", values)
        if cur.rowcount!=1:
            raise ValueError('Nota non trovata.')
        row=con.execute('SELECT * FROM notes WHERE id=? AND workspace_id=?',(note_id,workspace_id)).fetchone()
    from .offline_sync import sync_server_upsert
    sync_server_upsert(workspace_id,'note',note_id,_note_payload(row))
    return dict(row)


def list_notes(workspace_id: int, limit: int = 100):
    with connect() as con:
        return con.execute(
            "SELECT n.*, d.name document_name FROM notes n LEFT JOIN documents d ON d.id=n.document_id "
            "WHERE n.workspace_id=? ORDER BY n.updated_at DESC LIMIT ?",
            (workspace_id, limit),
        ).fetchall()


def delete_note(workspace_id: int, note_id: int):
    with connect() as con:
        row=con.execute('SELECT * FROM notes WHERE id=? AND workspace_id=?',(note_id,workspace_id)).fetchone()
        if not row: return False
        con.execute("DELETE FROM notes WHERE id=? AND workspace_id=?", (note_id, workspace_id))
    from .offline_sync import sync_server_delete
    sync_server_delete(workspace_id,'note',note_id,_note_payload(row))
    return True
