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

T02 introduces only the structural collection root. Ownership, members, roles, and
sharing are intentionally deferred to the authentication and collection ACL milestones.

Key concepts:
- id
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
- condition optional
- notes optional
- acquired_at optional later
- purchase_price optional later
- timestamps

Multiple inventory items may reference the same edition.

Location assignment is intentionally deferred until the collection-scoped locations
table is introduced.

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
