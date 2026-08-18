from __future__ import annotations
import os, tempfile
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from .db import list_documents, save_lesson
from .pipeline import ingest_file
from .teacher import answer_question, build_lesson, summarize, deepen, build_exercises, build_reasoning
from .assessment import grade_answer
from .workspaces import create_workspace, list_workspaces, get_workspace, ensure_default_workspace
from .sessions import start_session, update_session, get_session, end_session
from .notes import create_note, list_notes

app = FastAPI(title="Tutor LLM API", version="0.4.0")


class WorkspaceIn(BaseModel):
    name: str
    description: str = ""
    goal: str = ""


class TutorRequest(BaseModel):
    workspace_id: int
    topic: str
    document_ids: list[int] | None = None
    epistemic_mode: str = "Grounded"
    lesson_mode: str = "Approfondita"


class AssessmentIn(BaseModel):
    workspace_id: int
    topic: str
    question: str
    answer: str
    document_ids: list[int] | None = None


class SessionIn(BaseModel):
    workspace_id: int
    learning_goal: str = ""


class SessionContextIn(BaseModel):
    workspace_id: int
    current_document_id: int | None = None
    current_page: int | None = None
    selected_text: str | None = None
    current_concept: str | None = None
    learning_goal: str | None = None
    state: dict | None = None


class NoteIn(BaseModel):
    workspace_id: int
    title: str
    content: str = ""
    kind: str = "text"
    document_id: int | None = None
    page: int | None = None


@app.on_event("startup")
def startup():
    ensure_default_workspace()


@app.get("/health")
def health():
    return {"ok": True, "service": "tutor-llm", "api_version": "0.4.0"}


@app.get("/workspaces")
def workspaces():
    return [dict(r) for r in list_workspaces()]


@app.post("/workspaces")
def new_workspace(payload: WorkspaceIn):
    try:
        wid = create_workspace(payload.name, payload.description, payload.goal)
        return dict(get_workspace(wid))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/workspaces/{workspace_id}/documents")
def documents(workspace_id: int):
    return [dict(r) for r in list_documents(workspace_id)]


@app.post("/workspaces/{workspace_id}/documents")
async def upload_document(workspace_id: int, file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename or "upload")[1]
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        with open(path, "wb") as out:
            out.write(await file.read())
        return ingest_file(workspace_id, path, file.filename)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


@app.post("/tutor/ask")
def ask(payload: TutorRequest):
    try:
        answer, sources = answer_question(payload.workspace_id, payload.topic, payload.document_ids, payload.epistemic_mode)
        return {"content": answer, "sources": sources}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/tutor/lesson")
def lesson(payload: TutorRequest):
    try:
        content, sources = build_lesson(payload.workspace_id, payload.topic, payload.lesson_mode, payload.document_ids, payload.epistemic_mode)
        lesson_id = save_lesson(payload.workspace_id, payload.topic, payload.lesson_mode, content, sources, payload.epistemic_mode)
        return {"lesson_id": lesson_id, "content": content, "sources": sources}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/tutor/summary")
def summary(payload: TutorRequest):
    content, sources = summarize(payload.workspace_id, payload.topic, payload.document_ids, payload.epistemic_mode)
    return {"content": content, "sources": sources}


@app.post("/tutor/deepen")
def deepen_topic(payload: TutorRequest):
    content, sources = deepen(payload.workspace_id, payload.topic, payload.document_ids, payload.epistemic_mode)
    return {"content": content, "sources": sources}


@app.post("/tutor/exercises")
def exercises(payload: TutorRequest):
    content, sources = build_exercises(payload.workspace_id, payload.topic, payload.document_ids, epistemic_mode=payload.epistemic_mode)
    return {"content": content, "sources": sources}


@app.post("/tutor/reasoning")
def reasoning(payload: TutorRequest):
    content, sources = build_reasoning(payload.workspace_id, payload.topic, payload.document_ids, payload.epistemic_mode)
    return {"content": content, "sources": sources}


@app.post("/assessment/grade")
def assessment(payload: AssessmentIn):
    try:
        return grade_answer(payload.workspace_id, payload.topic, payload.question, payload.answer, payload.document_ids)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/sessions")
def new_session(payload: SessionIn):
    sid = start_session(payload.workspace_id, payload.learning_goal)
    return dict(get_session(sid))


@app.patch("/sessions/{session_id}")
def patch_session(session_id: int, payload: SessionContextIn):
    update_session(session_id, payload.workspace_id, current_document_id=payload.current_document_id,
                   current_page=payload.current_page, selected_text=payload.selected_text,
                   current_concept=payload.current_concept, learning_goal=payload.learning_goal, state=payload.state)
    return dict(get_session(session_id))


@app.delete("/sessions/{session_id}")
def close_session(session_id: int, workspace_id: int):
    end_session(session_id, workspace_id)
    return {"ok": True}


@app.get("/workspaces/{workspace_id}/notes")
def notes(workspace_id: int):
    return [dict(r) for r in list_notes(workspace_id)]


@app.post("/notes")
def new_note(payload: NoteIn):
    note_id = create_note(payload.workspace_id, payload.title, payload.content, kind=payload.kind,
                          document_id=payload.document_id, page=payload.page)
    return {"id": note_id}
