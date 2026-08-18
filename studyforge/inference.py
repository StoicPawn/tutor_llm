from __future__ import annotations
from typing import Protocol
from .config import settings
from . import ollama_client


class InferenceProvider(Protocol):
    def health(self) -> bool: ...
    def embed(self, texts: list[str]) -> list[list[float]]: ...
    def chat(self, messages: list[dict], temperature: float = 0.2) -> str: ...


class OllamaProvider:
    def health(self) -> bool:
        return ollama_client.health()

    def embed(self, texts: list[str]) -> list[list[float]]:
        return ollama_client.embed(texts)

    def chat(self, messages: list[dict], temperature: float = 0.2) -> str:
        return ollama_client.chat(messages, temperature)


def get_provider() -> InferenceProvider:
    if settings.inference_provider == 'ollama':
        return OllamaProvider()
    raise RuntimeError(f'Inference provider non supportato: {settings.inference_provider}')


def health() -> bool:
    return get_provider().health()


def embed(texts: list[str]) -> list[list[float]]:
    return get_provider().embed(texts)


def chat(messages: list[dict], temperature: float = 0.2) -> str:
    return get_provider().chat(messages, temperature)
