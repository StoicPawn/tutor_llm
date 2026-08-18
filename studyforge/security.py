from __future__ import annotations
import hmac
from fastapi import Request
from fastapi.responses import JSONResponse
from .config import settings

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


async def auth_middleware(request: Request, call_next):
    if not auth_required() or request.url.path in PUBLIC_PATHS:
        return await call_next(request)
    supplied = _bearer_token(request)
    expected = settings.api_token
    if not supplied or not expected or not hmac.compare_digest(supplied, expected):
        return JSONResponse(status_code=401, content={'detail': 'Bearer token mancante o non valido.'})
    return await call_next(request)
