from __future__ import annotations
import json, sqlite3, uuid
from pathlib import Path
from datetime import datetime, timezone

SCHEMA='''
CREATE TABLE IF NOT EXISTS cache_state(workspace_id INTEGER PRIMARY KEY,cursor INTEGER NOT NULL DEFAULT 0,manifest_revision TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cache_objects(workspace_id INTEGER NOT NULL,entity_type TEXT NOT NULL,client_uuid TEXT NOT NULL,server_id INTEGER,revision INTEGER NOT NULL DEFAULT 0,deleted INTEGER NOT NULL DEFAULT 0,payload_json TEXT NOT NULL DEFAULT '{}',dirty INTEGER NOT NULL DEFAULT 0,conflict_json TEXT,updated_at TEXT NOT NULL,PRIMARY KEY(workspace_id,entity_type,client_uuid));
CREATE TABLE IF NOT EXISTS cached_documents(workspace_id INTEGER NOT NULL,document_id INTEGER NOT NULL,name TEXT NOT NULL DEFAULT '',local_path TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'missing',downloaded_at TEXT,PRIMARY KEY(workspace_id,document_id));
'''

def _now(): return datetime.now(timezone.utc).isoformat()

class ClientCacheStore:
    def __init__(self,path:str|Path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self._ensure()
    def _con(self):
        con=sqlite3.connect(self.path); con.row_factory=sqlite3.Row; return con
    def _ensure(self):
        with self._con() as con: con.executescript(SCHEMA)
    def state(self,workspace_id:int)->dict:
        with self._con() as con: row=con.execute('SELECT * FROM cache_state WHERE workspace_id=?',(workspace_id,)).fetchone()
        return dict(row) if row else {'workspace_id':workspace_id,'cursor':0,'manifest_revision':'','updated_at':''}
    def set_state(self,workspace_id:int,*,cursor:int|None=None,manifest_revision:str|None=None):
        old=self.state(workspace_id); cursor=old['cursor'] if cursor is None else int(cursor); manifest_revision=old['manifest_revision'] if manifest_revision is None else str(manifest_revision)
        with self._con() as con: con.execute('INSERT INTO cache_state(workspace_id,cursor,manifest_revision,updated_at) VALUES(?,?,?,?) ON CONFLICT(workspace_id) DO UPDATE SET cursor=excluded.cursor,manifest_revision=excluded.manifest_revision,updated_at=excluded.updated_at',(workspace_id,cursor,manifest_revision,_now()))
    def upsert_remote(self,workspace_id:int,obj:dict):
        with self._con() as con:
            local=con.execute('SELECT dirty FROM cache_objects WHERE workspace_id=? AND entity_type=? AND client_uuid=?',(workspace_id,obj['entity_type'],obj['client_uuid'])).fetchone()
            if local and local['dirty']: return
            con.execute('''INSERT INTO cache_objects(workspace_id,entity_type,client_uuid,server_id,revision,deleted,payload_json,dirty,conflict_json,updated_at) VALUES(?,?,?,?,?,?,?,?,NULL,?)
            ON CONFLICT(workspace_id,entity_type,client_uuid) DO UPDATE SET server_id=excluded.server_id,revision=excluded.revision,deleted=excluded.deleted,payload_json=excluded.payload_json,dirty=0,conflict_json=NULL,updated_at=excluded.updated_at''',(workspace_id,obj['entity_type'],obj['client_uuid'],obj.get('server_id'),int(obj.get('revision',0)),1 if obj.get('deleted') else 0,json.dumps(obj.get('payload') or {},ensure_ascii=False),0,_now()))
    def edit_local(self,workspace_id:int,entity_type:str,payload:dict,*,client_uuid:str|None=None,server_id:int|None=None,base_revision:int=0,deleted:bool=False)->str:
        client_uuid=client_uuid or str(uuid.uuid4())
        with self._con() as con:
            row=con.execute('SELECT revision,server_id FROM cache_objects WHERE workspace_id=? AND entity_type=? AND client_uuid=?',(workspace_id,entity_type,client_uuid)).fetchone()
            revision=int(row['revision']) if row else int(base_revision); server_id=row['server_id'] if row and row['server_id'] is not None else server_id
            con.execute('''INSERT INTO cache_objects(workspace_id,entity_type,client_uuid,server_id,revision,deleted,payload_json,dirty,conflict_json,updated_at) VALUES(?,?,?,?,?,?,?,?,NULL,?)
            ON CONFLICT(workspace_id,entity_type,client_uuid) DO UPDATE SET server_id=excluded.server_id,deleted=excluded.deleted,payload_json=excluded.payload_json,dirty=1,conflict_json=NULL,updated_at=excluded.updated_at''',(workspace_id,entity_type,client_uuid,server_id,revision,1 if deleted else 0,json.dumps(payload,ensure_ascii=False),1,_now()))
        return client_uuid
    def dirty(self,workspace_id:int)->list[dict]:
        with self._con() as con: rows=con.execute('SELECT * FROM cache_objects WHERE workspace_id=? AND dirty=1 ORDER BY updated_at,client_uuid',(workspace_id,)).fetchall()
        out=[]
        for r in rows:
            d=dict(r); d['payload']=json.loads(d.pop('payload_json')); d['deleted']=bool(d['deleted']); d['conflict']=json.loads(d.pop('conflict_json')) if d.get('conflict_json') else None; out.append(d)
        return out
    def mark_pushed(self,workspace_id:int,obj:dict): self.upsert_remote(workspace_id,obj)
    def mark_conflict(self,workspace_id:int,entity_type:str,client_uuid:str,conflict:dict):
        with self._con() as con: con.execute('UPDATE cache_objects SET conflict_json=?,updated_at=? WHERE workspace_id=? AND entity_type=? AND client_uuid=?',(json.dumps(conflict,ensure_ascii=False),_now(),workspace_id,entity_type,client_uuid))
    def objects(self,workspace_id:int,entity_type:str|None=None)->list[dict]:
        q='SELECT * FROM cache_objects WHERE workspace_id=?'; params=[workspace_id]
        if entity_type: q+=' AND entity_type=?'; params.append(entity_type)
        with self._con() as con: rows=con.execute(q+' ORDER BY updated_at DESC',params).fetchall()
        out=[]
        for r in rows:
            d=dict(r); d['payload']=json.loads(d.pop('payload_json')); d['deleted']=bool(d['deleted']); d['dirty']=bool(d['dirty']); d['conflict']=json.loads(d.pop('conflict_json')) if d.get('conflict_json') else None; out.append(d)
        return out
    def document_status(self,workspace_id:int,document_id:int)->dict|None:
        with self._con() as con: row=con.execute('SELECT * FROM cached_documents WHERE workspace_id=? AND document_id=?',(workspace_id,document_id)).fetchone()
        return dict(row) if row else None
    def mark_document(self,workspace_id:int,document_id:int,name:str,local_path:str,status:str='available'):
        with self._con() as con: con.execute('INSERT INTO cached_documents(workspace_id,document_id,name,local_path,status,downloaded_at) VALUES(?,?,?,?,?,?) ON CONFLICT(workspace_id,document_id) DO UPDATE SET name=excluded.name,local_path=excluded.local_path,status=excluded.status,downloaded_at=excluded.downloaded_at',(workspace_id,document_id,name,local_path,status,_now() if status=='available' else None))

class ClientSyncEngine:
    def __init__(self,client,store:ClientCacheStore): self.client=client; self.store=store
    def sync(self,workspace_id:int)->dict:
        state=self.store.state(workspace_id); pulled=self.client.sync_pull(workspace_id,state['cursor'])
        for change in pulled.get('changes',[]):
            if change.get('object'): self.store.upsert_remote(workspace_id,change['object'])
        self.store.set_state(workspace_id,cursor=pulled.get('cursor',state['cursor']))
        applied=0; conflicts=0
        for obj in self.store.dirty(workspace_id):
            result=self.client.sync_push(workspace_id,obj['entity_type'],obj['client_uuid'],obj['revision'],obj['payload'],deleted=obj['deleted'],server_id=obj['server_id'])
            if result.get('status')=='applied': self.store.mark_pushed(workspace_id,result['object']); applied+=1
            else: self.store.mark_conflict(workspace_id,obj['entity_type'],obj['client_uuid'],result); conflicts+=1
        manifest=self.client.workspace_manifest(workspace_id); self.store.set_state(workspace_id,manifest_revision=manifest.get('revision',''))
        return {'workspace_id':workspace_id,'cursor':self.store.state(workspace_id)['cursor'],'pulled':len(pulled.get('changes',[])),'pushed':applied,'conflicts':conflicts,'manifest_revision':manifest.get('revision','')}
    def cache_document(self,workspace_id:int,document_id:int,name:str,directory:str|Path)->Path:
        target=Path(directory)/f'{document_id}_{Path(name).name}'; path=self.client.download_document(workspace_id,document_id,target); self.store.mark_document(workspace_id,document_id,name,str(path)); return path
