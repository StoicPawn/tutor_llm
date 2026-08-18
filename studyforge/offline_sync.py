from __future__ import annotations
import json, uuid
from datetime import datetime, timezone
from .db import connect

SCHEMA='''
CREATE TABLE IF NOT EXISTS sync_objects (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 workspace_id INTEGER NOT NULL,
 entity_type TEXT NOT NULL,
 client_uuid TEXT NOT NULL,
 server_id INTEGER,
 revision INTEGER NOT NULL DEFAULT 1,
 deleted INTEGER NOT NULL DEFAULT 0,
 payload_json TEXT NOT NULL DEFAULT '{}',
 updated_at TEXT NOT NULL,
 UNIQUE(workspace_id,entity_type,client_uuid)
);
CREATE TABLE IF NOT EXISTS sync_changes (
 seq INTEGER PRIMARY KEY AUTOINCREMENT,
 workspace_id INTEGER NOT NULL,
 entity_type TEXT NOT NULL,
 client_uuid TEXT NOT NULL,
 revision INTEGER NOT NULL,
 operation TEXT NOT NULL,
 changed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sync_changes_ws_seq ON sync_changes(workspace_id,seq);
CREATE INDEX IF NOT EXISTS idx_sync_objects_server ON sync_objects(workspace_id,entity_type,server_id);
'''
SUPPORTED={'note','annotation','notebook_page'}

def _now(): return datetime.now(timezone.utc).isoformat()
def _ensure():
    with connect() as con: con.executescript(SCHEMA)

def _emit(con,workspace_id,entity_type,client_uuid,revision,operation):
    con.execute('INSERT INTO sync_changes(workspace_id,entity_type,client_uuid,revision,operation,changed_at) VALUES(?,?,?,?,?,?)',
                (workspace_id,entity_type,client_uuid,revision,operation,_now()))

def _decode(row):
    d=dict(row); d['payload']=json.loads(d.pop('payload_json') or '{}'); d['deleted']=bool(d['deleted']); return d

def register_server_object(workspace_id:int,entity_type:str,server_id:int,payload:dict,client_uuid:str|None=None)->dict:
    _ensure(); entity_type=entity_type.strip().lower()
    if entity_type not in SUPPORTED: raise ValueError('Entità sync non supportata.')
    client_uuid=client_uuid or str(uuid.uuid4()); now=_now()
    with connect() as con:
        row=con.execute('SELECT * FROM sync_objects WHERE workspace_id=? AND entity_type=? AND server_id=?',(workspace_id,entity_type,server_id)).fetchone()
        if row: return _decode(row)
        con.execute('INSERT INTO sync_objects(workspace_id,entity_type,client_uuid,server_id,revision,deleted,payload_json,updated_at) VALUES(?,?,?,?,1,0,?,?)',
                    (workspace_id,entity_type,client_uuid,server_id,json.dumps(payload,ensure_ascii=False),now))
        _emit(con,workspace_id,entity_type,client_uuid,1,'upsert')
        row=con.execute('SELECT * FROM sync_objects WHERE workspace_id=? AND entity_type=? AND client_uuid=?',(workspace_id,entity_type,client_uuid)).fetchone()
    return _decode(row)

def sync_server_upsert(workspace_id:int,entity_type:str,server_id:int,payload:dict)->dict:
    _ensure(); entity_type=entity_type.strip().lower()
    if entity_type not in SUPPORTED: raise ValueError('Entità sync non supportata.')
    with connect() as con:
        row=con.execute('SELECT * FROM sync_objects WHERE workspace_id=? AND entity_type=? AND server_id=?',(workspace_id,entity_type,server_id)).fetchone(); now=_now()
        if not row:
            client_uuid=str(uuid.uuid4()); revision=1
            con.execute('INSERT INTO sync_objects(workspace_id,entity_type,client_uuid,server_id,revision,deleted,payload_json,updated_at) VALUES(?,?,?,?,1,0,?,?)',
                        (workspace_id,entity_type,client_uuid,server_id,json.dumps(payload,ensure_ascii=False),now))
        else:
            client_uuid=row['client_uuid']; revision=int(row['revision'])+1
            con.execute('UPDATE sync_objects SET revision=?,deleted=0,payload_json=?,updated_at=? WHERE id=?',
                        (revision,json.dumps(payload,ensure_ascii=False),now,row['id']))
        _emit(con,workspace_id,entity_type,client_uuid,revision,'upsert')
        new=con.execute('SELECT * FROM sync_objects WHERE workspace_id=? AND entity_type=? AND client_uuid=?',(workspace_id,entity_type,client_uuid)).fetchone()
    return _decode(new)

