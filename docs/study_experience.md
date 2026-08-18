# Unified Study Experience

Tutor LLM treats studying as a persistent session, not a sequence of unrelated prompts.

## Core layout

The reference client uses three coordinated areas:

```text
Document / PDF          Tutor + Notes
------------------      ------------------------
current page            contextual conversation
selected passage   ->   explain / why / deepen
page provenance         examples / prerequisites
                        personal notes
                        next best activity
```

The Streamlit reference implementation is `pages/01_Studio.py`. It is intentionally a client of reusable logic in `studyforge/study_view.py`; product logic must not migrate into Streamlit-specific code.

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

The client maps the visual selection back to document/page/chunks and creates a contextual tutor request with provenance. On iPad, the selected text and bounding box will come directly from the PDF viewer instead of a text field.

## Notes

Notes remain user artifacts, separate from authoritative library sources. They can be linked to document and page. The future iPad client will extend the same model with Pencil drawings/handwriting and attachments rather than creating a separate note system.

## API contract

Relevant endpoints include:

- `GET /workspaces/{workspace_id}/study`
- `POST /study/context-action`
- `POST /documents/selection/map`
- page and section endpoints
- Tutor endpoints
- notes and Study Session endpoints

Server mode protects these routes with the same Bearer token policy as the rest of Tutor LLM.

## Design rule

Desktop local mode and private-server mode must expose the same study semantics. A client may change presentation and local cache behavior, but it must not fork curriculum, mastery, RAG, provenance or tutor logic.
