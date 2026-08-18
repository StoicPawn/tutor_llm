# Offline sync protocol

Tutor LLM supports controlled offline synchronization for personal study artifacts: `note`, `annotation`, and `notebook_page`.

## Identity

Every client-created object gets a stable UUID generated on the client. The server keeps its legacy integer `server_id` separately. This lets iPad/desktop create objects offline before a server ID exists.

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

A successful push returns `status=applied` and the new revision.

## Conflicts

When two devices edit revision 2 independently, the first accepted edit creates revision 3. The second receives a conflict instead of overwriting revision 3.

Conflict resolution is explicit through `POST /sync/resolve`. The client may present both versions, let the user choose, or create a merged payload. The resolution must target the current server revision.

## Deletes

Deletes are tombstones. They remain in the change feed so an offline client can remove its cached object rather than resurrecting it later.

## Scope

The first protocol intentionally covers user-generated mutable artifacts only. Source documents, embeddings, generated curricula, mastery and model state remain server-authoritative. A client may cache them but should not independently merge them.

## iPad flow

1. Pair iPad and obtain its device token.
2. Download workspace manifest and change feed.
3. Cache desired PDFs and personal artifacts locally.
4. Work offline; assign UUIDs and retain each object's base revision.
5. On reconnection, pull server changes first.
6. Push local changes.
7. Resolve any revision conflicts explicitly.
8. Store the latest change-feed cursor.

This protocol is deliberately conservative: preserving user work is more important than automatic last-write-wins behavior.
