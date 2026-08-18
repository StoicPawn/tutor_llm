from __future__ import annotations
from datetime import datetime, timezone
from .db import connect

DEFAULT_WORKSPACE = "General"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_default_workspace() -> int:
    with connect() as con:
        row = con.execute("SELECT id FROM workspaces ORDER BY id LIMIT 1").fetchone()
        if row:
            return int(row["id"])
        cur = con.execute(
            "INSERT INTO workspaces(name,description,goal,created_at) VALUES(?,?,?,?)",
            (DEFAULT_WORKSPACE, "Workspace creato automaticamente per i dati esistenti.", "", _now()),
        )
        return int(cur.lastrowid)


def create_workspace(name: str, description: str = "", goal: str = "") -> int:
    name = " ".join(name.split()).strip()[:120]
    if not name:
        raise ValueError("Il nome del workspace è obbligatorio.")
    with connect() as con:
        cur = con.execute(
            "INSERT INTO workspaces(name,description,goal,created_at) VALUES(?,?,?,?)",
            (name, description.strip()[:2000], goal.strip()[:2000], _now()),
        )
        return int(cur.lastrowid)


def list_workspaces():
    with connect() as con:
        return con.execute(
            "SELECT w.*, (SELECT COUNT(*) FROM documents d WHERE d.workspace_id=w.id) AS document_count "
            "FROM workspaces w ORDER BY w.name COLLATE NOCASE"
        ).fetchall()


def get_workspace(workspace_id: int):
    with connect() as con:
        return con.execute("SELECT * FROM workspaces WHERE id=?", (workspace_id,)).fetchone()


def update_workspace(workspace_id: int, *, name: str | None = None, description: str | None = None, goal: str | None = None):
    fields, values = [], []
    if name is not None:
        clean = " ".join(name.split()).strip()[:120]
        if not clean:
            raise ValueError("Il nome del workspace è obbligatorio.")
        fields.append("name=?"); values.append(clean)
    if description is not None:
        fields.append("description=?"); values.append(description.strip()[:2000])
    if goal is not None:
        fields.append("goal=?"); values.append(goal.strip()[:2000])
    if not fields:
        return
    values.append(workspace_id)
    with connect() as con:
        con.execute(f"UPDATE workspaces SET {', '.join(fields)} WHERE id=?", values)


def delete_workspace(workspace_id: int):
    with connect() as con:
        count = con.execute("SELECT COUNT(*) n FROM workspaces").fetchone()["n"]
        if count <= 1:
            raise ValueError("Deve esistere almeno un workspace.")
        con.execute("DELETE FROM workspaces WHERE id=?", (workspace_id,))
