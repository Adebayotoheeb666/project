# LSIA Architecture

Local-First School Intelligence System. The school computer is the source of truth. Teacher phones work offline and sync over the school LAN.

## Components

| Component | Stack | Role |
|-----------|--------|------|
| School server | Python, FastAPI, PostgreSQL | Authority, API, events, approvals, reports |
| Admin dashboard | React (served by the school server) | Administrators and office staff |
| Teacher app | Kotlin, Compose, Room | Offline work on Android |

## Layers

- **Presentation:** FastAPI routers, React screens, later Android UI.
- **Application:** use-case services (students, teachers, auth, events, sync).
- **Domain:** identities, permissions, academic rules, conflict policy.
- **Infrastructure:** SQLAlchemy, Ed25519 keys, JWT sessions, local files.

## Trust model

1. School generates an Ed25519 identity on first start.
2. Teachers enroll devices; device public keys are stored on the school computer.
3. The school computer enforces every permission. Clients never decide authorization.
4. Mutations emit signed events. History is append-only.

## Phase 1 scope

Accounts, sessions, classes, subjects, students, teachers, audit log, school identity, and the admin dashboard for those functions.

## Phase 2 scope

Teacher Android application, Room database, offline student CRUD, local signed operation queue, device enrollment (QR), and class-scoped directory access. LAN push sync is Phase 3.
