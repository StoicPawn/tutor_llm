# Client Cache Store

Tutor LLM now includes a client-neutral offline cache engine in `studyforge/client_cache.py`.

The purpose is to model the behavior required by future iPadOS, desktop and mobile clients without putting product logic in Streamlit.

## Local client database

The cache keeps three classes of state:

- workspace sync cursor and manifest revision;
- cached personal artifacts (`note`, `annotation`, `notebook_page`) with UUID, server revision, dirty flag and conflict state;
- source-document download status and local path.

A client can create or edit personal artifacts while disconnected. These edits remain `dirty` until the next successful synchronization.

## Automatic synchronization

`ClientSyncEngine.sync(workspace_id)` performs:

```text
pull server changes
→ reconcile clean local cache
→ preserve dirty local edits
→ push dirty queue
→ retain conflicts explicitly
→ refresh workspace manifest
```

Remote changes never silently overwrite a dirty local object. Conflicts remain stored for explicit resolution.

## Offline documents

The server exposes the authenticated workspace-safe route:

`GET /workspaces/{workspace_id}/documents/{document_id}/source`

`ClientSyncEngine.cache_document(...)` downloads the original source file and records it as available offline. This does not duplicate embeddings or model state on the client.

## iPad mapping

The Swift client should mirror this model with a native local database and file storage:

- SQLite/Core Data/SwiftData equivalent for cache metadata;
- FileManager storage for downloaded PDFs;
- Keychain for the per-device token;
- background sync invoking the same pull/push protocol;
- explicit UI for conflicts rather than last-write-wins.

The Python implementation is a reference implementation of behavior, not a requirement that iPadOS run Python.
