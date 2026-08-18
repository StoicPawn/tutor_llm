from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .offline_sync import pull_changes, push_change, resolve_conflict

router=APIRouter()

class SyncPushIn(BaseModel):
    workspace_id:int
    entity_type:str
    client_uuid:str
    base_revision:int=0
    payload:dict|None=None
    deleted:bool=False
    server_id:int|None=None

class SyncResolveIn(BaseModel):
    workspace_id:int
    entity_type:str
    client_uuid:str
    server_revision:int
    payload:dict
    deleted:bool=False

@router.get('/sync/workspaces/{workspace_id}/changes')
def sync_pull(workspace_id:int,since:int=0,limit:int=500):
    try: return pull_changes(workspace_id,since,limit)
    except Exception as exc: raise HTTPException(status_code=400,detail=str(exc))

@router.post('/sync/push')
def sync_push(payload:SyncPushIn):
    try:
        result=push_change(payload.workspace_id,payload.entity_type,payload.client_uuid,payload.base_revision,payload.payload,payload.deleted,payload.server_id)
        if result.get('status')=='conflict':
            return result
        return result
    except Exception as exc: raise HTTPException(status_code=400,detail=str(exc))

@router.post('/sync/resolve')
def sync_resolve(payload:SyncResolveIn):
    try: return resolve_conflict(payload.workspace_id,payload.entity_type,payload.client_uuid,payload.server_revision,payload.payload,payload.deleted)
    except Exception as exc: raise HTTPException(status_code=400,detail=str(exc))
