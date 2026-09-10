# Stashive — Codex Task Queue

Jede Aufgabe ist als eigenständige Codex-Arbeitseinheit gedacht.

## T01 — Repository Foundation

Milestone: v0.1

Use `CODEX_BOOTSTRAP_PROMPT.md`.

Acceptance:
- backend starts
- frontend starts
- `/api/health` works
- SQLite configuration exists
- migrations can run
- lint/test/typecheck/build are documented and green

## T02 — Database Core

Milestone: v0.1

Implement the first durable generic tables only:
- users shell if required for foreign keys, otherwise defer to T03
- structural collections without ownership or ACLs
- catalog entries
- editions
- inventory items
- identifiers

Keep specialized movie data out until T07.

Acceptance:
- models
- schemas
- migration
- CRUD service tests
- SQLite upgrade/downgrade test
- no vendor-specific DB types

## T03 — Local Authentication

Milestone: v0.1

Implement:
- local user
- secure password hashing
- login
- logout
- current-session endpoint
- secure same-origin cookie session
- session expiration
- route guards in frontend
- no public registration endpoint/page after setup
- one-time setup-token flow when no user exists
- plaintext setup token exposed only to the operator through server/container logs
- only token hash persisted
- first user becomes instance administrator
- bootstrap endpoint disabled after first user exists
- administrator-created user accounts after bootstrap

Acceptance:
- no long-lived auth token in localStorage
- password hashes never exposed
- unauthenticated API tests
- login/logout E2E

## T04 — Collections & ACL

Milestone: v0.1

Implement:
- collections
- collection membership
- owner/admin/editor/viewer
- collection list
- create/edit collection
- invite/add existing local user
- member management

Acceptance:
- server-side authorization matrix tests
- inaccessible collection resources do not leak
- owner-only destructive actions tested

## T05 — Location Tree

Milestone: v0.1

Implement collection-scoped hierarchical locations.

Fields:
- id
- collection_id
- parent_id
- name
- type
- optional description

Types:
- room
- cabinet
- shelf
- box
- drawer
- other

Acceptance:
- create/edit/reparent/delete rules
- cycle prevention
- tree endpoint
- permissions
- basic Vue tree UI

## T06 — Generic Inventory Core

Milestone: v0.1

Implement:
- catalog entry
- edition
- physical inventory copy
- identifiers
- location assignment
- basic condition/notes
- duplicate copies allowed

Acceptance:
- title/edition/copy separation proven by tests
- multiple copies of same edition supported
- multiple editions of same title supported
- move item endpoint
- list/filter by location

Status: complete. T06 provides collection-scoped catalog entries, editions, identifiers, physical copies, and location assignment/filtering.

## T06e — Preview Container Packaging

Milestone: after T06, before T07

Implement a preview-ready multi-stage Docker image that builds the Vue frontend, persists `/app/data` including SQLite, runs Alembic migrations at startup, exposes `/api/health`, and includes minimal Docker Compose, container smoke coverage, and a GitHub Actions build/push workflow for `ghcr.io/ledomme/stashive`.

## T07 — Movie Domain

Milestone: v0.2

Add typed movie extension tables.

Movie title:
- title
- original title
- year
- summary
- runtime
- external IDs
- poster reference

Movie edition:
- medium
- edition name
- region
- distributor/publisher
- release date
- disc count

Inventory movie state:
- rip status

Acceptance:
- no EAV
- movie filters
- rip status enum implemented portably
- API tests

## T08 — Movie Catalogue UI

Milestone: v0.2

Implement:
- poster grid
- list mode optional if cheap
- filters
- detail view
- edition view
- copy/location state
- rip state indicator

Filters:
- medium
- year
- location
- rip state
- loan state later

Acceptance:
- responsive desktop/mobile
- Stashive design tokens
- accessible controls
- stable URL/query state for filters

## T09 — Metadata Provider Layer

Milestone: v0.3

Implement provider contracts.

At minimum:
- `BarcodeProvider`
- `MovieMetadataProvider`

Initial barcode provider:
- UPCitemdb free Explorer

Optional second free provider:
- UPC Database

Add:
- provider cache
- normalized result DTOs
- timeout/error handling
- provider-specific code isolated from domain services

Acceptance:
- mocked provider tests
- cached lookup tests
- free-tier throttling handled without breaking manual intake
- repeated barcode lookup hits local cache instead of provider
- no paid barcode provider required
- manual fields not silently overwritten
- UI can show candidates before applying

## T10 — Barcode Intake

Milestone: v0.3

Implement mobile-first scan workflow.

Requirements:
- manual barcode entry always available
- camera scanning abstraction
- native browser API when available
- fallback scanner implementation
- fixed target location for batch scanning
- lookup -> candidate -> confirmation -> save -> next scan

Acceptance:
- duplicate barcode behavior defined
- provider failure allows manual entry
- E2E for successful intake
- E2E for no-match/manual fallback

## T11 — Location Print & QR

Milestone: v0.4

Implement:
- print-friendly location inventory
- item count
- title/edition/media columns
- printable QR label for location
- QR resolves to Stashive location page

Prefer print CSS before introducing a PDF renderer.

Acceptance:
- usable A4 print
- clean print-only layout
- QR route tested
- no unnecessary application chrome when printing

## T12 — Loans

Milestone: v0.5

Implement historical loans, not a boolean flag.

Fields:
- inventory item
- borrower name
- optional internal user later
- loaned at
- expected return at
- returned at
- notes

Acceptance:
- active loan is derived from open loan record
- return closes record
- history remains visible
- loan permissions tested
- overdue filter

## T13 — Board Game Domain

Milestone: v0.6

Add typed board game extension tables and provider abstraction.

Do not alter the generic inventory model to fit board games.

## T14 — Import / Export / Bulk

Milestone: v0.7

Implement:
- CSV export
- safe CSV import
- bulk move
- bulk metadata actions
- bulk rip-state actions where appropriate

## T15 — PWA / Scan Hardening

Milestone: v0.8

Implement:
- installable PWA
- camera permission UX
- offline-friendly shell where useful
- scan retry behavior
- mobile performance work

Do not make inventory writes offline unless explicitly designed.

## T16 — Security / Permissions / Release Polish

Milestone: v0.9

Perform:
- ACL leak matrix
- session hardening
- CSRF review
- dependency review
- migration upgrade testing
- SQLite backup/recovery test
- optional PostgreSQL CI
- accessibility pass
- release checklist

## T17 — 1.0 Release

Milestone: v1.0

Required:
- documented backup/restore
- stable migrations
- upgrade notes
- production Docker image
- minimal compose
- SQLite default
- optional PostgreSQL documentation
- release smoke test
