from __future__ import annotations
import json
from datetime import datetime, timezone
from .db import connect, document_belongs_to_workspace

SCHEMA='''
CREATE TABLE IF NOT EXISTS study_notebooks (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 workspace_id INTEGER NOT NULL,
 title TEXT NOT NULL,
 description TEXT NOT NULL DEFAULT '',
 linked_document_id INTEGER,
 linked_page INTEGER,
 linked_concept TEXT,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
 FOREIGN KEY(linked_document_id) REFERENCES documents(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS notebook_pages (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 notebook_id INTEGER NOT NULL,
 position INTEGER NOT NULL,
 title TEXT NOT NULL DEFAULT '',
 width REAL NOT NULL DEFAULT 1024,
 height REAL NOT NULL DEFAULT 1365,
 background TEXT NOT NULL DEFAULT 'blank',
 layers_json TEXT NOT NULL DEFAULT '[]',
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 FOREIGN KEY(notebook_id) REFERENCES study_notebooks(id) ON DELETE CASCADE,
 UNIQUE(notebook_id,position)
);
CREATE INDEX IF NOT EXISTS idx_notebooks_workspace ON study_notebooks(workspace_id,id);
CREATE INDEX IF NOT EXISTS idx_notebook_pages ON notebook_pages(notebook_id,position);
'''

ALLOWED_BACKGROUNDS={'blank','ruled','grid','dot'}
ALLOWED_LAYER_KINDS={'ink','text','shape','image_ref','source_ref'}


def _now()->str:
    return datetime.now(timezone.utc).isoformat()


def _ensure():
    with connect() as con: con.executescript(SCHEMA)


def _validate_layers(layers:list[dict])->list[dict]:
    if not isinstance(layers,list): raise ValueError('layers deve essere una lista.')
    if len(layers)>2000: raise ValueError('Troppi layer nella pagina.')
    out=[]
    for layer in layers:
        if not isinstance(layer,dict): raise ValueError('Layer non valido.')
        kind=str(layer.get('kind','')).strip().lower()
        if kind not in ALLOWED_LAYER_KINDS: raise ValueError(f'Layer non supportato: {kind}')
        item=dict(layer); item['kind']=kind
        if kind=='ink':
            strokes=item.get('strokes',[])
            if not isinstance(strokes,list): raise ValueError('Stroke non validi.')
            total_points=0
            for stroke in strokes:
                if not isinstance(stroke,dict): raise ValueError('Stroke non valido.')
                points=stroke.get('points',[])
                if not isinstance(points,list): raise ValueError('Punti stroke non validi.')
                total_points += len(points)
            if total_points>100000: raise ValueError('Pagina ink troppo grande.')
        out.append(item)
    return out


def create_notebook(workspace_id:int,title:str,description:str='',*,document_id:int|None=None,page:int|None=None,concept:str|None=None)->int:
    _ensure(); title=title.strip()
    if not title: raise ValueError('Titolo quaderno obbligatorio.')
    if document_id is not None and not document_belongs_to_workspace(document_id,workspace_id): raise ValueError('Documento fuori workspace.')
    now=_now()
    with connect() as con:
        cur=con.execute('''INSERT INTO study_notebooks(workspace_id,title,description,linked_document_id,linked_page,linked_concept,created_at,updated_at)
                           VALUES(?,?,?,?,?,?,?,?)''',
                        (workspace_id,title[:300],description[:4000],document_id,max(1,int(page)) if page else None,(concept or '').strip()[:500] or None,now,now))
        notebook_id=int(cur.lastrowid)
        con.execute('''INSERT INTO notebook_pages(notebook_id,position,title,width,height,background,layers_json,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?)''',(notebook_id,1,'Pagina 1',1024.0,1365.0,'blank','[]',now,now))
    return notebook_id


