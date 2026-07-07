# Security & Authentication Integration Plan (Phase 1)

Date: July 4, 2026

Project: Katz Nursing School Inventory Management System (going to market as a product)

## Purpose

This document explains how to take the current Flask inventory application from a
local, ID-only prototype to an application that is safe to expose on a public
domain. It covers the five "Security & authentication" items identified in the
production-readiness review and breaks each into small, independently testable
substeps, in the same step-by-step style as `QR_CODE_SYSTEM_INTEGRATION_PLAN.md`.

The end state for Phase 1:

```text
Every user has an email + a hashed password (no more ID-only login)
Accounts are created by an admin (invite-only) and activated via an emailed link
All state-changing forms are CSRF-protected
Login and other sensitive endpoints are rate-limited
Sessions expire after inactivity; sensitive admin actions require re-auth
The app is served only over HTTPS with HSTS
```

This plan does not require splitting `app.py` into blueprints yet. Security can be
added on the current structure; the larger refactor is a later phase.

---

## Product context and locked decisions

This is a **commercial product**, not an integration with one university's identity
system. Therefore SSO/SAML against a specific institution is explicitly **out of
scope for Phase 1** (it becomes a per-customer enterprise feature later). The
following decisions are locked and drive every step below:

```text
Tenancy:       Single-tenant  (one deployment + one database per customer)
Account model: Invite-only    (an admin creates users; users set their own password)
Login method:  Email + password only  (no OAuth/SSO in Phase 1)
```

Consequences of these decisions:

- No `organizations` table and no tenant columns are needed.
- There is **no public self-service registration page**.
- There is exactly one login path to build, test, and harden.

---

## Current authentication behavior (the problem)

Current `users` table (`schema.sql`):

```sql
users (
    id SERIAL PRIMARY KEY,
    institution_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    role TEXT NOT NULL,              -- student | faculty | administrator
    department TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
)
```

Current login (`app.py`):

```text
User submits institution_id + a chosen login_mode (user | faculty | admin)
App looks up the row by institution_id
If found and active, the user is logged in
```

Problems:

```text
No password field exists — knowing an ID (e.g. S1001) is enough to log in
login_mode lets the user choose their own privilege level at login time
There is no email, so password reset / invites are impossible
```

---

## Status of the five Phase 1 items

| # | Improvement | Priority | Effort | Status |
|---|-------------|----------|--------|--------|
| 1 | Replace ID-only login with real authentication (email + password) | Critical | L | To do (this plan, Step A) |
| 2 | Add CSRF protection (Flask-WTF) on every POST form | Critical | S | Done (documented in Step B) |
| 3 | Enforce HTTPS/TLS on the domain + HSTS | Critical | S | To do at deploy (Step E) |
| 4 | Rate limiting & brute-force protection (Flask-Limiter) | High | S | To do (Step D) |
| 5 | Session idle-timeout + re-auth for admin actions | High | S | To do (Step C) |

---

## External dependencies to secure before launch

These are required for the plan to fully function in production. Development can
proceed without them using the fallbacks noted.

```text
Transactional email provider (SES / SendGrid / Postmark / Resend)
    - Needed to send invite and password-reset links.
    - Dev fallback: send_email() logs the link to the console instead of sending.

Strong SECRET_KEY (environment variable)
    - Signs both session cookies AND invite/reset tokens.
    - The dev fallback key must never be used in production.

TLS certificate + HTTPS termination (host/reverse proxy or managed platform)
    - Required so passwords/sessions are never sent in clear text.
```

---

## Recommended execution order

Auth is the foundation the other items build on, so it goes first. HTTPS is a
deploy-time toggle and goes last.

```text
Step A  Real authentication (email + password, invite-only)     [do first]
Step B  CSRF protection                                         [already done]
Step C  Session idle-timeout + admin re-auth
Step D  Rate limiting & brute-force protection
Step E  HTTPS/TLS + HSTS                                        [at deploy time]
```

---

## Step A — Replace ID-only login with real authentication

Effort: L. This is the largest change and is split into six substeps (A1–A6).
Each substep should compile, pass a manual check, and get a dated
`PROGRESS_REPORT.md` entry before moving on.

### Substep A1 — Schema, migrations, and password hashing

Files:

```text
requirements.txt
schema.sql
app.py
migrations/            (new, if adopting Flask-Migrate/Alembic)
```

Add:

```text
users.email           TEXT UNIQUE NOT NULL
users.password_hash   TEXT               (nullable: NULL = invited, not yet set)
users.created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
users.last_login_at   TIMESTAMP
users.institution_id  -> make NULLABLE   (now an optional employee number)

Password hashing helpers using werkzeug.security:
    hash_password(raw)   -> generate_password_hash(raw)
    verify_password(hash, raw) -> check_password_hash(hash, raw)

A password-strength check (minimum length, etc.)
```

Migration note:

```text
Replace the ensure_*_columns() "ALTER TABLE on every request" pattern with
real migrations (Flask-Migrate/Alembic) starting with this change. Auth schema
changes must not run on every page load.
```

Verify:

```text
init-db / migration creates the new columns
Seed users (S1001/F1001/A1001) get real emails + hashed passwords
hash_password / verify_password round-trip correctly in a shell test
```

### Substep A2 — Real login (email + password)

Files:

```text
app.py
templates/login.html
templates/base.html
```

