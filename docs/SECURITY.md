# Security Model

## Threat model

Stashive is self-hosted but must not assume a trusted LAN.

Treat every request as potentially untrusted.

## Authentication

Preferred initial approach:
- local accounts
- strong password hashing with a maintained Argon2 implementation
- opaque or server-controlled session
- HttpOnly cookie
- Secure cookie when served via HTTPS
- appropriate SameSite policy
- bounded session lifetime

Do not store reusable long-lived bearer tokens in LocalStorage.

## First-run setup token

When no user exists:
- generate at least 256 bits of cryptographically secure random entropy
- encode it in a URL-safe textual form
- store only a cryptographic hash of the token
- show the plaintext token only in operator-facing server/container logs
- do not include it in a clickable setup URL
- token validation must be constant-time where applicable
- token is single-use
- token has a bounded lifetime
- successful setup invalidates all outstanding setup tokens
- setup endpoint refuses all requests once any user exists
- failed attempts should be rate-limited
- never log the token when it is submitted by the browser

If the token expires before setup and the database still has no users, a new token may be generated and logged.

## CSRF

If cookie-authenticated mutating endpoints are used, include explicit CSRF protection appropriate to the final session design.

Do not assume SameSite alone covers every deployment scenario.

T03 uses an opaque HttpOnly session cookie with SameSite=Lax and a separate readable
CSRF cookie. Mutating authenticated requests send that value in the X-CSRF-Token header;
the server stores only its hash alongside the session. AUTH_COOKIE_SECURE must be enabled
behind HTTPS.

## Authorization

Every protected backend operation must establish:
- authenticated user
- collection scope
- role capability
- resource ownership/scope

Frontend visibility is not authorization.

## Data isolation

Collection A must never expose:
- items
- editions
- locations
- loans
- metadata private to the collection
to a user who can only access Collection B.

Maintain an ACL leak test matrix.

## Provider secrets

External provider credentials:
- environment/config only
- never committed
- never sent to browser unless specifically intended as public client keys
- never logged in full

## Uploads/artwork

When local artwork support is added:
- validate media type
- impose size limits
- do not trust filenames
- generate internal filenames
- prevent path traversal
- never execute uploaded content

## Logging

Do not log:
- passwords
- session secrets
- auth cookies
- full provider API keys
- sensitive request headers

## Production

Production guidance should eventually include:
- reverse proxy
- HTTPS
- trusted hosts/origins
- backup/restore
- security headers
