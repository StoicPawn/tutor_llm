from __future__ import annotations
from datetime import datetime, timedelta, timezone
from .db import connect
from .student import mastery_for

SCHEMA = '''
CREATE TABLE IF NOT EXISTS review_items (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 workspace_id INTEGER NOT NULL,
 concept TEXT NOT NULL,
 ease REAL NOT NULL DEFAULT 2.5,
 interval_days INTEGER NOT NULL DEFAULT 0,
 repetitions INTEGER NOT NULL DEFAULT 0,
 due_at TEXT NOT NULL,
 last_score REAL,
 updated_at TEXT NOT NULL,
 UNIQUE(workspace_id,concept),
 FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_review_due ON review_items(workspace_id,due_at);
'''


def _ensure():
    with connect() as con:
        con.executescript(SCHEMA)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def schedule_concept(workspace_id: int, concept: str, due_now: bool = True):
    _ensure(); now = _now(); due = now if due_now else now + timedelta(days=1)
    with connect() as con:
        con.execute('''INSERT INTO review_items(workspace_id,concept,due_at,updated_at)
                       VALUES(?,?,?,?) ON CONFLICT(workspace_id,concept) DO NOTHING''',
                    (workspace_id, concept.strip(), due.isoformat(), now.isoformat()))


def record_review(workspace_id: int, concept: str, score: float) -> dict:
    _ensure(); score = max(0., min(1., float(score))); now = _now()
    schedule_concept(workspace_id, concept)
    with connect() as con:
        row = con.execute('SELECT * FROM review_items WHERE workspace_id=? AND concept=?', (workspace_id, concept)).fetchone()
        ease = float(row['ease']); reps = int(row['repetitions']); interval = int(row['interval_days'])
        quality = round(score * 5)
        if quality < 3:
            reps = 0; interval = 1
        else:
            reps += 1
            if reps == 1: interval = 1
            elif reps == 2: interval = 6
            else: interval = max(1, round(interval * ease))
            ease = max(1.3, ease + (0.1 - (5-quality)*(0.08 + (5-quality)*0.02)))
        mastery = mastery_for(workspace_id, concept)
        # Strong mastery may modestly lengthen, but never bypass, retrieval practice.
        interval = max(1, round(interval * (0.8 + 0.4 * mastery)))
        due = now + timedelta(days=interval)
        con.execute('''UPDATE review_items SET ease=?,interval_days=?,repetitions=?,due_at=?,last_score=?,updated_at=?
                       WHERE workspace_id=? AND concept=?''',
                    (ease, interval, reps, due.isoformat(), score, now.isoformat(), workspace_id, concept))
    return {'concept': concept, 'score': score, 'interval_days': interval, 'due_at': due.isoformat(), 'ease': ease}


def due_reviews(workspace_id: int, limit: int = 20):
    _ensure(); now = _now().isoformat()
    with connect() as con:
        return con.execute('''SELECT * FROM review_items WHERE workspace_id=? AND due_at<=?
                              ORDER BY due_at ASC LIMIT ?''', (workspace_id, now, limit)).fetchall()


def upcoming_reviews(workspace_id: int, limit: int = 20):
    _ensure()
    with connect() as con:
        return con.execute('SELECT * FROM review_items WHERE workspace_id=? ORDER BY due_at ASC LIMIT ?', (workspace_id, limit)).fetchall()
