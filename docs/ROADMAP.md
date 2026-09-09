# Roadmap

## v0.1 — Foundation

Goal: stable application base.

Includes:
- monorepo
- FastAPI
- Vue 3
- SQLite
- SQLAlchemy
- Alembic
- local authentication
- collections
- collection roles (owner/admin/editor/viewer), sharing, and ownership transfer
- location tree
- generic title/edition/inventory core

Exit criteria:
- multiuser permissions work
- title/edition/copy separation works
- migrations are reliable
- core UI is usable

## v0.2 — Movies

Goal: useful manual movie collection management.

Includes:
- movie title metadata fields
- DVD/Blu-ray/UHD edition fields
- poster
- rip status
- movie catalogue
- filters
- detail page

Exit criteria:
- a movie collection can be managed without external metadata providers

## v0.3 — Barcode & Metadata

Goal: fast media intake.

Includes:
- barcode provider abstraction
- movie metadata provider abstraction
- provider cache
- candidate matching
- manual confirmation
- mobile scan workflow
- repeated scan mode with fixed target location

Exit criteria:
- a user can process a box of discs efficiently
- provider failure never blocks manual entry

## v0.4 — Locations & Printing

Goal: physical inventory utility.

Includes:
- location detail
- bulk move
- print inventory
- QR code labels
- QR deep link

Exit criteria:
- every box can have a printable inventory and QR label

## v0.5 — Loans

Goal: track who has an item.

Includes:
- lend
- return
- borrower
- due date
- loan history
- overdue view

## v0.6 — Board Games

Goal: second specialized collection type.

Includes:
- board game typed metadata
- edition metadata
- external provider abstraction
- board-game catalogue UI

## v0.7 — Bulk / Import / Export

Includes:
- CSV
- bulk moves
- bulk edit
- provider refresh tools
- duplicate review

## v0.8 — PWA & Scan Hardening

Includes:
- installable PWA
- camera UX
- scanner fallback hardening
- mobile performance
- resilient scanning

## v0.9 — Security & Release Hardening

Includes:
- ACL leak matrix
- session security review
- CSRF review
- migration matrix
- backup/restore validation
- optional PostgreSQL test target
- accessibility pass
- deployment polish

## v1.0 — Stable

Required:
- reliable upgrade path
- documented backup/restore
- production image
- minimal compose
- SQLite default
- optional PostgreSQL setup
- release smoke test
