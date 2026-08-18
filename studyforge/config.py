from dataclasses import dataclass
import os


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'on'}


@dataclass(frozen=True)
class Settings:
    # Deployment profile: local = everything on one PC; server = shared core for remote clients.
    deploy_mode: str = os.getenv('DEPLOY_MODE', 'local').strip().lower()
    inference_provider: str = os.getenv('INFERENCE_PROVIDER', 'ollama').strip().lower()

    # Inference backend. In local mode this normally points to localhost; in server mode
    # it may point to an Ollama service/container on the same private server network.
    ollama_url: str = os.getenv('OLLAMA_URL', 'http://localhost:11434')
    chat_model: str = os.getenv('CHAT_MODEL', 'qwen3:4b')
    embedding_model: str = os.getenv('EMBEDDING_MODEL', 'embeddinggemma')

    # Persistent user data. These paths are local to the machine running Tutor LLM Core.
    db_path: str = os.getenv('STUDYFORGE_DB', 'data/studyforge.db')
    upload_dir: str = os.getenv('STUDYFORGE_UPLOADS', 'data/uploads')

    # API/network settings are mainly relevant in server mode.
    api_host: str = os.getenv('API_HOST', '127.0.0.1')
    api_port: int = int(os.getenv('API_PORT', '8000'))
    api_token: str = os.getenv('API_TOKEN', '').strip()
    trust_proxy_headers: bool = _env_bool('TRUST_PROXY_HEADERS', False)

    ocr_lang: str = os.getenv('OCR_LANG', 'ita+eng')
    chunk_chars: int = int(os.getenv('CHUNK_CHARS', '2200'))
    chunk_overlap: int = int(os.getenv('CHUNK_OVERLAP', '300'))
    top_k: int = int(os.getenv('TOP_K', '8'))

    def validate(self) -> None:
        if self.deploy_mode not in {'local', 'server'}:
            raise ValueError('DEPLOY_MODE deve essere local oppure server.')
        if self.inference_provider not in {'ollama'}:
            raise ValueError(f'Inference provider non supportato: {self.inference_provider}')


settings = Settings()
settings.validate()
