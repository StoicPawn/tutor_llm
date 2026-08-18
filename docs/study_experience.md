# Unified Study Experience

Tutor LLM treats studying as a persistent session, not a sequence of unrelated prompts.

## Core layout

The reference client uses coordinated areas:

```text
Document / PDF          Tutor + Notes
------------------      ------------------------
rendered current page   contextual conversation
visual selection   ->   explain / why / deepen
page provenance         examples / prerequisites
                        personal notes
                        next best activity
```

The Streamlit reference implementation is `pages/01_Studio.py`. It is intentionally a client of reusable logic in `studyforge/study_view.py` and `studyforge/pdf_viewer.py`; product logic must not migrate into Streamlit-specific code.

## Rendered PDF model

Native PDFs are rendered from the source file with PyMuPDF. Tutor LLM keeps two coordinate spaces explicit:

- **render coordinates** — pixels in the client image/view;
- **source coordinates** — PDF points used by the stored layout blocks and provenance engine.

`studyforge.pdf_viewer.normalize_render_bbox` converts a client rectangle back to source coordinates. This prevents zoom, Retina scaling or client layout from changing the semantic selection.

The API exposes:

- `GET /workspaces/{workspace_id}/documents/{document_id}/render/{page}` — PNG page plus source/render dimensions in response headers;
- `POST /documents/render-selection` — convert a render-space rectangle to source coordinates, recover intersecting blocks and map the result to chunks/citations.

The current Streamlit prototype renders the real PDF but selects layout blocks explicitly instead of pretending to provide a reliable drag overlay. The future iPad client will send the native visual-selection rectangle directly to the same API contract.

## Study Session

A Study Session persists the operational context:

- workspace
- document
- page
- selected text
- current concept
- learning goal
- client state

This state is shared by desktop/web clients and is the contract for the future iPadOS client.

## Context actions

A selected passage supports standardized actions:

- Explain
- Why?
- Deepen
- Example
- Exercise
- Prerequisites

The client maps the visual selection back to document/page/chunks and creates a contextual tutor request with provenance.

## Notes

Notes remain user artifacts, separate from authoritative library sources. They can be linked to document and page. The future iPad client will extend the same model with Pencil drawings/handwriting and attachments rather than creating a separate note system.

## API contract

Relevant endpoints include:

- `GET /workspaces/{workspace_id}/study`
- `POST /study/context-action`
- `POST /documents/selection/map`
- `GET /workspaces/{workspace_id}/documents/{document_id}/render/{page}`
- `POST /documents/render-selection`
- page and section endpoints
- Tutor endpoints
- notes and Study Session endpoints

Server mode protects these routes with the same Bearer token policy as the rest of Tutor LLM.

## Design rule

Desktop local mode and private-server mode must expose the same study semantics. A client may change presentation and local cache behavior, but it must not fork curriculum, mastery, RAG, provenance or tutor logic.
