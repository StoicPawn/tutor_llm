from __future__ import annotations
import hashlib
import json
from .db import connect


def _table_state(con,table:str,workspace_id:int)->dict:
    cols={r['name'] for r in con.execute(f'PRAGMA table_info({table})').fetchall()}
    if 'workspace_id' not in cols: return {'count':0,'version':''}
    order_col='updated_at' if 'updated_at' in cols else ('created_at' if 'created_at' in cols else 'id')
    try:
        row=con.execute(f'SELECT COUNT(*) n, MAX({order_col}) v FROM {table} WHERE workspace_id=?',(workspace_id,)).fetchone()
        return {'count':int(row['n'] or 0),'version':str(row['v'] or '')}
    except Exception:
        return {'count':0,'version':''}


def workspace_manifest(workspace_id:int)->dict:
    tables=['documents','lessons','notes','study_sessions','student_concepts','curricula','knowledge_nodes','review_schedule','flashcards','document_annotations','notebooks']
    with connect() as con:
        states={t:_table_state(con,t,workspace_id) for t in tables}
        # notebook pages live under notebooks, so include their aggregate explicitly.
        try:
            row=con.execute('''SELECT COUNT(*) n, MAX(p.updated_at) v FROM notebook_pages p
                               JOIN notebooks n ON n.id=p.notebook_id WHERE n.workspace_id=?''',(workspace_id,)).fetchone()
            states['notebook_pages']={'count':int(row['n'] or 0),'version':str(row['v'] or '')}
        except Exception: states['notebook_pages']={'count':0,'version':''}
    canonical=json.dumps(states,sort_keys=True,separators=(',',':'))
    revision=hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:24]
    return {'workspace_id':workspace_id,'revision':revision,'entities':states}
