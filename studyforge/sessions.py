from __future__ import annotations
import json
from datetime import datetime, timezone
from .db import connect, document_belongs_to_workspace


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def start_session(workspace_id: int, learning_goal: str = "") -> int:
    now = _now()
    with connect() as con:
        cur = con.execute(
            "INSERT INTO study_sessions(workspace_id,learning_goal,started_at,updated_at,state_json) VALUES(?,?,?,?,?)",
            (workspace_id, learning_goal.strip()[:2000], now, now, "{}"),
        )
        return int(cur.lastrowid)


def get_session(session_id: int):
    with connect() as con:
        return con.execute("SELECT * FROM study_sessions WHERE id=?", (session_id,)).fetchone()


def active_sessions(workspace_id: int, limit: int = 10):
    with connect() as con:
        return con.execute(
            "SELECT * FROM study_sessions WHERE workspace_id=? AND ended_at IS NULL ORDER BY updated_at DESC LIMIT ?",
            (workspace_id, limit),
        ).fetchall()


def update_session(
    session_id: int,
    workspace_id: int,
    *,
    current_document_id: int | None = None,
    current_page: int | None = None,
    selected_text: str | None = None,
    current_concept: str | None = None,
    learning_goal: str | None = None,
    state: dict | None = None,
):
    fields, values = [], []
    if current_document_id is not None:
        if not document_belongs_to_workspace(current_document_id, workspace_id):
            raise ValueError("Il documento non appartiene al workspace della sessione.")
        fields.append("current_document_id=?"); values.append(current_document_id)
    if current_page is not None:
        fields.append("current_page=?"); values.append(max(1, int(current_page)))
    if selected_text is not None:
        fields.append("selected_text=?"); values.append(selected_text[:12000])
    if current_concept is not None:
        fields.append("current_concept=?"); values.append(current_concept.strip()[:500])
    if learning_goal is not None:
        fields.append("learning_goal=?"); values.append(learning_goal.strip()[:2000])
    if state is not None:
        fields.append("state_json=?"); values.append(json.dumps(state, ensure_ascii=False))
    fields.append("updated_at=?"); values.append(_now())
    values.extend([session_id, workspace_id])
    with connect() as con:
        con.execute(
            f"UPDATE study_sessions SET {', '.join(fields)} WHERE id=? AND workspace_id=? AND ended_at IS NULL",
            values,
        )


def end_session(session_id: int, workspace_id: int):
    now = _now()
    with connect() as con:
        con.execute(
            "UPDATE study_sessions SET ended_at=?,updated_at=? WHERE id=? AND workspace_id=?",
            (now, now, session_id, workspace_id),
        )
