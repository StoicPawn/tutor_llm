# Offline sync protocol

Tutor LLM supports controlled offline synchronization for personal study artifacts: `note`, `annotation`, and `notebook_page`.

## Core rule: one canonical state

Offline sync is not a parallel storage system. Normal application CRUD and sync traffic converge on the same canonical tables.

- Creating/updating/deleting a note, PDF annotation or notebook page through the normal Tutor LLM API automatically updates its sync envelope and emits a change event.
- `POST /sync/push` materializes accepted offline changes into the real `notes`, `document_annotations` or `notebook_pages` tables before advancing the sync revision.
- A conflict is rejected before canonical data is modified.
- Deletes create tombstones in sync while removing the canonical object.

This means the Tutor, web client and iPad always see the same data after synchronization.

## Identity

Every client-created object gets a stable UUID generated on the client. The server keeps its integer `server_id` separately. This lets iPad/desktop create objects offline before a server ID exists.

Existing objects created normally on the server receive a UUID automatically when their first sync envelope is created.

## Revisions

Every synced object has a monotonically increasing `revision`.

A client push includes `base_revision`. The server applies the change only when `base_revision` equals the current server revision. Otherwise it returns `status=conflict` with the current server copy. Tutor LLM never silently overwrites a newer edit.

## Pull

`GET /sync/workspaces/{workspace_id}/changes?since=<seq>` returns an ordered change feed and a new cursor. Clients persist the cursor locally and request only later changes.

## Push

`POST /sync/push`

```json
{
  "workspace_id": 1,
  "entity_type": "note",
  "client_uuid": "...",
  "base_revision": 2,
  "payload": {"title":"...","content":"..."},
  "deleted": false,
  "server_id": 12
}
```

A successful push returns `status=applied`, the canonical `server_id` and the new revision.

For a new offline object use `base_revision: 0`; the server creates its canonical row and assigns `server_id`.

## Conflicts

When two devices edit revision 2 independently, the first accepted edit creates revision 3. The second receives a conflict instead of overwriting revision 3. The rejected payload is not written to canonical application data.

Conflict resolution is explicit through `POST /sync/resolve`. The client may present both versions, let the user choose, or create a merged payload. The resolution must target the current server revision.

## Deletes

Deletes are tombstones. They remain in the change feed so an offline client can remove its cached object rather than resurrecting it later. The canonical application row is deleted when the tombstone is accepted.

## Workspace safety

Relationships carried by offline payloads are revalidated on the server. A note or annotation cannot reference a document belonging to another workspace. Notebook pages can only target a notebook in the same workspace.

If two clients create a notebook page with the same requested position, Tutor LLM preserves both pages and allocates a free position instead of dropping one.

## Scope

The first protocol intentionally covers user-generated mutable artifacts only. Source documents, embeddings, generated curricula, mastery and model state remain server-authoritative. A client may cache them but should not independently merge them.

Creating an entirely new notebook offline is not part of this first protocol; pages can be edited or added offline to an already known notebook. Notebook-level offline creation can be added later with the same envelope model.

## Reference client

`studyforge.client.TutorClient` exposes:

- `workspace_manifest(...)`
- `sync_pull(...)`
- `sync_push(...)`
- `sync_resolve(...)`

The future iPad networking layer should implement the same semantics.

## iPad flow

1. Pair iPad and obtain its device token.
2. Download workspace manifest and change feed.
3. Cache desired PDFs and personal artifacts locally.
4. Work offline; assign UUIDs and retain each object's base revision.
5. On reconnection, pull server changes first.
6. Push local changes.
7. Accepted changes immediately become canonical Tutor LLM data.
8. Resolve any revision conflicts explicitly.
9. Store the latest change-feed cursor.

This protocol is deliberately conservative: preserving user work is more important than automatic last-write-wins behavior.
