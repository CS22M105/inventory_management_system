# Data, Migrations & Reliability Plan (Phase 2)

Date: July 8, 2026

Project: Katz Nursing School Inventory Management System (going to market as a product)

## Purpose

This document is the second step toward a safe public deployment. Phase 1
(`SECURITY_AND_AUTH_PLAN.md`) hardened authentication, sessions, CSRF, and rate
limiting; all of its substeps are complete except HTTPS/HSTS, which is a
deploy-time toggle (Step E).

Phase 2 makes the **data layer** production-grade: schema changes stop running on
every request, the database can be recovered after a mistake or crash, large
tables stay fast, and dates are stored as real dates. As in the security plan,
every improvement is broken into small, independently testable substeps with
`Files:` / `Add:` / `Verify:` sections, and each substep should compile, pass a
manual check, and get a dated `PROGRESS_REPORT.md` entry before moving on.

This plan does **not** require splitting `app.py` into blueprints or adopting a
full ORM. The improvements below work on the current raw-`psycopg2` structure.

---

## Product context and locked decisions

The Phase 1 decisions still hold (single-tenant, one database per customer,
email + password, invite-only). Phase 2 adds these data-layer decisions:

```text
Database:        PostgreSQL (unchanged)
DB access:       Raw psycopg2 (no SQLAlchemy ORM added in this phase)
Migrations:      Alembic in "SQL migration" mode (op.execute / raw SQL),
                 NOT tied to SQLAlchemy models
Schema changes:  Delivered ONLY as migrations, never as per-request ALTER TABLE
Backups:         Managed PostgreSQL with automated backups + PITR preferred;
                 self-managed pg_dump + WAL archiving documented as the fallback
```

Why Alembic (not Flask-Migrate): Flask-Migrate is a thin wrapper around Alembic
that expects SQLAlchemy models to autogenerate migrations. This app uses raw
`psycopg2` with no models, so we adopt **Alembic directly** and write explicit
SQL migrations. This matches the note already recorded in the Phase 1 A1 log,
where adopting a migration framework was deliberately deferred to this phase.

---

## Current data behavior (the problem)

Current schema (`schema.sql`):

```sql
users (
    id SERIAL PRIMARY KEY,
    institution_id TEXT UNIQUE,          -- nullable (Phase 1)
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    department TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
)

items (
    id SERIAL PRIMARY KEY,
    barcode TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    bin_location TEXT NOT NULL,
    room TEXT NOT NULL,
    company TEXT,
    quantity INTEGER NOT NULL DEFAULT 0,
    minimum_quantity INTEGER NOT NULL DEFAULT 0,
    location TEXT,
    expiration_date TEXT DEFAULT '00/00/0000',   -- stored as TEXT
    notes TEXT
)

transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    item_id INTEGER NOT NULL REFERENCES items(id),
    transaction_type TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    transaction_date DATE NOT NULL DEFAULT CURRENT_DATE,
    transaction_time TIME(0) NOT NULL DEFAULT LOCALTIME(0),
    lab_instructor TEXT,
    topic_of_day TEXT,
    notes TEXT
)
-- No indexes beyond the primary keys and UNIQUE constraints.
```

Problems this phase fixes:

```text
1. Schema is mutated on every request.
   ensure_transaction_columns(db) and ensure_auth_columns(db) run ALTER TABLE /
   CREATE INDEX / UPDATE statements on ordinary page loads (dashboard, scan,
   transactions, items, login, admin). This is:
     - fragile   (a failed ALTER can break a normal page view)
     - slow       (extra DDL round-trips on the hot path)
     - racy       (concurrent requests issuing DDL under real traffic)
   Call sites today (app.py): ensure_transaction_columns at the transactions
   view, exports, and stock/scan paths; ensure_auth_columns at login, forgot,
   reset, set-password, admin user views, etc.

2. No backups / no recovery.
   One bad DELETE, a bad migration, or a host crash currently loses all
   inventory and the full audit (transactions) history. There is no restore path.

3. No pagination and no indexes.
   /transactions and /items run SELECT ... (no LIMIT) and fetchall() the whole
   table. transactions has no index on transaction_date, item_id, or user_id, and
   the list ORDER BY (transaction_date DESC, transaction_time DESC, id DESC) has
   no supporting index. Performance degrades as history grows.

4. expiration_date is TEXT with a '00/00/0000' sentinel.
   It cannot be compared, sorted, or used for "expiring soon" logic reliably, and
   the sentinel leaks into templates. It should be a real nullable DATE.
```

