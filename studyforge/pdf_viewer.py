from __future__ import annotations
from pathlib import Path
import fitz
from .db import connect


def _document_row(workspace_id:int, document_id:int):
    with connect() as con:
        row=con.execute('SELECT id,name,path FROM documents WHERE id=? AND workspace_id=?',(document_id,workspace_id)).fetchone()
    if not row:
        raise ValueError('Documento non trovato nel workspace.')
    return row


def render_pdf_page(workspace_id:int, document_id:int, page:int, scale:float=1.6)->dict:
    row=_document_row(workspace_id,document_id)
    path=Path(row['path'])
    if path.suffix.lower()!='.pdf':
        raise ValueError('Il viewer renderizzato è disponibile solo per PDF.')
    if not path.exists():
        raise FileNotFoundError('File PDF non disponibile sul server.')
    with fitz.open(path) as doc:
        if page < 1 or page > doc.page_count:
            raise ValueError('Pagina fuori intervallo.')
        p=doc.load_page(page-1)
        zoom=max(.5,min(4.0,float(scale)))
        pix=p.get_pixmap(matrix=fitz.Matrix(zoom,zoom),alpha=False)
        return {
            'png':pix.tobytes('png'),
            'page':page,
            'page_count':doc.page_count,
            'source_width':float(p.rect.width),
            'source_height':float(p.rect.height),
            'render_width':pix.width,
            'render_height':pix.height,
            'scale':zoom,
            'document_name':row['name'],
        }


def normalize_render_bbox(bbox:list[float], render_width:float, render_height:float, source_width:float, source_height:float)->list[float]:
    if len(bbox)!=4: raise ValueError('bbox deve contenere quattro coordinate.')
    if render_width<=0 or render_height<=0: raise ValueError('Dimensioni render non valide.')
    sx=source_width/render_width; sy=source_height/render_height
    x0,y0,x1,y1=[float(v) for v in bbox]
    x0,x1=sorted((max(0,x0),min(render_width,x1))); y0,y1=sorted((max(0,y0),min(render_height,y1)))
    return [x0*sx,y0*sy,x1*sx,y1*sy]


def blocks_in_bbox(workspace_id:int, document_id:int, page:int, bbox:list[float])->dict:
    from .db import get_document_page
    pdata=get_document_page(workspace_id,document_id,page)
    if not pdata: raise ValueError('Pagina non indicizzata.')
    x0,y0,x1,y1=[float(v) for v in bbox]
    selected=[]
    for block in pdata.get('blocks',[]):
        bb=block.get('bbox')
        if not bb: continue
        bx0,by0,bx1,by1=[float(v) for v in bb]
        ix0=max(x0,bx0); iy0=max(y0,by0); ix1=min(x1,bx1); iy1=min(y1,by1)
        if ix1>ix0 and iy1>iy0:
            selected.append(block)
    text='\n'.join(str(b.get('text','')) for b in selected if b.get('text')).strip()
    return {'bbox':bbox,'blocks':selected,'text':text,'ocr_used':bool(pdata.get('ocr_used'))}
