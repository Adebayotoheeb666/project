# Synchronization protocol (contract)

Implemented in Phase 3. Phase 1 defines the contract so clients and the server stay aligned.

## Transport

HTTPS on the school LAN. No internet required. Batches: at most 20 operations and 500 KB.

## Handshake

1. Device presents `device_id` and a signed challenge.
2. School rejects revoked devices and invalid signatures.
3. Server returns current permission snapshot and last applied operation ids.

## Push

`POST /api/v1/sync/push`

Body: `{ "device_id", "operations": [ event, ... ] }`

School validates identity, signature, replay (operation id), permissions, and payload. Applied events receive receipts. Conflicts are stored, not discarded.

## Pull

`POST /api/v1/sync/pull`

Returns events after the device watermark, truncated to batch limits.

## Retry

Device retries at 1, 5, then 30 minutes with exponential backoff, then keeps the 30-minute interval until success.
