# Architecture

## Goals

- simple self-hosted deployment
- clean separation of frontend, API, domain, persistence, and external providers
- SQLite as first-class default
- PostgreSQL portability
- no premature distributed architecture

## Repository layout

Target:

```text
backend/
├── alembic/
├── app/
│   ├── api/
│   ├── auth/
│   ├── collections/
│   ├── db/
│   ├── inventory/
│   ├── locations/
│   ├── loans/
│   ├── metadata/
│   │   └── providers/
│   ├── movies/
│   ├── boardgames/
│   ├── users/
│   ├── config.py
│   └── main.py
└── tests/

frontend/
├── src/
│   ├── api/
│   ├── assets/
│   ├── components/
│   ├── composables/
│   ├── features/
│   ├── router/
│   ├── stores/
│   ├── styles/
│   └── views/
└── tests/

docs/
assets/
```

Only create domain directories when their milestone begins. Empty architecture theater is not required.

## Backend layers

```text
HTTP route
   |
   v
service / domain operation
   |
   +---- authorization policy
   |
   +---- persistence repository / SQLAlchemy session
   |
   +---- provider interface
```

Rules:
- routes validate transport concerns
- services implement use cases
- persistence handles query details
- providers isolate external systems

## Instance administration and collection ACL

Instance administration is limited to local account management. It is not a bypass for collection
authorization: every collection route resolves the caller's owner or membership role separately.
Collection ownership is stored only in `collections.owner_user_id`; `collection_members` contains
only non-owner `admin`, `editor`, and `viewer` rows. On an owner-initiated transfer, the target
becomes the sole owner and the former owner remains an `admin` member.

## Location tree

T05 implements `locations` as a collection-scoped self-referencing tree. The hierarchy service
owns parent-scope and cycle validation; the API reuses `CollectionCapability.VIEW` for reads and
`CollectionCapability.EDIT_CONTENT` for mutations. Consequently Owner, Admin, and Editor can
manage locations, while Viewer is read-only and Instance Admin is never a collection ACL bypass.
The API builds a complete tree from one collection-scoped location query; the frontend reloads it
after mutations instead of maintaining a parallel client-side hierarchy algorithm.

## Frontend layers

```text
View
 |
 +-- feature component
 |
 +-- composable/store
 |
 +-- typed API client
```

Do not make Pinia a dumping ground for all state.

Prefer URL state for catalogue filters that users should be able to bookmark.

## Deployment direction

Development:
- frontend dev server
- backend dev server
- local SQLite file

Production target:
- one application image by default
- built Vue assets served with the application or a minimal co-located static layer
- `/app/data` persistent volume
- SQLite database under the data directory

PostgreSQL:
- optional via `DATABASE_URL`
- not required for the default compose

## Background work

Do not add Redis/Celery initially.

Short metadata lookups may run in request flow with:
- timeouts
- cancellation
- cached results

Introduce a job system only when measured behavior requires it.

## Artwork

Provider artwork should not be treated as opaque forever-hot external URLs.

Preferred later architecture:
- provider metadata keeps original URL/source
- selected artwork may be cached locally
- DB stores reference/metadata
- files live under persistent data storage

Implementation belongs to the relevant metadata milestone.
