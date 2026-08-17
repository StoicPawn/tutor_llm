from __future__ import annotations
from pathlib import Path
import fitz
from docx import Document
from PIL import Image
import pytesseract
from .config import settings

SUPPORTED = {".pdf", ".docx", ".txt", ".md", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}

def _ocr_pixmap(pix: fitz.Pixmap) -> str:
    mode = "RGB" if pix.n < 4 else "RGBA"
    img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
    return pytesseract.image_to_string(img, lang=settings.ocr_lang)

def extract(path: str) -> list[dict]:
    p = Path(path)
    ext = p.suffix.lower()
    if ext not in SUPPORTED:
        raise ValueError(f"Formato non supportato: {ext}")
    pages: list[dict] = []
    if ext == ".pdf":
        doc = fitz.open(path)
        for i, page in enumerate(doc):
            text = page.get_text("text").strip()
            if len(text) < 80:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                text = _ocr_pixmap(pix).strip()
            if text:
                pages.append({"page": i + 1, "text": text})
    elif ext == ".docx":
        doc = Document(path)
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        pages.append({"page": None, "text": text})
    elif ext in {".txt", ".md"}:
        pages.append({"page": None, "text": p.read_text(encoding="utf-8", errors="ignore")})
    else:
        img = Image.open(path)
        pages.append({"page": 1, "text": pytesseract.image_to_string(img, lang=settings.ocr_lang).strip()})
    return pages

def chunk_pages(pages: list[dict]) -> list[dict]:
    size, overlap = settings.chunk_chars, settings.chunk_overlap
    out, idx = [], 0
    for page in pages:
        text = " ".join(page["text"].split())
        start = 0
        while start < len(text):
            end = min(len(text), start + size)
            piece = text[start:end]
            if end < len(text):
                cut = max(piece.rfind(". "), piece.rfind("; "), piece.rfind("\n"))
                if cut > size * 0.55:
                    end = start + cut + 1
                    piece = text[start:end]
            if piece.strip():
                out.append({"page": page.get("page"), "chunk_index": idx, "text": piece.strip()})
                idx += 1
            if end >= len(text):
                break
            start = max(start + 1, end - overlap)
    return out
