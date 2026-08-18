from __future__ import annotations
import json, re
from datetime import datetime, timezone
from .db import connect
from .ollama_client import chat
from .teacher import _context
from .repetition import schedule_concept, record_review

SCHEMA='''
CREATE TABLE IF NOT EXISTS flashcards (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 workspace_id INTEGER NOT NULL,
 concept TEXT NOT NULL,
 question TEXT NOT NULL,
 answer TEXT NOT NULL,
 sources_json TEXT NOT NULL DEFAULT '[]',
 created_at TEXT NOT NULL,
 archived INTEGER NOT NULL DEFAULT 0,
 FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_flashcards_workspace ON flashcards(workspace_id,archived,id);
'''


def _ensure():
    with connect() as con: con.executescript(SCHEMA)


def _json(text:str)->dict:
    text=re.sub(r'^```(?:json)?\s*|\s*```$','',text.strip(),flags=re.I|re.S)
    try: return json.loads(text)
    except json.JSONDecodeError:
        m=re.search(r'\{.*\}',text,re.S)
        if not m: raise ValueError('Flashcard JSON non valido.')
        return json.loads(m.group(0))


def generate_flashcards(workspace_id:int, topic:str, document_ids:list[int]|None=None, n:int=8)->list[dict]:
    _ensure(); _,blocks,compact=_context(workspace_id,topic,document_ids,min(10,max(5,n)))
    prompt=f'''Crea {n} flashcard di active recall sul tema "{topic}" usando soltanto il materiale.
Restituisci SOLO JSON valido: {{"cards":[{{"concept":"...","question":"...","answer":"...","sources":[1,2]}}]}}.
Le domande devono testare comprensione, relazioni e applicazione, non solo definizioni. Le risposte devono essere concise.
MATERIALE:\n{chr(10).join(blocks)}'''
    data=_json(chat([{'role':'system','content':'Sei un tutor rigoroso. Produci solo JSON.'},{'role':'user','content':prompt}],temperature=.08))
    cards=[]; concepts=[]; now=datetime.now(timezone.utc).isoformat()
    with connect() as con:
        for raw in data.get('cards',[])[:n]:
            q=str(raw.get('question','')).strip(); a=str(raw.get('answer','')).strip(); concept=str(raw.get('concept') or topic).strip()[:180]
            if not q or not a: continue
            nums=[int(x) for x in raw.get('sources',[]) if isinstance(x,(int,float)) and 1 <= int(x) <= len(compact)]
            src=[compact[i-1] for i in nums]
            cur=con.execute('INSERT INTO flashcards(workspace_id,concept,question,answer,sources_json,created_at) VALUES(?,?,?,?,?,?)',
                            (workspace_id,concept,q,a,json.dumps(src,ensure_ascii=False),now))
            fid=int(cur.lastrowid); cards.append({'id':fid,'concept':concept,'question':q,'answer':a,'sources':src}); concepts.append(concept)
    for concept in dict.fromkeys(concepts):
        schedule_concept(workspace_id,concept)
    return cards


def list_flashcards(workspace_id:int, limit:int=100):
    _ensure()
    with connect() as con:
        rows=con.execute('SELECT * FROM flashcards WHERE workspace_id=? AND archived=0 ORDER BY id DESC LIMIT ?', (workspace_id,limit)).fetchall()
    out=[]
    for r in rows:
        d=dict(r); d['sources']=json.loads(d.pop('sources_json')); out.append(d)
    return out


def review_flashcard(workspace_id:int, flashcard_id:int, score:float)->dict:
    _ensure()
    with connect() as con:
        r=con.execute('SELECT concept FROM flashcards WHERE id=? AND workspace_id=? AND archived=0',(flashcard_id,workspace_id)).fetchone()
    if not r: raise ValueError('Flashcard non trovata.')
    sched=record_review(workspace_id,r['concept'],score)
    return {'flashcard_id':flashcard_id,'concept':r['concept'],**sched}


def archive_flashcard(workspace_id:int, flashcard_id:int):
    _ensure()
    with connect() as con:
        con.execute('UPDATE flashcards SET archived=1 WHERE id=? AND workspace_id=?',(flashcard_id,workspace_id))
