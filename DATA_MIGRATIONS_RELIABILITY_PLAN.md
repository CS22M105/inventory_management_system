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

---

## Implementation Log — F2 (Baseline the current schema) — 2026-07-08

### What was built

The first real migration, `0001_baseline`, which creates the entire current
schema (after all Phase 1 changes) on an empty database, and can be `stamp`ed on
an existing database so Alembic adopts it without recreating anything.

### How it works

- **Revision:** `migrations/versions/0001_baseline.py`, `revision = "0001_baseline"`,
  `down_revision = None` (it is the first/root revision). Generated with
  `alembic revision --rev-id 0001_baseline` and then filled in / renamed to the
  plan's filename.
- **upgrade():** explicit `op.execute(...)` SQL that mirrors `schema.sql` exactly
  (minus the DROP statements and the demo seed rows): the `users`, `items`, and
  `transactions` tables, the standalone `item_barcode_number_seq` sequence, and
  every column/constraint the `ensure_*_columns()` shims guarantee (email
  NOT NULL UNIQUE -> the `users_email_key` index, `password_hash`, `created_at`,
  `last_login_at`, nullable `institution_id`, the transaction date/time/instructor/
  topic columns, and the two FKs with `ON DELETE RESTRICT`).
- **downgrade():** drops everything in reverse dependency order (transactions,
  items, sequence, users).
- **Adoption on an existing DB:** documented in the file's docstring —
  `alembic stamp 0001_baseline` marks the DB as already at the baseline without
  running the CREATE statements.

### Why these choices

- **Mirror schema.sql verbatim** so a freshly migrated database and an existing
  `stamp`ed database are structurally identical (verified below). Writing it as
  raw SQL keeps the migration readable and matches the raw-`psycopg2` app.
- **Standalone sequence + inline UNIQUE constraints** reproduce the exact object
  names production already has (e.g. `users_email_key`), so `stamp` is truthful
  and later revisions line up.

### Modifications by file

```text
migrations/versions/0001_baseline.py (new)
    - upgrade(): CREATE users, items, item_barcode_number_seq, transactions.
    - downgrade(): DROP them in reverse order.

schema.sql
    - Added a header note: this file is now a dev-bootstrap/reference; the
      migrations/ directory is the source of truth. Production uses
      `alembic upgrade head`. (No DDL changed.)
```

### Verification performed

```text
Fresh empty DB (inv_f2_fresh):
    - `alembic upgrade head` ran 0001_baseline and built the full schema.
    - `alembic current` -> "0001_baseline (head)".
Existing DB (inv_f2_existing, built by applying schema.sql):
    - `alembic stamp 0001_baseline` marked it at the baseline (no CREATEs run).
    - `alembic upgrade head` was a clean no-op (no "Running upgrade" line).
    - `alembic current` -> "0001_baseline (head)".
Schema equality:
    - `pg_dump -s` of both databases is IDENTICAL (ignoring pg_dump's random
      \restrict/\unrestrict session tokens); alembic_version = 0001_baseline in
      both.
Reversibility smoke:
    - `alembic downgrade base` dropped users/items/transactions (leaving only
      alembic_version); `alembic upgrade head` rebuilt them.
Regression:
    - Full auth suite still passes (37 passed).
Scratch databases and temp dumps were removed; the real database was untouched.
```

### Next

```text
F3 — confirm the baseline covers everything the ensure_*_columns() functions do,
then remove those per-request calls from the view code paths.
```

---

## Implementation Log — F3 (Fold ensure_*_columns into migrations; remove from request paths) — 2026-07-08

### What was built

The per-request schema-mutation shims are gone. `ensure_transaction_columns`,
`ensure_barcode_sequence`, and `ensure_auth_columns` — which issued `ALTER TABLE`
/ `CREATE INDEX` / `CREATE SEQUENCE` on ordinary page loads — have been removed
entirely, along with every call to them. The schema they used to guarantee is now
owned by the `0001_baseline` migration (and `schema.sql` for local dev).

