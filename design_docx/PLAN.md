# Inventory Project Skeleton Plan

## Recommended Reading Sequence

Read the project documents in this order to build understanding from the "why"
to the "how" to the "what is built next":

1. `design_docx/planning_and_proposal.md` — The original proposal. Explains the
   problem, the goal, and the overall idea (start here).
2. `design_docx/Phase 1 and Phase 2 Build Plan.md` — Breaks the project into
   phased, trackable tasks (requirements, design, and prototype setup).
3. `design_docx/HIGH_LEVEL_DESIGN.md` — The systems-design view: how users, the
   web app, the database, and the scanner fit together.
4. `design_docx/SYSTEM_DIAGRAMS.md` — Visual Mermaid diagrams (context, data,
   classes, and user workflows) that support the high-level design.
5. `design_docx/PLAN.md` — This file. The concrete skeleton plan for the first
   runnable Flask + PostgreSQL app.
6. `design_docx/PROJECT_DOCUMENTATION.md` — The main learning/documentation
   record: what was added, why, and how it works.
7. `README.md` — How to install, initialize the database, and run the app.
8. `PROGRESS_REPORT.md` — What has actually been built so far and current status.
9. `QR_CODE_SYSTEM_INTEGRATION_PLAN.md` — Plan to add self-generated QR code
   labels and camera-based scanning.
10. `SECURITY_AND_AUTH_PLAN.md` — Plan to move from ID-only login to secure,
    production-ready authentication.

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
