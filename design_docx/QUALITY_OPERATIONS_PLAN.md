# Quality & Operations Plan (Phase 4)

Date: July 9, 2026

Project: Katz Nursing School Inventory Management System (going to market as a product)

## Purpose

This document is the fourth step toward a safe, maintainable public deployment.
Phase 1 (`SECURITY_AND_AUTH_PLAN.md`) hardened authentication; Phase 2
(`DATA_MIGRATIONS_RELIABILITY_PLAN.md`) made the data layer production-grade;
Phase 3 (`DEPLOYMENT_INFRASTRUCTURE_PLAN.md`) covers hosting, secrets, static
serving, Gunicorn tuning, and CI/CD.

Phase 4 makes the running product **observable and safe to change**: expand the
automated test suite so regressions cannot ship silently, add error monitoring and
structured logging so production failures are visible, expose a proper health
endpoint for uptime monitoring, and (optionally, longer-term) split the monolithic
`app.py` into blueprints and a service layer so future features are easier to
add safely.

As in the earlier plans, every improvement is broken into small, independently
testable substeps with `Files:` / `Add:` / `Verify:` sections, and each substep
should get a dated `PROGRESS_REPORT.md` entry before moving on.

---

## Product context and locked decisions

The earlier decisions still hold (single-tenant, email + password, invite-only,
raw `psycopg2`, Alembic migrations, Gunicorn + WhiteNoise in production). Phase 4
adds these quality/ops decisions:

```text
Test database:     Real PostgreSQL throwaway DBs in CI and locally (never SQLite).
                   The existing conftest.py pattern is kept.
CI gate:           pytest + migration up/down must pass on every PR before merge.
                   (`.github/workflows/ci.yml` already exists from Phase 3 M1.)
Error monitoring:  Sentry for uncaught exceptions + Flask integration; DSN via env.
Logging:           Structured JSON logs to stdout/stderr (platform log drain).
                   Request ID per request for correlation with Sentry events.
Health check:      Unauthenticated GET /health (or /healthz) returning JSON;
                   optional lightweight DB ping. Separate from /db-status (admin UI).
Refactor timing:   Blueprint split is NOT a launch blocker; do it when feature
                   velocity or contributor count makes the monolith painful.
```

---

## Current quality & operations behavior (the starting point)

What already exists:

```text
Automated tests (54 passing as of Phase 2 H3):
    tests/test_auth.py                  (37) — login, invite/reset, roles, sudo,
                                              lockout, rate limits
    tests/test_migrations.py            (3)  — Alembic upgrade/downgrade, indexes
    tests/test_item_form.py             (5)  — expiration DATE add/edit/detail/label
    tests/test_transactions_pagination.py (9)— pagination math, EXPLAIN index usage
    tests/conftest.py                        — shared DB fixtures, CSRF off in tests

CI (Phase 3 M1):
    .github/workflows/ci.yml            — pytest on push/PR + migration up/down
    .github/workflows/deploy.yml        — deploy on green main (if configured)

Application structure:
    app.py                              (~1,980 lines) — routes, auth, DB, stock,
                                              transactions, admin, CLI, all in one file
    process_stock_transaction()         — shared stock logic (scan + QR stock)

Observability today:
    /db-status                          — HTML page for system administrators only;
                                        counts users/items/transactions; NOT suitable
                                        for load balancers or uptime monitors
    Flask/Werkzeug default logging      — unstructured text to stderr
    No Sentry or external error tracking
    No dedicated /health JSON endpoint
```

Gaps this phase fixes:

```text
1. Test coverage holes.
   Auth, migrations, item forms, and transaction pagination are well covered, but
   stock add/remove (process_stock_transaction), item-manager permissions (faculty
   vs student on /items/new, /scan), CSV exports, and admin user deactivate/delete
   flows lack dedicated regression tests. A stock bug could ship despite 54 green
   tests.

2. No production error visibility.
   Uncaught exceptions in Gunicorn workers are only visible in platform logs if
   someone is watching. There is no alerting, grouping, or stack-trace collection.

3. No operator-friendly health signal.
   Uptime monitors and load balancers need a fast, unauthenticated 200/503 JSON
   endpoint. /db-status requires admin login and returns HTML.

4. Monolithic app.py.
   Every feature change touches the same ~2,000-line file. This is manageable for
   a single maintainer today but becomes risky as the product grows.
```

---

## Status of the Phase 4 items

| # | Improvement | Priority | Effort | Plan step | Status |
|---|-------------|----------|--------|-----------|--------|
| 1 | Automated test suite (pytest) for auth, stock, and permissions | High | M | Step N | **Partial** — 54 tests exist; stock/permissions/export gaps remain |
| 2 | Error monitoring (Sentry) + structured logging | High | S | Step O | To do |
| 3 | Health-check endpoint + uptime monitoring | Medium | S | Step P | To do |
| 4 | Split `app.py` into blueprints + service layer | Medium | L | Step Q | To do (post-launch acceptable) |

