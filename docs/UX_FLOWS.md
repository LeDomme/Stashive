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
