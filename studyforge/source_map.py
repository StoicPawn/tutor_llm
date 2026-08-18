from __future__ import annotations
import json
from difflib import SequenceMatcher
from .db import connect, get_document_page


def _overlap(a: list[float], b: list[float]) -> float:
    ax0,ay0,ax1,ay1=a; bx0,by0,bx1,by1=b
    x0=max(ax0,bx0); y0=max(ay0,by0); x1=min(ax1,bx1); y1=min(ay1,by1)
    if x1<=x0 or y1<=y0: return 0.0
    inter=(x1-x0)*(y1-y0)
    area=max(1e-9,(ax1-ax0)*(ay1-ay0))
    return inter/area


def map_selection(workspace_id:int, document_id:int, page:int, selected_text:str='', bbox:list[float]|None=None) -> dict:
    page_data=get_document_page(workspace_id,document_id,page)
    if not page_data:
        raise ValueError('Pagina non trovata nel workspace.')
    blocks=page_data.get('blocks',[])
    selected_blocks=[]
    if bbox:
        for b in blocks:
            bb=b.get('bbox')
            if bb and _overlap([float(x) for x in bb],[float(x) for x in bbox]) >= .08:
                selected_blocks.append(b)
    if not selected_text and selected_blocks:
        selected_text='\n'.join(str(b.get('text','')) for b in selected_blocks if b.get('text')).strip()
    selected_text=' '.join(selected_text.split())
    with connect() as con:
        rows=con.execute('''SELECT c.*,d.name document_name FROM chunks c JOIN documents d ON d.id=c.document_id
                            WHERE c.document_id=? AND c.page=? AND d.workspace_id=? ORDER BY c.chunk_index''',
                         (document_id,page,workspace_id)).fetchall()
    candidates=[]
    for r in rows:
        chunk_text=' '.join(r['text'].split())
        if not selected_text:
            score=0.0
        elif selected_text in chunk_text:
            score=1.0
        elif chunk_text in selected_text:
            score=min(1.0,len(chunk_text)/max(1,len(selected_text)))
        else:
            score=SequenceMatcher(None,selected_text[:2500],chunk_text[:2500]).ratio()
        candidates.append({
            'chunk_id':int(r['id']), 'chunk_index':int(r['chunk_index']), 'score':round(float(score),4),
            'text':r['text'], 'document':r['document_name'], 'page':page,
        })
    candidates.sort(key=lambda x:x['score'],reverse=True)
    return {
        'workspace_id':workspace_id,'document_id':document_id,'page':page,
        'selected_text':selected_text,'bbox':bbox,'ocr_used':bool(page_data.get('ocr_used')),
        'blocks':selected_blocks,'matches':candidates[:5],
        'citation':f"{page_data['document_name']}, p. {page}",
    }
