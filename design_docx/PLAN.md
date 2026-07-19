# Inventory Project Skeleton Plan

## Recommended Reading Sequence

Read the project documents in this order to build understanding from the current
system requirements to operations and deployment:

1. `design_docx/SOFTWARE_REQUIREMENTS_SPECIFICATION.md` — The consolidated
   requirements, architecture, workflows, and system diagrams.
2. `README.md` — How to install, initialize the database, run tests, configure
   production, and start the app.
3. `PROGRESS_REPORT.md` — What has actually been built so far and current status.
4. `design_docx/PROJECT_DOCUMENTATION.md` — Beginner-friendly implementation
   notes and project explanation.
5. `QR_CODE_SYSTEM_INTEGRATION_PLAN.md` — QR code labels and camera-based
   scanning plan/status.
6. `SECURITY_AND_AUTH_PLAN.md` — Authentication and security-hardening plan.
7. `DATA_MIGRATIONS_RELIABILITY_PLAN.md` — Database migrations, reliability,
   backups, and restore planning.
8. `DEPLOYMENT_INFRASTRUCTURE_PLAN.md` — Hosting, managed PostgreSQL, TLS, and
   deployment plan.
9. `QUALITY_OPERATIONS_PLAN.md` — Testing, observability, health checks, and
   maintainability plan.
10. `UNIVERSITY_MARKET_READINESS_PLAN.md` — University/product readiness plan.

## Summary

Create a small Flask + PostgreSQL web app skeleton inside `inventory/

The skeleton will be runnable locally and will include placeholder screens for login, dashboard, item management, barcode entry, transaction history, and reports/export.

## Implementation Changes

- Add core project files:
  - `inventory/requirements.txt`
  - `inventory/README.md`
  - `inventory/app.py`
  - `inventory/schema.sql`
  - `inventory/.gitignore`

- Add frontend structure:
  - `inventory/templates/base.html`
  - `inventory/templates/login.html`
  - `inventory/templates/dashboard.html`
  - `inventory/templates/items.html`
  - `inventory/templates/item_new.html`
  - `inventory/templates/scan.html`
  - `inventory/templates/transactions.html`
  - `inventory/static/css/styles.css`

- Configure the database connection:
  - The app reads a PostgreSQL connection string from the `DATABASE_URL` environment variable.
  - Tables are created by running the `init-db` command, which executes `schema.sql`.

## Initial App Behavior

- Use Flask with PostgreSQL.
- Add routes:
  - `/` redirects to `/login` or `/dashboard`.
  - `/login` accepts an institutional ID.
  - `/logout` clears the session.
  - `/dashboard` shows inventory summary placeholders.
  - `/items` lists inventory items.
  - `/items/new` provides the add-item form.
  - `/scan` provides a barcode input form for future scanner workflow.
  - `/transactions` lists transaction history.
  - `/reports/export` is a placeholder route for future CSV export.

- Add PostgreSQL tables:
  - `users`
  - `items`
  - `transactions`

- Seed a few demo users in `schema.sql`:
  - Student user.
  - Faculty/staff user.
  - Administrator user.

## Test Plan

- Install dependencies with `pip install -r requirements.txt`.
- Initialize the database with `flask --app app init-db`.
- Start the app with `flask --app app run --debug`.
- Verify:
  - Login page opens.
  - Demo user ID can log in.
  - Dashboard loads after login.
  - Items page opens.
  - New item form opens.
  - Scan page opens and accepts barcode text.
  - Transactions page opens.
  - Logout returns user to login.

## Assumptions

- Flask is the preferred framework for the first skeleton because it is simple, local-friendly, and fast to prototype.
- Barcode scanner input will initially be handled as plain text input.
- The first skeleton will focus on structure and navigation, not complete inventory logic.
- Styling will be simple and professional, suitable for a nursing education tool.