### Baseline coverage check (no 0002 needed)

Every object the three functions created is already in `0001_baseline`, so no
additional revision was required:

```text
ensure_transaction_columns ->
    transaction_date DATE, transaction_time TIME(0), lab_instructor, topic_of_day,
    their DEFAULTs (CURRENT_DATE / LOCALTIME(0)) and NOT NULL constraints
        ... all present in the baseline transactions table.
    (The UPDATE backfills only mattered for upgrading OLD data in place; a
     migration-built DB starts correct, so they are not needed.)
ensure_barcode_sequence ->
    CREATE SEQUENCE item_barcode_number_seq ... present in the baseline.
ensure_auth_columns ->
    email NOT NULL UNIQUE, password_hash, created_at DEFAULT now(), last_login_at,
    institution_id nullable, and the users_email_key unique index (the inline
    UNIQUE on email creates exactly that index) ... all present in the baseline.
```

### Decision on the function definitions

Deleted them (not kept as dead code). Rationale: keeping DDL helpers around invites
the "ALTER on request" anti-pattern to creep back; the schema now has one source of
truth (migrations, mirrored by `schema.sql` for dev). Emergency manual repair, if
ever needed, is `alembic upgrade head` against the database.

### Modifications by file

```text
app.py
    - Deleted the ensure_transaction_columns / ensure_barcode_sequence /
      ensure_auth_columns function definitions; left a short comment explaining
      that migrations own the schema.
    - generate_next_item_barcode() no longer calls ensure_barcode_sequence; it
      just draws nextval() from the sequence (created by the baseline).
    - Removed every per-request call:
        login, reauth, forgot_password, reset_password, set_password,
        admin_user_new, admin_user_resend_invite  (were ensure_auth_columns)
        dashboard, process_stock_transaction, transactions, export_transactions
                                                   (were ensure_transaction_columns)
    - CLI: init-db no longer calls ensure_* (schema.sql builds everything);
      set-password no longer calls ensure_auth_columns.

tests/conftest.py
    - Test DB is built from schema.sql only; removed the ensure_auth_columns(db)
      call (the columns already exist in schema.sql).
```

### Verification performed

```text
Code review / grep:
    - No ensure_*_columns(...) calls remain in app.py or tests/ (only a comment).
    - No ALTER TABLE / CREATE INDEX / CREATE SEQUENCE / ADD COLUMN remains in
      app.py (only the explanatory comment mentions the words).
Boots against a MIGRATION-BUILT database (inv_f3, schema created solely by
`alembic upgrade head` -> 0001_baseline; schema.sql NOT used):
    - Seeded an admin, logged in (302), created an item (write path) -> barcode
      KATZ-NURS-000001 generated via the migration's sequence, stock add -> 200.
    - GET 200 on dashboard, items, item detail, low-stock, scan, item stock,
      transactions, transactions/export, reports/export, admin users, login,
      forgot-password.
    - forgot POST -> 200; reset/set-password with a bad token -> 400.
Regression: full auth suite still passes (37 passed). py_compile clean; no linter
    errors. Scratch database dropped; the real database was untouched.
```

### Next

```text
F4 — wire migrations into startup/deploy (run `alembic upgrade head` once per
release, document the init-db-vs-migrations story), then F5 migration tests.
```

---

## Implementation log — Substep F4 (Wire migrations into startup/deploy)

Date: 2026-07-08

### What changed and why

Migrations now have a documented home in the deploy lifecycle, and operators have
a single consistent interface for them. Previously Alembic existed (F1–F3) but
nothing tied `alembic upgrade head` to a release; there was also a risk operators
would keep using `init-db` (which rebuilds from `schema.sql`) on a database that
is under Alembic control. F4 makes the split explicit: `init-db` is local-dev
bootstrap only; migrations own production/shared schema, and they run once per
release before the new app serves traffic — never per request.

### Modifications by file

