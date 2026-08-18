from __future__ import annotations
import hashlib
import secrets
from datetime import datetime, timezone
from .db import connect

SCHEMA='''
CREATE TABLE IF NOT EXISTS client_devices (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL,
 platform TEXT NOT NULL DEFAULT 'unknown',
 token_hash TEXT NOT NULL UNIQUE,
 token_prefix TEXT NOT NULL,
 created_at TEXT NOT NULL,
 last_seen_at TEXT,
 revoked_at TEXT,
 metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_client_devices_active ON client_devices(revoked_at,id);
'''


def _now()->str:
    return datetime.now(timezone.utc).isoformat()


def _hash(token:str)->str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def _ensure():
    with connect() as con: con.executescript(SCHEMA)


def create_device(name:str,platform:str='unknown',metadata_json:str='{}')->dict:
    _ensure(); secret=secrets.token_urlsafe(36); prefix=secrets.token_hex(4)
    token=f'tllm_{prefix}_{secret}'; now=_now()
    with connect() as con:
        cur=con.execute('''INSERT INTO client_devices(name,platform,token_hash,token_prefix,created_at,metadata_json)
                           VALUES(?,?,?,?,?,?)''',(name.strip()[:200] or 'Device',platform.strip()[:80] or 'unknown',_hash(token),prefix,now,metadata_json[:12000]))
        did=int(cur.lastrowid)
    return {'id':did,'name':name.strip()[:200] or 'Device','platform':platform.strip()[:80] or 'unknown','token':token,'token_prefix':prefix,'created_at':now}


def authenticate_device(token:str,*,touch:bool=True)->dict|None:
    _ensure()
    if not token.startswith('tllm_'): return None
    digest=_hash(token)
    with connect() as con:
        row=con.execute('SELECT * FROM client_devices WHERE token_hash=? AND revoked_at IS NULL',(digest,)).fetchone()
        if not row: return None
        if touch: con.execute('UPDATE client_devices SET last_seen_at=? WHERE id=?',(_now(),int(row['id'])))
        return dict(row)


def list_devices(include_revoked:bool=False)->list[dict]:
    _ensure()
    q='SELECT id,name,platform,token_prefix,created_at,last_seen_at,revoked_at,metadata_json FROM client_devices'
    if not include_revoked: q+=' WHERE revoked_at IS NULL'
    q+=' ORDER BY id DESC'
    with connect() as con: return [dict(r) for r in con.execute(q).fetchall()]


def revoke_device(device_id:int)->bool:
    _ensure()
    with connect() as con:
        cur=con.execute('UPDATE client_devices SET revoked_at=? WHERE id=? AND revoked_at IS NULL',(_now(),int(device_id)))
        return cur.rowcount==1


def get_device(device_id:int)->dict|None:
    _ensure()
    with connect() as con:
        row=con.execute('SELECT id,name,platform,token_prefix,created_at,last_seen_at,revoked_at,metadata_json FROM client_devices WHERE id=?',(int(device_id),)).fetchone()
        return dict(row) if row else None
