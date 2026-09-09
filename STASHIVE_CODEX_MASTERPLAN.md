# Stashive — Codex Masterplan

Structured repository-ready source is included in the starter ZIP.



---

# FILE: `README.md`

# Stashive

**Self-hosted collection and inventory management for physical collections.**

Stashive is a web application for cataloguing physical collections, tracking where items are stored, sharing collections with multiple users, recording loans, and enriching items with external metadata.

The first-class use case is DVD / Blu-ray / UHD Blu-ray management. Board games follow as the second specialized collection type. The core must remain generic enough to support additional physical collections later without turning the database into an EAV system.

## Product principles

- Self-hosted first
- SQLite first, PostgreSQL-ready
- Simple single-container deployment as the default target
- Strong separation between a title/work, an edition/product, and a physical owned copy
- Collection-level sharing and permissions
- First instance administrator created through a one-time setup token
- No public self-registration after setup
- Hierarchical locations such as `House > Basement > Shelf > Box`
- Fast mobile barcode capture
- Provider abstraction for barcode and metadata services
- Manual data always wins over provider refreshes
- No hard dependency on a specific metadata provider
- Good print output for box inventories and QR labels
- Vue-based UI with a distinct Stashive identity

## Technology direction

### Frontend
- Vue 3
- TypeScript
- Vite
- Vue Router
- Pinia
- CSS custom properties for the Stashive design system
- Vitest
- Playwright

### Backend
- Python
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- pytest
- Ruff

### Database
Default:
- SQLite
- WAL mode
- foreign keys enabled
- busy timeout configured

Optional later:
- PostgreSQL via the same SQLAlchemy model layer

## Start here