```text
app.py
    - Added _alembic_config(): builds an alembic.config.Config from the project's
      alembic.ini. It does NOT set a URL; migrations/env.py reads DATABASE_URL
      from the environment, so the CLI and the app always target the same DB.
      Alembic is imported lazily inside the CLI functions, so the web-serving
      process never imports Alembic.
    - Added `flask db-upgrade [revision]` (default "head"): wraps
      `alembic upgrade` — the production/release-phase schema command.
    - Added `flask db-downgrade <revision>` (e.g. `-1`): wraps `alembic downgrade`.
      Uses context_settings ignore_unknown_options so a leading "-1" is accepted
      as an argument (matching the native Alembic CLI) instead of being parsed as
      an option.
    - Rewrote the init-db docstring/echo to state it is a LOCAL DEV bootstrap only
      and to point at `flask db-upgrade` / `alembic upgrade head` for shared DBs.

Procfile
    - Added a `release: alembic upgrade head` line before `web: gunicorn app:app`
      so platforms with a release phase run migrations once per deploy, before the
      new web dyno/process serves traffic.

README.md
    - init-db section now labelled "LOCAL DEV bootstrap only".
    - Production Configuration Procfile snippet updated to show the release line.
    - New "Database migrations" section: alembic upgrade head / flask db-upgrade,
      the release-phase behaviour, `alembic current`, rollback with
      `alembic downgrade -1` / `flask db-downgrade -1`, creating revisions, and a
      clear "do not run init-db against an Alembic-managed database" note.
```

### Verification performed

```text
Scratch database inv_f4 (built purely by migrations):
    - `flask --app app --help` lists db-upgrade, db-downgrade, init-db.
    - Fresh DB: `alembic current` reports no version.
    - CLEAN DEPLOY: `flask db-upgrade` -> "Running upgrade -> 0001_baseline";
      `alembic current` = 0001_baseline (head).
    - NO-OP REDEPLOY: `flask db-upgrade` again -> no "Running upgrade" line
      (safe no-op).
    - ROLLBACK: `flask db-downgrade -1` -> "Running downgrade 0001_baseline -> ";
      `alembic current` = none; re-`db-upgrade` restores head.
    - App boots and serves against the migration-built DB: GET /login -> 200.
py_compile app.py clean; no linter errors.
```

### Next

```text
F5 — migration tests / CI check (empty DB -> upgrade head -> assert schema;
optional up/down round-trip on a scratch DB in CI).
```

---

## Implementation log — Substep F5 (Migration tests / CI check)

Date: 2026-07-08

### What changed and why

Added an automated safety net so the migration chain can never silently rot. Up
to F4, migrations were exercised only by hand. F5 makes CI prove, on every run,
that a database built purely by Alembic has the schema the app expects, that the
latest chain is reversible, and that the migration graph has not branched.

### Modifications by file

```text
tests/test_migrations.py  (new)
    - Uses its OWN throwaway database (default inventory_mig_test, overridable
      via MIG_DATABASE_URL), separate from the auth suite's inventory_test,
      because a migration test needs an empty, never-stamped DB it fully owns.
    - migration_db fixture: drops+creates the throwaway DB and monkeypatches
      DATABASE_URL to point at it (migrations/env.py reads DATABASE_URL at run
      time), then drops the DB and restores DATABASE_URL afterwards.
    - Drives Alembic through app.py's own _alembic_config(), so the test path
      and the production/CLI path share one config.
    - test_upgrade_head_creates_expected_schema: `alembic upgrade head` from
      zero, then asserts the users/items/transactions tables, a representative
      column set per table (incl. everything the old ensure_* shims added),
      the item_barcode_number_seq sequence, unique indexes on users(email) and
      items(barcode), and a primary-key index on each table.
    - test_upgrade_downgrade_upgrade_roundtrip: upgrade head -> downgrade base
      (asserts tables + sequence are gone) -> upgrade head again, all without
      error; guards reversibility.
    - test_single_migration_head: ScriptDirectory.get_heads() must be length 1
      (no divergent heads). Needs no live DB.
```