Cross-reference — already done elsewhere:

```text
CI runs pytest on every PR          -> Phase 3 M1 (.github/workflows/ci.yml)
Auth + role tests (37 cases)        -> Phase 1 A6 (tests/test_auth.py)
Migration tests (3 cases)           -> Phase 2 F5 (tests/test_migrations.py)
```

---

## External dependencies

```text
Sentry account (free tier is sufficient to start) + SENTRY_DSN environment variable.
An uptime monitor (UptimeRobot, Better Stack, Pingdom, or the host's built-in
    health checks) pointed at https://<domain>/health once Step P is live.
(Optional) Log drain / search on the hosting platform (Render/Railway/etc.) —
    structured JSON logs are readable without a separate tool at first.
```

---

## Recommended execution order

Observability (O, P) should land soon after the first production deploy so real
users are covered. Test expansion (N) can run in parallel with early production
use. The blueprint refactor (Q) is the largest change and should not block launch.

```text
Step N  Expand pytest coverage (stock, permissions, exports)     [can start now]
Step O  Sentry + structured logging                              [soon after deploy]
Step P  /health endpoint + uptime monitor                        [soon after deploy]
Step Q  Blueprint / service-layer refactor                       [when needed; not a blocker]
```

---

## Step N — Expand automated test suite (pytest)

Effort: M. A strong foundation exists (54 tests + CI); this step closes the
remaining gaps called out in the production-readiness review. Split into four
substeps (N1–N4).

### Substep N1 — Stock / scan regression tests

Files:

```text
tests/test_stock.py   (new)
```

Add:

```text
Dedicated tests for process_stock_transaction() via the HTTP layer (same pattern
as the manual Step 7/8 verification), covering BOTH entry points:
    - POST /scan (barcode in form body)
    - POST /items/<barcode>/stock (barcode in URL)
Cases:
    - Add stock increases quantity and creates a transaction row.
    - Remove stock decreases quantity and creates a transaction row.
    - Cannot remove more than available (400, no DB change).
    - Missing lab instructor / topic / notes rejected (400).
    - Unknown barcode returns 404 on scan; 404 on item_stock.
    - Transaction row records user_id, transaction_type, quantity, date, time,
      lab_instructor, topic_of_day, notes.
Use the shared conftest fixtures (faculty or student login, seeded users).
```

Verify:

```text
pytest tests/test_stock.py -v  -> all green.
Full suite still passes (pytest -q).
```

### Substep N2 — Permissions regression tests

Files:

```text
tests/test_permissions.py   (new)
```

Add:

```text
Route-level permission checks beyond what test_auth.py already covers:
    - Student can GET /items, /items/<barcode>, /scan, /items/<barcode>/stock,
      /transactions but NOT /items/new, /items/<id>/edit, /admin/users,
      /db-status, /reports/export.
    - Faculty can add/edit items, access /admin/users (student management),
      /items/<barcode>/label, /items/<barcode>/qr.png; cannot access /db-status
      (system admin only).
    - Administrator can access /db-status and /reports/export.
    - Faculty cannot deactivate/delete faculty or administrator accounts.
    - Administrator cannot deactivate/delete the protected administrator account.
Use GET for page access (302/403/200) and POST with CSRF disabled (conftest) for
    mutating actions where a smoke POST is enough.
```

Verify:

```text
pytest tests/test_permissions.py -v  -> all green.
No test relies on hard-coded seeded institution IDs from schema.sql demo users;
    use the conftest `users` fixture emails/passwords.
```

### Substep N3 — Export and report smoke tests

Files:

```text
tests/test_exports.py   (new)
```

Add:

```text
Smoke tests for CSV endpoints (logged-in admin or faculty as appropriate):
    - GET /transactions/export returns 200, text/csv, header row + data rows.
    - GET /transactions/export?item_id=<id> returns only matching rows.
    - GET /reports/export returns 200, text/csv, inventory columns present.
    - Unauthenticated requests redirect to /login.
Parse CSV with Python csv module; assert row counts match seeded data.
```

Verify:

```text
pytest tests/test_exports.py -v  -> all green.
Export responses are NOT paginated (full filtered set) — regression guard for H2.
```

### Substep N4 — Document the test contract in README

Files:

```text
README.md
```

Add:

```text
A "Running tests" section:
    pytest -q
    TEST_DATABASE_URL=... override for a different local Postgres
    Note that tests need a running PostgreSQL server (createdb permissions).
List what each test module covers (auth, stock, permissions, exports, migrations,
    item form, pagination).
Point to ci.yml: tests run automatically on every push/PR.
```

