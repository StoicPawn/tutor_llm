# Study notebooks and canvas

Tutor LLM treats a notebook as a personal study artifact inside one workspace. It is separate from authoritative library sources and therefore is not automatically injected into RAG.

## Data model

```text
StudyNotebook
├── workspace_id
├── title / description
├── optional document/page link
├── optional concept link
└── pages[]
    ├── width / height
    ├── background: blank | ruled | grid | dot
    └── layers[]
        ├── text
        ├── ink
        ├── shape
        ├── image_ref
        └── source_ref
```

A notebook can therefore be free-standing, tied to a whole subject, or linked to the exact document/page/concept being studied.

## Pencil-ready ink

Ink is stored as vector data rather than raster screenshots. A client can send one or more strokes, for example:

```json
{
  "kind": "ink",
  "strokes": [
    {
      "tool": "pen",
      "width": 2.0,
      "points": [[120.0, 200.0, 0.42], [121.5, 201.2, 0.57]]
    }
  ]
}
```

The third value is pressure. Future clients may add tilt/timestamps without changing the notebook concept. Coordinates are canvas-local, independent from PDF source coordinates.

## Source references

A notebook page may contain `source_ref` layers pointing to a document/page and an optional excerpt. They are references, not copies of authority: the Tutor should re-resolve the source through the workspace when factual grounding matters.

## API

- `GET /workspaces/{workspace_id}/notebooks`
- `POST /notebooks`
- `GET /workspaces/{workspace_id}/notebooks/{notebook_id}`
- `POST /notebooks/{notebook_id}/pages`
- `PATCH /notebooks/{notebook_id}/pages/{page_id}`
- `DELETE /workspaces/{workspace_id}/notebooks/{notebook_id}`

Server mode protects the same endpoints with the application Bearer token.

## Reference web client

`pages/02_Quaderno.py` provides a lightweight reference UI for creating notebooks, pages, backgrounds, text and source links. It deliberately does not fake Apple Pencil drawing in Streamlit. The native iPad client will render and edit the same vector layers directly.

## Design rule

Notebook content is user-authored. It may later be explicitly promoted into searchable notes or used as tutor context when requested, but it must never silently become an authoritative book/source.