### Verification performed

```text
pytest tests/test_migrations.py -v  -> 3 passed.
Full suite (auth + migrations)      -> 40 passed (37 auth + 3 migration).
Each migration test creates and drops its own scratch DB (same pattern as the
auth suite); the dev/production database is never touched. No linter errors.
```

### Next

```text
G — convert expiration_date TEXT -> real DATE (data migration + app updates).
H — pagination + indexes on transactions. I — automated backups / PITR.
```

---

## Implementation log — Substep G1 (Data migration: TEXT -> DATE)

Date: 2026-07-08

### What changed and why

`items.expiration_date` was free-text (`TEXT DEFAULT '00/00/0000'`) because the
add/edit forms use a plain text input defaulting to the sentinel `00/00/0000`.
Free text makes "expiring soon" queries, sorting, and validation impossible and
lets malformed values in. G1 converts the column to a real `DATE` and cleans up
the existing data, reversibly.

Input format decision: the UI placeholder/default is `00/00/0000`
(month/day/year), so the canonical format is treated as **MM/DD/YYYY**. A few
other common formats (`YYYY-MM-DD`, `MM-DD-YYYY`, `MM/DD/YY`) are accepted
defensively. Empty, the `00/00/0000` sentinel, and anything unparseable become
`NULL` ("no expiration recorded") -- rows are never dropped.

### Modifications by file

```text
migrations/versions/0003_expiration_date_to_date.py  (new)
    down_revision = 0001_baseline (0003 is now the single head).
    upgrade():   ADD COLUMN expiration_date_new DATE
                 -> backfill in Python (op.get_bind()) parsing the old TEXT
                 -> DROP old TEXT column -> RENAME new -> expiration_date.
    downgrade(): ADD COLUMN expiration_date_old TEXT DEFAULT '00/00/0000'
                 -> format each DATE back to MM/DD/YYYY (NULL -> '00/00/0000')
                 -> DROP the DATE column -> RENAME back.

Why a Python backfill and not SQL to_date(): PostgreSQL's to_date() does NOT
raise on junk like '00/00/0000' -- it silently returns a bogus date. Parsing in
Python and mapping failures to NULL is the correct, lossless behaviour.
```

### IMPORTANT follow-up (G2 — app code)

```text
After 0003 runs, the column is a DATE. The add/edit/CSV-import write paths in
app.py still send the string '00/00/0000' (see the item form default), which will
FAIL against a DATE column. G2 must update those paths to send a real date or
NULL, switch the form input to type="date", and adjust templates/exports that
render/compare against '00/00/0000'. This substep (G1) is schema + data only.
```

### Verification performed

```text
Scratch DB inv_g1, seeded at baseline (0001) with 7 items, then upgraded to head:
    00/00/0000  -> NULL        (empty)      -> NULL
    12/31/2025  -> 2025-12-31  2026-01-15   -> 2026-01-15
    garbage     -> NULL        13/40/2025   -> NULL (impossible)
    02/29/2024  -> 2024-02-29  (leap day preserved)
    row count 7 -> 7 (no rows lost). Column type afterwards: date.
Downgrade -1 restores TEXT: NULL -> '00/00/0000', dates -> MM/DD/YYYY
    (e.g. 2026-01-15 normalizes to '01/15/2026'); re-upgrade returns to DATE.
pytest tests/test_migrations.py -> 3 passed (chain 0001->0003, single head).
No linter errors.
```

### Next

```text
G2 — update app.py write paths + item forms/templates for DATE (send NULL/real
date, input type="date", stop using the '00/00/0000' sentinel).
```

---

## Implementation log — Substep G2 (Application + template updates)

Date: 2026-07-08

### What changed and why

