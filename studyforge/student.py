from __future__ import annotations
import re
from datetime import datetime, timezone
from .db import connect

STUDENT_SCHEMA = '''
CREATE TABLE IF NOT EXISTS concepts (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 workspace_id INTEGER NOT NULL,
 name TEXT NOT NULL,
 mastery REAL NOT NULL DEFAULT 0.20,
 attempts INTEGER NOT NULL DEFAULT 0,
 correct INTEGER NOT NULL DEFAULT 0,
 last_seen TEXT,
 UNIQUE(workspace_id,name),
 FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS study_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 workspace_id INTEGER NOT NULL,
 concept TEXT NOT NULL,
 score REAL NOT NULL,
 event_type TEXT NOT NULL,
 created_at TEXT NOT NULL,
 FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_concepts_workspace ON concepts(workspace_id,mastery);
CREATE INDEX IF NOT EXISTS idx_events_workspace ON study_events(workspace_id,created_at);
'''


def _columns(con, table: str) -> set[str]:
    return {r['name'] for r in con.execute(f'PRAGMA table_info({table})').fetchall()}


def _ensure():
    with connect() as con:
        default = int(con.execute('SELECT id FROM workspaces ORDER BY id LIMIT 1').fetchone()['id'])
        if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='concepts'").fetchone() and 'workspace_id' not in _columns(con, 'concepts'):
            con.execute('ALTER TABLE concepts RENAME TO concepts_legacy')
            con.execute('ALTER TABLE study_events RENAME TO study_events_legacy')
            con.executescript(STUDENT_SCHEMA)
            con.execute('INSERT INTO concepts(workspace_id,name,mastery,attempts,correct,last_seen) SELECT ?,name,mastery,attempts,correct,last_seen FROM concepts_legacy', (default,))
            con.execute('INSERT INTO study_events(workspace_id,concept,score,event_type,created_at) SELECT ?,concept,score,event_type,created_at FROM study_events_legacy', (default,))
            con.execute('DROP TABLE concepts_legacy')
            con.execute('DROP TABLE study_events_legacy')
        else:
            con.executescript(STUDENT_SCHEMA)


def normalize_concept(name: str) -> str:
    return re.sub(r'\s+', ' ', name.strip().lower())[:180]


def record_result(workspace_id: int, concept: str, score: float, event_type: str = 'self_check') -> float:
    _ensure(); c = normalize_concept(concept); score = max(0.0, min(1.0, float(score)))
    now = datetime.now(timezone.utc).isoformat()
    with connect() as con:
        row = con.execute('SELECT mastery,attempts,correct FROM concepts WHERE workspace_id=? AND name=?', (workspace_id, c)).fetchone()
        old = float(row['mastery']) if row else 0.20
        mastery = max(0.02, min(0.99, old * 0.72 + score * 0.28))
        if row:
            con.execute('UPDATE concepts SET mastery=?,attempts=attempts+1,correct=correct+?,last_seen=? WHERE workspace_id=? AND name=?',
                        (mastery, 1 if score >= .7 else 0, now, workspace_id, c))
        else:
            con.execute('INSERT INTO concepts(workspace_id,name,mastery,attempts,correct,last_seen) VALUES(?,?,?,?,?,?)',
                        (workspace_id, c, mastery, 1, 1 if score >= .7 else 0, now))
        con.execute('INSERT INTO study_events(workspace_id,concept,score,event_type,created_at) VALUES(?,?,?,?,?)',
                    (workspace_id, c, score, event_type, now))
    return mastery


def mastery_for(workspace_id: int, concept: str) -> float:
    _ensure(); c = normalize_concept(concept)
    with connect() as con:
        row = con.execute('SELECT mastery FROM concepts WHERE workspace_id=? AND name=?', (workspace_id, c)).fetchone()
        return float(row['mastery']) if row else 0.20


def weakest(workspace_id: int, limit: int = 8):
    _ensure()
    with connect() as con:
        return con.execute(
            'SELECT name,mastery,attempts,last_seen FROM concepts WHERE workspace_id=? ORDER BY mastery ASC, attempts DESC LIMIT ?',
            (workspace_id, limit),
        ).fetchall()
