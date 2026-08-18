from __future__ import annotations
import json
from datetime import datetime, timezone
from .db import connect, document_belongs_to_workspace

SCHEMA='''
CREATE TABLE IF NOT EXISTS document_annotations (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 workspace_id INTEGER NOT NULL,
 document_id INTEGER NOT NULL,
 page INTEGER NOT NULL,
 kind TEXT NOT NULL,
 bbox_json TEXT,
 text TEXT NOT NULL DEFAULT '',
 payload_json TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
 FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_annotations_page ON document_annotations(workspace_id,document_id,page,id);
'''

ALLOWED_KINDS={'highlight','bookmark','comment','ink'}


def _now()->str:
    return datetime.now(timezone.utc).isoformat()


def _ensure():
    with connect() as con: con.executescript(SCHEMA)


def _decode(row)->dict:
    d=dict(row); d['bbox']=json.loads(d.pop('bbox_json')) if d.get('bbox_json') else None; d['payload']=json.loads(d.pop('payload_json') or '{}'); return d


def _sync_payload(data:dict)->dict:
    return {
        'document_id':data.get('document_id'),
        'page':data.get('page'),
        'kind':data.get('kind'),
        'bbox':data.get('bbox'),
        'text':data.get('text',''),
        'payload':data.get('payload') or {},
        'created_at':data.get('created_at'),
        'updated_at':data.get('updated_at'),
    }


def create_annotation(workspace_id:int,document_id:int,page:int,kind:str,*,bbox:list[float]|None=None,text:str='',payload:dict|None=None)->int:
    _ensure()
    kind=kind.strip().lower()
    if kind not in ALLOWED_KINDS: raise ValueError('Tipo annotazione non supportato.')
    if not document_belongs_to_workspace(document_id,workspace_id): raise ValueError('Documento fuori workspace.')
    page=max(1,int(page)); now=_now()
    if bbox is not None:
        if len(bbox)!=4: raise ValueError('bbox deve contenere quattro coordinate.')
        bbox=[float(x) for x in bbox]
    payload=payload or {}
    if kind=='ink':
        strokes=payload.get('strokes',[])
        if not isinstance(strokes,list): raise ValueError('Ink strokes non validi.')
        for stroke in strokes:
            pts=stroke.get('points',[]) if isinstance(stroke,dict) else []
            if len(pts)>20000: raise ValueError('Stroke troppo grande.')
    with connect() as con:
        cur=con.execute('''INSERT INTO document_annotations(workspace_id,document_id,page,kind,bbox_json,text,payload_json,created_at,updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?)''',
                        (workspace_id,document_id,page,kind,json.dumps(bbox) if bbox is not None else None,text[:12000],json.dumps(payload,ensure_ascii=False),now,now))
        annotation_id=int(cur.lastrowid)
        row=con.execute('SELECT * FROM document_annotations WHERE id=? AND workspace_id=?',(annotation_id,workspace_id)).fetchone()
    data=_decode(row)
    from .offline_sync import sync_server_upsert
    sync_server_upsert(workspace_id,'annotation',annotation_id,_sync_payload(data))
    return annotation_id


def list_annotations(workspace_id:int,document_id:int|None=None,page:int|None=None,limit:int=500)->list[dict]:
    _ensure(); where=['workspace_id=?']; params:list[object]=[workspace_id]
    if document_id is not None: where.append('document_id=?'); params.append(int(document_id))
    if page is not None: where.append('page=?'); params.append(int(page))
    params.append(max(1,min(int(limit),2000)))
    with connect() as con:
        rows=con.execute('SELECT * FROM document_annotations WHERE '+' AND '.join(where)+' ORDER BY page,id LIMIT ?',params).fetchall()
    return [_decode(r) for r in rows]


def update_annotation(workspace_id:int,annotation_id:int,*,text:str|None=None,bbox:list[float]|None=None,payload:dict|None=None)->dict:
    _ensure(); fields=[]; values=[]
    if text is not None: fields.append('text=?'); values.append(text[:12000])
    if bbox is not None:
        if len(bbox)!=4: raise ValueError('bbox deve contenere quattro coordinate.')
        fields.append('bbox_json=?'); values.append(json.dumps([float(x) for x in bbox]))
    if payload is not None: fields.append('payload_json=?'); values.append(json.dumps(payload,ensure_ascii=False))
    fields.append('updated_at=?'); values.append(_now()); values.extend([annotation_id,workspace_id])
    with connect() as con:
        cur=con.execute('UPDATE document_annotations SET '+','.join(fields)+' WHERE id=? AND workspace_id=?',values)
        if cur.rowcount!=1: raise ValueError('Annotazione non trovata.')
        row=con.execute('SELECT * FROM document_annotations WHERE id=? AND workspace_id=?',(annotation_id,workspace_id)).fetchone()
    data=_decode(row)
    from .offline_sync import sync_server_upsert
    sync_server_upsert(workspace_id,'annotation',annotation_id,_sync_payload(data))
    return data


def delete_annotation(workspace_id:int,annotation_id:int):
    _ensure()
    with connect() as con:
        row=con.execute('SELECT * FROM document_annotations WHERE id=? AND workspace_id=?',(annotation_id,workspace_id)).fetchone()
        if not row: return False
        data=_decode(row)
        con.execute('DELETE FROM document_annotations WHERE id=? AND workspace_id=?',(annotation_id,workspace_id))
    from .offline_sync import sync_server_delete
    sync_server_delete(workspace_id,'annotation',annotation_id,_sync_payload(data))
    return True