def sync_server_delete(workspace_id:int,entity_type:str,server_id:int,payload:dict|None=None)->dict|None:
    _ensure(); entity_type=entity_type.strip().lower()
    if entity_type not in SUPPORTED: raise ValueError('Entità sync non supportata.')
    with connect() as con:
        row=con.execute('SELECT * FROM sync_objects WHERE workspace_id=? AND entity_type=? AND server_id=?',(workspace_id,entity_type,server_id)).fetchone()
        if not row: return None
        revision=int(row['revision'])+1; now=_now(); client_uuid=row['client_uuid']
        con.execute('UPDATE sync_objects SET revision=?,deleted=1,payload_json=?,updated_at=? WHERE id=?',
                    (revision,json.dumps(payload or {},ensure_ascii=False),now,row['id']))
        _emit(con,workspace_id,entity_type,client_uuid,revision,'delete')
        new=con.execute('SELECT * FROM sync_objects WHERE id=?',(row['id'],)).fetchone()
    return _decode(new)

def _materialize(workspace_id:int,entity_type:str,server_id:int|None,payload:dict,deleted:bool)->int|None:
    """Apply a sync change to canonical application tables without calling public CRUD hooks."""
    now=_now()
    if entity_type=='note':
        if deleted:
            if server_id is not None:
                with connect() as con: con.execute('DELETE FROM notes WHERE id=? AND workspace_id=?',(server_id,workspace_id))
            return server_id
        with connect() as con:
            if server_id is not None and con.execute('SELECT 1 FROM notes WHERE id=? AND workspace_id=?',(server_id,workspace_id)).fetchone():
                con.execute('UPDATE notes SET title=?,content=?,kind=?,document_id=?,page=?,updated_at=? WHERE id=? AND workspace_id=?',
                            ((payload.get('title') or 'Nota senza titolo')[:240],payload.get('content',''),(payload.get('kind') or 'text')[:40],payload.get('document_id'),payload.get('page'),now,server_id,workspace_id))
                return server_id
            cur=con.execute('INSERT INTO notes(workspace_id,title,content,kind,document_id,page,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',
                            (workspace_id,(payload.get('title') or 'Nota senza titolo')[:240],payload.get('content',''),(payload.get('kind') or 'text')[:40],payload.get('document_id'),payload.get('page'),payload.get('created_at') or now,now))
            return int(cur.lastrowid)
    if entity_type=='annotation':
        from .annotations import _ensure as ensure_annotations
        ensure_annotations()
        if deleted:
            if server_id is not None:
                with connect() as con: con.execute('DELETE FROM document_annotations WHERE id=? AND workspace_id=?',(server_id,workspace_id))
            return server_id
        document_id=payload.get('document_id')
        if document_id is None: raise ValueError('document_id obbligatorio per annotation sync.')
        bbox=payload.get('bbox'); bbox_json=json.dumps(bbox) if bbox is not None else None
        payload_json=json.dumps(payload.get('payload') or {},ensure_ascii=False)
        with connect() as con:
            if server_id is not None and con.execute('SELECT 1 FROM document_annotations WHERE id=? AND workspace_id=?',(server_id,workspace_id)).fetchone():
                con.execute('UPDATE document_annotations SET document_id=?,page=?,kind=?,bbox_json=?,text=?,payload_json=?,updated_at=? WHERE id=? AND workspace_id=?',
                            (document_id,max(1,int(payload.get('page') or 1)),payload.get('kind') or 'comment',bbox_json,payload.get('text','')[:12000],payload_json,now,server_id,workspace_id))
                return server_id
            cur=con.execute('INSERT INTO document_annotations(workspace_id,document_id,page,kind,bbox_json,text,payload_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
                            (workspace_id,document_id,max(1,int(payload.get('page') or 1)),payload.get('kind') or 'comment',bbox_json,payload.get('text','')[:12000],payload_json,payload.get('created_at') or now,now))
            return int(cur.lastrowid)
    if entity_type=='notebook_page':
        from .notebooks import _ensure as ensure_notebooks, _validate_layers
        ensure_notebooks()
        if deleted:
            if server_id is not None:
                with connect() as con:
                    row=con.execute('SELECT p.id FROM notebook_pages p JOIN study_notebooks n ON n.id=p.notebook_id WHERE p.id=? AND n.workspace_id=?',(server_id,workspace_id)).fetchone()
                    if row: con.execute('DELETE FROM notebook_pages WHERE id=?',(server_id,))
            return server_id
        notebook_id=payload.get('notebook_id')
        if notebook_id is None: raise ValueError('notebook_id obbligatorio per notebook_page sync.')
        layers=_validate_layers(payload.get('layers') or [])
        background=(payload.get('background') or 'blank').strip().lower()
        with connect() as con:
            if not con.execute('SELECT 1 FROM study_notebooks WHERE id=? AND workspace_id=?',(notebook_id,workspace_id)).fetchone(): raise ValueError('Quaderno fuori workspace o inesistente.')
            if server_id is not None and con.execute('SELECT 1 FROM notebook_pages WHERE id=? AND notebook_id=?',(server_id,notebook_id)).fetchone():
                con.execute('UPDATE notebook_pages SET position=?,title=?,width=?,height=?,background=?,layers_json=?,updated_at=? WHERE id=?',
                            (int(payload.get('position') or 1),(payload.get('title') or '')[:300],float(payload.get('width') or 1024),float(payload.get('height') or 1365),background,json.dumps(layers,ensure_ascii=False),now,server_id))
                con.execute('UPDATE study_notebooks SET updated_at=? WHERE id=?',(now,notebook_id)); return server_id
            position=int(payload.get('position') or con.execute('SELECT COALESCE(MAX(position),0)+1 n FROM notebook_pages WHERE notebook_id=?',(notebook_id,)).fetchone()['n'])
            cur=con.execute('INSERT INTO notebook_pages(notebook_id,position,title,width,height,background,layers_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',
                            (notebook_id,position,(payload.get('title') or f'Pagina {position}')[:300],float(payload.get('width') or 1024),float(payload.get('height') or 1365),background,json.dumps(layers,ensure_ascii=False),payload.get('created_at') or now,now))
            con.execute('UPDATE study_notebooks SET updated_at=? WHERE id=?',(now,notebook_id)); return int(cur.lastrowid)
    raise ValueError('Entità sync non supportata.')