Add:

```text
Rewrite /login to accept email + password
Look up user by email; require is_active; verify_password(...)
On success: session.clear(), then set session; update last_login_at
On failure: generic "Invalid email or password" (never reveal which field)
Remove the login_mode selector; privileges now come from users.role
Update require_admin / require_system_admin / require_item_manager to use role
Update the nav in base.html to key off role (not login_mode)
```

Verify:

```text
Correct email + password logs in; wrong password is rejected
Inactive users cannot log in
A student cannot reach admin-only routes; faculty/admin can
Logout still works
```

### Substep A3 — Signed token utility

Files:

```text
app.py
```

Add:

```text
A token helper using itsdangerous.URLSafeTimedSerializer(SECRET_KEY):
    make_token(user_id, purpose)      purpose in {"invite", "reset"}
    read_token(token, purpose, max_age)  -> user_id or None (checks purpose + expiry)

A send_email(to, subject, body) helper:
    Production: send via configured provider (env vars)
    Development: log the message/link to the console
```

Verify:

```text
A token created for one purpose is rejected when read for another purpose
An expired token (past max_age) is rejected
send_email() logs the link in development
```

### Substep A4 — Invite flow (admin creates users)

Files:

```text
app.py
templates/user_new.html
templates/admin_users.html
templates/set_password.html   (new)
```

Add:

```text
Update admin "create user": fields become name + email + role (+ optional institution_id)
New user row is created with password_hash = NULL
Generate an "invite" token and email a "Set your password" link
New route: GET/POST /set-password/<token>
    Validates the invite token, lets the user set a password, fills password_hash
Optional: "Resend invite" action on the admin users list
```

Verify:

```text
Admin creates a user -> invite link is produced (logged in dev)
Opening the link lets the user set a password and then log in
An invalid/expired invite link is rejected with a clear message
A user with password_hash = NULL cannot log in until they set a password
```

### Substep A5 — Forgot / reset password

Files:

```text
app.py
templates/login.html
templates/forgot_password.html   (new)
templates/reset_password.html    (new)
```

Add:

```text
GET/POST /forgot-password -> always respond "if that email exists, we sent a link"
    (do not reveal whether an email is registered)
Email a "reset" token link (shorter expiry, e.g. 1 hour)
GET/POST /reset-password/<token> -> validate token, set new password_hash
```

Verify:

```text
Requesting a reset for a real email produces a working link (logged in dev)
Requesting a reset for an unknown email shows the same generic message
An expired/invalid reset token is rejected
After reset, the old password no longer works and the new one does
```

### Substep A6 — Tests for authentication

Files:

```text
tests/                 (new)
requirements.txt       (add pytest)
```

Add:

```text
pytest cases:
    login success / wrong password / inactive user
    invite -> set-password -> login
    reset token validity and expiry
    protected routes redirect to /login when logged out
    role-based access (student blocked from admin routes)
```

Verify:

```text
pytest passes locally against a test database
```

---

## Step B — CSRF protection (already completed)

Files:

```text
requirements.txt        (Flask-WTF added)
app.py                  (CSRFProtect enabled)
templates/*.html        (csrf_token in every POST form)
```

Status:

```text
DONE. Flask-WTF is installed and CSRFProtect is initialized; POST forms include
the CSRF token (login, scan, item create/edit, item stock, user management).
```

Verify (regression checklist to keep passing after auth changes):

```text
Every POST form still renders a csrf_token hidden field
Submitting a form without a valid token is rejected (400)
No new POST route/form is added without a token
```

---

## Step C — Session idle-timeout + admin re-auth

Effort: S.

Files:

```text
app.py
templates/ (a small re-auth confirmation page, if used)
```

Add:

```text
Set PERMANENT_SESSION_LIFETIME (e.g. 30-60 minutes) and mark sessions permanent
Refresh the session on activity so active users are not logged out mid-task
Idle sessions expire and require logging in again
Optional but recommended: require a password re-entry ("sudo mode") before
    destructive admin actions (delete user, deactivate, bulk changes)
Optional: account lockout / cooldown after N failed logins
```

Verify:

```text
A session left idle past the timeout is rejected and redirects to /login
An active user is not logged out while working
Re-auth is prompted before the protected admin action (if implemented)
```

---

## Step D — Rate limiting & brute-force protection

Effort: S.

Files:

```text
requirements.txt        (add Flask-Limiter)
app.py
```

Add:

```text
Initialize Flask-Limiter (keyed by client IP; use a shared store like Redis in prod)
Strict limits on:
    POST /login
    POST /forgot-password
    POST /set-password/<token>, /reset-password/<token>
    /scan and /items/<barcode>/stock (abuse/scraping protection)
A clear "too many attempts, try again later" response (HTTP 429)
```

Verify:

```text
Rapid repeated login attempts are throttled with 429
Normal usage is unaffected by the limits
Limits are configurable via environment variables
```

Note:

```text
In-memory limiting works for a single process only. For multiple Gunicorn
workers or multiple hosts, back Flask-Limiter with Redis so limits are shared.
```

---

## Step E — Enforce HTTPS/TLS + HSTS (at deploy time)

Effort: S. This is a deployment/config step, not application logic.

Files:

```text
Deployment/host configuration (reverse proxy or managed platform)
app.py (or a small extension such as Flask-Talisman) for HSTS + redirects
.env / platform secrets
```

