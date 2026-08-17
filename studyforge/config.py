from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    chat_model: str = os.getenv("CHAT_MODEL", "qwen3:4b")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "embeddinggemma")
    db_path: str = os.getenv("STUDYFORGE_DB", "data/studyforge.db")
    upload_dir: str = os.getenv("STUDYFORGE_UPLOADS", "data/uploads")
    ocr_lang: str = os.getenv("OCR_LANG", "ita+eng")
    chunk_chars: int = int(os.getenv("CHUNK_CHARS", "2200"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "300"))
    top_k: int = int(os.getenv("TOP_K", "8"))

settings = Settings()