def list_notebooks(workspace_id:int)->list[dict]:
    _ensure()
    with connect() as con:
        rows=con.execute('''SELECT n.*, d.name linked_document_name,
            (SELECT COUNT(*) FROM notebook_pages p WHERE p.notebook_id=n.id) page_count
            FROM study_notebooks n LEFT JOIN documents d ON d.id=n.linked_document_id
            WHERE n.workspace_id=? ORDER BY n.updated_at DESC,n.id DESC''',(workspace_id,)).fetchall()
    return [dict(r) for r in rows]


def get_notebook(workspace_id:int,notebook_id:int)->dict|None:
    _ensure()
    with connect() as con:
        n=con.execute('SELECT * FROM study_notebooks WHERE id=? AND workspace_id=?',(notebook_id,workspace_id)).fetchone()
        if not n: return None
        pages=con.execute('SELECT * FROM notebook_pages WHERE notebook_id=? ORDER BY position',(notebook_id,)).fetchall()
    out=dict(n); out['pages']=[]
    for p in pages:
        d=dict(p); d['layers']=json.loads(d.pop('layers_json') or '[]'); out['pages'].append(d)
    return out


def add_page(workspace_id:int,notebook_id:int,*,title:str='',background:str='blank',width:float=1024,height:float=1365)->dict:
    _ensure(); background=background.strip().lower()
    if background not in ALLOWED_BACKGROUNDS: raise ValueError('Sfondo non supportato.')
    now=_now()
    with connect() as con:
        n=con.execute('SELECT 1 FROM study_notebooks WHERE id=? AND workspace_id=?',(notebook_id,workspace_id)).fetchone()
        if not n: raise ValueError('Quaderno non trovato.')
        pos=int(con.execute('SELECT COALESCE(MAX(position),0)+1 n FROM notebook_pages WHERE notebook_id=?',(notebook_id,)).fetchone()['n'])
        cur=con.execute('''INSERT INTO notebook_pages(notebook_id,position,title,width,height,background,layers_json,created_at,updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?)''',(notebook_id,pos,(title or f'Pagina {pos}')[:300],float(width),float(height),background,'[]',now,now))
        con.execute('UPDATE study_notebooks SET updated_at=? WHERE id=?',(now,notebook_id))
        row=con.execute('SELECT * FROM notebook_pages WHERE id=?',(cur.lastrowid,)).fetchone()
    d=dict(row); d['layers']=json.loads(d.pop('layers_json')); return d


def save_page(workspace_id:int,notebook_id:int,page_id:int,*,layers:list[dict],title:str|None=None,background:str|None=None)->dict:
    _ensure(); layers=_validate_layers(layers); fields=['layers_json=?','updated_at=?']; values=[json.dumps(layers,ensure_ascii=False),_now()]
    if title is not None: fields.append('title=?'); values.append(title[:300])
    if background is not None:
        background=background.strip().lower()
        if background not in ALLOWED_BACKGROUNDS: raise ValueError('Sfondo non supportato.')
        fields.append('background=?'); values.append(background)
    values.extend([page_id,notebook_id,workspace_id])
    with connect() as con:
        cur=con.execute('''UPDATE notebook_pages SET '''+','.join(fields)+''' WHERE id=? AND notebook_id=?
                           AND EXISTS(SELECT 1 FROM study_notebooks n WHERE n.id=notebook_pages.notebook_id AND n.workspace_id=?)''',values)
        if cur.rowcount!=1: raise ValueError('Pagina quaderno non trovata.')
        con.execute('UPDATE study_notebooks SET updated_at=? WHERE id=?',(_now(),notebook_id))
        row=con.execute('SELECT * FROM notebook_pages WHERE id=?',(page_id,)).fetchone()
    d=dict(row); d['layers']=json.loads(d.pop('layers_json')); return d


def delete_notebook(workspace_id:int,notebook_id:int):
    _ensure()
    with connect() as con: con.execute('DELETE FROM study_notebooks WHERE id=? AND workspace_id=?',(notebook_id,workspace_id))
