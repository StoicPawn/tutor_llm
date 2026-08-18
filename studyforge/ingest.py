from __future__ import annotations
from pathlib import Path
import fitz
from docx import Document
from PIL import Image
import pytesseract
from .config import settings

SUPPORTED = {'.pdf', '.docx', '.txt', '.md', '.png', '.jpg', '.jpeg', '.tif', '.tiff', '.webp'}


def _ocr_pixmap(pix: fitz.Pixmap) -> str:
    mode = 'RGB' if pix.n < 4 else 'RGBA'
    img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
    return pytesseract.image_to_string(img, lang=settings.ocr_lang)


def _pdf_blocks(page: fitz.Page) -> list[dict]:
    blocks=[]
    for b in page.get_text('blocks'):
        if len(b) < 5: continue
        x0,y0,x1,y1,text = b[:5]
        text=' '.join(str(text).split())
        if text:
            blocks.append({'bbox':[round(float(x0),2),round(float(y0),2),round(float(x1),2),round(float(y1),2)],'text':text})
    return blocks


def extract(path: str) -> list[dict]:
    p=Path(path); ext=p.suffix.lower()
    if ext not in SUPPORTED: raise ValueError(f'Formato non supportato: {ext}')
    pages=[]
    if ext == '.pdf':
        doc=fitz.open(path)
        for i,page in enumerate(doc):
            blocks=_pdf_blocks(page)
            text=page.get_text('text').strip()
            ocr_used=False
            if len(text) < 80:
                pix=page.get_pixmap(matrix=fitz.Matrix(2,2), alpha=False)
                text=_ocr_pixmap(pix).strip(); ocr_used=True
                blocks=[]
            if text:
                pages.append({'page':i+1,'text':text,'blocks':blocks,'width':float(page.rect.width),'height':float(page.rect.height),'ocr_used':ocr_used})
    elif ext == '.docx':
        doc=Document(path); text='\n'.join(p.text for p in doc.paragraphs if p.text.strip())
        pages.append({'page':None,'text':text,'blocks':[],'ocr_used':False})
    elif ext in {'.txt','.md'}:
        pages.append({'page':None,'text':p.read_text(encoding='utf-8',errors='ignore'),'blocks':[],'ocr_used':False})
    else:
        img=Image.open(path); text=pytesseract.image_to_string(img,lang=settings.ocr_lang).strip()
        pages.append({'page':1,'text':text,'blocks':[],'width':img.width,'height':img.height,'ocr_used':True})
    return pages


def chunk_pages(pages: list[dict]) -> list[dict]:
    size, overlap=settings.chunk_chars, settings.chunk_overlap
    out=[]; idx=0
    for page in pages:
        text=' '.join(page['text'].split()); start=0
        while start < len(text):
            end=min(len(text), start+size); piece=text[start:end]
            if end < len(text):
                cut=max(piece.rfind('. '),piece.rfind('; '),piece.rfind('\n'))
                if cut > size*.55:
                    end=start+cut+1; piece=text[start:end]
            clean=piece.strip()
            if clean:
                left_trim=len(piece)-len(piece.lstrip())
                right_trim=len(piece)-len(piece.rstrip())
                out.append({
                    'page':page.get('page'),'chunk_index':idx,'text':clean,
                    'char_start':start+left_trim,'char_end':end-right_trim,
                }); idx+=1
            if end >= len(text): break
            start=max(start+1,end-overlap)
    return out