Add:

```text
Terminate TLS at the host/reverse proxy (managed cert or Let's Encrypt)
Redirect all HTTP traffic to HTTPS
Send HSTS header (Strict-Transport-Security) once HTTPS is confirmed working
Confirm SESSION_COOKIE_SECURE = True in production (already set when APP_ENV=production)
Set APP_ENV=production and a strong SECRET_KEY in the environment
```

Verify:

```text
http:// requests redirect to https://
HSTS header is present on responses
Session cookies are marked Secure
The dev fallback SECRET_KEY is not in use (app refuses to start without one in prod)
```

---

## Consolidated testing plan

```text
Unit / integration (pytest):
    Auth: login, invite, set-password, reset, role access (Step A6)
    CSRF: POST without token is rejected
Manual, against local PostgreSQL:
    Full invite -> set password -> login -> logout cycle
    Forgot -> reset -> login with new password
    Idle timeout expiry
    Rate-limit throttling on /login
Pre-deploy:
    HTTPS redirect + HSTS + Secure cookies on the real domain
```

---

## Pre-launch security checklist

```text
[ ] No route logs a user in without a verified password
[ ] login_mode selector removed; role comes from the account
[ ] All POST forms carry a CSRF token
[ ] Login / reset / invite endpoints are rate-limited
[ ] Sessions expire on inactivity; cookies are HttpOnly + SameSite + Secure
[ ] SECRET_KEY is strong and set via environment (no dev fallback in prod)
[ ] Email provider configured; invite/reset emails deliver
[ ] HTTPS enforced with HSTS; HTTP redirects to HTTPS
[ ] pytest suite passes in CI
[ ] Automated database backups enabled (Phase 1 data step)
```

---

## Notes on sequencing with the rest of the roadmap

```text
Step A (auth) should land before Steps C and D, which build on real accounts.
Step E (HTTPS) is done when the app is first deployed to its domain.
Database backups and migrations (data reliability items) pair naturally with
    Substep A1, since that is the first real schema change.
```
---

# Implementation Log

## Substep A1 — Schema, migrations, and password hashing (completed July 4, 2026)

### What was done

Added the database columns and the password-hashing foundation that the rest of
Step A builds on. No login behavior changed yet (that is A2); this substep only
puts the account fields and hashing helpers in place and gives a safe way to set
a password.

- The `users` table now has `email`, `password_hash`, `created_at`, and
  `last_login_at`, and `institution_id` is now optional.
- The app can hash and verify passwords with Werkzeug.
- A `set-password` CLI command lets an operator set/reset any user's password
  securely (used to bootstrap the first admin).
- Seed users now have emails but no password (invited state) until a password
  is set.

### Why it was done this way

- **Email + password, invite-ready:** `email` is the future login identifier and
  `password_hash` is nullable on purpose — a `NULL` hash marks an "invited but
  not yet activated" account, which is exactly what the invite flow (A4) needs.
- **`institution_id` made optional:** for a commercial product it is no longer
  the login key, just an optional per-org employee number, so it can be blank.
- **Werkzeug hashing:** `generate_password_hash` / `check_password_hash` are
  already available through Flask (no new dependency) and salt each password.
- **`set-password` CLI instead of hard-coded hashes in `schema.sql`:** seeding
  real password hashes into source control would bake a known credential into
  the repo. Leaving seed users password-less and setting a password via a command
  keeps secrets out of the codebase and mirrors how a real admin will be created.

### Decision: full Alembic/Flask-Migrate deferred to its own step

The plan lists adopting Alembic/Flask-Migrate here. That was intentionally
**deferred to a dedicated migration step** because this app uses raw `psycopg2`
with no SQLAlchemy models; introducing Alembic is a sizable, independent change,
and doing it inside the auth schema change would risk destabilizing a working
app. Instead, A1 follows the project's existing, proven migration convention:
new columns are defined in `schema.sql` for fresh databases and added in place
for existing databases by a runtime-safety helper (`ensure_auth_columns`), the
same pattern already used by `ensure_transaction_columns` and
`ensure_barcode_sequence`. Adopting a formal migration framework remains
recommended as a separate infrastructure task.

### Modifications by file

```text
schema.sql
    - users table: added email TEXT NOT NULL UNIQUE, password_hash TEXT (nullable),
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, last_login_at TIMESTAMP.
    - users table: institution_id changed from "NOT NULL UNIQUE" to "UNIQUE" (optional).
    - Seed INSERT now includes emails (student@/faculty@/admin@example.edu);
      password_hash is left NULL (invited state), with a comment pointing to set-password.

app.py
    - Imported generate_password_hash / check_password_hash from werkzeug.security.
    - Added MIN_PASSWORD_LENGTH constant (8).
    - Added ensure_auth_columns(db): runtime-safety upgrade that adds the new
      users columns IF NOT EXISTS, drops NOT NULL on institution_id, and creates
      the unique email index (reusing the default users_email_key name so a fresh
      DB is untouched).
    - Added hash_password(), verify_password() (False on empty hash), and
      validate_password_strength() helpers.
    - init-db now also calls ensure_auth_columns(db).
    - Added the "set-password <email> <password>" Flask CLI command: validates
      strength, hashes, updates the row by email, and errors clearly if the
      password is too short or the email is unknown.
```

### Verification performed

