# Nursing Inventory Management System

This project is a barcode-based inventory management system for nursing education, simulation labs, medication rooms, and healthcare training environments.

The goal is to replace manual Excel-based inventory tracking with a simple web application that can:

- Let users log in with a student, faculty, or staff ID.
- Add new inventory items.
- Track items using barcode values.
- Record how many items are added or removed.
- Save inventory activity in a database.
- Support reports and exports later.

## Current Status

The project is a working local Flask prototype.

Completed so far:

- Registered user and administrator login.
- Inventory item creation and listing.
- Barcode-based add/remove stock workflow.
- Transaction history.
- Dashboard counts.
- CSV inventory export.

## Technology

This project will use:

- **Python** for backend logic.
- **Flask** for the web application.
- **PostgreSQL** for the database.
- **HTML/CSS/JavaScript** for the user interface.

## Virtual Environment

The project virtual environment is named:

```text
invent
```

It is located inside the project folder:

```text
inventory/invent/
```

To use this environment in the terminal, run:

```bash
source invent/bin/activate
```

After activation, the terminal should show that the `invent` environment is active.

## Install Dependencies

After activating the virtual environment, install the required packages with:

```bash
pip install -r requirements.txt
```

The main dependencies are Flask and psycopg.

## Check Flask Installation

To confirm Flask is installed, run:

```bash
python -m flask --version
```

Expected result should show Flask version information.

## PostgreSQL Setup

Create a local PostgreSQL database:

```bash
createdb inventory_management_system
```

By default, the app connects to:

```text
postgresql://localhost/inventory_management_system
```

To use a different PostgreSQL database, set `DATABASE_URL` before running Flask:

```bash
export DATABASE_URL="postgresql://username:password@localhost:5432/inventory_management_system"
```

Set a secret key for sessions:

```bash
export SECRET_KEY="replace-with-a-long-random-secret-key"
```

Initialize the database tables and demo users (LOCAL DEV bootstrap only):

```bash
flask --app app init-db
```

`init-db` loads `schema.sql` (tables plus demo users) and is a convenience for
local development. Shared and production databases are managed with migrations
instead (see "Database migrations" below).

Run the app:

```bash
flask --app app run --debug
```

## Production Configuration

Use `.env.example` as the redacted template for local setup and for configuring
the production platform. Real production values belong in the hosting
platform's secret/environment store, not in git.

```bash
cp .env.example .env
```

Generate a production secret key outside git:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Required production environment variables:

| Variable | Secret? | Description |
| --- | --- | --- |
| `APP_ENV` | No | Set to `production` in deployed environments so secure-cookie and production guards are active. |
| `SECRET_KEY` | Yes | 64+ character random value used to sign sessions, CSRF tokens, invite links, and password-reset links. |
| `DATABASE_URL` | Yes | Managed PostgreSQL connection string. Shared by the Flask app and Alembic migrations through `migrations/env.py`. |
| `APP_BASE_URL` | No | Public HTTPS base URL used when generating invite/reset links and QR-code links. |
| `EMAIL_PROVIDER` | No | Set to `smtp` in production so invite/reset emails are actually sent. |
| `EMAIL_FROM` | No | Approved sender address for invite/reset emails. |
| `SMTP_HOST` | No | SMTP provider hostname. |
| `SMTP_PORT` | No | SMTP provider port, usually `587` for STARTTLS or `465` for SSL. |
| `SMTP_USERNAME` | Usually yes | SMTP account username; treat as secret unless the provider says otherwise. |
| `SMTP_PASSWORD` | Yes | SMTP password or app password. |
| `SMTP_USE_TLS` | No | `true` when the provider uses STARTTLS. |
| `SMTP_USE_SSL` | No | `true` when the provider requires SMTP over SSL. |

Optional environment variables:

| Variable | Secret? | Description |
| --- | --- | --- |
| `BARCODE_PREFIX` | No | Per-customer prefix for generated item codes, for example `KATZ-NURS`. |
| `SESSION_IDLE_MINUTES` | No | Minutes of inactivity before a signed session expires. |
| `SUDO_MODE_MAX_AGE` | No | Seconds after login/re-auth that destructive admin actions remain allowed. |
| `LOGIN_MAX_ATTEMPTS` | No | Consecutive failed-login threshold before temporary lockout. |
| `LOGIN_LOCKOUT_SECONDS` | No | Lockout duration after too many failed login attempts. |
| `RATELIMIT_ENABLED` | No | Enables/disables Flask-Limiter route limits. Keep enabled in production. |
| `RATELIMIT_STORAGE_URI` | Usually yes | Rate-limit backend URI. Use Redis/shared storage for multi-worker or multi-host production; treat URI credentials as secret. |
| `RATELIMIT_LOGIN` | No | Rate limit for login POST requests. |
| `RATELIMIT_PASSWORD` | No | Rate limit for forgot-password, set-password, and reset-password POST requests. |
| `RATELIMIT_STOCK` | No | Rate limit for stock add/remove endpoints. |
| `TRANSACTIONS_PAGE_SIZE` | No | Number of transaction rows shown per history page. |
| `WEB_CONCURRENCY` | No | Number of Gunicorn worker processes. If unset, defaults to `(2 * CPU count) + 1`; `GUNICORN_WORKERS` is still accepted as a compatibility alias. |
| `GUNICORN_THREADS` | No | Threads per Gunicorn worker. Default is `2` for this I/O-bound Flask app. |
| `GUNICORN_TIMEOUT` | No | Worker request timeout in seconds. Default is `30`. |
| `GUNICORN_GRACEFUL_TIMEOUT` | No | Seconds Gunicorn allows workers to finish during graceful restart/shutdown. |
| `GUNICORN_KEEPALIVE` | No | Seconds to keep HTTP connections open for reuse. |
| `GUNICORN_MAX_REQUESTS` | No | Number of requests after which a worker is recycled. Default is `1000`. |
| `GUNICORN_MAX_REQUESTS_JITTER` | No | Random extra requests added before recycling to avoid all workers restarting together. |
| `GUNICORN_ACCESSLOG` | No | Gunicorn access-log destination. Default `-` writes to stdout for platform logs. |
| `GUNICORN_ERRORLOG` | No | Gunicorn error-log destination. Default `-` writes to stderr/stdout platform logs. |
| `GUNICORN_LOGLEVEL` | No | Gunicorn log level. Default is `info`. |
| `PROXY_FIX_ENABLED` | No | Enables trusting one upstream proxy's `X-Forwarded-*` headers; keep enabled behind a TLS-terminating platform/proxy. |
| `HSTS_ENABLED` | No | Sends the `Strict-Transport-Security` header on HTTPS responses. Enable only after HTTPS is confirmed working. |
| `HSTS_MAX_AGE` | No | HSTS max-age in seconds. Default is `31536000` (one year). |
| `HSTS_INCLUDE_SUBDOMAINS` | No | Adds `includeSubDomains` to HSTS when every subdomain is HTTPS-ready. |
| `HSTS_PRELOAD` | No | Adds `preload` to HSTS only if the domain is intentionally prepared for browser preload lists. |

Important production notes:

- Do not commit `.env`; it is listed in `.gitignore`.
- `DATABASE_URL` is used by both the Flask app and Alembic. `migrations/env.py`
  reads it from the environment at migration time, and `alembic.ini` intentionally
  does not store a real connection string.
- Rotating `SECRET_KEY` immediately invalidates all active sessions and all
  pending invite/password-reset links because those tokens are signed with it.
- In production, the app refuses to start when `SECRET_KEY` is missing, equal to
  the development fallback, or shorter than 64 characters.
- Behind a TLS-terminating proxy/platform, keep `PROXY_FIX_ENABLED=true` so the
  app honors `X-Forwarded-Proto` and `X-Forwarded-Host` for secure request state
  and correct public URLs.
- Enable `HSTS_ENABLED=true` only after the custom domain has a valid HTTPS
  certificate and HTTP redirects to HTTPS.
- Operators can run `flask --app app check-config` to print required config
  names/status without printing secret values.

The app includes a `Procfile` for platforms that support it:

```text
release: alembic upgrade head
web: gunicorn app:app -c gunicorn.conf.py
```

The `release` line runs database migrations once per deploy, before the new web
process starts serving traffic (see "Database migrations" below).

For cloud hosting, install dependencies from `requirements.txt`, set the environment variables, run the migrations, and start the app with Gunicorn.

## First Production Bootstrap

On the first production deploy, let the release phase create the schema with
Alembic migrations. Do **not** run `flask --app app init-db` against the managed
database; `init-db` is only for local development and loads demo users from
`schema.sql`.

Before traffic is enabled, confirm the production environment has:

```bash
flask --app app check-config
```

For a brand-new managed database, the platform release phase should run:

```bash
alembic upgrade head
```

Create the first permanent administrator row directly in the managed database.
Use the real university email address, not the placeholder value below:

```bash
psql "$DATABASE_URL" -c "INSERT INTO users (institution_id, email, name, role, department, is_active) VALUES ('A1001', 'admin@example.edu', 'Katz Administrator', 'administrator', 'Simulation Lab', TRUE);"
```

Then set the first administrator password with a one-off platform command:

```bash
flask --app app set-password admin@example.edu "replace-with-a-strong-temporary-password"
```

After this admin logs in over HTTPS, create faculty and student accounts from the
user-management screen so the normal invite email and set-password flow is tested
end to end. Do not ship demo/default passwords.

First production smoke test checklist:

- Log in as the administrator at `https://<your-domain>`.
- Create one faculty user and one student user; confirm the invite email is
  delivered and the set-password link works.
