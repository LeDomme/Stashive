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

GET    /api/inventory/{inventory_item_id}
PATCH  /api/inventory/{inventory_item_id}
```

Final endpoint design may evolve with implementation.

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