---

## Status of the Phase 2 items

| # | Improvement | Priority | Effort | Plan step |
|---|-------------|----------|--------|-----------|
| 1 | Replace per-request `ALTER TABLE` with real migrations (Alembic) | Critical | M | Step F (do first) |
| 2 | Automated DB backups + point-in-time recovery | High | S | Step I (before launch / at deploy) |
| 3 | Pagination + indexes on `transactions` (date / item / user) | High | M | Step H |
| 4 | Store `expiration_date` as a real `DATE` (not TEXT `'00/00/0000'`) | Medium | S | Step G |

---

## External dependencies to secure before launch

```text
Managed PostgreSQL with automated backups + PITR (preferred)
    - e.g. Amazon RDS / Aurora, Google Cloud SQL, Azure Database, Neon, Supabase.
    - Gives daily snapshots + write-ahead-log (WAL) point-in-time recovery with
      almost no application code.
    - Fallback (self-managed): pg_dump on a schedule + WAL archiving to object
      storage, plus a tested restore script.

A release/deploy step that runs migrations
    - Migrations run once per deploy ("alembic upgrade head" / "flask db upgrade"),
      NOT on every request. Needs a place in the deploy pipeline (release phase,
      entrypoint, or a one-off job) before the new app version serves traffic.

Off-host storage for backups
    - Backups must live on different storage than the primary DB so a host loss
      does not take the backups with it.
```

---

## Recommended execution order

Migrations come first because every other schema change in this phase is
delivered as a migration. Backups can be set up in parallel but must be verified
before launch.

```text
Step F  Adopt Alembic migrations; remove per-request ALTER TABLE   [do first]
Step G  Convert expiration_date TEXT -> real DATE (a migration)
Step H  Add indexes (migration) + server-side pagination
Step I  Automated backups + PITR + a tested restore runbook        [before launch]
```

---

## Step F — Replace per-request ALTER TABLE with real migrations (Alembic)

Effort: M. This is the foundation for Steps G and H. Split into five substeps
(F1–F5). Nothing in G/H should be written as an ad-hoc `ALTER` — it becomes an
Alembic revision instead.

### Substep F1 — Introduce Alembic (standalone, raw-SQL mode)

Files:

```text
requirements.txt              (add alembic)
alembic.ini                   (new)
migrations/                   (new: env.py, script.py.mako, versions/)
.env.example                  (document DATABASE_URL usage for migrations)
```

Add:

```text
Add alembic to requirements.txt and install it.
Run `alembic init migrations` to scaffold the migration environment.
Configure migrations/env.py to:
    - read DATABASE_URL from the environment (do NOT hardcode a URL in alembic.ini)
    - run in "offline" and "online" modes against that URL
    - target_metadata = None (we are not using SQLAlchemy models; migrations are
      explicit SQL via op.execute / op.create_index / op.add_column)
Keep alembic.ini free of secrets; the URL comes from the environment.
```

Verify:

```text
`alembic current` connects using DATABASE_URL and reports "no version" on a DB
    that has never been stamped.
`alembic revision -m "smoke"` creates an empty revision file under versions/.
py_compile / import of app.py is unaffected (Alembic is separate from the app).
```

### Substep F2 — Baseline the current schema

Files:

```text
migrations/versions/0001_baseline.py   (new)
```

Add:

```text
Author a baseline revision that represents the CURRENT production schema exactly
    as it exists after all Phase 1 changes (the users/items/transactions tables,
    the item_barcode_number_seq sequence, the users_email_key unique index, and
    all columns the ensure_* functions currently guarantee).
The baseline upgrade() should be safe to run on a brand-new empty database
    (CREATE TABLE ... etc.), and its downgrade() should drop what it created.
Provide a documented way to adopt the baseline on an EXISTING populated database
    without recreating tables: `alembic stamp 0001_baseline` (marks the DB as
    already at the baseline without running the CREATE statements).
```

Verify:

```text
Fresh empty DB: `alembic upgrade head` builds the full schema from nothing.
Existing DB (created by schema.sql today): `alembic stamp 0001_baseline` marks it
    at the baseline; a following `alembic upgrade head` is a no-op (no errors).
`schema.sql` remains as a readable reference/dev bootstrap, but the source of
    truth for schema changes is now the migrations directory.
```

### Substep F3 — Fold the ensure_*_columns logic into migrations and remove it from request paths

Files:

```text
app.py
migrations/versions/0002_ensure_columns_as_migration.py   (new, if the baseline
                                                            did not already include
                                                            everything ensure_* did)
```

Add:

```text
Confirm every column/index/default the ensure_* functions create is present in
    the baseline (F2). If anything is missing, add it as revision 0002.
Remove the per-request calls to ensure_transaction_columns(db) and
    ensure_auth_columns(db) from the request/view code paths (dashboard, scan,
    stock, transactions, exports, login, forgot/reset/set-password, admin users,
    etc.). ensure_barcode_sequence is folded into the baseline as well; the
    barcode generator no longer needs to create the sequence at runtime.
Keep the ensure_* function definitions temporarily (dead code) ONLY if useful for
    an emergency manual repair; otherwise delete them. Document the choice.
```

Verify:

```text
grep shows no ensure_*_columns(...) calls remain on any request path.
The app boots and every page (dashboard, items, item detail, scan, item stock,
    transactions, exports, admin users, login/forgot/reset) works against a
    database that was built purely by migrations.
No ALTER TABLE / CREATE INDEX runs during a normal page load (confirm via
    PostgreSQL statement logging or code review).
```

### Substep F4 — Wire migrations into startup/deploy

Files:

```text
app.py (or a CLI command) 
README / deploy notes
Procfile / entrypoint / release step (deploy-target specific)
```

Add:

```text
Add a documented command to run migrations at deploy time, e.g.:
    alembic upgrade head            (preferred, run in the release phase)
Optionally add a Flask CLI wrapper (e.g. `flask db-upgrade`) that calls Alembic so
    operators have one consistent interface.
Update the init-db story: `flask init-db` may remain for local dev bootstrap, but
    production schema management is `alembic upgrade head`. Document this clearly.
Ensure migrations run ONCE per release, before the new app version serves traffic,
    and never on a per-request basis.
```

Verify:

```text
A clean deploy against an empty DB: migrations run to head, then the app serves.
A redeploy with no new migrations: `alembic upgrade head` is a safe no-op.
Rolling back a bad migration: `alembic downgrade -1` works on a scratch DB.
```

### Substep F5 — Migration tests / CI check

Files:

```text
tests/test_migrations.py   (new)
```

Add:

```text
A test that, against a throwaway database, runs `alembic upgrade head` from zero
    and asserts the expected tables/columns/indexes exist.
A test that upgrade -> downgrade -> upgrade round-trips without error for the
    latest revision (guards reversibility).
Optionally: a check that the migrations "head" is single (no divergent heads).
```

Verify:

```text
pytest runs the migration tests green against a scratch database (same pattern as
    the existing auth suite, which creates/drops its own test DB).
```

---

## Step G — Store expiration_date as a real DATE

Effort: S. Delivered as an Alembic migration plus app/template updates. Depends
on Step F. Split into three substeps (G1–G3).

### Substep G1 — Data migration: TEXT -> DATE

Files:

```text
migrations/versions/0003_expiration_date_to_date.py   (new)
```

Add:

```text
upgrade():
    Add a new nullable column expiration_date_new DATE.
    Backfill it by parsing the existing TEXT column:
        '00/00/0000', '', and unparseable values  -> NULL
        valid dates                                 -> the parsed DATE
        (decide and document the input format; today the UI uses a free-text
         field defaulting to '00/00/0000', so parse defensively.)
    Drop the old TEXT column and rename expiration_date_new -> expiration_date.
downgrade():
    Reverse: add TEXT column, format DATE back to text (NULL -> '00/00/0000'),
    drop the DATE column, rename back.
```

Verify:

```text
On a copy of real data: rows with '00/00/0000' become NULL; rows with real dates
    become the correct DATE; no row is lost.
The column type is DATE afterward (\d items in psql).
```

### Substep G2 — Application + template updates

Files:

```text
app.py
templates/item_new.html
templates/item_edit.html
templates/item_detail.html
templates/item_label.html
schema.sql   (update the reference schema to DATE for fresh dev bootstraps)
```

Add:

```text
Forms: replace the free-text expiration field with <input type="date">; submit an
    empty value (not '00/00/0000') when unset.
app.py: in get_item_form_data(), store None for an empty date instead of the
    '00/00/0000' sentinel; pass a real date (or NULL) to INSERT/UPDATE.
Templates: show "Not set" when NULL; the label page shows the exp line only when a
    date is present (it currently special-cases '00/00/0000' — that check goes
    away once the value is a real DATE/NULL).
Optional (nice-to-have, not required here): an "expiring soon" indicator now that
    the column is comparable.
```

Verify:

```text
Create an item with a real expiration date -> stored as DATE, shown correctly on
    detail and label.
Create an item with no date -> stored as NULL, shown as "Not set", label hides exp.
Edit an existing item's date -> persists correctly.
The '00/00/0000' string no longer appears anywhere in the UI or DB.
```

### Substep G3 — Regression check

Files:

```text
tests/ (optional new item-form test)
```

Verify:

```text
Existing QR label / item detail / item edit flows still pass.
py_compile clean; no linter errors on changed files.
```

---

## Step H — Pagination + indexes on transactions

Effort: M. Indexes ship as a migration; pagination is an app change. Depends on
Step F. Split into three substeps (H1–H3).

### Substep H1 — Indexes (migration)

Files:

```text
migrations/versions/0004_transaction_indexes.py   (new)
```

Add:

```text
CREATE INDEX on transactions (item_id)
CREATE INDEX on transactions (user_id)
CREATE INDEX on transactions (transaction_date)
A composite index matching the list ORDER BY so the sort is index-supported:
    (transaction_date DESC, transaction_time DESC, id DESC)
Consider an index on items (name) for the item filter dropdown / items list sort.
Use CREATE INDEX (optionally CONCURRENTLY in production) so large tables are not
    locked; document the CONCURRENTLY caveat (cannot run inside a txn block).
```

Verify:

```text
On a large seeded dataset, EXPLAIN (ANALYZE) on the /transactions query shows the
    indexes are used (index scan, not a full seq scan + sort).
Filtered queries by date range / item / user use the matching index.
```

### Substep H2 — Server-side pagination

Files:

```text
app.py                       (get_transaction_rows + the /transactions view)
templates/transactions.html  (page controls)
(optionally /items + templates/items.html if that list also grows large)
```

Add:

```text
Add LIMIT/OFFSET (or keyset/"seek" pagination on the ORDER BY key for large
    tables) to get_transaction_rows; default page size configurable (e.g. 50).
Add a page number / next-prev controls to transactions.html that PRESERVE the
    active filters (carry the filter querystring across pages).
Return a total count (or "has next page") so controls can be rendered.
Keep the CSV export UNPAGINATED: it should stream/return all matching rows (the
    export endpoint is separate from the on-screen list). Consider server-side
    streaming for very large exports as a follow-up.
```

Verify:

```text
With more rows than one page, the list shows one page and navigates correctly.
Filters + pagination combine (changing page keeps the filter; changing the filter
    resets to page 1).
Export still returns the full filtered result set, not just the current page.
Normal small datasets look and behave the same as before.
```

### Substep H3 — Verification with volume

Files:

```text
tests/ or a scratch seeding script
```

Verify:

```text
Seed thousands of transactions on a scratch DB; page load time stays low and
    EXPLAIN confirms index usage.
Pagination math (page count, last page, empty result) is correct at the edges.
```

---

## Step I — Automated backups + point-in-time recovery

Effort: S. Mostly infrastructure/ops, but the restore procedure MUST be written
and tested (an untested backup is not a backup). Split into three substeps.

### Substep I1 — Enable automated backups + PITR

Files:

```text
Deployment/host configuration (managed DB settings or backup cron + WAL archiving)
.env / platform secrets (backup storage credentials, if self-managed)
Ops documentation
```

Add:

```text
Preferred: use a managed PostgreSQL with automated daily snapshots and PITR (WAL)
    enabled; set a retention window (e.g. 7-30 days) appropriate for the customer.
Fallback (self-managed): schedule pg_dump (daily logical backup) AND enable WAL
    archiving to off-host object storage for point-in-time recovery; document
    retention and encryption at rest.
Store backups on DIFFERENT storage/region than the primary database.
Record RPO (max acceptable data loss) and RTO (max acceptable downtime) targets.
```

Verify:

```text
A backup exists and completes on schedule (check the provider console / cron logs).
PITR is enabled (WAL retention configured) for the chosen retention window.
```

### Substep I2 — Tested restore runbook

Files:

```text
Ops documentation (RESTORE runbook)
```

Add:

```text
A written, step-by-step restore procedure:
    - restore the latest snapshot (or PITR to a chosen timestamp) into a scratch
      database/instance
    - run `alembic upgrade head` if needed
    - run a smoke test (log in, list items, view transactions) against the restore
Document who runs it, expected duration (compare to RTO), and rollback of DNS/app
    to point at the restored instance if the primary is lost.
```

Verify:

```text
Perform a real test restore into a scratch instance from a backup; the app boots
    against it and core pages work.
Perform a PITR to a timestamp BEFORE a deliberate test DELETE and confirm the
    deleted rows come back (validates point-in-time recovery, not just snapshots).
The restore completes within the documented RTO.
```

### Substep I3 — Guard against accidental data loss (application-side)

Files:

```text
app.py (review of destructive endpoints)
```

Add:

```text
Review destructive operations for safety nets:
    - user delete already blocks when transactions reference the user (ON DELETE
      RESTRICT + a transaction-count check); keep that.
    - prefer soft-delete/deactivate over hard delete for auditable records.
Confirm transactions (the audit log) cannot be edited/deleted by regular users.
(These complement backups; they reduce how often a restore is ever needed.)
```

Verify:

```text
Deleting a user with history is still refused.
Regular (non-admin) users cannot delete transactions or items.
```

---

## Consolidated testing plan

```text
Migrations (Step F):
    Fresh DB: alembic upgrade head builds the whole schema.
    Existing DB: stamp baseline, then upgrade head is a clean no-op.
    upgrade -> downgrade -> upgrade round-trips (tests/test_migrations.py).
    No ensure_*_columns() calls remain on request paths (grep + boot test).
Schema/data (Steps G, H):
    expiration_date is DATE; '00/00/0000' backfilled to NULL; forms use a date input.
    Indexes exist and EXPLAIN shows they are used; pagination navigates and
    preserves filters; export still returns all rows.
Reliability (Step I):
    A real test restore succeeds within RTO; PITR recovers pre-DELETE data.
Regression:
    The full existing auth suite (currently 37 tests) still passes.
    py_compile clean; no linter errors on changed files.
```

---

## Pre-deploy data & reliability checklist

```text
[ ] Alembic adopted; schema changes are migrations, not per-request ALTERs
[ ] No ensure_*_columns() runs on any request path
[ ] Migrations run once per deploy (release phase), before serving traffic
[ ] expiration_date is a real nullable DATE; no '00/00/0000' in UI or DB
[ ] transactions has indexes on date, item_id, user_id (+ ORDER BY composite)
[ ] /transactions is paginated; filters preserved; export returns full results
[ ] Automated backups enabled and stored off-host
[ ] PITR enabled for a defined retention window
[ ] A restore was actually performed and succeeded within RTO
[ ] RPO/RTO targets documented
```

