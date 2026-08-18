from __future__ import annotations
import json
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from .devices import create_device, list_devices, revoke_device, get_device
from .security import require_admin
from .sync import workspace_manifest

router=APIRouter()

class DeviceIn(BaseModel):
    name:str
    platform:str='unknown'
    metadata:dict={}

@router.post('/admin/devices')
def device_create(payload:DeviceIn,request:Request):
    require_admin(request)
    return create_device(payload.name,payload.platform,json.dumps(payload.metadata,ensure_ascii=False))

@router.get('/admin/devices')
def devices(request:Request,include_revoked:bool=False):
    require_admin(request)
    return list_devices(include_revoked)

@router.delete('/admin/devices/{device_id}')
def device_revoke(device_id:int,request:Request):
    require_admin(request)
    if not revoke_device(device_id): raise HTTPException(status_code=404,detail='Dispositivo non trovato o già revocato.')
    return {'ok':True,'device':get_device(device_id)}

@router.get('/device/me')
def device_me(request:Request):
    auth=getattr(request.state,'auth',{})
    if auth.get('kind')=='admin': return {'kind':'admin'}
    if auth.get('kind')=='device': return auth
    return {'kind':auth.get('kind','local')}

@router.get('/sync/workspaces/{workspace_id}/manifest')
def sync_manifest(workspace_id:int):
    return workspace_manifest(workspace_id)
