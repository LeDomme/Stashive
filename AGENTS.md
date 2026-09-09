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
