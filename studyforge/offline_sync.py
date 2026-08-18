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
    """Register an existing application object in sync without changing its application data."""
    _ensure(); entity_type=entity_type.strip().lower()
    if entity_type not in SUPPORTED: raise ValueError('Entità sync non supportata.')
    client_uuid=client_uuid or str(uuid.uuid4()); now=_now()
    with connect() as con:
        row=con.execute('SELECT * FROM sync_objects WHERE workspace_id=? AND entity_type=? AND server_id=?',
                        (workspace_id,entity_type,server_id)).fetchone()
        if row: return _decode(row)
        con.execute('INSERT INTO sync_objects(workspace_id,entity_type,client_uuid,server_id,revision,deleted,payload_json,updated_at) VALUES(?,?,?,?,1,0,?,?)',
                    (workspace_id,entity_type,client_uuid,server_id,json.dumps(payload,ensure_ascii=False),now))
        _emit(con,workspace_id,entity_type,client_uuid,1,'upsert')
        row=con.execute('SELECT * FROM sync_objects WHERE workspace_id=? AND entity_type=? AND client_uuid=?',(workspace_id,entity_type,client_uuid)).fetchone()
    return _decode(row)

def sync_server_upsert(workspace_id:int,entity_type:str,server_id:int,payload:dict)->dict:
    """Mirror a normal application create/update into the sync envelope and change feed."""
    _ensure(); entity_type=entity_type.strip().lower()
    if entity_type not in SUPPORTED: raise ValueError('Entità sync non supportata.')
    with connect() as con:
        row=con.execute('SELECT * FROM sync_objects WHERE workspace_id=? AND entity_type=? AND server_id=?',
                        (workspace_id,entity_type,server_id)).fetchone()
        now=_now()
        if not row:
            client_uuid=str(uuid.uuid4()); revision=1
            con.execute('INSERT INTO sync_objects(workspace_id,entity_type,client_uuid,server_id,revision,deleted,payload_json,updated_at) VALUES(?,?,?,?,1,0,?,?)',
                        (workspace_id,entity_type,client_uuid,server_id,json.dumps(payload,ensure_ascii=False),now))
        else:
            client_uuid=row['client_uuid']; revision=int(row['revision'])+1
            con.execute('UPDATE sync_objects SET revision=?,deleted=0,payload_json=?,updated_at=? WHERE id=?',
                        (revision,json.dumps(payload,ensure_ascii=False),now,row['id']))
        _emit(con,workspace_id,entity_type,client_uuid,revision,'upsert')
        new=con.execute('SELECT * FROM sync_objects WHERE workspace_id=? AND entity_type=? AND client_uuid=?',
                        (workspace_id,entity_type,client_uuid)).fetchone()
    return _decode(new)

def sync_server_delete(workspace_id:int,entity_type:str,server_id:int,payload:dict|None=None)->dict|None:
    """Emit a tombstone when an application object is deleted through the normal API."""
    _ensure(); entity_type=entity_type.strip().lower()
    if entity_type not in SUPPORTED: raise ValueError('Entità sync non supportata.')
    with connect() as con:
        row=con.execute('SELECT * FROM sync_objects WHERE workspace_id=? AND entity_type=? AND server_id=?',
                        (workspace_id,entity_type,server_id)).fetchone()
        if not row:
            return None
        revision=int(row['revision'])+1; now=_now(); client_uuid=row['client_uuid']
        con.execute('UPDATE sync_objects SET revision=?,deleted=1,payload_json=?,updated_at=? WHERE id=?',
                    (revision,json.dumps(payload or {},ensure_ascii=False),now,row['id']))
        _emit(con,workspace_id,entity_type,client_uuid,revision,'delete')
        new=con.execute('SELECT * FROM sync_objects WHERE id=?',(row['id'],)).fetchone()
    return _decode(new)

def pull_changes(workspace_id:int,since_seq:int=0,limit:int=500)->dict:
    _ensure(); limit=max(1,min(int(limit),2000))
    with connect() as con:
        rows=con.execute('SELECT * FROM sync_changes WHERE workspace_id=? AND seq>? ORDER BY seq LIMIT ?',
                         (workspace_id,max(0,int(since_seq)),limit)).fetchall()
        changes=[]
        for r in rows:
            obj=con.execute('SELECT * FROM sync_objects WHERE workspace_id=? AND entity_type=? AND client_uuid=?',
                            (workspace_id,r['entity_type'],r['client_uuid'])).fetchone()
            changes.append({'seq':r['seq'],'operation':r['operation'],'object':_decode(obj) if obj else None})
        cursor=changes[-1]['seq'] if changes else max(0,int(since_seq))
    return {'workspace_id':workspace_id,'since':since_seq,'cursor':cursor,'changes':changes}

def push_change(workspace_id:int,entity_type:str,client_uuid:str,base_revision:int,payload:dict|None,deleted:bool=False,server_id:int|None=None)->dict:
    _ensure(); entity_type=entity_type.strip().lower()
    if entity_type not in SUPPORTED: raise ValueError('Entità sync non supportata.')
    try: uuid.UUID(client_uuid)
    except Exception as exc: raise ValueError('client_uuid non valido.') from exc
    with connect() as con:
        row=con.execute('SELECT * FROM sync_objects WHERE workspace_id=? AND entity_type=? AND client_uuid=?',
                        (workspace_id,entity_type,client_uuid)).fetchone()
        if row:
            current=int(row['revision'])
            if int(base_revision)!=current:
                return {'status':'conflict','server':_decode(row),'expected_revision':current}
            revision=current+1
            con.execute('UPDATE sync_objects SET server_id=COALESCE(?,server_id),revision=?,deleted=?,payload_json=?,updated_at=? WHERE id=?',
                        (server_id,revision,1 if deleted else 0,json.dumps(payload or {},ensure_ascii=False),_now(),row['id']))
        else:
            if int(base_revision) not in (0,-1):
                return {'status':'conflict','server':None,'expected_revision':0}
            revision=1
            con.execute('INSERT INTO sync_objects(workspace_id,entity_type,client_uuid,server_id,revision,deleted,payload_json,updated_at) VALUES(?,?,?,?,?,?,?,?)',
                        (workspace_id,entity_type,client_uuid,server_id,revision,1 if deleted else 0,json.dumps(payload or {},ensure_ascii=False),_now()))
        _emit(con,workspace_id,entity_type,client_uuid,revision,'delete' if deleted else 'upsert')
        new=con.execute('SELECT * FROM sync_objects WHERE workspace_id=? AND entity_type=? AND client_uuid=?',
                        (workspace_id,entity_type,client_uuid)).fetchone()
    return {'status':'applied','object':_decode(new)}

def resolve_conflict(workspace_id:int,entity_type:str,client_uuid:str,server_revision:int,payload:dict,deleted:bool=False)->dict:
    return push_change(workspace_id,entity_type,client_uuid,server_revision,payload,deleted)
