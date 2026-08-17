from __future__ import annotations
import json, re
from datetime import datetime, timezone
from .db import connect, iter_chunks
from .ollama_client import chat
from .student import mastery_for

SCHEMA='''
CREATE TABLE IF NOT EXISTS curricula (
 id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, goal TEXT NOT NULL,
 document_ids_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS curriculum_nodes (
 id INTEGER PRIMARY KEY AUTOINCREMENT, curriculum_id INTEGER NOT NULL,
 position INTEGER NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL,
 prerequisites_json TEXT NOT NULL, importance REAL NOT NULL DEFAULT .5,
 status TEXT NOT NULL DEFAULT 'todo', FOREIGN KEY(curriculum_id) REFERENCES curricula(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_curriculum_nodes ON curriculum_nodes(curriculum_id,position);
'''

def _ensure():
    with connect() as con: con.executescript(SCHEMA)

def _json_object(text:str)->dict:
    text=re.sub(r'^```(?:json)?\s*|\s*```$','',text.strip(),flags=re.I|re.S)
    try: return json.loads(text)
    except json.JSONDecodeError:
        m=re.search(r'\{.*\}',text,re.S)
        if not m: raise ValueError('Il modello non ha restituito un syllabus JSON valido.')
        return json.loads(m.group(0))

def _sample_material(document_ids:list[int], max_chars:int=42000)->str:
    rows=list(iter_chunks(document_ids));
    if not rows: raise ValueError('Nessun contenuto disponibile.')
    step=max(1,len(rows)//24); chosen=rows[::step][:28]
    parts=[]; used=0
    for r in chosen:
        loc=f"p.{r['page']}" if r['page'] else f"sez.{r['chunk_index']}"
        block=f"[{r['document_name']} {loc}]\n{r['text']}\n"
        if used+len(block)>max_chars: break
        parts.append(block); used+=len(block)
    return '\n'.join(parts)

def create_curriculum(title:str, goal:str, document_ids:list[int], max_nodes:int=18)->int:
    _ensure(); material=_sample_material(document_ids)
    prompt=f'''Analizza il materiale e costruisci un percorso didattico coerente per l'obiettivo: {goal}.
Restituisci SOLO JSON valido: {{"nodes":[{{"title":"...","description":"...","prerequisites":["titolo esatto di un nodo precedente"],"importance":0.0}}]}}.
Regole: 6-{max_nodes} nodi; dal fondamentale all'avanzato; niente argomenti non sostenuti dal materiale; prerequisiti solo tra nodi precedenti; titoli distintivi e brevi; importance tra 0 e 1.
MATERIALE:\n{material}'''
    data=_json_object(chat([{'role':'system','content':'Sei un instructional designer rigoroso. Produci solo JSON.'},{'role':'user','content':prompt}],temperature=.05))
    nodes=data.get('nodes',[])[:max_nodes]
    if not nodes: raise ValueError('Syllabus vuoto.')
    now=datetime.now(timezone.utc).isoformat()
    with connect() as con:
        cur=con.execute('INSERT INTO curricula(title,goal,document_ids_json,created_at) VALUES(?,?,?,?)',(title,goal,json.dumps(document_ids),now)); cid=int(cur.lastrowid)
        known=[]
        for i,n in enumerate(nodes,1):
            name=str(n.get('title','')).strip()[:180]
            if not name: continue
            prereq=[p for p in n.get('prerequisites',[]) if p in known]
            imp=max(0.,min(1.,float(n.get('importance',.5))))
            con.execute('INSERT INTO curriculum_nodes(curriculum_id,position,title,description,prerequisites_json,importance) VALUES(?,?,?,?,?,?)',(cid,i,name,str(n.get('description',''))[:1200],json.dumps(prereq,ensure_ascii=False),imp)); known.append(name)
    return cid

def list_curricula():
    _ensure()
    with connect() as con: return con.execute('SELECT * FROM curricula ORDER BY id DESC').fetchall()

def curriculum_nodes(curriculum_id:int):
    _ensure()
    with connect() as con: return con.execute('SELECT * FROM curriculum_nodes WHERE curriculum_id=? ORDER BY position',(curriculum_id,)).fetchall()

def curriculum_document_ids(curriculum_id:int)->list[int]:
    _ensure()
    with connect() as con:
        r=con.execute('SELECT document_ids_json FROM curricula WHERE id=?',(curriculum_id,)).fetchone()
    return json.loads(r['document_ids_json']) if r else []

def next_node(curriculum_id:int):
    nodes=curriculum_nodes(curriculum_id); by_title={r['title']:r for r in nodes}
    candidates=[]
    for r in nodes:
        if r['status']=='done': continue
        prereq=json.loads(r['prerequisites_json'])
        ready=all((p in by_title and (by_title[p]['status']=='done' or mastery_for(p)>=.68)) for p in prereq)
        if ready:
            mastery=mastery_for(r['title']); priority=(1-mastery)*.7+float(r['importance'])*.3
            candidates.append((priority,-int(r['position']),r))
    return max(candidates,key=lambda x:(x[0],x[1]))[2] if candidates else None

def set_node_status(node_id:int,status:str):
    if status not in {'todo','learning','done'}: raise ValueError('Stato non valido')
    _ensure()
    with connect() as con: con.execute('UPDATE curriculum_nodes SET status=? WHERE id=?',(status,node_id))

def delete_curriculum(curriculum_id:int):
    _ensure()
    with connect() as con:
        con.execute('DELETE FROM curriculum_nodes WHERE curriculum_id=?',(curriculum_id,)); con.execute('DELETE FROM curricula WHERE id=?',(curriculum_id,))
