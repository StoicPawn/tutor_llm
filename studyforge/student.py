from __future__ import annotations
import re
from datetime import datetime, timezone
from .db import connect

STUDENT_SCHEMA = '''
CREATE TABLE IF NOT EXISTS concepts (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL UNIQUE,
 mastery REAL NOT NULL DEFAULT 0.20,
 attempts INTEGER NOT NULL DEFAULT 0,
 correct INTEGER NOT NULL DEFAULT 0,
 last_seen TEXT
);
CREATE TABLE IF NOT EXISTS study_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 concept TEXT NOT NULL,
 score REAL NOT NULL,
 event_type TEXT NOT NULL,
 created_at TEXT NOT NULL
);
'''

def _ensure():
    with connect() as con: con.executescript(STUDENT_SCHEMA)

def normalize_concept(name: str) -> str:
    return re.sub(r'\s+', ' ', name.strip().lower())[:180]

def record_result(concept: str, score: float, event_type: str = 'self_check') -> float:
    _ensure(); c = normalize_concept(concept); score = max(0.0, min(1.0, float(score)))
    now = datetime.now(timezone.utc).isoformat()
    with connect() as con:
        row = con.execute('SELECT mastery,attempts,correct FROM concepts WHERE name=?', (c,)).fetchone()
        old = float(row['mastery']) if row else 0.20
        mastery = max(0.02, min(0.99, old * 0.72 + score * 0.28))
        if row:
            con.execute('UPDATE concepts SET mastery=?,attempts=attempts+1,correct=correct+?,last_seen=? WHERE name=?',
                        (mastery, 1 if score >= .7 else 0, now, c))
        else:
            con.execute('INSERT INTO concepts(name,mastery,attempts,correct,last_seen) VALUES(?,?,?,?,?)',
                        (c, mastery, 1, 1 if score >= .7 else 0, now))
        con.execute('INSERT INTO study_events(concept,score,event_type,created_at) VALUES(?,?,?,?)', (c,score,event_type,now))
    return mastery

def mastery_for(concept: str) -> float:
    _ensure(); c=normalize_concept(concept)
    with connect() as con:
        row=con.execute('SELECT mastery FROM concepts WHERE name=?',(c,)).fetchone()
        return float(row['mastery']) if row else 0.20

def weakest(limit: int = 8):
    _ensure()
    with connect() as con:
        return con.execute('SELECT name,mastery,attempts,last_seen FROM concepts ORDER BY mastery ASC, attempts DESC LIMIT ?', (limit,)).fetchall()
