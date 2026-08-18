from __future__ import annotations
import hmac
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from .config import settings
from .devices import authenticate_device

PUBLIC_PATHS = {'/health', '/docs', '/openapi.json', '/redoc'}


def auth_required() -> bool:
    return settings.deploy_mode == 'server'


def validate_server_security() -> None:
    if auth_required() and not settings.api_token:
        raise RuntimeError('In DEPLOY_MODE=server è obbligatorio impostare API_TOKEN.')


def _bearer_token(request: Request) -> str:
    header = request.headers.get('authorization', '')
    if not header.lower().startswith('bearer '):
        return ''
    return header[7:].strip()


def is_admin_token(token:str)->bool:
    return bool(token and settings.api_token and hmac.compare_digest(token,settings.api_token))


def require_admin(request:Request)->None:
    token=_bearer_token(request)
    if not is_admin_token(token):
        raise HTTPException(status_code=403,detail='Richiesta riservata all amministratore del Tutor Server.')


async def auth_middleware(request: Request, call_next):
    if not auth_required() or request.url.path in PUBLIC_PATHS:
        request.state.auth={'kind':'local' if not auth_required() else 'public'}
        return await call_next(request)
    supplied = _bearer_token(request)
    if is_admin_token(supplied):
        request.state.auth={'kind':'admin'}
        return await call_next(request)
    device=authenticate_device(supplied) if supplied else None
    if device:
        request.state.auth={'kind':'device','device_id':int(device['id']),'device_name':device['name']}
        return await call_next(request)
    return JSONResponse(status_code=401, content={'detail': 'Bearer token mancante, revocato o non valido.'})
