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
