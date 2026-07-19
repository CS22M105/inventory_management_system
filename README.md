# Katz Nursing Inventory Management System

A Flask-based inventory management system for nursing education and simulation
lab environments. The application tracks inventory items, QR/code-based stock
actions, users, transaction history, exports, and production audit logs.

## Features

- Role-based login for administrators, faculty, and students.
- Inventory item creation, editing, low-stock tracking, and item detail pages.
- QR/code-based add-stock and remove-stock workflows.
- Printable full labels and compact QR-only labels.
- Transaction history with filters, pagination, and controlled CSV export.
- User management for administrators and approved faculty workflows.
- PostgreSQL persistence with Alembic migrations.
- Production safeguards: CSRF protection, rate limiting, secure config checks,
  structured request logging, Sentry support, health checks, and audit logs.

## Tech Stack

- Python
- Flask
- PostgreSQL
- Alembic
- Gunicorn
- HTML/CSS/JavaScript
- Pytest

## Project Structure

```text
app.py                  Flask/Gunicorn entrypoint
inventory/              application package
  auth/                 login, password reset, invite/set-password routes
  admin/                user management, DB status, audit logs
  dashboard/            dashboard and health check
  items/                item list/detail/create/edit/QR/label routes
  stock/                scan and stock transaction workflows
  transactions/         transaction history, filters, export
  reports/              inventory export
  services/             integration helpers
migrations/             Alembic migration chain
templates/              Jinja templates
static/                 CSS and images
tests/                  automated regression tests
design_docx/            project plans, policies, and operational documentation
```

## Local Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a local PostgreSQL database:

```bash
createdb inventory_management_system
```

Set local environment variables as needed:

```bash
export DATABASE_URL="postgresql://localhost/inventory_management_system"
export SECRET_KEY="dev-local-secret-key"
```

Initialize a local development database:

```bash
flask --app app init-db
```

Run the app:

```bash
flask --app app run --debug --port 5001
```

Open:

```text
http://127.0.0.1:5001
```

## Database Migrations

Shared and production databases are managed with Alembic:

```bash
alembic upgrade head
```

`flask --app app init-db` is for local development bootstrap only. Do not run
`init-db` against a production or shared managed database.

## Tests

The test suite requires a running PostgreSQL server and permission to create/drop
throwaway test databases.

```bash
pytest -q
```

Optional overrides:

```bash
TEST_DATABASE_URL="postgresql://localhost/inventory_test" pytest -q
MIG_DATABASE_URL="postgresql://localhost/inventory_mig_test" pytest -q
```

GitHub Actions runs tests and migration checks on push and pull request.

## Production Deployment

The app is prepared for deployment with Gunicorn:

```bash
gunicorn app:app -c gunicorn.conf.py
```

The `Procfile` contains:

```text
release: alembic upgrade head
web: gunicorn app:app -c gunicorn.conf.py
```

Configure production secrets and environment variables in the hosting platform,
not in git. Use `.env.example` as the redacted template.

At minimum, production needs:

```text
APP_ENV=production
SECRET_KEY=<64+ character random secret>
DATABASE_URL=<managed PostgreSQL URL>
APP_BASE_URL=https://<production-domain>
EMAIL_PROVIDER=smtp
```

For temporary private hosted testing without SMTP, `ALLOW_LOCAL_AUTH_LINKS=true`
can show invite/reset links on screen. Keep it disabled for real production.

## Security Notes

- Do not commit `.env`, production `SECRET_KEY`, database URLs, SMTP passwords,
  deploy hooks, or provider tokens.
- Use managed PostgreSQL backups and point-in-time recovery in production.