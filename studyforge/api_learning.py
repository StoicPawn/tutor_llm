from __future__ import annotations
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from .structure import rebuild_structure, list_sections, section_context
from .source_map import map_selection
from .flashcards import generate_flashcards, list_flashcards, review_flashcard, archive_flashcard
from .review_queue import review_queue
from .planner import next_best_activity
from .study_view import study_workspace_state, selection_context, contextual_tutor_request, set_reading_context
from .pdf_viewer import render_pdf_page, normalize_render_bbox, blocks_in_bbox

router=APIRouter()

class StructureIn(BaseModel):
    workspace_id:int
    document_id:int

class SelectionIn(BaseModel):
    workspace_id:int
    document_id:int
    page:int
    selected_text:str=''
    bbox:list[float]|None=None

class RenderSelectionIn(BaseModel):
    workspace_id:int
    document_id:int
    page:int
    bbox:list[float]
    render_width:float
    render_height:float
    source_width:float
    source_height:float

class ContextActionIn(BaseModel):
    workspace_id:int
    document_id:int
    page:int
    action:str='explain'
    selected_text:str=''
    bbox:list[float]|None=None
    user_instruction:str=''
    session_id:int|None=None

class FlashcardsIn(BaseModel):
    workspace_id:int
    topic:str
    document_ids:list[int]|None=None
    n:int=8

class FlashcardReviewIn(BaseModel):
    workspace_id:int
    score:float

@router.post('/documents/structure/rebuild')
def structure_rebuild(payload:StructureIn):
    try: return rebuild_structure(payload.workspace_id,payload.document_id)
    except Exception as exc: raise HTTPException(status_code=400,detail=str(exc))

@router.get('/workspaces/{workspace_id}/documents/{document_id}/sections')
def sections(workspace_id:int,document_id:int):
    return [dict(r) for r in list_sections(workspace_id,document_id)]

@router.get('/workspaces/{workspace_id}/documents/{document_id}/sections/{section_id}')
def section(workspace_id:int,document_id:int,section_id:int):
    data=section_context(workspace_id,document_id,section_id)
    if not data: raise HTTPException(status_code=404,detail='Sezione non trovata.')
    return data

@router.post('/documents/selection/map')
def selection_map(payload:SelectionIn):
    try: return map_selection(payload.workspace_id,payload.document_id,payload.page,payload.selected_text,payload.bbox)
    except Exception as exc: raise HTTPException(status_code=400,detail=str(exc))

@router.get('/workspaces/{workspace_id}/documents/{document_id}/render/{page}')
def render_page(workspace_id:int,document_id:int,page:int,scale:float=1.6):
    try:
        data=render_pdf_page(workspace_id,document_id,page,scale)
        headers={
            'X-Page-Count':str(data['page_count']),
            'X-Source-Width':str(data['source_width']),
            'X-Source-Height':str(data['source_height']),
            'X-Render-Width':str(data['render_width']),
            'X-Render-Height':str(data['render_height']),
        }
        return Response(content=data['png'],media_type='image/png',headers=headers)
    except Exception as exc: raise HTTPException(status_code=400,detail=str(exc))

@router.post('/documents/render-selection')
def render_selection(payload:RenderSelectionIn):
    try:
        source_bbox=normalize_render_bbox(payload.bbox,payload.render_width,payload.render_height,payload.source_width,payload.source_height)
        selected=blocks_in_bbox(payload.workspace_id,payload.document_id,payload.page,source_bbox)
        mapped=map_selection(payload.workspace_id,payload.document_id,payload.page,selected.get('text',''),source_bbox)
        return {'source_bbox':source_bbox,'selection':selected,'mapped':mapped}
    except Exception as exc: raise HTTPException(status_code=400,detail=str(exc))

@router.get('/workspaces/{workspace_id}/study')
def study_state(workspace_id:int,session_id:int|None=None,document_id:int|None=None,page:int|None=None):
    try: return study_workspace_state(workspace_id,session_id,document_id,page)
    except Exception as exc: raise HTTPException(status_code=400,detail=str(exc))

@router.post('/study/context-action')
def context_action(payload:ContextActionIn):
    try:
        mapped=selection_context(payload.workspace_id,payload.document_id,payload.page,payload.selected_text,payload.bbox)
        if payload.session_id is not None:
            set_reading_context(payload.session_id,payload.workspace_id,payload.document_id,payload.page,mapped.get('selected_text',''))
        return {
            'selection':mapped,
            'prompt':contextual_tutor_request(payload.action,mapped,payload.user_instruction),
            'action':payload.action,
        }
    except Exception as exc: raise HTTPException(status_code=400,detail=str(exc))

@router.post('/flashcards/generate')
def flashcards_generate(payload:FlashcardsIn):
    try: return generate_flashcards(payload.workspace_id,payload.topic,payload.document_ids,payload.n)
    except Exception as exc: raise HTTPException(status_code=400,detail=str(exc))

@router.get('/workspaces/{workspace_id}/flashcards')
def flashcards(workspace_id:int,limit:int=100):
    return list_flashcards(workspace_id,limit)

@router.post('/flashcards/{flashcard_id}/review')
def flashcard_review(flashcard_id:int,payload:FlashcardReviewIn):
    try: return review_flashcard(payload.workspace_id,flashcard_id,payload.score)
    except Exception as exc: raise HTTPException(status_code=400,detail=str(exc))

@router.delete('/workspaces/{workspace_id}/flashcards/{flashcard_id}')
def flashcard_archive(workspace_id:int,flashcard_id:int):
    archive_flashcard(workspace_id,flashcard_id); return {'ok':True}

@router.get('/workspaces/{workspace_id}/review-queue')
def queue(workspace_id:int,limit:int=20):
    return review_queue(workspace_id,limit)

@router.get('/workspaces/{workspace_id}/next-activity')
def next_activity(workspace_id:int,curriculum_id:int|None=None):
    return next_best_activity(workspace_id,curriculum_id)