G1 turned the column into a `DATE` but the app still sent the string
`'00/00/0000'`, which would fail against a `DATE` column. G2 updates the write
paths, forms, templates, and the dev reference schema so the whole app speaks
`DATE`/`NULL` and the `00/00/0000` sentinel is gone from the UI and DB.

### Modifications by file

```text
app.py
    - New helper parse_expiration_date(value): parses the submitted value into a
      datetime.date, or None when empty/unparseable. Accepts ISO (YYYY-MM-DD,
      what <input type="date"> submits) first, plus MM/DD/YYYY, MM-DD-YYYY,
      MM/DD/YY defensively. No more '00/00/0000' default.
    - get_item_form_data() now stores None (SQL NULL) for an unset date instead
      of the sentinel; the INSERT/UPDATE already bind item_data["expiration_date"]
      directly, so psycopg2 sends a real DATE or NULL.
    - Added `from datetime import datetime` (was only timedelta).

templates/item_new.html, templates/item_edit.html
    - Expiration field is now <input type="date"> with value
      `{{ item.get('expiration_date') or '' }}` (empty when unset; a date renders
      as ISO, which is what type="date" expects).

templates/item_label.html
    - Condition simplified from `if expiration_date and != '00/00/0000'` to just
      `if item["expiration_date"]` (NULL hides the Exp line).

templates/item_detail.html
    - Unchanged: already `{{ item["expiration_date"] or "Not set" }}`, which now
      shows "Not set" for NULL and the real date otherwise.

schema.sql
    - items.expiration_date is now `DATE` (was `TEXT DEFAULT '00/00/0000'`), so
      fresh dev bootstraps match the migrated (head) schema.
```

### Verification performed

```text
Functional (scratch DB inv_g2, schema built by `alembic upgrade head`; login as
seeded admin, CSRF disabled for the client):
    - Create item WITH date 2025-12-31 -> stored as DATE (pg_typeof = date);
      detail shows 2025-12-31; label shows "Exp: 2025-12-31".
    - Create item WITHOUT date -> stored as NULL; detail shows "Not set"; label
      hides the Exp line.
    - Edit the no-date item to 2026-06-01 -> persists as DATE.
    - 0 rows equal the '00/00/0000' sentinel in the DB; '00/00/0000' appears in
      none of the rendered detail/label pages.
Full suite: 40 passed (37 auth + 3 migration). py_compile clean; no linter errors.
grep: '00/00/0000' now appears only inside the migration files (0001 baseline /
0003 reverse mapping), never in app.py, templates, or schema.sql.
```

### Next

```text
H — pagination + indexes on transactions (date/item/user). I — automated backups
/ PITR. (Optional G follow-up: an "expiring soon" indicator, now that the column
is comparable.)
```

---

## Implementation log — Substep G3 (Regression check)

Date: 2026-07-08

### What changed and why

Locked the G1/G2 DATE behaviour behind automated tests so the add/edit/detail/
label flows can't silently regress, and re-confirmed the toolchain is clean.

### Modifications by file

```text
tests/test_item_form.py  (new)
    Uses the shared throwaway DB + fixtures from conftest.py (logs in as the
    seeded faculty item-manager). Covers:
    - create item WITH a real date -> stored as datetime.date; detail + label
      show 2025-12-31.
    - create item WITHOUT a date -> stored as NULL; detail shows "Not set";
      label hides the Exp line.
    - unparseable date ("not-a-date") -> stored as NULL (defensive parse, no
      crash).
    - edit an item's date -> persists as DATE.
    - the '00/00/0000' sentinel never appears in rendered detail/label pages.
```

### Verification performed

```text
pytest tests/test_item_form.py -> 5 passed.
Full suite -> 45 passed (37 auth + 3 migration + 5 item-form).
py_compile app.py clean; no linter errors on changed files.
Existing QR label / item detail / item edit flows: covered by the new tests and
green.
```

### Next

```text
H — pagination + indexes on transactions (date/item/user). I — automated backups
/ PITR.
```

---

