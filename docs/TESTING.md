# Testing Strategy

## Principles

- test domain rules, not implementation trivia
- permission tests are mandatory
- migrations are product behavior
- critical flows get E2E coverage
- SQLite is the default test database
- PostgreSQL may be added as a secondary compatibility target later

## Backend

Use:
- pytest
- API test client
- isolated test database
- factories/fixtures kept small

Required test areas:
- auth/session
- collection ACL
- location cycle prevention
- title/edition/copy relationships
- inventory movement
- metadata merge/manual override behavior
- loans
- barcode intake
- migration upgrade

## Frontend

Use:
- typecheck
- unit/component tests for meaningful logic
- Playwright for critical workflows

Do not test every static component snapshot.

## E2E critical path

Eventually:

1. create first user
2. log in
3. create collection
4. add member
5. create location tree
6. create movie title
7. create edition
8. add copy
9. move copy
10. barcode intake
11. lend item
12. return item
13. print location inventory

## Migration testing

For schema changes:
- upgrade empty DB
- upgrade representative previous DB where practical
- downgrade when supported
- upgrade again

Never assume migration correctness because models import successfully.

## Definition of done

A task is not done until:
- relevant automated checks pass
- manual UX check is performed when visual behavior changes
- new permission paths are covered
- documentation is updated if contracts changed