```text
- python -m py_compile app.py: clean; no linter errors.
- Werkzeug hash round-trip: correct password verifies, wrong password rejected.
- Fresh DB (scratch database inv_a1_test):
    - init-db created all new columns with the expected nullability
      (email NOT NULL; password_hash / last_login_at nullable; institution_id nullable).
    - Seed users present with emails and NULL password_hash.
    - set-password with a valid password succeeded; the stored hash verifies.
    - set-password rejected a too-short password and an unknown email.
    - Re-running init-db succeeded (idempotent).
- Legacy upgrade path: on a pre-auth users table, ensure_auth_columns added the
  new columns, made institution_id nullable, and preserved the existing row.
- Scratch database dropped after testing; the real database was never touched.
```

### Follow-ups this unlocks / requires

```text
- A2 will use verify_password() and last_login_at in the rewritten /login.
- A dedicated migration-framework (Alembic/Flask-Migrate) step is recommended
  before the schema grows much further.
```

## Substep A2 — Real login (email + password) (completed July 4, 2026)

### What was done

Replaced the institution-ID + login-type login with a real email + password
login, and made all privileges derive from the account's `role` instead of a
selectable login mode.

- `/login` now authenticates by email + password (using A1's `verify_password`).
- A single generic error ("Invalid email or password") is shown for every
  failure case.
- The `login_mode` concept is fully removed from the app.
- Successful login records `last_login_at` and stores a minimal session.

### Why it was done this way

- **Generic failure message:** the same message is returned for unknown email,
  wrong password, inactive account, and "invited but no password set yet", so
  the login form never reveals which emails are registered.
- **Role-only authorization:** letting a user pick "Administrator" at login was
  a privilege-escalation footgun. Privileges now come solely from `users.role`,
  which is set by an admin — the user cannot choose their own access level.
- **Session fixation guard + minimal session:** `session.clear()` runs before
  the new session is set, and only `user_id`, `user_name`, `user_role`, and
  `email` are stored.
- **Case-insensitive email:** login matches on `LOWER(email)` so capitalization
  in the typed email does not block a valid user.

### Modifications by file

```text
app.py
    - Removed the ELEVATED_LOGIN_MODES constant.
    - require_admin / require_system_admin: removed login_mode checks; they now
      test only user_role (elevated roles / administrator).
    - allowed_user_roles_to_manage: removed login_mode checks; administrators
      manage {student, faculty}, faculty manage {student}.
    - Rewrote /login: reads email + password, looks up by LOWER(email) with
      is_active = TRUE, verifies the password hash, returns a generic 401 on any
      failure, updates last_login_at, and stores user_id/user_name/user_role/email
      in the session (no more institution_id or login_mode).

templates/login.html
    - Replaced the "Login Type" dropdown and "Institution ID" field with Email
      and Password inputs (type=email / type=password, appropriate autocomplete).

templates/base.html
    - Navigation now keys off user_role only (removed the login_mode conditions
      on the elevated menu and on the Database Status link).
```

### Verification performed

```text
On a scratch database (inv_a2_test), via the Flask test client (CSRF disabled
for the test only, since the client sends no token):
    - Correct admin login -> 302 to /dashboard; session role=administrator,
      email set, no login_mode key.
    - Admin can open /admin/users (200) and /db-status (200).
    - Login with the email in different case still succeeds.
    - Wrong password / unknown email / inactive account / no-password-set all
      return 401 with the generic "Invalid email or password" message.
    - Student login is blocked from /admin/users and /db-status (302 redirect)
      but can open /items (200).
    - /logout is POST-only (GET -> 405, POST -> 302).
    - last_login_at is populated after a successful login.
    - Scratch database dropped afterward; the real database was never touched.
python -m py_compile app.py: clean; no linter errors on app.py, login.html, base.html.
```

### Known interim state (resolved in A4)

```text
Because A1 made users.email NOT NULL, the existing admin "create user" route
(admin_user_new / templates/user_new.html) will fail until A4, since it does not
set an email yet. This is expected: A4 rewrites account creation as the
invite flow (name + email + role, password set by the user). Until then, use the
schema seed users plus the set-password CLI to create/activate accounts.
```

## Substep A3 — Signed token utility + email helper (completed July 4, 2026)

### What was done

Added the plumbing the invite (A4) and password-reset (A5) flows depend on: a
signed, expiring token utility and a `send_email()` helper. No routes use them
yet; this substep only introduces and tests the helpers.

- `make_token(user_id, purpose)` / `read_token(token, purpose, max_age)` create
  and validate tamper-proof, time-limited action tokens.
- `send_email(to, subject, body)` delivers transactional mail, logging the
  message to the console when no provider is configured.

### Why it was done this way

- **itsdangerous, no new dependency:** it ships with Flask, and
  `URLSafeTimedSerializer` gives signed + timestamped tokens with no database
  table to store or clean up.
- **Purpose baked into the token:** the token embeds `purpose` ("invite" or
  "reset") so an invite link cannot be replayed as a reset (or vice versa).
  `read_token` rejects any purpose mismatch.
- **Uniform rejection:** tampering, expiry, and purpose mismatch all return
  `None`, so callers have a single "invalid link" path.
- **Signed with SECRET_KEY:** rotating the key invalidates all outstanding
  links, which is the desired safety behavior.
- **Fail loud in production:** if `EMAIL_PROVIDER` is set but no integration is
  wired, `send_email()` raises instead of silently pretending to send — so a
  misconfigured production deploy is obvious rather than dropping invite/reset
  mail. With no provider set (development), it logs the full message/link.

### Modifications by file

```text
app.py
    - Imported URLSafeTimedSerializer and BadData from itsdangerous.
    - Added constants: INVITE_TOKEN_MAX_AGE (72h), RESET_TOKEN_MAX_AGE (1h),
      and EMAIL_PROVIDER (from env; unset = log-only dev mode).
    - Added get_token_serializer(), make_token(user_id, purpose),
      and read_token(token, purpose, max_age).
    - Added send_email(to, subject, body): logs in development; raises
      NotImplementedError if EMAIL_PROVIDER is set (provider not wired yet).
```

### Verification performed

```text
- python -m py_compile app.py: clean; no linter errors.
- A valid "invite" token read back the correct user_id.
- Reading an "invite" token with purpose "reset" returned None (no cross-use).
- An expired token (max_age=0) returned None.
- A tampered token returned None.
- send_email() logged the full message in development and returned True.
```

### Follow-ups this unlocks

```text
- A4 uses make_token(..., "invite") + send_email() to send set-password links,
  and read_token(..., "invite", INVITE_TOKEN_MAX_AGE) to validate them.
- A5 uses the same helpers with purpose "reset" and RESET_TOKEN_MAX_AGE.
- Before production, wire a real provider inside send_email() (SES/SendGrid/SMTP)
  and set EMAIL_PROVIDER accordingly.
```

## Substep A4 — Invite flow (admin creates users) (completed July 4, 2026)

### What was done

Rewrote account creation as an invite flow and added the page where an invited
user sets their own password. This also resolves the interim breakage noted in
A2 (admin user creation failing because email was required but not collected).

- Admin "Add User" now collects name + email + role (+ optional institution ID),
  creates the account with no password, and emails a "set your password" link.
- New public route `/set-password/<token>` lets the invited user choose a
  password after validating the signed invite token.
- Admins can resend an invite to a still-pending user from the Manage Users list.

### Why it was done this way

- **Invite-only, no self-service:** matches the locked product decision. An admin
  creates the account; the user proves control of their email by using the link,
  and chooses their own password (the admin never sets or sees it).
- **password_hash left NULL = "invited/pending":** reuses the A1 design so the
  account cannot log in until the link is used; the Manage Users list shows this
  as "(invited)".
- **institution_id optional / stored as NULL when blank:** it is no longer the
  login key, and NULL (not "") avoids false uniqueness collisions.
- **Email normalized to lowercase** on creation to match the case-insensitive
  login lookup from A2.
- **Resend restricted:** only a manageable, still-pending account can be
  re-invited; activated users must use password reset (A5) instead.
- **No login required on /set-password:** the signed token is the credential;
  it is validated for the "invite" purpose and expiry on both GET and POST.

### Modifications by file

```text
app.py
    - Added send_invite(user_id, email): mints an "invite" token, builds the
      set-password link (APP_BASE_URL or request host), and sends the email.
    - Rewrote admin_user_new: collects name + email + role (+ optional
      institution_id), inserts with password_hash NULL (RETURNING id), sends the
      invite, and handles duplicate email/institution_id (IntegrityError -> 400).
    - Added route /set-password/<token> (GET/POST): validates the invite token
      and active user, enforces password strength + confirmation match, sets
      password_hash, then redirects to login. Invalid/expired token -> 400.
    - Added route /admin/users/<id>/resend-invite (POST): re-invites a
      manageable, still-pending account.
    - admin_users query now also selects email and "password_hash IS NULL AS
      invite_pending".

templates/user_new.html
    - Fields are now Full Name + Email + optional Institution ID + Role +
      Department; submit button reads "Create User & Send Invite".

templates/set_password.html (new)
    - Password + confirm form for invited users; shows an "invalid/expired link"
      state when the token does not resolve. Navigation hidden (anonymous page).

templates/admin_users.html
    - Added Email column; Institution ID now shows "Not set" when blank.
    - Status shows "Active (invited)" for pending accounts.
    - Added a "Resend invite" button for active, pending, manageable users.
```

### Verification performed

```text
On a scratch database (inv_a4_test), Flask test client (CSRF disabled for the
test; send_email stubbed to capture messages):
    - Admin creates a faculty user -> 302; one invite email captured; email
      stored lowercased with password_hash NULL.
    - Duplicate email -> 400; admin creating an "administrator" -> 400
      (not an allowed role for the admin to create here).
    - GET /set-password/<valid token> -> 200 with the form; GET with a bad token
      -> 400 "invalid/expired" state.
    - POST with mismatched passwords -> 400 ("do not match"); weak password ->
      400; valid matching password -> 302 to /login.
    - The newly activated faculty user can then log in successfully.
    - Resend invite for a pending student -> 302 and another email sent.
    - Scratch database dropped afterward; the real database was never touched.
python -m py_compile app.py: clean; no linter errors on the changed files.
```

### Resolves

```text
The A2 "known interim state" (admin user creation broken by the NOT NULL email
column) is now fixed: creation collects an email and sends an invite.
```

---

## Implementation Log — A5 (Forgot / reset password) — 2026-07-04

### What was built

A self-service password-reset flow so users who forget their password can regain
access without an admin. It reuses the A3 signed-token plumbing with the "reset"
purpose (1-hour expiry) and re-adds the "Forgot password?" link to the login page.

### How it works

- **/forgot-password (GET/POST):** GET shows an email form. POST looks up an
  active user by (case-insensitive) email; if found, it emails a reset link. It
  ALWAYS renders the same "if an account exists, we've sent a link" confirmation,
  so the endpoint cannot be used to enumerate which emails are registered.
- **/reset-password/<token> (GET/POST):** the signed "reset" token is the
  credential (no login required). The token is validated for purpose "reset" and
  the 1-hour expiry, and the referenced user must still be active. GET shows the
  new-password form; POST enforces password strength + confirmation match, writes
  the new password_hash, and redirects to login. An invalid/expired token (or an
  unknown/inactive user) renders a 400 "link not valid" state.

### Why these choices

- **Same generic response for known/unknown emails:** prevents account
  enumeration via the reset form (a standard auth-hardening requirement).
- **Short 1-hour token lifetime (RESET_TOKEN_MAX_AGE):** a reset link is more
  sensitive than an invite, so it expires quickly; reuses the A3 helpers rather
  than inventing new token logic.
- **No login required on /reset-password:** by definition the user cannot log in;
  the signed, purpose-scoped, time-limited token is the proof of control.
- **Reuses validate_password_strength + hash_password:** identical password
  rules and hashing as A1/A4 for consistency.

### Modifications by file

```text
app.py
    - Added send_reset(user_id, email): mints a "reset" token, builds the
      reset-password link (APP_BASE_URL or request host), and sends the email.
    - Added route /forgot-password (GET/POST): generic-response email lookup that
      only dispatches a reset email when an active account matches.
    - Added route /reset-password/<token> (GET/POST): validates the "reset" token
      and active user, enforces password strength + confirmation match, updates
      password_hash, then redirects to login. Invalid/expired token -> 400.

templates/forgot_password.html (new)
    - Email form; after submit shows the generic "if an account exists..."
      confirmation. Navigation hidden (anonymous page).

templates/reset_password.html (new)
    - New-password + confirm form; shows an "invalid/expired link" state when the
      token does not resolve. Navigation hidden (anonymous page).

templates/login.html
    - Re-added the "Forgot password?" link (points at /forgot-password).
```

### Verification performed

```text
On a scratch database (inv_a5_test), Flask test client (CSRF disabled for the
test; send_email stubbed to capture messages):
    - POST /forgot-password with an unknown email -> 200 generic page, 0 emails
      sent (no enumeration).
    - POST /forgot-password with a real email -> 200 generic page, 1 email
      captured containing a /reset-password/<token> link.
    - GET /reset-password/<valid token> -> 200 with the form.
    - POST with mismatched passwords -> 400 ("do not match"); weak password ->
      400; valid matching password -> 302 to /login.
    - After reset: login with the NEW password -> 302; login with the OLD
      password -> 401.
    - GET /reset-password/<garbage token> -> 400 "invalid or has expired" state.
    - GET /login contains the "Forgot password?" link.
    - Scratch database dropped afterward; the real database was never touched.
python -m py_compile app.py: clean; no linter errors on the changed files.
```

---

## Implementation Log — A6 (Tests for authentication) — 2026-07-04

### What was built

A pytest suite that exercises the whole authentication surface built in A1–A5,
so future changes can't silently regress login, invites, resets, or access
control. 20 tests, all passing.

### How it works

- **Throwaway database:** the suite runs against a dedicated database
  (``inventory_test`` by default, overridable with ``TEST_DATABASE_URL``). A
  session-scoped fixture drops/recreates it, applies schema.sql, and runs
  ensure_auth_columns; it is dropped again at the end. The real dev/prod
  database is never touched.
- **Known state per test:** a ``users`` fixture TRUNCATEs and reseeds a fixed
  set of accounts before each test — admin, faculty, student, an inactive
  student, and an invited (password_hash NULL) student — and returns their ids,
  emails and plaintext passwords.
- **Email capture:** a ``captured_emails`` fixture monkeypatches
  ``app.send_email`` so invite/reset links can be read out of the message body
  instead of being logged/sent.
- **CSRF:** disabled for the test client (WTF_CSRF_ENABLED = False) so the tests
  target auth logic; CSRF itself is covered by Step B.

### Why these choices

- **Real Postgres, not a mock/SQLite:** the app uses raw psycopg2 and
  Postgres-specific SQL (sequences, TRUNCATE ... RESTART IDENTITY, TIME(0));
  testing against real Postgres keeps the tests honest.
- **Reseed per test (function scope):** each test is independent and order does
  not matter; failures are easy to localize.
- **Direct token unit tests + full HTTP-flow tests:** token purpose/expiry are
  verified at the helper level (fast, precise) and end-to-end through the routes
  (proves the wiring), covering both layers.

### Files added

```text
tests/conftest.py
    - sys.path + DATABASE_URL/SECRET_KEY setup (before app import), test-DB
      create/drop, per-test app config, users reseed, client, captured_emails,
      and a login() helper fixture.
tests/test_auth.py
    - 20 tests (see coverage below).
requirements.txt
    - added pytest>=8.0,<9.0.
```

### Coverage

```text
Login:          success -> /dashboard; session is set; wrong password -> 401;
                unknown email -> 401; inactive user -> 401; invited user with no
                password -> 401.
Invite flow:    admin creates user -> invite email; set-password link works;
                new user can then log in. Bad set-password token -> 400.
Reset tokens:   round-trips for the correct purpose; rejected for wrong purpose;
                rejected when expired (negative max_age); rejected when tampered.
Forgot/reset:   real email -> working reset link that changes the password (old
                fails, new works); unknown email -> no email sent.
Auth gate:      /dashboard, /items, /scan, /transactions, /admin/users all
                redirect to /login when logged out.
Roles:          student blocked from /admin/users and /admin/users/new
                (-> /dashboard, no email); admin and faculty can open
                /admin/users; faculty blocked from /db-status (system-admin only).
```

### Verification performed

```text
.venv/bin/python -m pytest tests/ -v  ->  20 passed in ~5.5s.
The test database is created and dropped by the suite; the development/
production database is never touched. No linter errors on the new files.
```

### How to run

```text
# Requires a local PostgreSQL the current user can create databases on.
pip install -r requirements.txt
python -m pytest tests/ -v
# Optional: point at a specific server/name
TEST_DATABASE_URL=postgresql://localhost/inventory_test python -m pytest tests/
```

---

## Implementation Log — Step C (Session idle-timeout + admin re-auth) — 2026-07-04

### What was built

Three session-hardening measures for shared/lab computers and public exposure:
1. **Idle-timeout with a sliding window** — sessions expire after inactivity but
   active users are never logged out mid-task.
2. **Admin re-auth ("sudo mode")** — destructive user-management actions require
   a fresh password re-entry.
3. **Failed-login cooldown** — a lightweight per-process lockout after repeated
   failures (a safety net ahead of the Redis-backed limiter in Step D).

### How it works

- **Idle-timeout:** `PERMANENT_SESSION_LIFETIME` is set from
  `SESSION_IDLE_MINUTES` (default 30) and sessions are marked `permanent` at
  login. Flask signs the session cookie with a timestamp and rejects it once it
  is older than this lifetime. `SESSION_REFRESH_EACH_REQUEST = True` re-issues
  the cookie with a fresh timestamp on every response, so the window slides
  forward while the user is active; a session left idle past the timeout is
  rejected and `require_login()` redirects to /login.
- **Admin re-auth:** `mark_sudo()` stamps `session["sudo_at"]` on login and on a
  successful re-auth; `has_fresh_sudo()` treats it as valid for
  `SUDO_MODE_MAX_AGE` seconds (default 300). `require_sudo()` (used by the
  deactivate and delete routes) redirects to `/reauth?next=/admin/users` when
  the stamp is stale. `/reauth` verifies the current user's password, re-stamps
  sudo, and returns to a validated same-site `next` path.
- **Failed-login cooldown:** an in-memory dict counts consecutive failures per
  email; after `LOGIN_MAX_ATTEMPTS` (default 5) further attempts return HTTP 429
  for `LOGIN_LOCKOUT_SECONDS` (default 300), even with the correct password. A
  successful login clears the counter.

### Why these choices

- **Flask's built-in signed-cookie expiry (no server-side session store):** keeps
  the app stateless and dependency-free while still enforcing idle expiry; the
  sliding refresh is a one-line config (`SESSION_REFRESH_EACH_REQUEST`).
- **Sudo re-stamped at login, 5-minute freshness:** the common case (delete right
  after logging in) is friction-free; the prompt only appears on a session that
  has been sitting idle, which is exactly the shared-computer risk.
- **safe_next() allow-list:** the `?next=` target must be a same-site relative
  path (starts with "/", not "//") to prevent an open-redirect via re-auth.
- **In-memory lockout, clearly scoped:** per-process and reset on restart — a
  deliberate lightweight net. Step D (Flask-Limiter + Redis) is the robust,
  shared defense; this avoids overlap while still slowing trivial guessing.
- **Everything env-configurable:** SESSION_IDLE_MINUTES, SUDO_MODE_MAX_AGE,
  LOGIN_MAX_ATTEMPTS, LOGIN_LOCKOUT_SECONDS.

### Modifications by file

```text
app.py
    - Imports: added `time` and `datetime.timedelta`.
    - Config: SESSION_IDLE_MINUTES, SUDO_MODE_MAX_AGE, LOGIN_MAX_ATTEMPTS,
      LOGIN_LOCKOUT_SECONDS constants; PERMANENT_SESSION_LIFETIME and
      SESSION_REFRESH_EACH_REQUEST set on app.config.
    - Added failed-login store + helpers: is_locked_out(), record_failed_login(),
      clear_failed_login().
    - Added session helpers: mark_sudo(), has_fresh_sudo(), safe_next(),
      require_sudo().
    - login route: lockout check (429), session.permanent = True, mark_sudo(),
      clear_failed_login() on success / record_failed_login() on failure.
    - Added route /reauth (GET/POST): confirms the current user's password and
      re-stamps sudo, then redirects to a validated next path.
    - admin_user_deactivate and admin_user_delete now call require_sudo().

templates/reauth.html (new)
    - Password-confirmation form with a hidden next field and CSRF token.
```

### Verification performed

```text
Added 11 tests to tests/test_auth.py (suite now 31 tests, all passing):
    - Idle-timeout config: PERMANENT_SESSION_LIFETIME matches SESSION_IDLE_MINUTES;
      SESSION_REFRESH_EACH_REQUEST is True; login marks the session permanent and
      stamps sudo.
    - Lockout: LOGIN_MAX_ATTEMPTS failures -> the next attempt (even correct) is
      429; a success before the threshold resets the counter.
    - Re-auth: a stale-sudo deactivate redirects to /reauth and does NOT change
      the account; with fresh sudo it succeeds; /reauth GET renders; wrong
      password -> 401; correct password re-stamps sudo and redirects; an external
      next is ignored (open-redirect blocked); /reauth requires login.
.venv/bin/python -m pytest tests/ -v  ->  31 passed. py_compile clean; no linter
errors. (A conftest fixture clears the in-memory lockout store between tests.)
```

### Notes / follow-ups

```text
- The in-memory lockout is per-process; with multiple Gunicorn workers or hosts,
  Step D's shared-store limiter supersedes it.
- Re-auth currently gates deactivate + delete. Activate and create are treated as
  non-destructive; extend require_sudo() to more actions if desired.
```

---

## Implementation Log — Step D (Rate limiting & brute-force protection) — 2026-07-07

### What was built

Flask-Limiter is initialized (keyed by client IP) and applied to the sensitive
endpoints. Exceeding a limit returns a clear HTTP 429 page. All limits and the
storage backend are environment-configurable.

### How it works

- **Limiter:** `Limiter(get_remote_address, app=app, default_limits=[],
  storage_uri=RATELIMIT_STORAGE_URI, headers_enabled=True)`. There are no global
  default limits; each sensitive route opts in with `@limiter.limit(...)`.
  `limiter.enabled` follows `RATELIMIT_ENABLED`.
- **Per-route limits (env-configurable):**
    - `POST /login`            -> RATELIMIT_LOGIN    (default "10 per minute")
    - `POST /forgot-password`  -> RATELIMIT_PASSWORD (default "5 per minute")
    - `POST /set-password/<token>`   -> RATELIMIT_PASSWORD
    - `POST /reset-password/<token>` -> RATELIMIT_PASSWORD
    - `/scan`                  -> RATELIMIT_STOCK    (default "60 per minute")
    - `/items/<barcode>/stock` -> RATELIMIT_STOCK
  The auth limits use `methods=["POST"]` so only the state-changing verb is
  counted; the stock endpoints are limited on all methods (scraping is a GET
  concern too).
- **429 response:** an `@app.errorhandler(429)` renders `templates/rate_limited.html`
  ("Too Many Attempts") instead of a raw error.
- **Storage:** `RATELIMIT_STORAGE_URI` defaults to `memory://` (single process).
  Point it at Redis (e.g. `redis://host:6379`) in production so limits are shared
  across Gunicorn workers/hosts.

### Why these choices

- **IP-keyed, per-route opt-in:** the login lockout (Step C) is per-email; the
  limiter is per-IP, so together they cover both a single account being targeted
  and one client hammering many accounts. Opt-in avoids accidentally throttling
  read-only pages.
- **Two tiers (auth vs stock):** credential/password endpoints get strict limits;
  stock endpoints get a higher bound so legitimate lab activity is unaffected
  while still capping scraping/abuse.
- **Everything env-configurable + a disable switch:** operators tune limits per
  deployment, and `RATELIMIT_ENABLED=false` (used in the test suite) turns it off
  cleanly.

### Modifications by file

```text
requirements.txt
    - added Flask-Limiter>=3.5,<4.0.

app.py
    - Imports: Limiter, get_remote_address.
    - Config: RATELIMIT_ENABLED, RATELIMIT_STORAGE_URI, RATELIMIT_LOGIN,
      RATELIMIT_PASSWORD, RATELIMIT_STOCK.
    - Initialized `limiter` (IP-keyed, no default limits, headers enabled) and
      set limiter.enabled from RATELIMIT_ENABLED.
    - Added @app.errorhandler(429) -> rate_limited.html.
    - Decorated login, forgot_password, set_password, reset_password (POST) and
      scan, item_stock (all methods) with @limiter.limit(...).

templates/rate_limited.html (new)
    - Friendly "Too Many Attempts" page (navigation hidden).

tests/conftest.py
    - Rate limiting disabled by default for tests (so other tests are not
      throttled) and the limiter storage is reset around each test.
```

### Verification performed

```text
Added 5 tests to tests/test_auth.py (suite now 36 tests, all passing):
    - Rate-limit settings are configurable and the limiter exists.
    - 12 rapid logins from one IP (distinct emails, so the per-email lockout is
      not the cause) -> a 429 appears; early attempts are 401.
    - The 429 body is the friendly "Too Many Attempts" page.
    - A few normal logins from one IP are never 429.
    - forgot-password trips its stricter 5/min limit.
.venv/bin/python -m pytest tests/ -v  ->  36 passed.
Manual env check: RATELIMIT_LOGIN="2 per minute" -> statuses [401, 401, 429, 429]
    (throttled after exactly 2 attempts), confirming env configurability.
py_compile clean; no linter errors.
```

### Notes / follow-ups

```text
- memory:// is per-process. Set RATELIMIT_STORAGE_URI to Redis for multi-worker /
  multi-host production so the limit counts are shared.
- Consider limiting a few more write endpoints (item create/edit, user actions)
  if abuse is observed; the pattern is a one-line @limiter.limit decorator.
```