## Implementation log — Substep H1 (Indexes migration)

Date: 2026-07-08

### What changed and why

The /transactions list sorts by `(transaction_date DESC, transaction_time DESC,
id DESC)` and filters by item/user/date range; on a growing table those become a
full seq scan + sort. Revision 0004 adds the supporting indexes so the sort and
the filters are index-served.

### Modifications by file

```text
migrations/versions/0004_transaction_indexes.py  (new)
    down_revision = 0003_expiration_date_to_date (0004 is now the single head).
    upgrade(): CREATE INDEX IF NOT EXISTS
        ix_transactions_item_id            ON transactions (item_id)
        ix_transactions_user_id            ON transactions (user_id)
        ix_transactions_transaction_date   ON transactions (transaction_date)
        ix_transactions_date_time_id       ON transactions
            (transaction_date DESC, transaction_time DESC, id DESC)  <- matches ORDER BY
        ix_items_name                      ON items (name)
    downgrade(): DROP INDEX IF EXISTS (reverse order).

CONCURRENTLY caveat (documented in the migration): plain CREATE INDEX takes a
brief lock; fine for today's small table. On a large busy table build with
CREATE INDEX CONCURRENTLY in a maintenance window instead -- but CONCURRENTLY
cannot run inside a transaction block and Alembic wraps migrations in one, so it
must be run manually, then `alembic stamp 0004_transaction_indexes`. The
IF NOT EXISTS guards make that path a safe no-op.

Note: ix_transactions_transaction_date is partly redundant with the composite
(same leading column); kept per plan since write volume is low and it is cheaper
for pure date-range scans. Drop later if bloat matters.

tests/test_migrations.py
    - test_upgrade_head_creates_expected_schema now also asserts the four
      ix_transactions_* indexes and ix_items_name exist at head.
```

### Verification performed

```text
Scratch DB inv_h1: schema+indexes built by `alembic upgrade head` (0001->0004),
seeded 10 users, 50 items, 100,000 transactions, then ANALYZE. EXPLAIN (ANALYZE):
    ORDER BY (date,time,id) DESC LIMIT 50
        -> Index Scan using ix_transactions_date_time_id, NO explicit sort.
    WHERE item_id = 7   -> Bitmap Index Scan on ix_transactions_item_id.
    WHERE user_id = 3   -> Bitmap Index Scan on ix_transactions_user_id.
    WHERE transaction_date BETWEEN ... 
        -> Bitmap Index Scan on ix_transactions_transaction_date.
    items ORDER BY name -> seq scan+sort (items has only 50 rows, so a scan is
        optimal; ix_items_name is present and used once the catalog grows).
pg_indexes confirms all five ix_* indexes exist.
Migration chain: single head = 0004; upgrade/downgrade/upgrade round-trip green.
Full suite: 45 passed. No linter errors.
```

### Next

```text
H2 — pagination on /transactions (LIMIT/OFFSET or keyset) so the list and export
use bounded queries that lean on ix_transactions_date_time_id. Then I — backups.
```

---

## Implementation log — Substep H2 (Server-side pagination)

Date: 2026-07-08

### What changed and why

The /transactions page loaded the entire (filtered) table into one HTML page --
fine now, unusable as history grows. H2 paginates the on-screen list with
LIMIT/OFFSET on the existing ORDER BY (so it rides the 0004 composite index),
while the CSV export stays UNPAGINATED (full filtered set).

### Modifications by file

