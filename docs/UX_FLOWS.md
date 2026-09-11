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

## 3. Inventory and add an item

Collections -> Inventory -> Title -> Editions -> Physical Copies

Inventory is the primary title-centric library. A title detail groups title metadata, editions,
media format, barcodes and IDs, physical copies, locations, condition, and notes. Management is
reached from that structure: titles have General and Danger Zone; editions have General, Barcodes
& IDs, and Danger Zone; physical copies have General, Location, and Danger Zone.

```text
Collections -> Inventory -> Add item
-> explicitly choose an existing title or create a new title
-> explicitly choose an existing edition or create a new edition
-> add physical copy details and optional location
-> save through one transactional Add Item request
-> title detail
```

The normal flow never requires Advanced Catalog and never automatically merges title matches.
Search can suggest an exact existing title, but the user explicitly chooses Use existing or Create
new title. Existing/new title and edition choices support all three transactional cases without
partial writes.

Edition, media format, and condition controls offer optional UI presets. Media formats: DVD,
Blu-ray, UHD Blu-ray, HD DVD, LaserDisc, VHS. Editions: Standard Edition, Collector's Edition,
Director's Cut, Extended Edition, Limited Edition, Steelbook, Box Set. Conditions: Mint, Very
Good, Good, Fair, Poor. Other / Custom keeps arbitrary strings such as Video CD, 40th Anniversary
Edition, and Sealed; it also preserves unknown stored values.

Advanced Catalog remains a low-level fallback under Settings → Advanced. It is not primary
collection navigation, while its backend CRUD remains available.

## Location tree

```text
Collection details -> Locations
-> create a root location
-> add children for physical nesting
-> edit metadata or select a different parent
-> select No parent / Root to promote a child
-> confirm leaf deletion when no children remain
```

Owner, Admin, and Editor can manage the tree. Viewer can read it only. Parent selection omits the
current node and its descendants as a cycle-prevention convenience; server-side validation remains
authoritative. T05 does not yet assign inventory items to locations.

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

Only collection owners may transfer ownership. The selected existing user becomes owner, is not
also shown as a normal member, and the previous owner remains an admin member.

## 9. Instance user management

```text
Admin > Users
-> create local user / promote or demote instance admin
-> disable or enable account
-> reset password
```

There is no public registration after setup and no hard-delete flow. Disable and password reset
end existing sessions; collection ownership and memberships remain intact.
