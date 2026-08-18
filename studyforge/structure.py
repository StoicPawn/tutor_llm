from __future__ import annotations
import re
from .db import connect, get_document_page

SCHEMA = '''
CREATE TABLE IF NOT EXISTS document_sections (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 document_id INTEGER NOT NULL,
 parent_id INTEGER,
 level INTEGER NOT NULL,
 title TEXT NOT NULL,
 start_page INTEGER,
 end_page INTEGER,
 ordinal INTEGER NOT NULL,
 FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE,
 FOREIGN KEY(parent_id) REFERENCES document_sections(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_sections_document ON document_sections(document_id,ordinal);
'''

HEADING_PATTERNS = [
    re.compile(r'^\s*(?:capitolo|chapter)\s+([0-9ivxlcdm]+)\s*[:.\-]?\s*(.*)$', re.I),
    re.compile(r'^\s*(\d+(?:\.\d+){0,3})\s+(.{3,120})$'),
    re.compile(r'^\s*([A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ0-9 ,:;\-]{4,100})\s*$'),
]


def _ensure():
    with connect() as con:
        con.executescript(SCHEMA)


def _candidate_headings(page_text: str) -> list[tuple[int, str]]:
    out=[]
    for raw in page_text.splitlines():
        line=' '.join(raw.split())
        if len(line) < 4 or len(line) > 140:
            continue
        m=HEADING_PATTERNS[0].match(line)
        if m:
            out.append((1, line)); continue
        m=HEADING_PATTERNS[1].match(line)
        if m:
            depth=min(4, m.group(1).count('.')+1)
            out.append((depth, line)); continue
        if HEADING_PATTERNS[2].match(line) and len(line.split()) <= 12:
            out.append((2, line.title()))
    seen=set(); unique=[]
    for item in out:
        key=item[1].casefold()
        if key not in seen:
            seen.add(key); unique.append(item)
    return unique[:8]


def rebuild_structure(workspace_id: int, document_id: int) -> list[dict]:
    _ensure()
    with connect() as con:
        belongs=con.execute('SELECT 1 FROM documents WHERE id=? AND workspace_id=?',(document_id,workspace_id)).fetchone()
        if not belongs:
            raise ValueError('Documento non appartenente al workspace.')
        pages=con.execute('SELECT page,text FROM document_pages WHERE document_id=? ORDER BY page',(document_id,)).fetchall()
        con.execute('DELETE FROM document_sections WHERE document_id=?',(document_id,))
        candidates=[]
        for p in pages:
            for level,title in _candidate_headings(p['text']):
                candidates.append({'level':level,'title':title,'start_page':int(p['page'])})
        if not candidates and pages:
            candidates=[{'level':1,'title':'Documento','start_page':int(pages[0]['page'])}]
        stack=[]
        last_page=int(pages[-1]['page']) if pages else None
        for i,item in enumerate(candidates):
            while stack and stack[-1][0] >= item['level']:
                stack.pop()
            parent_id=stack[-1][1] if stack else None
            if i+1 < len(candidates):
                end_page=max(item['start_page'],candidates[i+1]['start_page']-1)
            else:
                end_page=max(item['start_page'],last_page) if last_page is not None else item['start_page']
            cur=con.execute('''INSERT INTO document_sections(document_id,parent_id,level,title,start_page,end_page,ordinal)
                               VALUES(?,?,?,?,?,?,?)''',
                            (document_id,parent_id,item['level'],item['title'],item['start_page'],end_page,i))
            sid=int(cur.lastrowid); stack.append((item['level'],sid))
    return [dict(r) for r in list_sections(workspace_id,document_id)]


def list_sections(workspace_id: int, document_id: int):
    _ensure()
    with connect() as con:
        return con.execute('''SELECT s.* FROM document_sections s JOIN documents d ON d.id=s.document_id
                              WHERE s.document_id=? AND d.workspace_id=? ORDER BY s.ordinal''',
                           (document_id,workspace_id)).fetchall()


def section_context(workspace_id:int, document_id:int, section_id:int) -> dict | None:
    _ensure()
    with connect() as con:
        row=con.execute('''SELECT s.* FROM document_sections s JOIN documents d ON d.id=s.document_id
                           WHERE s.id=? AND s.document_id=? AND d.workspace_id=?''',
                        (section_id,document_id,workspace_id)).fetchone()
    if not row: return None
    data=dict(row); pages=[]
    if data['start_page'] is not None and data['end_page'] is not None:
        for p in range(int(data['start_page']), int(data['end_page'])+1):
            page=get_document_page(workspace_id,document_id,p)
            if page: pages.append(page)
    data['pages']=pages
    return data