Verify:

```text
A new contributor can run the suite from README instructions alone.
```

---

## Step O — Error monitoring (Sentry) + structured logging

Effort: S. Makes production failures visible and debuggable. Split into three
substeps (O1–O3).

### Substep O1 — Add Sentry

Files:

```text
requirements.txt
app.py
.env.example
```

Add:

```text
Add sentry-sdk[flask] to requirements.txt.
Initialize Sentry only when SENTRY_DSN is set (no-op in local dev without DSN):
    - integrations: FlaskIntegration
    - environment: APP_ENV
    - traces_sample_rate: low default (e.g. 0.1) or 0 in dev
    - send_default_pii: False (inventory app; do not ship user emails to Sentry
      unless explicitly decided later)
Capture unhandled exceptions automatically; optionally capture failed 5xx responses.
Document SENTRY_DSN in .env.example (commented / empty by default).
```

Verify:

```text
With SENTRY_DSN unset: app starts normally, no Sentry network calls.
With a test DSN (or Sentry dev project): a deliberate test exception appears in
    the Sentry dashboard.
py_compile clean; pytest suite still passes (Sentry must not break tests).
```

### Substep O2 — Structured request logging

Files:

```text
app.py
```

Add:

```text
Configure Python logging to emit JSON lines to stdout in production
    (APP_ENV=production), plain text in development.
Each request logs at INFO on completion:
    - method, path, status, duration_ms, remote_addr (or X-Forwarded-For)
    - a short request_id (uuid4) stored in flask.g for the request lifetime
Log WARNING for 4xx where useful; ERROR for unhandled exceptions (Sentry also
    receives these).
Do NOT log passwords, session cookies, or full CSRF tokens.
Use stdlib logging + a small JSON formatter (no heavy dependency required), OR
    python-json-logger if preferred.
Gunicorn access/error logs already go to stdout; avoid duplicating every field —
    the app log focuses on request context Sentry can correlate.
```

Verify:

```text
Local dev: readable text log lines on a few requests.
With APP_ENV=production (locally): log lines are valid JSON objects.
A 500 test route (dev only, or in a test) produces an ERROR log line + Sentry event.
```

### Substep O3 — Document observability setup

Files:

```text
README.md  (or DEPLOYMENT_INFRASTRUCTURE_PLAN.md observability appendix)
.env.example
```

Add:

```text
How to create a Sentry project, set SENTRY_DSN on the host, and verify the first
    event.
How to read structured logs on the hosting platform (Render/Railway log tail).
What is intentionally NOT logged (credentials, tokens).
```

Verify:

```text
Operator can follow the doc to enable Sentry on a staging deploy.
```

---

## Step P — Health-check endpoint + uptime monitoring

Effort: S. Gives load balancers and uptime services a simple signal. Split into
two substeps (P1–P2).

### Substep P1 — Add `/health` JSON endpoint

Files:

```text
app.py
templates/   (none — JSON only)
```

Add:

```text
GET /health  (or /healthz — pick one and document it)
    - No authentication required (safe: returns no secrets, no user data).
    - Returns JSON, e.g.:
        { "status": "ok", "database": "ok" }
    - Runs a lightweight DB check: SELECT 1 (or pool ping via get_db()).
    - HTTP 200 when app + DB are reachable; HTTP 503 when DB check fails.
    - Does NOT run heavy queries (no COUNT(*) on large tables).
Exclude from Flask-Limiter default limits if a monitor polls every 30–60s
    (or set a generous limit on this route only).
Keep /db-status as the human admin dashboard; /health is for machines only.
```

Verify:

```text
GET /health -> 200 {"status":"ok","database":"ok"} when Postgres is up.
Stop Postgres (or point at a bad DATABASE_URL in a scratch run) -> 503.
Endpoint works without a session cookie.
pytest: one test in tests/test_health.py (new) for 200 + JSON shape.
```

### Substep P2 — Wire uptime monitoring

Files:

```text
(no app code) — hosting / external monitor configuration
README.md or DEPLOYMENT_INFRASTRUCTURE_PLAN.md
```

Add:

```text
Document setting up an external uptime check:
    - URL: https://<domain>/health
    - Interval: 1–5 minutes
    - Alert: email/SMS/Slack on non-200 or timeout
If the host provides built-in health checks (Render health check path, Railway,
    etc.), point them at /health as well.
Record expected response time (<500ms) so alerts distinguish slow from down.
```

Verify:

```text
Manual curl https://<domain>/health returns 200 from outside the network.
Uptime monitor shows "up" after configuration.
A deliberate DB outage (staging) triggers an alert within one interval.
```

