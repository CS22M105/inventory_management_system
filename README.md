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

Copy the example environment file and set real values on the server or cloud platform:

```bash
cp .env.example .env
```

Required environment variables:

- `SECRET_KEY`: long random value used to protect user sessions.
- `DATABASE_URL`: PostgreSQL connection string.
- `APP_ENV`: use `production` in deployed environments.

The app includes a `Procfile` for platforms that support it:

```text
release: alembic upgrade head
web: gunicorn app:app
```

The `release` line runs database migrations once per deploy, before the new web
process starts serving traffic (see "Database migrations" below).

For cloud hosting, install dependencies from `requirements.txt`, set the environment variables, run the migrations, and start the app with Gunicorn.

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
