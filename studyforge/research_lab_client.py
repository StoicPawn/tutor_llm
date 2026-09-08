from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from .config import settings


class ResearchLabError(RuntimeError):
    pass


@dataclass
class ResearchLabClient:
    base_url: str
    token: str
    timeout: float = 180.0

    def _headers(self) -> dict[str, str]:
        if not self.token:
            raise ResearchLabError('RESEARCH_LAB_TOKEN non configurato')
        return {'Authorization': f'Bearer {self.token}'}

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = requests.request(
                method,
                self.base_url.rstrip('/') + path,
                headers=self._headers(),
                timeout=self.timeout,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise ResearchLabError(f'Research Lab non raggiungibile: {exc}') from exc
        if response.status_code >= 400:
            try:
                detail = response.json().get('detail', response.text)
            except ValueError:
                detail = response.text
            raise ResearchLabError(f'Research Lab HTTP {response.status_code}: {detail}')
        return response.json()

    def health(self) -> bool:
        try:
            response = requests.get(self.base_url.rstrip('/') + '/health', timeout=3)
            return response.ok and bool(response.json().get('ok'))
        except Exception:
            return False

    def workspaces(self) -> list[dict[str, Any]]:
        return self._request('GET', '/api/workspaces')

    def create_workspace(
        self,
        name: str,
        description: str = '',
        source_project: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request('POST', '/api/workspaces', json={
            'name': name,
            'description': description,
            'source_project': source_project,
            'metadata': metadata or {},
        })

    def ensure_workspace(
        self,
        project_key: str,
        name: str,
        description: str = '',
    ) -> dict[str, Any]:
        project_key = project_key.strip()
        if not project_key:
            raise ResearchLabError('project_key non può essere vuoto')
        for workspace in self.workspaces():
            metadata = workspace.get('metadata') or {}
            if metadata.get('project_key') == project_key:
                return workspace
        return self.create_workspace(
            name,
            description,
            source_project='shared',
            metadata={
                'project_key': project_key,
                'created_by': 'tutor_llm',
            },
        )

    def delete_workspace(self, workspace_id: str) -> dict[str, Any]:
        return self._request('DELETE', f'/api/workspaces/{workspace_id}?confirm=true')

    def runs(self, workspace_id: str) -> list[dict[str, Any]]:
        return self._request('GET', f'/api/workspaces/{workspace_id}/runs')

    def run(
        self,
        workspace_id: str,
        code: str,
        title: str = 'Experiment',
        timeout_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {'title': title, 'code': code, 'metadata': metadata or {}}
        if timeout_seconds is not None:
            payload['timeout_seconds'] = timeout_seconds
        return self._request('POST', f'/api/workspaces/{workspace_id}/runs', json=payload)

    def publish_context(
        self,
        workspace_id: str,
        project_key: str,
        content: str,
        *,
        title: str = 'Tutor theory snapshot',
        topic: str = '',
        sources: Any = None,
    ) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            'caller': 'tutor_llm',
            'kind': 'theory_context',
            'project_key': project_key,
            'topic': topic,
            'content': content,
        }
        if sources is not None:
            metadata['sources'] = sources
        return self.run(
            workspace_id,
            "print('Tutor LLM theory snapshot published')",
            title=title,
            timeout_seconds=30,
            metadata=metadata,
        )

    def latest_context(self, workspace_id: str) -> dict[str, Any] | None:
        for run in self.runs(workspace_id):
            metadata = run.get('metadata') or {}
            if metadata.get('kind') in {'theory_context', 'shared_context'}:
                return run
        return None


def configured_client() -> ResearchLabClient | None:
    if not settings.research_lab_url or not settings.research_lab_token:
        return None
    return ResearchLabClient(settings.research_lab_url, settings.research_lab_token)