1. Read [`AGENTS.md`](AGENTS.md).
2. Read [`PROJECT_PLAN.md`](PROJECT_PLAN.md).
3. Read [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
4. Read [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md).
5. Start Codex with [`CODEX_BOOTSTRAP_PROMPT.md`](CODEX_BOOTSTRAP_PROMPT.md).
6. Do not implement later milestones while bootstrapping the repository.

The current design decisions and open questions are tracked in [`docs/DECISIONS.md`](docs/DECISIONS.md).

## License

Stashive is licensed under **AGPL-3.0-only**.


---

# FILE: `AGENTS.md`

# AGENTS.md — Stashive

This file contains mandatory repository instructions for Codex and other coding agents.

## 1. Mission

Build **Stashive**, a self-hosted web application for managing physical collections.

The first supported specialized collection is physical video media:
- DVD
- Blu-ray
- UHD Blu-ray

Board games are the next planned specialized collection.

Stashive must support:
- multi-user collection sharing
- hierarchical storage locations
- owned physical copies
- loan tracking
- barcode-based intake
- external metadata enrichment
- printable box/location inventories
- media-specific rip state

Read the project documentation before changing architecture.

## 2. Mandatory reading order

Before any non-trivial task, read:

1. `AGENTS.md`
2. `PROJECT_PLAN.md`
3. `docs/ARCHITECTURE.md`
4. `docs/DATA_MODEL.md`
5. `docs/DECISIONS.md`
6. the task-specific document, if one exists

Do not invent architecture that contradicts these documents.

## 3. Scope discipline

Work only on the requested task.

### Project license

Stashive is licensed **AGPL-3.0-only**.

When project/package metadata is created:
- use SPDX identifier `AGPL-3.0-only`
- preserve the license in distributions
- add the canonical GNU AGPL v3 license text as `LICENSE`
- do not silently change to `AGPL-3.0-or-later`


Do not:
- implement future roadmap milestones opportunistically
- add frameworks "just in case"
- introduce Redis before a concrete need exists
- introduce PostgreSQL-only features
- create a generic EAV property system
- silently redesign permissions
- rewrite unrelated code
- clean or reset unrelated working-tree changes
- remove existing behavior because a cleaner design is possible

Prefer the smallest coherent change that satisfies the acceptance criteria.

## 4. Repository safety

Assume the working tree may contain user changes.

Never use destructive Git commands on unrelated work:
- no `git reset --hard`
- no `git clean -fd`
- no forced checkout of unrelated files
- no force-push unless explicitly requested

Before editing:
- inspect `git status`
- identify the active branch
- note unrelated dirty files
- leave unrelated dirty files untouched

For larger tasks, prefer an isolated feature branch. If the user is using worktrees, keep the task inside the dedicated worktree and never modify another dirty checkout.

Recommended branch pattern:

- `feature/<milestone>-<slug>`
- `fix/<slug>`
- `chore/<slug>`
- `release/<version>`

Do not merge, tag, release, or push to `main` unless explicitly asked.

## 5. Architecture rules

### 5.1 Monorepo

Use:

```text
backend/
frontend/
docs/
assets/
```

Do not split the project into multiple repositories.

### 5.2 Frontend

Use:
- Vue 3
- TypeScript
- Vite
- Vue Router
- Pinia

Keep domain logic out of presentation components.

Prefer:
- typed API clients
- composables for reusable UI behavior
- small components
- CSS custom properties for design tokens

Do not add a heavy UI framework without an explicit architectural decision.

### 5.3 Backend

Use:
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic

Keep layers separate:

```text
api -> service/domain -> persistence/provider
```

Route handlers must not contain substantial business logic.

### 5.4 Database portability

SQLite is the default database.

The schema must remain PostgreSQL-compatible.

Do not use:
- PostgreSQL ARRAY types
- PostgreSQL ENUM types
- JSONB-only logic
- GIN-only indexing assumptions
- SQLite-only raw SQL in application logic

Use SQLAlchemy abstractions where practical.

If JSON is used, treat it as portable JSON and do not depend on vendor-specific query features for core functionality.

### 5.5 SQLite setup

Application-created SQLite connections must enable:
- foreign keys
- WAL mode where supported
- a reasonable busy timeout

The database location must be configurable through environment configuration.

### 5.6 Migrations

Every persistent schema change requires an Alembic migration.

For each migration:
- upgrade must work on an existing database
- downgrade should be provided when reasonably safe
- do not manually edit production databases
- migration tests must cover SQLite
- later CI may additionally cover PostgreSQL

### 5.7 Domain model

Never collapse these concepts:

```text
Title / Work
Edition / Product
Owned physical inventory item
```

Example:

```text
Alien (1979)
  -> German Blu-ray edition, EAN ...
      -> physical copy owned by the user
```

A user may own multiple editions and multiple copies.

### 5.8 Specialized domain extensions

Keep a generic inventory core, but use typed extension tables for specialized domains.

Preferred direction:

```text
catalog_entries
editions
inventory_items

movie_titles
movie_editions
movie_inventory_state

boardgame_titles
boardgame_editions
```

Do not replace typed extension tables with a generic key/value property store.

### 5.9 Metadata providers

All external metadata access must go through provider interfaces.

Barcode lookup cost rule:
- the supported default workflow must not require a paid barcode API
- implement UPCitemdb free Explorer as the first barcode provider
- UPC Database may be added as a second free adapter
- cache successful barcode lookups locally
- gracefully handle free-tier throttling
- manual entry must remain fully functional
- never make a paid provider mandatory


Examples:
- barcode/product provider
- movie metadata provider
- board game metadata provider

No UI or domain service may depend directly on a specific provider implementation.

Provider responses must be cacheable.

Manual user edits must never be silently overwritten by provider refreshes.

### 5.10 Authentication

Prefer same-origin, secure cookie-based authentication.

Registration policy:
- there is no public/self-service registration after first-run setup
- when the database contains no users, Stashive uses a one-time setup-token flow
- generate a cryptographically strong setup token and show the plaintext token only to the operator via server/container logs
- persist only a hash of the token
- the setup UI accepts the token plus first-user credentials
- the first user becomes an instance administrator
- invalidate the token immediately after successful account creation
- disable the bootstrap endpoint permanently once any user exists
- avoid passing the setup token in URLs
- after bootstrap, only instance administrators create users
- do not add a public `/register` flow without explicit owner approval


Do not store long-lived bearer tokens in browser local storage.

Authorization must be enforced server-side on every protected resource. Frontend checks are convenience only.

### 5.11 Collection permissions

Initial collection roles:

- `owner`
- `admin`
- `editor`
- `viewer`

Expected semantics:

| Capability | Owner | Admin | Editor | Viewer |
|---|---:|---:|---:|---:|
| View collection | yes | yes | yes | yes |
| Add/edit items | yes | yes | yes | no |
| Move items | yes | yes | yes | no |
| Manage loans | yes | yes | yes | no |
| Manage collection members | yes | yes | no | no |
| Delete collection | yes | no | no | no |
| Transfer ownership | yes | no | no | no |

Do not change these semantics without updating documentation and tests.

## 6. Coding standards

### Python

- typed function signatures for application code
- avoid `Any` unless justified
- use Ruff formatting/linting
- small focused services
- explicit transaction boundaries
- no swallowed exceptions
- errors returned to API clients must be safe and useful

### TypeScript / Vue

- strict TypeScript
- avoid `any`
- prefer typed props/emits
- no business rules duplicated across multiple components
- API response types must be explicit
- accessibility is required for interactive controls

## 7. Testing requirements

Every feature must have appropriate tests.

Backend:
- unit tests for domain/service logic
- API tests for permissions and validation
- migration coverage for schema changes

Frontend:
- component/unit tests for logic-heavy UI
- `vue-tsc` / typecheck
- E2E for critical user flows

Critical E2E flows eventually include:
- login
- create collection
- share collection
- create location
- add media item
- barcode intake
- move item
- lend item
- return item
- print location inventory

Do not claim success without running relevant checks.

## 8. Required validation before finishing a task

Run the checks relevant to the touched code.

Expected baseline once scaffolding exists:

```bash
# backend
ruff check backend
pytest

# frontend
npm run typecheck
npm run test
npm run build
```

Run targeted Playwright tests when a user-facing flow changes.

If a check cannot run, state exactly why.

## 9. API conventions

- API prefix: `/api`
- JSON request/response bodies
- stable resource identifiers
- pagination for potentially unbounded lists
- validation errors must be actionable
- permission-denied and not-found behavior must not leak inaccessible resources

Prefer:
- `404` for resources the caller must not learn exist
- `403` only where existence is already legitimately known

Keep API details in `docs/API_CONVENTIONS.md`.

## 10. UX rules

Stashive is inventory software, not an admin database viewer.

Optimize common workflows:
- scan fast
- assign a location fast
- move many items fast
- see loan state immediately
- filter by format, location, rip status, and loan state
- print a useful inventory without layout configuration

Mobile barcode intake is a first-class workflow.

Destructive actions require clear confirmation.

## 11. Brand rules

Use the Stashive palette from `docs/BRAND.md`.

Primary tokens:
- Emerald `#065F46`
- Aqua Glow `#10E6A1`
- Mint `#6FF3C7`
- Ink `#0F172A`
- Cloud `#F6FBF9`

The glow is an accent, not a background effect on every surface.

Use the supplied assets in `assets/` as visual reference.

Do not regenerate or reinterpret the logo without an explicit design task.

## 12. Documentation

Update documentation in the same change when:
- architecture changes
- a data model changes
- a public API contract changes
- a permission rule changes
- deployment configuration changes
- a new environment variable is introduced

## 13. Commits and task summaries

If asked to commit, use concise conventional commits, for example:

```text
feat: add collection membership roles
fix: enforce collection scope on loans
chore: scaffold frontend and backend
docs: document barcode provider contract
```

At the end of a task, summarize:
1. what changed
2. files/modules affected
3. migrations added
4. tests run and result
5. remaining risks or follow-up items

Do not hide failures.


---

# FILE: `PROJECT_PLAN.md`

# Stashive — Gesamtplan

## 1. Vision

Stashive wird eine selbst gehostete Webanwendung zur Verwaltung physischer Sammlungen.

Der erste Fokus ist die Verwaltung von:
- DVDs
- Blu-rays
- UHD Blu-rays

Danach folgt:
- Brettspiele

Langfristig soll Stashive auch andere physische Sammlungen verwalten können, ohne dass der Kern auf Filme oder Brettspiele fest verdrahtet wird.

Die zentrale Frage lautet immer:

> Was ist der Gegenstand, welche konkrete Edition besitze ich, wo befindet sich mein physisches Exemplar und welchen aktuellen Zustand hat es?

## 2. Kernfunktionen

### Sammlungen
- mehrere Sammlungen pro Installation
- Sammlungen können unterschiedliche Typen besitzen
- Sammlungen können mit anderen Benutzern geteilt werden
- Rollen: Owner, Admin, Editor, Viewer

### Katalog / Inventar
- Trennung zwischen Werk/Titel, Edition und physischem Exemplar
- mehrere Editionen desselben Titels
- mehrere physische Exemplare derselben Edition
- eigene Notizen
- Zustand
- Kaufdaten später optional
- Tags später optional

### Standorte
Hierarchischer Standortbaum, z. B.:

```text
Haus
└── Keller
    └── Regal 2
        ├── Kiste BD-001
        └── Kiste BD-002
```

Funktionen:
- Gegenstand verschieben
- mehrere Gegenstände gemeinsam verschieben
- Inhalt eines Standortes anzeigen
- druckbare Inventarliste
- QR-Code für Standorte/Kisten

### Ausleihen
- Gegenstand ausleihen
- Freitextname oder später optional interner Benutzer
- Ausleihdatum
- erwartetes Rückgabedatum
- Rückgabedatum
- Notiz
- vollständige Historie

### Barcode-Aufnahme
- EAN / UPC scannen
- Produkt-/Editionsdaten über austauschbaren Provider suchen
- Film-/Spieldaten über spezialisierten Metadatenprovider ergänzen
- Ergebnis vor dem Speichern bestätigen
- Zielstandort vor dem Scan festlegen
- schneller Mehrfachscan einer ganzen Kiste

### Metadaten
- Provider-Abstraktion
- lokaler Cache
- manuelle Änderungen haben Vorrang
- Provider-Refresh darf manuelle Felder nicht still überschreiben

### Kostenregel für Barcode-Lookups
Barcode-Lookup muss im normalen Betrieb ohne kostenpflichtiges Abo nutzbar sein.

Geplanter Fallback:
```text
lokaler Cache
-> UPCitemdb Free
-> optional UPC Database Free
-> manuelle Eingabe / manuelles Matching
```

Kostenpflichtige Barcode-Provider gehören nicht zum erforderlichen Standardbetrieb.

## 3. Medienmodell

Für Filmmedien gilt:

```text
Film / Werk
└── Edition / Produkt
    └── physisches Exemplar
```

Beispiel:

```text
Alien (1979)
├── Blu-ray DE
│   └── EAN 123...
│       └── Exemplar #1 -> Keller > BD-001
└── UHD Steelbook DE
    └── EAN 456...
        └── Exemplar #1 -> Wohnzimmer > Regal
```

### Film-Metadaten
Geplant:
- Titel
- Originaltitel
- Jahr
- Beschreibung
- Genres
- Laufzeit
- Regie
- Cast
- Poster
- externe IDs

### Editionsdaten
Geplant:
- Barcode
- Medium
- Region
- Publisher/Distributor
- Release-Datum
- Editionsname
- Disc-Anzahl

Medientypen:
- DVD
- Blu-ray
- UHD Blu-ray
- HD DVD
- VHS
- Other

### Rip-Status
Nicht als Boolean modellieren.

Geplanter Status:
- `not_ripped`
- `queued`
- `ripped`
- `verified`
- `failed`
- `not_needed`

Später optional:
- Rip-Datum
- Dateipfad
- Format
- Dateigröße
- externe Media-Server-Verknüpfung

## 4. Brettspielmodell

Das Brettspielmodul kommt nach dem stabilen Medienworkflow.

Geplante Metadaten:
- Name
- Erscheinungsjahr
- Spieler min/max
- Alter
- Spieldauer
- Designer
- Verlag
- Kategorien
- Mechaniken
- Cover
- externe IDs

Besitz-/Inventardaten bleiben im generischen Kern.

Später möglich:
- Vollständigkeitsstatus
- fehlende Teile
- Erweiterungen
- Sprachversion
- Edition

## 5. Architektur

```text
Vue 3 / TypeScript
        |
        | REST / JSON
        v
FastAPI
        |
        +-- Services / Domain
        |
        +-- Metadata Provider
        |
        +-- SQLAlchemy
                |
                +-- SQLite (Default)
                +-- PostgreSQL (optional später)
```

Monorepo:

```text
backend/
frontend/
docs/
assets/
```

## 6. Datenbankstrategie

### Default
SQLite.

Anforderungen:
- WAL
- Foreign Keys
- busy timeout
- DB-Pfad per Konfiguration
- DB-Datei persistent außerhalb des Container-Layers

### Später
PostgreSQL optional.

Daher von Anfang an vermeiden:
- SQLite-only Business-SQL
- PostgreSQL ARRAY
- PostgreSQL ENUM
- JSONB-Abhängigkeiten
- Postgres-only Volltextsuche im Kern

Alembic wird ab der ersten Schema-Version verwendet.

## 7. Auth und Multiuser

Lokale Benutzerverwaltung.

Registrierung:
- keine öffentliche/Self-Service-Registrierung nach dem Erstsetup
- wenn noch kein Benutzer existiert, erzeugt Stashive einen einmaligen Setup-Token
- der Token wird dem Betreiber über Server-/Container-Logs angezeigt
- gespeichert wird nur ein Hash des Tokens
- über eine Setup-Seite werden Setup-Token und Zugangsdaten für den ersten Benutzer eingegeben
- der erste Benutzer wird Instance Administrator
- der Setup-Token ist nach erfolgreicher Erstellung sofort ungültig
- sobald ein Benutzer existiert, ist der Bootstrap-Endpunkt deaktiviert
- weitere Benutzer werden ausschließlich durch einen Administrator angelegt

Ziel:
- sichere Cookie-basierte Sessions
- kein langfristiges Token in LocalStorage
- serverseitige Rechteprüfung
- Collection ACLs

Rollen:
- Owner
- Admin
- Editor
- Viewer

## 8. UI-Struktur

Geplanter Hauptaufbau:

```text
Dashboard

SAMMLUNGEN
  Filme
  Brettspiele

INVENTAR
  Standorte
  Ausgeliehen
  Barcode Scan

TOOLS
  Import
  Export
  Drucken

ADMIN
  Benutzer
  Einstellungen
  Metadaten
```

Die sichtbaren Punkte hängen später von Rolle und aktivierten Features ab.

## 9. Wichtige UX-Flows

### Schnellscan

```text
Barcode Scan öffnen
-> Zielstandort wählen
-> Barcode scannen
-> Produkt erkennen
-> Metadaten-Kandidat ermitteln
-> bestätigen / korrigieren
-> speichern
-> sofort nächstes Objekt scannen
```

### Standort

```text
Standort öffnen
-> Inhalt sehen
-> drucken
-> QR-Code erzeugen
-> Elemente markieren
-> gesammelt verschieben
```

### Ausleihen

```text
Exemplar öffnen
-> Ausleihen
-> Name
-> optional Rückgabedatum
-> speichern
```

Rückgabe erzeugt einen Historieneintrag statt vorhandene Daten zu überschreiben.

## 10. Nicht-Ziele für den Anfang

Nicht in den frühen MVP ziehen:
- Redis
- Microservices
- Elasticsearch
- komplexe Event-Systeme
- Pluginsystem
- benutzerdefinierte EAV-Felder
- native mobile App
- HA/Clusterbetrieb
- automatische Jellyfin-Synchronisierung
- komplexer PDF-Designer

## 11. Roadmap

Siehe `docs/ROADMAP.md`.

Kurzfassung:

- v0.1 Foundation
- v0.2 Movie Core
- v0.3 Barcode & Metadata
- v0.4 Locations & Printing
- v0.5 Loans
- v0.6 Board Games
- v0.7 Bulk / Import / Export
- v0.8 PWA & Scan Hardening
- v0.9 Security / Permissions / Polish
- v1.0 Stable

## 12. Qualitätsziel

Stashive soll sich wie eine fertige Sammlungsanwendung anfühlen und nicht wie ein Datenbank-Frontend.

Besonders wichtig:
- schnelle Bedienung
- gute Filter
- mobile Scan-Nutzung
- nachvollziehbare Rechte
- einfache Backups
- einfache Self-Hosting-Installation
- migrationssichere Datenhaltung


## 13. Lizenz

Stashive verwendet wie Meshive:

```text
AGPL-3.0-only
```

Repository- und Paketmetadaten verwenden den SPDX-Identifier `AGPL-3.0-only`.


---

# FILE: `START_HERE.md`

# Stashive mit Codex starten

## 1. Repository anlegen

Leeres Repository für `Stashive` anlegen und dieses Starterpaket in den Repository-Root kopieren.

Empfohlener Startzustand:

```text
Stashive/
├── AGENTS.md
├── CODEX_BOOTSTRAP_PROMPT.md
├── PROJECT_PLAN.md
├── README.md
├── START_HERE.md
├── TASKS.md
├── assets/
└── docs/
```

## 2. Initialer Commit

Vor der ersten Codex-Implementierung ist ein sauberer Dokumentations-Baseline-Commit sinnvoll:

```bash
git add .
git commit -m "docs: add Stashive project specification"
```

## 3. Erste Codex-Aufgabe

Codex soll zuerst ausschließlich das Repository-Grundgerüst erstellen.

Prompt:
- `CODEX_BOOTSTRAP_PROMPT.md`

Wichtig:
- noch keine Auth
- noch keine Movie-Datenbank
- noch keine Barcode-API
- noch kein Redis
- noch kein Production-Docker

## 4. Danach

Die nächsten Aufgaben stehen in `TASKS.md`.

Empfohlene Reihenfolge:

```text
T01 Repository Foundation
T02 Database Core
T03 Local Authentication
T04 Collections & ACL
T05 Location Tree
T06 Generic Inventory Core
T07 Movie Domain
T08 Movie UI
T09 Metadata Providers
T10 Barcode Intake
T11 Printing / QR
T12 Loans
```

Jede Aufgabe einzeln umsetzen und testen.

## 5. Arbeitsweise

Für größere Aufgaben:

```text
feature/0.1-database-core
feature/0.1-auth
feature/0.1-collections
...
```

Nicht mehrere große Domänen in einen PR packen.

Wenn du wie bei Meshive mit Worktrees arbeitest, sollte Codex ausschließlich im Worktree der aktuellen Aufgabe arbeiten.


## Festgelegte Auth-Richtung

Beim Auth-Milestone verwendet Stashive einen einmaligen Setup-Token für den ersten Benutzer. Danach gibt es keine öffentliche Registrierung; weitere Benutzer werden nur durch Instance Administratoren angelegt.


---

# FILE: `TASKS.md`

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


---

# FILE: `docs/ARCHITECTURE.md`

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


---

# FILE: `docs/DATA_MODEL.md`

# Data Model

This document describes the intended conceptual model. Exact field names may evolve through migrations.

## Core invariant

Never merge:

1. work/title
2. edition/product
3. owned physical copy

## Proposed generic core

### users

Represents local Stashive accounts.

Key concepts:
- id
- username or email identity
- display name
- password hash
- active state
- timestamps

### setup_tokens

First-run bootstrap tokens.

This table only exists to securely bootstrap the first instance administrator.

Key concepts:
- id
- token hash
- created at
- expires at
- consumed at nullable

Rules:
- never persist the plaintext token
- token is single-use
- all unconsumed setup tokens become invalid once the first user is created
- bootstrap is disabled whenever at least one user exists

### collections

Represents a user-visible collection.

Key concepts:
- id
- owner user id
- name
- type
- description
- timestamps

Initial type examples:
- `movies`
- `board_games`

Do not use collection type as a giant switch in unrelated code. Specialized modules own their behavior.

### collection_members

Links users to collections.

Key concepts:
- collection id
- user id
- role
- timestamps

Unique:
- collection + user

Roles:
- owner
- admin
- editor
- viewer

### catalog_entries

Represents the conceptual title/work.

Examples:
- Alien (1979)
- 7 Wonders Duel

Key concepts:
- id
- collection id
- display title
- type discriminator
- sort title optional
- user notes optional
- timestamps

### editions

Represents a concrete edition/product.

Examples:
- Alien German Blu-ray
- Alien German UHD Steelbook

Key concepts:
- id
- catalog entry id
- edition display name
- release date optional
- publisher/distributor optional
- region/language optional
- timestamps

### identifiers

Identifiers belong primarily to editions.

Key concepts:
- id
- edition id
- type
- value
- provider/source optional

Types may include:
- EAN
- UPC
- GTIN
- ISBN
- provider IDs where appropriate

Uniqueness must be designed carefully. A barcode may sometimes be reused or provider data may be imperfect. Do not assume global uniqueness without tests and a migration-safe decision.

### inventory_items

Represents one owned physical copy.

Key concepts:
- id
- edition id
- location id nullable
- condition optional
- notes optional
- acquired_at optional later
- purchase_price optional later
- timestamps

Multiple inventory items may reference the same edition.

## Locations

### locations

Collection-scoped in the MVP.

Key concepts:
- id
- collection id
- parent id nullable
- name
- type
- description optional
- sort order optional
- timestamps

Types:
- room
- cabinet
- shelf
- box
- drawer
- other

Rules:
- no cycles
- parent must belong to same collection
- authorization derives from collection access
- deleting non-empty locations must be explicitly defined

Open future decision:
- whether locations should eventually be shareable across collections

Do not solve that future problem in v0.1.

## Loans

### loans

Historical records.

Key concepts:
- id
- inventory item id
- borrower name
- borrower user id nullable later
- loaned at
- expected return at nullable
- returned at nullable
- notes
- created by user id
- timestamps

An active loan is a loan whose `returned_at` is null.

Do not store `inventory_items.is_loaned` as a second source of truth.

## Movie extensions

### movie_titles

1:1 with catalog entry.

Possible fields:
- catalog_entry_id PK/FK
- original title
- release year
- overview
- runtime minutes
- poster reference
- external movie provider id
- imdb id optional

Genres and people may start simplified and normalize only when needed.

### movie_editions

1:1 with edition.

Possible fields:
- edition_id PK/FK
- media_format
- disc_count
- region code
- edition label
- distributor
- release date

Media format should be stored portably, not as a PostgreSQL-native enum.

### movie_inventory_state

1:1 with inventory item.

Fields:
- inventory_item_id PK/FK
- rip_status
- rip_date optional later
- rip_path optional later
- verification note optional later

Rip states:
- not_ripped
- queued
- ripped
- verified
- failed
- not_needed

## Board game extensions

Add only in the board game milestone.

### boardgame_titles

1:1 with catalog entry.

Potential fields:
- year
- min players
- max players
- min age
- play time
- description
- cover
- external provider id

### boardgame_editions

1:1 with edition.

Potential fields:
- language
- publisher
- edition name
- release date

## Metadata cache

### metadata_cache

Provider lookup cache.

Key concepts:
- provider
- lookup type
- lookup value
- normalized/raw payload
- fetched at
- expiry or stale marker

The cache must not become the canonical user record.

## Manual override strategy

Provider data and user-authored data must not fight each other.

Preferred direction:
- canonical domain fields hold current chosen value
- metadata refresh produces a proposed candidate
- fields explicitly edited by a user can be marked/protected from silent overwrite
- refresh UI shows changes before applying when data would be replaced

Exact implementation belongs to the metadata milestone.


---

# FILE: `docs/ROADMAP.md`

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
- collection roles
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


---

# FILE: `docs/BRAND.md`

# Stashive Brand

## Identity

Name:
- **Stashive**

Positioning:
- self-hosted collection and inventory management
- organized, technical, modern
- visually related in spirit to Meshive, but a distinct product

Concept:
- storage box = physical inventory
- map pin = location / finding
- green glow = active, modern, recognizable product identity

## Core palette

| Token | Hex | Purpose |
|---|---|---|
| Emerald | `#065F46` | primary brand / deep green |
| Aqua Glow | `#10E6A1` | primary accent / glow |
| Mint | `#6FF3C7` | secondary highlight |
| Ink | `#0F172A` | primary text / dark UI |
| Cloud | `#F6FBF9` | light background |

## Suggested CSS tokens

```css
:root {
  --stashive-emerald: #065F46;
  --stashive-glow: #10E6A1;
  --stashive-mint: #6FF3C7;
  --stashive-ink: #0F172A;
  --stashive-cloud: #F6FBF9;

  --color-brand-primary: var(--stashive-emerald);
  --color-brand-accent: var(--stashive-glow);
  --color-brand-soft: var(--stashive-mint);
  --color-text-primary: var(--stashive-ink);
  --color-page-background: var(--stashive-cloud);
}
```

## Glow usage

The glow should create recognizable emphasis, not visual noise.

Use glow for:
- active navigation accent
- selected cards
- primary scan action
- logo treatment
- focus/hover highlights
- important status accent

Avoid:
- large glowing text blocks
- every card edge glowing
- high bloom around body text
- glow replacing accessible contrast

## Logo

Reference assets are in `assets/`.

Rules:
- do not redraw or regenerate the logo as part of normal frontend work
- preserve aspect ratio
- transparent asset preferred on application surfaces
- maintain clear space around the logo
- use icon-only form where horizontal space is limited
- use horizontal form for header/login/about surfaces

## UI feel

Target:
- dark technical surfaces can use Ink + Emerald
- light surfaces use Cloud with restrained green accents
- rounded but not toy-like
- clean inventory density
- crisp typography
- green glow should make interactive focus obvious

The UI should feel like a serious self-hosted tool with a distinct identity, not a generic admin dashboard.


---

# FILE: `docs/DECISIONS.md`

# Architecture Decisions

## Accepted

### D001 — Product name
**Stashive**

### D002 — License
**AGPL-3.0-only**, matching Meshive.

The repository and package metadata must use the SPDX identifier `AGPL-3.0-only`.

A canonical AGPLv3 `LICENSE` file must be added during repository bootstrap.

### D003 — Frontend
Vue 3 + TypeScript + Vite.

### D004 — Backend
FastAPI + SQLAlchemy + Alembic.

### D005 — Default database
SQLite.

PostgreSQL must remain possible later.

### D006 — Data model separation
Work/title, edition/product, and owned physical copy are separate entities.

### D007 — Multiuser
Collections are shareable.

Initial roles:
- owner
- admin
- editor
- viewer

### D008 — Location model
Hierarchical location tree.

MVP locations are collection-scoped.

### D009 — Loans
Loans are historical records, not a boolean field on inventory.

### D010 — Rip state
Media rip state is a multi-state value, not true/false.

### D011 — External metadata
Provider abstraction and caching are mandatory.

### D012 — Brand palette
- `#065F46`
- `#10E6A1`
- `#6FF3C7`
- `#0F172A`
- `#F6FBF9`

## Open

### D015 — Initial barcode providers
Implement **UPCitemdb** as the first barcode provider.

Reasons:
- supports UPC/EAN/GTIN/ISBN lookup
- free Explorer access requires no signup
- suitable for development and normal low-volume self-hosted use
- responses are JSON
- provider abstraction keeps it replaceable

Add **UPC Database** as an optional second free provider after the first adapter is stable.

Important:
- free services are rate-limited
- successful lookups must be cached locally
- repeated scans of the same barcode should not call an external provider again
- provider throttling/no-match must degrade to manual entry, never block inventory creation
- do not add EAN-Search or other paid-only providers to the default plan

### O001 — Movie metadata provider configuration
A provider such as TMDB is expected, but final credential/configuration behavior should be decided during v0.3.

### O002 — UI component framework
No framework selected.

Default: custom Vue components + CSS tokens until a need is proven.

### O003 — Location scope beyond MVP
MVP locations are collection-scoped.

Future option:
shared location trees across collections.

Do not implement until there is a real use case.

### D013 — Registration model
There is **no public/self-service registration** after initial setup.

Initial instance bootstrap:
- when no user exists, Stashive exposes a first-run setup flow
- Stashive generates a cryptographically strong **one-time setup token**
- the plaintext token is shown in the server/container logs for the operator
- only a hash of the token is persisted
- the setup page asks the operator to enter the token and create the first account
- the first account becomes an **instance administrator**
- the token is single-use and is invalidated immediately after successful setup
- the bootstrap endpoint becomes unavailable once the first user exists
- if an unused token expires while no user exists, Stashive may generate a fresh token and log it

After bootstrap:
- there is no public `/register` flow
- only an instance administrator can create additional users
- additional instance administrators may only be created/promoted by an existing instance administrator

Avoid putting the setup token in a URL. Prefer an explicit token input so it does not leak through browser history, referrers, or reverse-proxy access logs.

### D014 — Barcode lookup cost policy
Core barcode lookup must be usable **without any paid subscription**.

Initial provider strategy:
1. local Stashive metadata/barcode cache
2. UPCitemdb free Explorer API
3. optional UPC Database free API adapter
4. manual entry / manual movie matching

Stashive must not require a paid barcode provider for normal use.
Paid providers may only ever be optional third-party extensions and must never be required for a supported workflow.

### O004 — Production frontend serving
Likely single production image.

Exact static serving layer to be decided near deployment milestone.


---

# FILE: `docs/TESTING.md`

# Testing Strategy

## Principles

- test domain rules, not implementation trivia
- permission tests are mandatory
- migrations are product behavior
- critical flows get E2E coverage
- SQLite is the default test database
- PostgreSQL may be added as a secondary compatibility target later

## Backend

Use:
- pytest
- API test client
- isolated test database
- factories/fixtures kept small

Required test areas:
- auth/session
- collection ACL
- location cycle prevention
- title/edition/copy relationships
- inventory movement
- metadata merge/manual override behavior
- loans
- barcode intake
- migration upgrade

## Frontend

Use:
- typecheck
- unit/component tests for meaningful logic
- Playwright for critical workflows

Do not test every static component snapshot.

## E2E critical path

Eventually:

1. create first user
2. log in
3. create collection
4. add member
5. create location tree
6. create movie title
7. create edition
8. add copy
9. move copy
10. barcode intake
11. lend item
12. return item
13. print location inventory

## Migration testing

For schema changes:
- upgrade empty DB
- upgrade representative previous DB where practical
- downgrade when supported
- upgrade again

Never assume migration correctness because models import successfully.

## Definition of done

A task is not done until:
- relevant automated checks pass
- manual UX check is performed when visual behavior changes
- new permission paths are covered
- documentation is updated if contracts changed


---

# FILE: `docs/SECURITY.md`

# Security Model

## Threat model

Stashive is self-hosted but must not assume a trusted LAN.

Treat every request as potentially untrusted.

## Authentication

Preferred initial approach:
- local accounts
- strong password hashing with a maintained Argon2 implementation
- opaque or server-controlled session
- HttpOnly cookie
- Secure cookie when served via HTTPS
- appropriate SameSite policy
- bounded session lifetime

Do not store reusable long-lived bearer tokens in LocalStorage.

## First-run setup token

When no user exists:
- generate at least 256 bits of cryptographically secure random entropy
- encode it in a URL-safe textual form
- store only a cryptographic hash of the token
- show the plaintext token only in operator-facing server/container logs
- do not include it in a clickable setup URL
- token validation must be constant-time where applicable
- token is single-use
- token has a bounded lifetime
- successful setup invalidates all outstanding setup tokens
- setup endpoint refuses all requests once any user exists
- failed attempts should be rate-limited
- never log the token when it is submitted by the browser

If the token expires before setup and the database still has no users, a new token may be generated and logged.

## CSRF

If cookie-authenticated mutating endpoints are used, include explicit CSRF protection appropriate to the final session design.

Do not assume SameSite alone covers every deployment scenario.

## Authorization

Every protected backend operation must establish:
- authenticated user
- collection scope
- role capability
- resource ownership/scope

Frontend visibility is not authorization.

## Data isolation

Collection A must never expose:
- items
- editions
- locations
- loans
- metadata private to the collection
to a user who can only access Collection B.

Maintain an ACL leak test matrix.

## Provider secrets

External provider credentials:
- environment/config only
- never committed
- never sent to browser unless specifically intended as public client keys
- never logged in full

## Uploads/artwork

When local artwork support is added:
- validate media type
- impose size limits
- do not trust filenames
- generate internal filenames
- prevent path traversal
- never execute uploaded content

## Logging

Do not log:
- passwords
- session secrets
- auth cookies
- full provider API keys
- sensitive request headers

## Production

Production guidance should eventually include:
- reverse proxy
- HTTPS
- trusted hosts/origins
- backup/restore
- security headers


---

# FILE: `docs/UX_FLOWS.md`

# UX Flows

## 1. Initial setup

```text
Start Stashive
-> no user exists
-> backend generates one-time setup token
-> token is printed to server/container logs
-> browser shows Setup Required
-> operator enters setup token
-> operator chooses username/display name/password
-> Stashive creates first instance administrator
-> token is invalidated
-> setup endpoint is disabled
-> normal login
```

The setup token should be pasted into a form field, not placed in the URL.

After initial setup:
- there is no public registration
- instance administrators create additional users from Admin > Users

## 2. Create a movie collection

```text
New collection
-> type: Movies
-> name
-> create
-> optional members
```

## 3. Manual movie entry

```text
Add item
-> search existing title
   or create title
-> choose/create edition
-> create physical copy
-> location
-> rip state
-> save
```

Avoid forcing provider lookup for manual entry.

## 4. Barcode batch intake

```text
Open Scan
-> choose collection
-> choose target location
-> enable continuous mode
-> scan barcode
-> lookup
-> show candidate
-> confirm
-> save
-> ready for next scan
```

Important:
- manual barcode typing fallback
- provider no-match fallback
- duplicate warning
- fast keyboard/USB scanner compatibility

## 5. Move items

Single:

```text
Item
-> Move
-> location picker
-> save
```

Bulk:

```text
Location/catalog
-> select items
-> Move selected
-> destination
-> confirm
```

## 6. Box inventory

```text
Open location
-> direct items
-> optionally descendants count
-> Print inventory
-> Print QR label
```

Printed output should remain useful without a full PDF designer.

## 7. Loan

```text
Item
-> Lend
-> borrower
-> loan date
-> optional expected return
-> note
-> save
```

Return:

```text
Active loan
-> Return
-> returned at
-> optional note
-> close loan
```

## 8. Sharing

```text
Collection settings
-> Members
-> add existing local user
-> choose role
-> save
```

No resource outside the shared collection should become visible.


---

# FILE: `docs/PROVIDERS.md`

# External Provider Design

## Goal

Stashive must not be locked to one external service.

## Barcode provider

Conceptual interface:

```python
class BarcodeProvider(Protocol):
    async def lookup(self, barcode: str) -> BarcodeLookupResult:
        ...
```

Normalized result should be provider-independent.

Possible normalized fields:
- barcode
- product name
- brand/publisher
- image URL
- raw provider reference
- confidence/source metadata

## Movie metadata provider

Conceptual operations:
- search movie
- fetch movie details
- fetch artwork references

Do not let provider response objects leak into domain models.

## Board game metadata provider

Added in the board game milestone.

## Caching

Provider calls should support local caching.

Cache key:
- provider
- operation/lookup type
- normalized lookup value

Cache is not canonical user data.

## Failure handling

Provider failures must not block manual inventory management.

Handle:
- timeout
- quota/rate limit
- authentication failure
- no result
- multiple candidates
- malformed provider data

## Manual override

Provider refresh must never silently replace user-curated values.

A later metadata screen should be able to show:
- current value
- provider value
- source
- apply/ignore choice


## Initial free barcode provider strategy

Barcode lookup is a convenience feature, but it must be usable without a paid subscription.

### Provider 1: UPCitemdb Free Explorer

Implement this adapter first.

Expected characteristics:
- UPC / EAN / GTIN / ISBN lookup
- no signup needed for the free Explorer API
- JSON response
- rate-limited free usage

Stashive behavior:
- read provider rate-limit headers when available
- never hammer the provider after HTTP 429
- cache successful normalized results
- cache sensible negative/no-match results for a shorter period
- show a clear non-blocking message when the free provider is throttled
- allow manual entry immediately

### Provider 2: UPC Database Free

Add as an optional second free adapter after the first provider is stable.

Characteristics:
- UPC/EAN product lookup
- free API tier
- requires the Stashive operator to create an account/API token
- useful as a fallback when the first provider has no result

Credentials:
- configured per Stashive instance
- server-side only
- never bundled into the frontend

### Lookup chain

Recommended:

```text
normalize/validate barcode
        |
        v
Stashive local cache
        |
        v
UPCitemdb Free
        |
        +-- match -> normalize/cache -> candidate
        |
        v
optional UPC Database Free
        |
        +-- match -> normalize/cache -> candidate
        |
        v
manual edition/title entry
```

### Important limits

Free public barcode databases have incomplete coverage and rate limits.

Therefore:
- barcode lookup is best-effort enrichment, not a prerequisite for adding an item
- do not claim a barcode match is authoritative
- the user confirms the candidate before save
- Stashive should learn locally: once a barcode has been confirmed, future scans use the local mapping first

### Optional local/community improvement

A later feature may allow Stashive to export/import a user-maintained barcode-to-edition mapping file.

Do not build a centralized Stashive cloud service unless explicitly requested.


---

# FILE: `docs/DEPLOYMENT.md`

# Deployment Direction

This is a target design, not a requirement for the repository bootstrap task.

## Default production goal

Simple:

```text
stashive container
  |
  +-- application
  +-- built frontend
  +-- SQLite
       |
       +-- persistent /app/data
```

The database must never live only in the ephemeral container layer.

## Environment direction

Likely variables:

```text
STASHIVE_DATA_DIR=/app/data
DATABASE_URL=sqlite:////app/data/stashive.db
```

Additional variables must be introduced only when needed.

## PostgreSQL

Optional later:

```text
DATABASE_URL=postgresql+psycopg://...
```

The app must not require PostgreSQL for normal self-hosting.

## Reverse proxy

Expected deployments may place Stashive behind:
- Traefik
- nginx
- Caddy
- similar reverse proxies

Do not hard-code public hostnames.

## Backup

For SQLite, backup documentation must eventually cover:
- application-safe DB backup
- artwork/data files
- restore verification

A built-in backup CLI may be considered later, but is not a v0.1 requirement.

## Production image

Production image should eventually:
- run non-root
- include only runtime dependencies
- include built frontend
- expose health endpoint
- use persistent data mount
- support graceful shutdown

Do not over-engineer container permissions during early application milestones.


---

# FILE: `CODEX_BOOTSTRAP_PROMPT.md`

# Codex Bootstrap Prompt

Use this prompt for the first implementation task.

---

Read `AGENTS.md`, `PROJECT_PLAN.md`, `docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md`, `docs/DECISIONS.md`, `docs/TESTING.md`, and `docs/BRAND.md` before making changes.

Then bootstrap Stashive as a monorepo, implementing only the **v0.1 repository foundation**.

Project license is **AGPL-3.0-only**. Add the canonical GNU AGPL v3 `LICENSE` file and use the SPDX identifier `AGPL-3.0-only` in package metadata.

Goals:

1. Create a `backend/` FastAPI application with:
   - SQLAlchemy
   - Alembic
   - Pydantic configuration
   - SQLite as the default database
   - configurable `DATABASE_URL`
   - SQLite foreign keys enabled
   - SQLite busy timeout
   - WAL enabled where appropriate
   - a simple `/api/health` endpoint
   - pytest setup
   - Ruff setup

2. Create a `frontend/` Vue 3 + TypeScript + Vite application with:
   - Vue Router
   - Pinia
   - strict TypeScript
   - a minimal application shell
   - Stashive design tokens from `docs/BRAND.md`
   - a simple health/status view or API connectivity check
   - frontend typecheck/test/build scripts

3. Establish the initial repository structure documented in `docs/ARCHITECTURE.md`.

4. Add development documentation and commands so a new developer can run:
   - backend
   - frontend
   - tests
   - migrations

5. Add an initial Alembic baseline only if required by the scaffold.
   Do not implement the complete domain schema yet unless the repository bootstrap naturally requires a tiny minimum.

6. Do not implement yet:
   - users/auth or the first-run setup-token flow (documented for T03)
   - collections
   - locations
   - movies
   - barcode lookup
   - metadata providers
   - loans
   - board games
   - Redis
   - PostgreSQL-specific features
   - Docker production packaging

7. Do not introduce a UI framework without explicit approval.

8. Keep all changes portable to PostgreSQL later.

Before finishing:
- run backend lint/tests
- run frontend typecheck/tests/build
- report all commands and results
- report any decisions that need owner approval
- do not merge, tag, release, or push to `main`

If the working tree contains unrelated changes, leave them untouched.

The intended result is a clean, boring, well-tested foundation that later feature branches can build on.