---

## Notes / relationship to Phase 1

```text
- Phase 1's A1 log explicitly deferred a migration framework to this phase; Step F
  is that deferred work. Once Alembic is in place, the ensure_auth_columns() and
  ensure_transaction_columns() runtime shims are retired.
- HTTPS/HSTS (Phase 1 Step E) and this phase are both "before launch" work and can
  proceed in parallel; neither blocks the other.
- This document is a PLAN only. No application code or schema has been changed by
  writing it; implementation happens substep by substep, each with its own
  PROGRESS_REPORT.md entry, exactly as in Phase 1.
```

---

## Implementation Log — F1 (Introduce Alembic, standalone raw-SQL mode) — 2026-07-08

### What was built

Alembic is now installed and scaffolded in the project, configured to manage the
database with explicit SQL migrations (no SQLAlchemy models). This is the
foundation for F2–F5 and for Steps G and H; no schema or application behavior
changed in this substep.

### How it works

- **Dependency:** added `alembic>=1.13,<2.0` to `requirements.txt` and installed
  it (Alembic 1.18.5). Alembic pulls in SQLAlchemy as its own dependency; we use
  SQLAlchemy only as Alembic's connection layer, not as an ORM.
- **Scaffold:** ran `alembic init migrations`, which created `alembic.ini` and the
  `migrations/` directory (`env.py`, `script.py.mako`, `versions/`, `README`).
- **URL from the environment:** `migrations/env.py` now reads `DATABASE_URL` from
  the environment and calls `config.set_main_option("sqlalchemy.url", ...)` so
  both offline and online modes use it. The default matches `app.py`
  (`postgresql://localhost/inventory_management_system`) for local dev.
- **No secrets in the ini:** the placeholder `sqlalchemy.url` line in
  `alembic.ini` was commented out with a note that the URL comes from `env.py` /
  `DATABASE_URL`.
- **Raw-SQL mode:** `target_metadata = None` (kept from the scaffold), so
  migrations are written explicitly with `op.execute` / `op.create_index` /
  `op.add_column` rather than autogenerated from models.

### Why these choices

- **Alembic directly (not Flask-Migrate):** Flask-Migrate expects SQLAlchemy
  models to autogenerate migrations; this app uses raw psycopg2 with no models,
  so plain Alembic with hand-written SQL is the correct fit (as decided in the
  plan's locked decisions and the Phase 1 A1 note).
- **URL only from the environment:** keeps credentials out of version control and
  guarantees migrations and the app always target the same database.

### Modifications by file

```text
requirements.txt
    - Added alembic>=1.13,<2.0.

alembic.ini (new)
    - Standard scaffold; sqlalchemy.url left blank/commented (URL comes from env).

migrations/env.py (new, edited)
    - Reads DATABASE_URL from the environment and sets sqlalchemy.url from it.
    - target_metadata = None (explicit-SQL migrations; no models).

migrations/script.py.mako, migrations/README, migrations/versions/ (new)
    - Standard Alembic scaffold. versions/ is currently empty (the F2 baseline is
      the first real revision).

.env.example
    - Noted that DATABASE_URL is used by BOTH the app and the Alembic migrations.
```

### Verification performed

```text
On a scratch database (inv_f1):
    - `alembic current` connected using DATABASE_URL and reported no version
      (Postgres impl loaded, no current revision line) -> DB is unstamped, as
      expected.
    - `alembic revision -m "smoke"` generated an empty revision file under
      migrations/versions/. It was then DELETED so it does not become a stray
      head before the F2 baseline; versions/ is intentionally empty now.
    - `python -m py_compile app.py` -> OK; `import app` succeeds and still
      registers 28 routes (Alembic is separate from the app and does not affect
      import).
    - migrations/env.py parses cleanly.
Regression: the full auth suite still passes (37 passed).
Scratch database dropped afterward; the real database was never touched.
```

### Next

```text
F2 — author the baseline revision (0001_baseline) that represents the current
schema, and support `alembic stamp` for existing databases.
```