```text
app.py
    - New constant TRANSACTIONS_PAGE_SIZE (env TRANSACTIONS_PAGE_SIZE, default 50).
    - get_transaction_rows(db, filters, limit=None, offset=None): appends
      LIMIT/OFFSET only when limit is given. Export calls it WITHOUT limit, so it
      still returns every matching row.
    - New count_transaction_rows(db, filters): COUNT(*) with the same filter
      clause (no JOINs needed) to drive the controls.
    - /transactions view: reads ?page=, computes total_pages, CLAMPS page into
      [1, total_pages] (out-of-range page lands on the last page), fetches just
      that page, and builds prev_url/next_url via url_for(..., page=, **filters)
      so navigation preserves active filters. Submitting the filter form omits
      ?page=, so changing a filter resets to page 1.
    - export_transactions unchanged (still get_transaction_rows without limit).

templates/transactions.html
    - Added a .pagination nav: Previous / "Page X of Y - N transactions" / Next,
      rendered when there are matching rows; boundary links render as disabled
      spans. Empty-state text now reads "No transactions match the current
      filters."

static/css/styles.css
    - .pagination, .pagination-status, and .button-link.disabled styles.
```

### Verification performed

```text
Scratch DB inv_h2, TRANSACTIONS_PAGE_SIZE=10, 30 seeded transactions
(25 on item_a/admin, 5 on item_b/student):
    - page 1/2/3 each show 10 rows; "Page 1 of 3" ... "Page 3 of 3".
    - Previous disabled on page 1; Next disabled on page 3.
    - ?page=99 clamps to "Page 3 of 3".
    - Filter item_b -> "Page 1 of 1", 5 rows, "5 transactions".
    - Filter item_a + ?page=2 -> "Page 2 of 3" and prev/next carry item_id
      (filters preserved across pages).
    - Export (no filter) returns 30 data rows; export?item_id=item_b returns 5 --
      i.e. the FULL filtered set, not one page.
Full suite: 45 passed. py_compile clean; no linter errors.
Note: /items pagination was left out (optional; the item catalog is small). Add
the same pattern there if it grows. Keyset/seek pagination is a future upgrade if
deep OFFSET pages ever get slow.
```

### Next

```text
I — automated backups + point-in-time recovery (managed-Postgres snapshots / WAL;
documented restore drill). Optional: an "expiring soon" indicator (Step G).
```

---

## Implementation log — Substep H3 (Verification with volume)

Date: 2026-07-08

### What changed and why

Locked H1+H2 behaviour under automated tests that run at volume, and fixed a
schema-mirror gap found while doing so.

### Modifications by file

```text
schema.sql
    - Added the five performance indexes from migration 0004 (ix_transactions_*
      and ix_items_name). schema.sql is the dev-bootstrap mirror of head, and it
      was missing them, so a DB built from schema.sql (including the test DB) did
      not match a migration-built DB. Now they agree.

tests/test_transactions_pagination.py  (new)
    - Module-scoped fixture seeds the shared test DB with 6 users, 20 items and
      5,000 transactions (bulk generate_series insert) + ANALYZE.
    - Pagination-math edges: first page (Page 1 of 100, 50 rows, Prev disabled),
      full last page (Page 100 of 100, Next disabled), out-of-range page clamps
      to last, non-numeric/<=0 page clamps to first, partial last page via a
      user filter (833 rows -> 17 pages, last page 33 rows), and empty result
      (impossible filter -> "No transactions match...", no nav).
    - Filter + paging: filter is preserved across page links; export stays
      unpaginated (5,000 rows).
    - Index usage: EXPLAIN (ANALYZE) of the paginated joined query asserts it
      uses ix_transactions_date_time_id with NO "Sort Method" and NO
      "Seq Scan on transactions".
    - Page-load timing: GET /transactions?page=50 completes well under a generous
      2s ceiling (actual: a few ms).
```

### Verification performed

```text
pytest tests/test_transactions_pagination.py -> 9 passed (5,000-row dataset).
Full suite -> 54 passed (37 auth + 3 migration + 5 item-form + 9 pagination).
py_compile clean; no linter errors.
EXPLAIN on the paginated query: Index Scan using ix_transactions_date_time_id,
no explicit sort, no sequential scan of transactions.
```

### Next

```text
I — automated backups + point-in-time recovery (managed-Postgres snapshots / WAL;
documented restore drill). Optional: an "expiring soon" indicator (Step G).
```
