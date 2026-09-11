# API Conventions

## Prefix

All application endpoints live under:

```text
/api
```

Health:

```text
GET /api/health
```

Authentication endpoints are GET /api/auth/status, POST /api/auth/setup, POST /api/auth/login,
POST /api/auth/logout, and GET /api/auth/me. There is no public registration endpoint.

Instance administrators manage local accounts through GET/POST `/api/admin/users`, PATCH
`/api/admin/users/{user_id}`, and POST `/api/admin/users/{user_id}/password`. These endpoints
never return password hashes, session data, CSRF data, or setup-token data. User removal is
implemented as disabling an account; no hard-delete endpoint exists.

Collection detail responses include safe owner identity data (`id`, `username`, and optional
`display_name`). Collection member list responses expose the same safe identity data plus the
collection role, allowing clients to manage the listed non-owner members without exposing secrets.

## Resource style

Prefer resource-oriented endpoints.

Examples:

```text
GET    /api/collections
POST   /api/collections
GET    /api/collections/{collection_id}
PATCH  /api/collections/{collection_id}

GET    /api/collections/{collection_id}/locations
POST   /api/collections/{collection_id}/locations
PATCH  /api/collections/{collection_id}/locations/{location_id}
DELETE /api/collections/{collection_id}/locations/{location_id}

GET    /api/collections/{collection_id}/inventory-items
POST   /api/collections/{collection_id}/inventory-items
GET    /api/collections/{collection_id}/inventory-items/{item_id}
PATCH  /api/collections/{collection_id}/inventory-items/{item_id}
DELETE /api/collections/{collection_id}/inventory-items/{item_id}

GET    /api/collections/{collection_id}/library
GET    /api/collections/{collection_id}/library/{catalog_entry_id}
GET    /api/collections/{collection_id}/library/title-search?q=al
POST   /api/collections/{collection_id}/items
```

Final endpoint design may evolve with implementation.

Library endpoints are collection-scoped VIEW read models over the existing
CatalogEntry → Edition → InventoryItem hierarchy; they introduce no persisted
library/grouping table. The list returns one summary per title and the detail
embeds editions, identifiers, and physical copies.

`POST /items` is the transactional user-oriented Add item use case. It explicitly
chooses either an existing or new title and edition, then always creates one new
physical copy; it does not change the CatalogEntry → Edition → InventoryItem model.

Location GET returns the complete nested tree for a collection. Roots and children are ordered
case-insensitively by name, then by ID. Create accepts `name`, `type`, optional `description`,
and optional `parent_id`. PATCH is partial: `parent_id: null` moves a node to the root and
`description: null` removes its description. Location IDs are resolved within the requested
collection scope. A non-leaf delete returns 409; recursive subtree deletion is not available.

## Pagination

Any list that can grow without a strict small bound must be paginated.

Response shape should be consistent.

## Filtering

Catalogue filters should use query parameters.

Examples:
- type
- medium
- year
- location
- rip status
- loan status

Inventory filtering uses `location_id`: it includes that location and descendants by
default. Set `include_descendants=false` for an exact location. `unassigned=true`
returns items without a location; it cannot be combined with `location_id`, and
`include_descendants` requires `location_id`.

Library summaries accept the same copy filters. With a filter, a title is returned
only when it has a matching physical copy; its edition and copy counts cover only
the matching copies and their editions. Without a filter, titles without copies are
also returned.

## Errors

Errors must be:
- safe
- actionable
- stable enough for frontend handling

Do not leak:
- password data
- provider secrets
- SQL details
- stack traces in normal production API responses

## Permission semantics

Authorization is server-side.

For inaccessible resources:
- prefer 404 when revealing existence would leak information
- use 403 when existence is already legitimately known and denial is useful

Create explicit authorization tests for each protected route family.

## Idempotency

Avoid accidental duplicate writes where the UI may retry.

Barcode intake must explicitly define duplicate handling instead of guessing.
