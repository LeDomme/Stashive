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
