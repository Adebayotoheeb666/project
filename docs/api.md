# API contract (Phase 1–2)

Base path: `/api/v1`. JSON. Bearer JWT after login.

## Auth

- `GET /auth/bootstrap-status` — `{ "needs_bootstrap": true }`
- `POST /auth/bootstrap` — first administrator `{ name, password, school_name }`
- `POST /auth/login` — `{ username, password }` → `{ token, teacher }`
- `GET /auth/me`
- `GET /school` — school id, name, public key

## Teachers

- `GET /teachers`
- `POST /teachers`
- `GET /teachers/{id}`
- `PATCH /teachers/{id}`
- `POST /teachers/{id}/revoke`
- `POST /teachers/{id}/password`

## Classes, subjects, students

Standard list/create/get/patch/delete.

Student list query: `q`, `class_id`.

## Directory (scoped)

Teachers only receive classes and students assigned to them.

- `GET /me/directory` — snapshot for phone seeding

## Devices

- `POST /devices/enrollment-tickets` — `{ "base_url" }` → QR payload (admin)
- `GET /devices/enrollment-tickets/{id}` — public inspect of a live ticket
- `GET /devices/enrollment-tickets/{id}/qr.png`
- `POST /devices/enroll` — teacher password + device public key
- `GET /devices`
- `POST /devices/{id}/revoke`

## Audit

- `GET /audit?limit=50`
