from dataclasses import dataclass, field
import os


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'on'}


@dataclass(frozen=True)
class Settings:
    # Use factories so tests and embedding applications can change environment
    # variables before constructing a Settings instance.
    deploy_mode: str = field(default_factory=lambda: os.getenv('DEPLOY_MODE', 'local').strip().lower())
    inference_provider: str = field(default_factory=lambda: os.getenv('INFERENCE_PROVIDER', 'ollama').strip().lower())

    ollama_url: str = field(default_factory=lambda: os.getenv('OLLAMA_URL', 'http://localhost:11434'))
    chat_model: str = field(default_factory=lambda: os.getenv('CHAT_MODEL', 'qwen3:4b'))
    embedding_model: str = field(default_factory=lambda: os.getenv('EMBEDDING_MODEL', 'embeddinggemma'))

    db_path: str = field(default_factory=lambda: os.getenv('STUDYFORGE_DB', 'data/studyforge.db'))
    upload_dir: str = field(default_factory=lambda: os.getenv('STUDYFORGE_UPLOADS', 'data/uploads'))

    api_host: str = field(default_factory=lambda: os.getenv('API_HOST', '127.0.0.1'))
    api_port: int = field(default_factory=lambda: int(os.getenv('API_PORT', '8000')))
    api_token: str = field(default_factory=lambda: os.getenv('API_TOKEN', '').strip())
    trust_proxy_headers: bool = field(default_factory=lambda: _env_bool('TRUST_PROXY_HEADERS', False))

    # Optional standalone Research Lab integration. Tutor does not own Lab data;
    # it only calls the service through its HTTP API when configured.
    research_lab_url: str = field(default_factory=lambda: os.getenv('RESEARCH_LAB_URL', '').strip())
    research_lab_token: str = field(default_factory=lambda: os.getenv('RESEARCH_LAB_TOKEN', '').strip())

    ocr_lang: str = field(default_factory=lambda: os.getenv('OCR_LANG', 'ita+eng'))
    chunk_chars: int = field(default_factory=lambda: int(os.getenv('CHUNK_CHARS', '2200')))
    chunk_overlap: int = field(default_factory=lambda: int(os.getenv('CHUNK_OVERLAP', '300')))
    top_k: int = field(default_factory=lambda: int(os.getenv('TOP_K', '8')))

    def validate(self) -> None:
        if self.deploy_mode not in {'local', 'server'}:
            raise ValueError('DEPLOY_MODE deve essere local oppure server.')
        if self.inference_provider not in {'ollama'}:
            raise ValueError(f'Inference provider non supportato: {self.inference_provider}')


settings = Settings()
settings.validate()