---

## Step Q — Split `app.py` into blueprints + service layer

Effort: L. Improves long-term maintainability; **not required before first public
launch**. Split into four substeps (Q1–Q4). Execute when feature work in `app.py`
becomes painful or a second contributor joins.

### Substep Q1 — Plan the module layout

Files:

```text
(design note in this plan or a short ARCHITECTURE.md — optional)
```

Add:

```text
Proposed package layout (example):
    inventory/
        __init__.py          create_app() factory; register blueprints; config
        db.py                get_db, connection helpers
        auth/                login, logout, reauth, forgot/reset, set-password
        items/               list, detail, new, edit, label, qr
        stock/               scan, item_stock, process_stock_transaction
        transactions/        list, export, filters, pagination helpers
        admin/               users CRUD, db-status
        reports/             inventory export
        services/            email, tokens, password, barcode generation
        cli.py               flask init-db, db-upgrade, set-password, check-config
Move constants (ELEVATED_ROLES, rate-limit strings) to config.py or __init__.
Keep one create_app() entry point so Gunicorn stays: gunicorn "inventory:create_app()"
    or a thin app.py that imports create_app.
```

Verify:

```text
Written plan reviewed; no code change yet. Test suite green before any move.
```

### Substep Q2 — Extract services (no route changes yet)

Files:

```text
services/email.py, services/tokens.py, services/passwords.py, etc.
app.py  (imports updated)
```

Add:

```text
Move pure helpers first (no Flask request context):
    - send_email, make_token/read_token
    - hash_password, verify_password, validate_password_strength
    - generate_next_item_barcode, parse_expiration_date
    - build_transaction_filter_clause, count_transaction_rows, get_transaction_rows
Run tests after each small extraction; behavior must be identical.
```

Verify:

```text
pytest -q full green after each extraction.
No circular imports; py_compile clean.
```

### Substep Q3 — Introduce blueprints

Files:

```text
auth/routes.py, items/routes.py, stock/routes.py, transactions/routes.py,
admin/routes.py, reports/routes.py
app.py or inventory/__init__.py
```

Add:

```text
One blueprint per area; register with url_prefix where natural (/admin, etc.).
Move routes in batches (auth first, then items, then stock, …).
Keep template names unchanged initially to minimize diff noise.
CSRF, limiter, and login guards stay on the same routes — only the registration
    location changes.
```

Verify:

```text
After each blueprint batch: pytest -q green; manual smoke of moved routes.
url_for endpoint names unchanged OR updated consistently in templates.
```

### Substep Q4 — Thin entrypoint + docs

Files:

```text
app.py              (becomes a few lines: from inventory import create_app; app = create_app())
Procfile            (confirm gunicorn target still works)
README.md
```

Add:

```text
Document the new package layout for contributors.
Confirm Gunicorn, Flask CLI (`flask --app app`), and pytest imports still work.
```

Verify:

```text
gunicorn app:app serves correctly.
flask --app app db-upgrade works.
Full pytest suite green.
No single file over ~400 lines except possibly transactions/admin if needed.
```

---

## Consolidated testing plan

```text
Local:
    pytest -q  (full suite after every substep)
CI (already wired):
    .github/workflows/ci.yml on every push/PR
    pytest + alembic upgrade head + alembic downgrade base
After Step O:
    Staging deploy + deliberate Sentry test event
After Step P:
    curl /health from outside; uptime monitor green
After Step Q (if done):
    Full regression + url_for/template link check
```

---

## Pre-launch quality checklist (Phase 4)

```text
[ ] pytest suite covers stock add/remove, permissions, and CSV exports (Step N)
[ ] CI blocks merge on failing tests (already true if branch protection enabled)
[ ] SENTRY_DSN set on production; test exception received in Sentry (Step O)
[ ] Structured JSON logs visible in platform log drain (Step O)
[ ] GET /health returns 200 with database ok; 503 when DB down (Step P)
[ ] External uptime monitor alerts on failure (Step P)
[ ] (Optional pre-launch) Blueprint refactor started only if team capacity allows (Step Q)
```

---

## Notes on sequencing with the rest of the roadmap

```text
Step N (tests) can start immediately and should be merged before heavy new features.
Steps O and P are high value right after the first production deploy (Phase 3 J).
Step Q is maintenance debt reduction — schedule after launch unless app.py edits
    become error-prone.
Phase 5 (compliance: audit trail, FERPA/privacy, accessibility, IT security review)
    builds on the observability from O and P (you need logs/alerts to operate).
The production-readiness canvas "Phase 2 — Quality & operations" maps to this
    document; update the canvas Status column as substeps complete.
```
