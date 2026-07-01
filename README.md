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

Initialize the database tables and demo users:

```bash
flask --app app init-db
```

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
web: gunicorn app:app
```

For cloud hosting, install dependencies from `requirements.txt`, set the environment variables, initialize the PostgreSQL database once, and start the app with Gunicorn.

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

```bash
cd /Users/farhatjahan/Desktop/YU/summer26/YU_internship/Sim_Intern/inventory/inventory_management_system
source .venv/bin/activate
python -m flask --app app run --debug --port 5001
```

Then open:

```text
http://127.0.0.1:5001/login
```

If PostgreSQL is not running, start it first:

```bash
brew services start postgresql
```

If you need to initialize the database from scratch:

```bash
python -m flask --app app init-db
```

Careful: `init-db` recreates the tables and demo data, so only run it if you are okay resetting the database.

