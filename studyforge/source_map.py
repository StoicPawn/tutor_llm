from __future__ import annotations
from difflib import SequenceMatcher
from .db import connect, get_document_page

SCHEMA='''
CREATE TABLE IF NOT EXISTS chunk_spans (
 chunk_id INTEGER PRIMARY KEY,
 char_start INTEGER,
 char_end INTEGER,
 FOREIGN KEY(chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
);
'''


def _ensure():
    with connect() as con: con.executescript(SCHEMA)


def store_chunk_spans(document_id:int, chunks:list[dict]):
    _ensure()
    with connect() as con:
        rows=con.execute('SELECT id,chunk_index FROM chunks WHERE document_id=? ORDER BY chunk_index',(document_id,)).fetchall()
        by_index={int(r['chunk_index']):int(r['id']) for r in rows}
        payload=[]
        for c in chunks:
            cid=by_index.get(int(c['chunk_index']))
            if cid is not None:
                payload.append((cid,c.get('char_start'),c.get('char_end')))
        con.executemany('INSERT OR REPLACE INTO chunk_spans(chunk_id,char_start,char_end) VALUES(?,?,?)',payload)


def _overlap(a:list[float],b:list[float])->float:
    ax0,ay0,ax1,ay1=a; bx0,by0,bx1,by1=b
    x0=max(ax0,bx0); y0=max(ay0,by0); x1=min(ax1,bx1); y1=min(ay1,by1)
    if x1<=x0 or y1<=y0:return 0.0
    inter=(x1-x0)*(y1-y0); area=max(1e-9,(ax1-ax0)*(ay1-ay0))
    return inter/area


def map_selection(workspace_id:int,document_id:int,page:int,selected_text:str='',bbox:list[float]|None=None)->dict:
    _ensure(); page_data=get_document_page(workspace_id,document_id,page)
    if not page_data: raise ValueError('Pagina non trovata nel workspace.')
    blocks=page_data.get('blocks',[]); selected_blocks=[]
    if bbox:
        for b in blocks:
            bb=b.get('bbox')
            if bb and _overlap([float(x) for x in bb],[float(x) for x in bbox])>=.08:selected_blocks.append(b)
    if not selected_text and selected_blocks:
        selected_text='\n'.join(str(b.get('text','')) for b in selected_blocks if b.get('text')).strip()
    selected_text=' '.join(selected_text.split())
    normalized_page=' '.join(page_data.get('text','').split())
    sel_start=normalized_page.find(selected_text) if selected_text else -1
    sel_end=sel_start+len(selected_text) if sel_start>=0 else -1
    with connect() as con:
        rows=con.execute('''SELECT c.*,d.name document_name,s.char_start,s.char_end FROM chunks c
                            JOIN documents d ON d.id=c.document_id LEFT JOIN chunk_spans s ON s.chunk_id=c.id
                            WHERE c.document_id=? AND c.page=? AND d.workspace_id=? ORDER BY c.chunk_index''',
                         (document_id,page,workspace_id)).fetchall()
    candidates=[]
    for r in rows:
        chunk_text=' '.join(r['text'].split()); span_score=0.0
        if sel_start>=0 and r['char_start'] is not None and r['char_end'] is not None:
            inter=max(0,min(sel_end,int(r['char_end']))-max(sel_start,int(r['char_start'])))
            span_score=inter/max(1,len(selected_text))
        if not selected_text:text_score=0.0
        elif selected_text in chunk_text:text_score=1.0
        elif chunk_text in selected_text:text_score=min(1.0,len(chunk_text)/max(1,len(selected_text)))
        else:text_score=SequenceMatcher(None,selected_text[:2500],chunk_text[:2500]).ratio()
        score=max(span_score,text_score)
        candidates.append({'chunk_id':int(r['id']),'chunk_index':int(r['chunk_index']),'score':round(float(score),4),
                           'text':r['text'],'document':r['document_name'],'page':page,
                           'char_start':r['char_start'],'char_end':r['char_end']})
    candidates.sort(key=lambda x:x['score'],reverse=True)
    return {'workspace_id':workspace_id,'document_id':document_id,'page':page,'selected_text':selected_text,
            'selection_char_start':sel_start if sel_start>=0 else None,'selection_char_end':sel_end if sel_end>=0 else None,
            'bbox':bbox,'ocr_used':bool(page_data.get('ocr_used')),'blocks':selected_blocks,'matches':candidates[:5],
            'citation':f"{page_data['document_name']}, p. {page}"}
