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
