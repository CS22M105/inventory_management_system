# Architecture Plan

Date: July 10, 2026

Project: Katz Nursing School Inventory Management System

## Purpose

This document records the planned module layout for splitting the current
single-file Flask app later. It is a planning document only. No routes, imports,
templates, database behavior, or deployment commands should change during Q1.

The current entrypoint is `app.py`, and it should keep working until the refactor
is complete:

```bash
flask --app app run --debug
gunicorn app:app -c gunicorn.conf.py
```

When the package refactor is finished, the preferred long-term entrypoint is:

```bash
gunicorn "inventory:create_app()" -c gunicorn.conf.py
```

A thin compatibility `app.py` may remain:

```python
from inventory import create_app

app = create_app()
```

## Target Package Layout

```text
inventory/
    __init__.py              create_app() factory; extension setup; blueprint registration
    config.py                env parsing, constants, production guards
    db.py                    Database wrapper, get_db(), close_db()
    observability.py         Sentry setup, JSON/text logging, request_id helpers
    core.py                  Flask app assembly and shared route helpers
    cli.py                   init-db, db-upgrade, db-downgrade, set-password, check-config

    auth/
        routes.py            login, logout, reauth, forgot/reset password, set-password
        tokens.py            make_token(), read_token()
        passwords.py         hash/verify password, password-strength validation

    dashboard/
        routes.py            dashboard and health endpoint

    items/
        routes.py            all items, low stock, item detail, add, edit
        forms.py             item form parsing and expiration-date parsing
        barcodes.py          barcode/QR generation helpers

    stock/
        routes.py            scan page and item stock page
        service.py           process_stock_transaction(), get_stock_item()

    transactions/
        routes.py            transaction history and transaction CSV export
        repository.py        count/get transaction rows

    admin/
        routes.py            user management and db-status

    reports/
        routes.py            inventory CSV export

    services/
        email.py             send_email()
```

## Ownership Boundaries

Keep each module responsible for one area:

```text
config.py:
    Reads environment variables and owns constants such as ELEVATED_ROLES,
    BARCODE_PREFIX, RATELIMIT_*, SESSION_IDLE_MINUTES, APP_BASE_URL,
    SENTRY_DSN, and production SECRET_KEY guards.

db.py:
    Owns PostgreSQL connections only. It should not import route modules.

auth/:
    Owns identity, sessions, password reset/invite tokens, sudo mode, and
    role/permission decorators.

items/:
    Owns item forms, item CRUD, QR image responses, and printable labels.

stock/:
    Owns add/remove stock behavior. process_stock_transaction() should stay in
    one shared service so /scan and /items/<barcode>/stock remain consistent.

transactions/:
    Owns transaction history filters, pagination, row queries, and transaction
    CSV export.

admin/:
    Owns user administration and the human db-status page.

reports/:
    Owns inventory-level CSV export.

services/:
    Owns integrations and pure helpers that do not need to know about routes.
```

## Refactor Order

Move in small batches and run the full test suite after each batch.

```text
1. Extract pure services first:
       auth/passwords.py
       auth/tokens.py
       services/email.py
       items/forms.py
       items/barcodes.py
       transactions/repository.py

2. Extract database/config/logging:
       config.py
       db.py
       logging_config.py
       security.py
       cli.py

3. Introduce blueprints one area at a time:
       dashboard
       auth
       items
       stock
       transactions
       reports
       admin

4. Add create_app():
       inventory/__init__.py registers extensions, middleware, CLI commands,
       error handlers, request hooks, and blueprints.

5. Thin app.py:
       app.py imports create_app() and exposes app for Flask CLI and Gunicorn.
```

## Compatibility Rules

Do not change user-facing behavior during the split.

```text
Routes:
    Keep existing URLs unless a later product task explicitly asks to change them.

Templates:
    Keep template filenames and visible labels unchanged during the refactor.

Endpoint names:
    Preserve endpoint names where practical. If a blueprint changes an endpoint
    name, update every url_for() and template reference in the same commit.

Database:
    Do not add schema changes during the refactor. Schema changes remain owned
    by Alembic migrations.

Transactions:
    Keep /scan and /items/<barcode>/stock using the same stock service.

Deployment:
    Keep Procfile and gunicorn.conf.py working at every step.

Testing:
    Run pytest -q after every extraction batch.
```

## Test Gate Before Code Moves

Before Q2 starts, confirm the baseline is green:

```bash
pytest -q
```

The current expected baseline after P1 is:

```text
82 passed
```

## Q2 Extraction Status

Completed on July 10, 2026:

```text
inventory/auth/passwords.py
    hash_password()
    verify_password()
    validate_password_strength()

inventory/auth/tokens.py
    make_token()
    read_token()

inventory/items/barcodes.py
    generate_next_item_barcode()

inventory/items/forms.py
    parse_expiration_date()

inventory/services/email.py
    send_email()

inventory/transactions/repository.py
    build_transaction_filter_clause()
    count_transaction_rows()
    get_transaction_rows()
```

`app.py` still exposes compatibility wrapper functions with the old names. This
keeps existing routes and tests stable while the app is still a single Flask
module.

Verification after Q2:

```text
python -m py_compile app.py inventory/auth/passwords.py inventory/auth/tokens.py \
    inventory/items/barcodes.py inventory/items/forms.py inventory/services/email.py \
    inventory/transactions/repository.py
pytest -q -> 82 passed
```

## Q3 Blueprint Status

Completed on July 10, 2026:

```text
inventory/dashboard/routes.py
    /, /health, /dashboard

inventory/auth/routes.py
    /login, /logout, /reauth, /forgot-password, /reset-password/<token>,
    /set-password/<token>

inventory/items/routes.py
    /items, /items/low-stock, /items/<barcode>, /items/new,
    /items/<int:item_id>/edit, /items/<barcode>/qr.png,
    /items/<barcode>/label

inventory/stock/routes.py
    /scan, /items/<barcode>/stock

inventory/transactions/routes.py
    /transactions, /transactions/export

inventory/reports/routes.py
    /reports/export

inventory/admin/routes.py
    /admin/users, /admin/users/new, admin user action POST routes, /db-status
```

The browser URLs stayed the same. Flask endpoint names are now blueprint
namespaced, so templates and internal redirects use names such as:

```text
auth.login
dashboard.dashboard
items.items
items.item_new
stock.scan
transactions.transactions
reports.export_inventory
admin.admin_users
admin.db_status
```

`inventory.create_app()` registers all blueprints through
`core.register_blueprints(core.app)`. `app.py` is now a thin compatibility
entrypoint for Flask CLI, Gunicorn, and older imports.

Verification after Q3:

```text
python -m py_compile app.py inventory/*/routes.py
pytest tests/test_health.py -v -> 2 passed
pytest -q -> 82 passed
```

## Q4 Thin Entrypoint Status

Completed on July 10, 2026:

```text
app.py
    from inventory import create_app
    app = create_app()

inventory/__init__.py
    create_app() returns the configured app and registers blueprints idempotently

inventory/core.py
    app assembly and compatibility wrappers

inventory/config.py
    environment-backed configuration

inventory/db.py
    Database wrapper and get_db()/close_db()

inventory/cli.py
    check-config, init-db, db-upgrade, db-downgrade, set-password

inventory/observability.py
    Sentry setup and structured request logging
```

Verification after Q4:

```text
python -m py_compile app.py inventory/*.py inventory/*/*.py
pytest -q -> 82 passed
flask --app app db-upgrade -> worked against scratch PostgreSQL database
gunicorn app:app -c gunicorn.conf.py -> served /health with 200 OK
Largest non-route module: inventory/core.py at 398 lines
```
