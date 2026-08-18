# Devices and remote cache

Tutor LLM server distinguishes the **server administrator credential** from normal client credentials.

## Credentials

`API_TOKEN` is the server administration secret. It is used to provision or revoke clients and should not be copied to everyday devices.

Each device receives a separate random token such as:

```text
tllm_<prefix>_<secret>
```

Only the SHA-256 hash of the device token is stored in the Tutor database. The clear token is returned once at provisioning time and must be stored securely by the client (Keychain on Apple platforms, OS credential store on desktop).

A revoked token immediately stops authenticating without changing credentials for other devices.

## Provisioning flow

With an authenticated admin request:

```http
POST /admin/devices
Authorization: Bearer <API_TOKEN>
Content-Type: application/json

{"name":"Federico iPad","platform":"ipados"}
```

The response contains the device token once. The iPad stores that token locally and subsequently uses it for normal Tutor API calls.

Admin endpoints:

- `POST /admin/devices` — provision a device;
- `GET /admin/devices` — list active or revoked devices;
- `DELETE /admin/devices/{device_id}` — revoke one device.

Client endpoint:

- `GET /device/me` — verify the current authenticated identity.

## Offline/cache strategy

The first cache primitive is deliberately conservative. Tutor Server remains the source of truth. Clients may cache read-only workspace material and compare a compact server manifest:

```http
GET /sync/workspaces/{workspace_id}/manifest
```

The response contains a workspace `revision` plus per-entity counts/version markers. If the revision is unchanged, the client can continue using its local cache. If it changes, the client refreshes the affected resources.

This is **cache invalidation**, not yet arbitrary offline multi-master editing. That distinction prevents silent conflicts while the data model is still evolving.

## Planned offline writes

For iPad Pencil and notes, the next synchronization layer should use:

1. client-generated UUIDs for mutable user artifacts;
2. per-record revisions / `updated_at` values;
3. an append-only change feed from the server;
4. deterministic conflict rules for notes, annotations and notebook pages;
5. explicit conflict presentation where automatic merge is unsafe.

Authoritative source documents, embeddings, curriculum and mastery remain server-owned state. Personal artifacts such as ink and notes are the first candidates for controlled offline writes.

## Security boundary

A private VPN/tunnel remains recommended. Device tokens are an application-level layer, not a replacement for encrypted transport. The raw Ollama service must remain inaccessible to clients and the public Internet.
