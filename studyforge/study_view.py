from __future__ import annotations
from .db import list_documents, get_document_page
from .notes import list_notes
from .sessions import get_session, update_session
from .source_map import map_selection
from .review_queue import review_queue
from .planner import next_best_activity
from .student import weakest

CONTEXT_ACTIONS = {
    'explain': 'Spiega con chiarezza questo passaggio nel suo contesto, esplicitando prerequisiti e passaggi impliciti.',
    'deepen': 'Approfondisci questo passaggio collegandolo ai concetti rilevanti del workspace.',
    'example': 'Costruisci un esempio concreto e poi un controesempio o caso limite, se pertinente.',
    'exercise': 'Crea un esercizio mirato che verifichi davvero la comprensione di questo passaggio. Non mostrare subito la soluzione.',
    'why': 'Spiega perché questo passaggio è vero o perché l autore può compiere questa inferenza, indicando le ipotesi necessarie.',
    'prerequisites': 'Identifica i prerequisiti necessari per comprendere questo passaggio e spiegali in ordine minimo sufficiente.',
}


def study_workspace_state(workspace_id:int, session_id:int|None=None, document_id:int|None=None, page:int|None=None)->dict:
    docs=[dict(r) for r in list_documents(workspace_id)]
    session=dict(get_session(session_id)) if session_id else None
    active_document_id=document_id or (session.get('current_document_id') if session else None)
    active_page=page or (session.get('current_page') if session else None) or 1
    page_data=get_document_page(workspace_id,int(active_document_id),int(active_page)) if active_document_id else None
    return {
        'workspace_id':workspace_id,
        'session':session,
        'documents':docs,
        'active_document_id':active_document_id,
        'active_page':int(active_page),
        'page':page_data,
        'notes':[dict(r) for r in list_notes(workspace_id)],
        'reviews':review_queue(workspace_id,12),
        'weakest':[dict(r) for r in weakest(workspace_id,8)],
        'next_activity':next_best_activity(workspace_id),
    }


def set_reading_context(session_id:int, workspace_id:int, document_id:int, page:int, selected_text:str=''):
    update_session(session_id,workspace_id,current_document_id=document_id,current_page=page,selected_text=selected_text)


def selection_context(workspace_id:int, document_id:int, page:int, selected_text:str='', bbox:list[float]|None=None)->dict:
    return map_selection(workspace_id,document_id,page,selected_text,bbox)


def contextual_tutor_request(action:str, selection:dict, user_instruction:str='')->str:
    instruction=CONTEXT_ACTIONS.get(action,CONTEXT_ACTIONS['explain'])
    selected=(selection.get('selected_text') or '').strip()
    citation=selection.get('citation','')
    extra=user_instruction.strip()
    parts=[instruction]
    if selected:
        parts.append(f'PASSAGGIO SELEZIONATO:\n{selected}')
    if citation:
        parts.append(f'POSIZIONE NEL DOCUMENTO: {citation}')
    if extra:
        parts.append(f'RICHIESTA AGGIUNTIVA DELLO STUDENTE: {extra}')
    parts.append('Usa il materiale del workspace come fonte primaria e distingui chiaramente eventuali integrazioni esterne secondo la politica epistemica attiva.')
    return '\n\n'.join(parts)
