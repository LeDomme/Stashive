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