def pull_changes(workspace_id:int,since_seq:int=0,limit:int=500)->dict:
    _ensure(); limit=max(1,min(int(limit),2000))
    with connect() as con:
        rows=con.execute('SELECT * FROM sync_changes WHERE workspace_id=? AND seq>? ORDER BY seq LIMIT ?',(workspace_id,max(0,int(since_seq)),limit)).fetchall(); changes=[]
        for r in rows:
            obj=con.execute('SELECT * FROM sync_objects WHERE workspace_id=? AND entity_type=? AND client_uuid=?',(workspace_id,r['entity_type'],r['client_uuid'])).fetchone()
            changes.append({'seq':r['seq'],'operation':r['operation'],'object':_decode(obj) if obj else None})
        cursor=changes[-1]['seq'] if changes else max(0,int(since_seq))
    return {'workspace_id':workspace_id,'since':since_seq,'cursor':cursor,'changes':changes}

def push_change(workspace_id:int,entity_type:str,client_uuid:str,base_revision:int,payload:dict|None,deleted:bool=False,server_id:int|None=None)->dict:
    _ensure(); entity_type=entity_type.strip().lower(); payload=payload or {}
    if entity_type not in SUPPORTED: raise ValueError('Entità sync non supportata.')
    try: uuid.UUID(client_uuid)
    except Exception as exc: raise ValueError('client_uuid non valido.') from exc
    with connect() as con:
        row=con.execute('SELECT * FROM sync_objects WHERE workspace_id=? AND entity_type=? AND client_uuid=?',(workspace_id,entity_type,client_uuid)).fetchone()
        if row:
            current=int(row['revision'])
            if int(base_revision)!=current: return {'status':'conflict','server':_decode(row),'expected_revision':current}
            current_server_id=row['server_id']; revision=current+1
        else:
            if int(base_revision) not in (0,-1): return {'status':'conflict','server':None,'expected_revision':0}
            current_server_id=server_id; revision=1
    materialized_id=_materialize(workspace_id,entity_type,current_server_id or server_id,payload,deleted)
    with connect() as con:
        row=con.execute('SELECT * FROM sync_objects WHERE workspace_id=? AND entity_type=? AND client_uuid=?',(workspace_id,entity_type,client_uuid)).fetchone()
        if row:
            con.execute('UPDATE sync_objects SET server_id=?,revision=?,deleted=?,payload_json=?,updated_at=? WHERE id=?',
                        (materialized_id,revision,1 if deleted else 0,json.dumps(payload,ensure_ascii=False),_now(),row['id']))
        else:
            con.execute('INSERT INTO sync_objects(workspace_id,entity_type,client_uuid,server_id,revision,deleted,payload_json,updated_at) VALUES(?,?,?,?,?,?,?,?)',
                        (workspace_id,entity_type,client_uuid,materialized_id,revision,1 if deleted else 0,json.dumps(payload,ensure_ascii=False),_now()))
        _emit(con,workspace_id,entity_type,client_uuid,revision,'delete' if deleted else 'upsert')
        new=con.execute('SELECT * FROM sync_objects WHERE workspace_id=? AND entity_type=? AND client_uuid=?',(workspace_id,entity_type,client_uuid)).fetchone()
    return {'status':'applied','object':_decode(new)}

def resolve_conflict(workspace_id:int,entity_type:str,client_uuid:str,server_revision:int,payload:dict,deleted:bool=False)->dict:
    return push_change(workspace_id,entity_type,client_uuid,server_revision,payload,deleted)