- Create a test item, print its QR label, scan it on a phone, and confirm the
  item stock page opens on the HTTPS domain.
- Add stock and remove stock for that item.
- Confirm the transaction appears with date, time, user, lab instructor, topic,
  action, quantity, and notes.
- Apply transaction filters, export the filtered CSV, then clear filters and
  export the full CSV.
- Check transaction pagination controls if enough rows exist.
- Confirm no demo/default credentials are enabled in production.

## Deployment and Rollback

The app is designed for platform-native deployment from Git. The `Procfile`
release phase runs migrations once before the new web process serves traffic:

```text
release: alembic upgrade head
web: gunicorn app:app -c gunicorn.conf.py
```

GitHub Actions includes an optional deployment workflow:

```text
.github/workflows/deploy.yml
```

It runs only after the `CI` workflow succeeds on a push to `main` or `master`.
Store the hosting provider's deploy-hook URL as a GitHub Actions secret named
`DEPLOY_HOOK_URL`. Do not put deploy tokens or provider URLs directly in the
workflow file.

Rollback procedure:

1. Redeploy the previous good platform release or previous good Git commit.
2. If a database migration must be reversed, first test the rollback on a
   scratch/restored database.
3. Only after the scratch test passes, run:

```bash
alembic downgrade -1
```

Migrations should run in the release phase or as an intentional operator action,
never inside request handlers.

## GitHub Protection and Secrets

Before production use, protect the default branch in GitHub:

1. Go to the repository on GitHub.
2. Open **Settings > Branches > Branch protection rules**.
3. Add a rule for `master` now, or `main` if the repository is renamed later.
4. Enable **Require status checks to pass before merging**.
5. Select the CI check, shown as `CI / Test and migrations` or `Test and migrations`.
6. Enable **Require branches to be up to date before merging**.
7. Optionally enable **Require a pull request before merging** and require one
   reviewer for production changes.
8. Do not allow force pushes or branch deletion on the protected branch.

For deployment secrets:

1. Open **Settings > Secrets and variables > Actions**.
2. Add `DEPLOY_HOOK_URL` as a repository secret, or store it under the
   `production` environment if environment-level approval is preferred.
3. Open **Settings > Environments** and create `production`.
4. Add required reviewers to `production` if deployment approval should be manual.
5. Restrict deployment branches to `master` or `main`.

Never commit provider deploy tokens, SMTP passwords, database URLs, or production
`SECRET_KEY` values to workflow YAML, README, `.env.example`, or app code.

## Database migrations

Schema changes are managed with [Alembic](https://alembic.sqlalchemy.org/) in
raw-SQL mode. Alembic reads the same `DATABASE_URL` the app uses (configured in
`migrations/env.py`), so no connection string is stored in `alembic.ini`.

**Production / any shared database** is managed by migrations, not `init-db`.
Apply all pending migrations before the new app version serves traffic:

```bash
alembic upgrade head
# or, through the Flask wrapper (one consistent interface for operators):
flask --app app db-upgrade
```

On platforms with a release phase (Heroku, Railway, Render, etc.), the
`Procfile` already runs `alembic upgrade head` there, so this happens
automatically on every deploy. A redeploy with no new migrations is a safe
no-op.

Check the current revision of a database:

```bash
alembic current
```

Roll back the most recent migration (test on a scratch database first):

```bash
alembic downgrade -1
# or:
flask --app app db-downgrade -1
```

Create a new migration (hand-written raw SQL via `op.execute` / `op.add_column`
/ `op.create_index`):

```bash
alembic revision -m "describe the change"
```

`init-db` remains only for local dev bootstrap; do not run it against a database
that is under Alembic control.

## Planned Project Structure

```text
inventory/
  app.py
  requirements.txt
  README.md
  schema.sql
  PROJECT_DOCUMENTATION.md
  templates/
  static/
    css/
    js/
```

## To run the current inventory app:

Run these from your terminal:

```bash
cd /Users/farhatjahan/Desktop/YU/summer26/YU_internship/Sim_Intern/inventory/inventory_management_system
source .venv/bin/activate
```

Check PostgreSQL:

```bash
pg_isready -h localhost -d inventory_management_system
```

Start Flask:

```bash
python -m flask --app app run --debug --port 5001
```

Then open this in your browser:

```text
http://127.0.0.1:5001
```

If port `5001` is busy, use another port:

```bash
python -m flask --app app run --debug --port 5002
```

Then open:

```text
http://127.0.0.1:5002
```

## Authentication part remaining things:
1. Password reset email not sent.

## QR codes
0. DONE: password reset link is working when the app will be deployed its gonna send the invite/reset password link to the invitee.
1. Label is big, I want only QR code, nothing else on the label. 
2. How to make it printable from the p-touch D610BT label maker we have.
3. Restrict the users to school email only.
