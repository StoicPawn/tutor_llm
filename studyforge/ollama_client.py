from __future__ import annotations
import requests
from .config import settings

class OllamaError(RuntimeError):
    pass

def _post(path: str, payload: dict, timeout: int = 300) -> dict:
    try:
        r = requests.post(f"{settings.ollama_url}{path}", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as exc:
        raise OllamaError(f"Ollama non raggiungibile: {exc}") from exc

def health() -> bool:
    try:
        r = requests.get(f"{settings.ollama_url}/api/version", timeout=3)
        return r.ok
    except requests.RequestException:
        return False

def embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    out = _post("/api/embed", {"model": settings.embedding_model, "input": texts})
    return out["embeddings"]

def chat(messages: list[dict], temperature: float = 0.2) -> str:
    out = _post("/api/chat", {
        "model": settings.chat_model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    })
    return out["message"]["content"]
