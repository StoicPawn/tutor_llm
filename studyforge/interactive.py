from __future__ import annotations
import json, re
from datetime import datetime, timezone
from .db import connect
from .ollama_client import chat
from .retrieval import retrieve
from .student import record_result
from .repetition import record_review, schedule_concept

SCHEMA = '''
CREATE TABLE IF NOT EXISTS exercise_sessions (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 workspace_id INTEGER NOT NULL,
 topic TEXT NOT NULL,
 epistemic_mode TEXT NOT NULL DEFAULT 'Grounded',
 document_ids_json TEXT NOT NULL DEFAULT '[]',
 current_index INTEGER NOT NULL DEFAULT 0,
 questions_json TEXT NOT NULL,
 created_at TEXT NOT NULL,
 completed_at TEXT,
 FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS exercise_attempts (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 session_id INTEGER NOT NULL,
 question_index INTEGER NOT NULL,
 answer TEXT NOT NULL,
 score REAL NOT NULL,
 feedback TEXT NOT NULL,
 created_at TEXT NOT NULL,
 UNIQUE(session_id,question_index),
 FOREIGN KEY(session_id) REFERENCES exercise_sessions(id) ON DELETE CASCADE
);
'''


def _ensure():
    with connect() as con:
        con.executescript(SCHEMA)


def _json(text: str):
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip(), flags=re.I|re.S)
    try: return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r'[\[{].*[\]}]', text, re.S)
        if not m: raise ValueError('Output JSON non valido.')
        return json.loads(m.group(0))


def _context(workspace_id: int, topic: str, document_ids: list[int] | None, top_k: int = 10):
    src = retrieve(workspace_id, topic, document_ids, top_k)
    if not src: raise ValueError('Nessun materiale disponibile.')
    blocks=[]
    for i,s in enumerate(src,1):
        loc=f"p.{s['page']}" if s['page'] else f"chunk {s['chunk_index']}"
        blocks.append(f"[FONTE {i}: {s['document_name']} {loc}]\n{s['text']}")
    return src, '\n\n'.join(blocks)


def start_exercise_session(workspace_id: int, topic: str, document_ids: list[int] | None = None,
                           n: int = 6, epistemic_mode: str = 'Grounded') -> int:
    _ensure(); _, material = _context(workspace_id, topic, document_ids)
    prompt = f'''Crea {n} esercizi progressivi sul tema "{topic}". Restituisci SOLO un array JSON.
Ogni elemento: {{"question":"...","concept":"...","difficulty":1,"expected":"criteri essenziali per valutarla","hint":"indizio breve"}}.
Alterna recall, applicazione e ragionamento. Difficoltà 1-5. Basa gli esercizi sul materiale e non mettere la soluzione nella domanda.
MATERIALE:\n{material}'''
    questions = _json(chat([{'role':'system','content':'Sei un tutor che genera esercizi verificabili. Solo JSON.'}, {'role':'user','content':prompt}], temperature=.08))
    if isinstance(questions, dict): questions = questions.get('questions', [])
    if not questions: raise ValueError('Nessun esercizio generato.')
    now = datetime.now(timezone.utc).isoformat()
    with connect() as con:
        cur = con.execute('''INSERT INTO exercise_sessions(workspace_id,topic,epistemic_mode,document_ids_json,questions_json,created_at)
                             VALUES(?,?,?,?,?,?)''',
                          (workspace_id, topic, epistemic_mode, json.dumps(document_ids or []), json.dumps(questions, ensure_ascii=False), now))
        sid=int(cur.lastrowid)
    for q in questions:
        schedule_concept(workspace_id, str(q.get('concept') or topic), due_now=False)
    return sid


def session_state(session_id: int) -> dict:
    _ensure()
    with connect() as con:
        row=con.execute('SELECT * FROM exercise_sessions WHERE id=?',(session_id,)).fetchone()
        if not row: raise ValueError('Sessione esercizi non trovata.')
        attempts=[dict(r) for r in con.execute('SELECT * FROM exercise_attempts WHERE session_id=? ORDER BY question_index',(session_id,)).fetchall()]
    data=dict(row); data['questions']=json.loads(data.pop('questions_json')); data['document_ids']=json.loads(data.pop('document_ids_json')); data['attempts']=attempts
    idx=int(data['current_index']); data['current_question']=data['questions'][idx] if idx < len(data['questions']) else None
    return data


def submit_answer(session_id: int, answer: str) -> dict:
    state=session_state(session_id); idx=int(state['current_index'])
    if idx >= len(state['questions']): raise ValueError('Sessione già completata.')
    q=state['questions'][idx]
    src, material=_context(int(state['workspace_id']), q.get('concept') or state['topic'], state['document_ids'])
    prompt=f'''Valuta la risposta dello studente da 0 a 1 rispetto alla domanda e al materiale.
Restituisci SOLO JSON: {{"score":0.0,"correct":["..."],"missing":["..."],"errors":["..."],"feedback":"...","next_hint":"..."}}.
Non premiare affermazioni non supportate. Sii didattico e conciso.
DOMANDA: {q['question']}
CRITERI: {q.get('expected','')}
RISPOSTA: {answer}
MATERIALE:\n{material}'''
    verdict=_json(chat([{'role':'system','content':'Sei un correttore rigoroso. Solo JSON.'},{'role':'user','content':prompt}], temperature=.03))
    score=max(0., min(1., float(verdict.get('score',0))))
    concept=str(q.get('concept') or state['topic'])
    mastery=record_result(int(state['workspace_id']), concept, score, 'interactive_exercise')
    review=record_review(int(state['workspace_id']), concept, score)
    now=datetime.now(timezone.utc).isoformat(); feedback=json.dumps(verdict, ensure_ascii=False)
    next_idx=idx+1; completed=next_idx>=len(state['questions'])
    with connect() as con:
        con.execute('INSERT OR REPLACE INTO exercise_attempts(session_id,question_index,answer,score,feedback,created_at) VALUES(?,?,?,?,?,?)',
                    (session_id,idx,answer,score,feedback,now))
        con.execute('UPDATE exercise_sessions SET current_index=?, completed_at=? WHERE id=?',
                    (next_idx, now if completed else None, session_id))
    return {'score':score,'mastery':mastery,'review':review,'verdict':verdict,'completed':completed,
            'next_question': None if completed else state['questions'][next_idx],
            'sources':[{'document':s['document_name'],'page':s['page'],'chunk':s['chunk_index']} for s in src]}
