from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import requests


class TutorClientError(RuntimeError):
    pass


@dataclass
class TutorClient:
    base_url: str
    token: str = ''
    timeout: int = 120

    def __post_init__(self):
        self.base_url = self.base_url.rstrip('/')

    def _headers(self) -> dict[str, str]:
        return {'Authorization': f'Bearer {self.token}'} if self.token else {}

    def _request(self, method: str, path: str, **kwargs):
        headers = dict(self._headers())
        headers.update(kwargs.pop('headers', {}))
        try:
            response = requests.request(method, self.base_url + path, headers=headers, timeout=self.timeout, **kwargs)
            response.raise_for_status()
        except requests.RequestException as exc:
            detail = ''
            if getattr(exc, 'response', None) is not None:
                try: detail = exc.response.json().get('detail', '')
                except Exception: detail = exc.response.text[:500]
            raise TutorClientError(detail or str(exc)) from exc
        content_type = response.headers.get('content-type', '')
        return response.json() if 'application/json' in content_type else response.content

    def health(self) -> dict:
        return self._request('GET', '/health')

    def identity(self) -> dict:
        return self._request('GET','/device/me')

    def workspace_manifest(self, workspace_id:int) -> dict:
        return self._request('GET',f'/sync/workspaces/{workspace_id}/manifest')

    def sync_pull(self, workspace_id:int, since:int=0, limit:int=500) -> dict:
        return self._request('GET',f'/sync/workspaces/{workspace_id}/changes?since={int(since)}&limit={int(limit)}')

    def sync_push(self, workspace_id:int, entity_type:str, client_uuid:str, base_revision:int,
                  payload:dict|None=None, *, deleted:bool=False, server_id:int|None=None) -> dict:
        return self._request('POST','/sync/push',json={
            'workspace_id':workspace_id,'entity_type':entity_type,'client_uuid':client_uuid,
            'base_revision':base_revision,'payload':payload or {},'deleted':deleted,'server_id':server_id,
        })

    def sync_resolve(self, workspace_id:int, entity_type:str, client_uuid:str, server_revision:int,
                     payload:dict|None=None, *, deleted:bool=False) -> dict:
        return self._request('POST','/sync/resolve',json={
            'workspace_id':workspace_id,'entity_type':entity_type,'client_uuid':client_uuid,
            'server_revision':server_revision,'payload':payload or {},'deleted':deleted,
        })

    def workspaces(self) -> list[dict]:
        return self._request('GET', '/workspaces')

    def ask(self, workspace_id: int, question: str, document_ids: list[int] | None = None,
            epistemic_mode: str = 'Tutor') -> dict:
        return self._request('POST', '/tutor/ask', json={
            'workspace_id': workspace_id,
            'topic': question,
            'document_ids': document_ids,
            'epistemic_mode': epistemic_mode,
        })

    def upload(self, workspace_id: int, path: str) -> dict:
        file_path = Path(path)
        with file_path.open('rb') as handle:
            return self._request('POST', f'/workspaces/{workspace_id}/documents',
                                 files={'file': (file_path.name, handle)})

    def download_document(self, workspace_id:int, document_id:int, destination:str|Path) -> Path:
        data=self._request('GET',f'/workspaces/{workspace_id}/documents/{document_id}/source')
        path=Path(destination); path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data); return path

    def page(self, workspace_id: int, document_id: int, page: int) -> dict:
        return self._request('GET', f'/workspaces/{workspace_id}/documents/{document_id}/pages/{page}')

    def next_activity(self, workspace_id: int, curriculum_id: int | None = None) -> dict:
        suffix = f'?curriculum_id={curriculum_id}' if curriculum_id is not None else ''
        return self._request('GET', f'/workspaces/{workspace_id}/next-activity{suffix}')
