# Progress Report: Nursing Inventory Management System

## Project Summary

This project is a barcode-based inventory management system for nursing education, simulation labs, medication rooms, and healthcare training environments.

The goal is to replace manual Excel-based tracking with a web application that supports registered user login, item management, barcode-based stock updates, and transaction history.

## Current Status

The project has moved from planning into a working Flask prototype.

The system now has:

- A Flask application structure.
- A PostgreSQL database.
- Registered user login.
- Administrator-only user management.
- Inventory item creation.
- Barcode-based add/remove stock workflow.
- Basic styling and page layout.

## Work Completed

### 1. Project Setup

Completed:

- Created the main Flask app file:
  ```text
  app.py
  ```
- Created dependency file:
  ```text
  requirements.txt
  ```
- Installed Flask in the project virtual environment:
  ```text
  .venv/
  ```
- Created project folders:
  ```text
  templates/
  static/css/
  design_docx/
  ```
- Created `.gitignore` to prevent local-only files from being pushed to GitHub.

### 2. Documentation and Design

Completed:

- Professional project proposal.
- Phase 1 and Phase 2 build plan.
- High-level system design.
- System diagrams using Mermaid.
- Project documentation explaining technical choices.

These documents are stored in:

```text
design_docx/
```

### 3. Database Setup

Completed:

- Created database schema:
  ```text
  schema.sql
  ```
- Created PostgreSQL database:
  ```text
  inventory_management_system
  ```
- Added core database tables:
  ```text
  users
  items
  transactions
  ```

The database supports:

- Registered users.
- Inventory items.
- Inventory transaction history.

### 4. Login and Access Control

Completed:

- Built login page:
  ```text
  templates/login.html
  ```
- Added user login type selection:
  - User
  - Administrator
- Added session-based login.
- Protected dashboard and inventory pages from anonymous access.
- Protected administrator pages from non-admin users.
- Removed navigation from login page.
- Added pop-up error message for unregistered users.

Current login behavior:

- Registered users can log in as users.
- Administrators can log in as administrators.
- Non-admin users cannot enter administrator mode.
- Direct access to protected pages redirects users appropriately.

### 5. Administrator User Management

Completed:

- Built administrator users page:
  ```text
  templates/admin_users.html
  ```
- Built add-user page:
  ```text
  templates/user_new.html
  ```
- Admin can add new users.
- Admin can deactivate users.
- Admin can reactivate users.
- Admin can permanently delete deactivated users if they have no transaction history.
- Current admin cannot deactivate or delete themselves.

Security behavior:

- Only users logged in with administrator mode can access user management.
- Students and regular users are redirected away from admin pages.

### 6. Inventory Item Management

Completed:

- Built items list page:
  ```text
  templates/items.html
  ```
- Built add-item page:
  ```text
  templates/item_new.html
  ```
- Faculty and administrators can add items.
- Students can view items but cannot add items.
- Items are saved in the database.
- Duplicate item barcodes are blocked.

Current item fields include:

- Barcode.
- Item name.
- Room.
- Bin location.
- Vendor.
- Quantity.
- Minimum quantity.
- General location.
- Expiration date.
- Notes.

### 7. Barcode Scan Workflow

Completed:

- Built scan page:
  ```text
  templates/scan.html
  ```
- Added `/scan` route in Flask.
- Users can scan or type a barcode.
- Users can add stock.
- Users can remove stock.
- System prevents removing more items than are available.
- Each add/remove action creates a transaction record.
- Each transaction can include lab instructor name and topic of the day.

Current scan workflow:

```text
User logs in
User scans or enters barcode
User selects Add Stock or Remove Stock
User enters quantity
User can enter lab instructor and topic of the day
System updates item quantity
System records transaction
```

### 8. Styling

Completed:

- Created shared stylesheet:
  ```text
  static/css/styles.css
  ```
- Created login-specific stylesheet:
  ```text
  static/css/login.css
  ```
- Styled:
  - Shared layout.
  - Login page.
  - Forms.
  - Tables.
  - Dashboard cards.
  - Error modal.
  - Admin action buttons.

## Current Working Features

The current prototype supports:

- User login.
- Admin login.
- Admin user management.
- User deactivation/reactivation.
- Permanent deletion of inactive users without transaction history.
- Inventory item creation.
- Inventory item listing.
- Barcode-based stock add/remove.
- Transaction records being created in the database.
- Basic protected routes.

## Known Issues and Gaps

The following items still need work:

- Transaction history page is not implemented yet.
- `/transactions` navigation link currently needs a route and page.
- Dashboard numbers are still hard-coded instead of database-driven.
- CSV/Excel export is not implemented yet.
- Some error messages should be improved for duplicate user creation.
- More detailed item pages and edit functionality are not implemented yet.
- GitHub repository setup still needs to be completed cleanly from inside the `inventory` folder.

## Recommended Next Steps

Recommended next development order:

1. Build the transaction history page.
2. Add `/transactions` route.
3. Update dashboard numbers from the database.
4. Improve duplicate user error handling.
5. Add item detail/edit pages.
6. Add CSV export.
7. Prepare clean GitHub push.

## Overall Progress

The project has completed the foundation and several core workflows.

The most important achievement is that the system now demonstrates the central idea:

```text
Registered user logs in
Inventory item exists in database
Barcode is scanned or entered
Quantity is added or removed
Database updates automatically
Transaction is recorded
```

This means the project has moved beyond planning and now has a functional prototype for the main inventory automation workflow.

---

## Progress Update - June 24, 2026

Today, several improvements were made to move the inventory management system closer to a complete working prototype and prepare it for future cloud deployment. The work was done carefully in small steps so the existing local system would continue working.

### 1. Faculty Login and Faculty Permissions

What was done:

- Added a separate Faculty option on the login page.
- Updated the permission logic so faculty users receive the same system authority as administrators.
- Faculty users can now access admin-level features such as:
  - Manage Users.
  - Add New Item.
  - Edit Item.
  - Export CSV.
  - Database Status.

Why it was needed:

- The database already supported faculty users, but the login screen did not provide a clear Faculty login option.
- In the project workflow, faculty members need the same level of access as administrators because they may manage users, inventory items, and transaction records.

How it was done:

- The login dropdown was updated to include Faculty.
- The role-checking logic was updated so both `faculty` and `administrator` are treated as elevated roles.
- The navigation menu was updated so faculty users see the same functional options as administrators.

### 2. Optional Expiration Date

What was done:

- Made the item expiration date optional.
- Set the default expiration date value to:

```text
00/00/0000
```

Why it was needed:

- Some inventory items may not have an expiration date.
- Requiring an expiration date would make item creation inconvenient or inaccurate for supplies that do not expire.

How it was done:

- The item form processing was updated so a blank expiration date is saved as `00/00/0000`.
- The database schema was updated so new rows can also use this default.
- The Add New Item and Edit Item forms were adjusted to show the default value.

### 3. Transaction History Filters

What was done:

- Added filters to the Transaction History page.
- Users can now filter transactions by:
  - From Date.
  - To Date.
  - Item.
  - User.
  - Lab Instructor.
  - Topic.
  - Action type.

Why it was needed:

- As the system is used more, the transaction history will become long.
- Filters make it easier to find specific records for a lab session, instructor, topic, item, user, or date range.

How it was done:

- The `/transactions` route was updated to read filter values from the page URL.
- SQL conditions are added only when a filter is selected.
- Item and user filters are populated from the database.
- Action type supports Add Stock and Remove Stock.

### 4. Lab Instructor and Topic Dropdown Filters

What was done:

- Changed Lab Instructor and Topic filters from text boxes to dropdown choices.

Why it was needed:

- Users may not remember the exact spelling of instructor names or lab topics.
- Dropdowns reduce typing mistakes and make filtering easier.

How it was done:

- The system now reads distinct existing lab instructor names and topics from transaction records.
- Empty instructor and topic values are excluded from the dropdown choices.
- Selecting a value filters the transaction history by that exact instructor or topic.

### 5. Transaction Filter Layout Fix

What was done:

- Fixed the User dropdown in the transaction filter area so it stays inside the filter box.

Why it was needed:

- Long user names or institution IDs could make the dropdown extend outside the filter rectangle.
- This made the page look unpolished.

How it was done:

- CSS was updated so filter inputs and dropdowns use proper width and shrink correctly inside the grid layout.

### 6. Transaction History CSV Export

What was done:

- Added a new CSV export for transaction history.
- Added an Export Transactions CSV button below the filter rectangle.
- The button was not added to the navigation bar.

Why it was needed:

- The system already supported inventory export.
- Transaction history export is useful for reporting, record keeping, audits, and reviewing lab usage.

How it was done:

- A new `/transactions/export` route was added.
- The export uses the same filter logic as the Transaction History page.
- If no filters are applied, all transactions are exported.
- If filters are applied, only the filtered transactions are exported.
- The CSV includes:
  - Date.
  - Time.
  - Action.
  - Item.
  - Barcode.
  - Quantity.
  - Lab Instructor.
  - Topic.
  - User.
  - Notes.

### 7. Production Configuration Preparation

What was done:

- Moved the Flask `SECRET_KEY` configuration to an environment variable.
- Added production-friendly session cookie settings.
- Added `gunicorn` to the project dependencies.
- Added a `Procfile` for cloud deployment startup.
- Added `.env.example` to document required environment variables.
- Updated `.gitignore` to avoid committing `.env` and `.venv/`.
- Updated the README with production configuration instructions.

Why it was needed:

- The project is currently running locally, but future deployment will require safer configuration.
- Secret values should not be hardcoded in `app.py` or pushed to GitHub.
- Flask's built-in development server is not intended for production hosting.

How it was done:

- `SECRET_KEY` now comes from the environment.
- Local development still works with a development fallback.
- Production mode requires `SECRET_KEY` to be set before the app starts.
- `APP_ENV=production` enables secure cookie behavior.
- Gunicorn can start the app using:

```text
web: gunicorn app:app
```

### 8. Verification Performed

The following checks were used during development:

- Python syntax checks using:

```bash
python -m py_compile app.py
```

- Flask route checks for new routes.
- Test client checks for:
  - Faculty login.
  - Transaction filter rendering.
  - Filtered transaction pages.
  - Transaction CSV export with and without filters.
  - Production configuration behavior.

### Current Result

The system now supports more complete inventory tracking and reporting:

```text
User, faculty, or admin logs in
Inventory items are managed
Stock is added or removed
Transaction details are recorded
Transactions can be filtered
Filtered or complete transaction history can be exported
Production configuration is partially prepared for cloud hosting
```

This update improves both daily usability and future deployment readiness while keeping the existing local workflow intact.

---

## Role Permission Update - June 24, 2026

The user roles were refined to better match the intended responsibilities of faculty and administrators.

### 1. Faculty Permissions

What was changed:

- Faculty users can manage students.
- Faculty users can:
  - Add students.
  - Activate students.
  - Deactivate students.
  - Delete inactive students when allowed.
- Faculty users cannot add, activate, deactivate, or delete faculty users.
- Faculty users cannot manage administrator accounts.
- Faculty users cannot see or access the Database Status page.

Why it was needed:

- Faculty need enough access to manage student users during normal lab operations.
- Faculty should not be able to control faculty accounts or system-level database information.
- This keeps faculty as faculty while still giving them the operational access they need.

How it was done:

- The backend permission logic now checks which role is being managed.
- Faculty sessions are allowed to manage only users with the `student` role.
- The Add User page only shows role choices that the logged-in user is allowed to create.
- The navigation bar hides Database Status from faculty users.
- Direct access to the Database Status route is blocked for faculty users.

### 2. Administrator Permissions

What was changed:

- Administrator users can manage students and faculty.
- Administrator users can:
  - Add students.
  - Add faculty.
  - Activate students and faculty.
  - Deactivate students and faculty.
  - Delete inactive students and faculty when allowed.
- Administrator users can see and access the Database Status page.
- Administrator accounts are permanent and protected.

Why it was needed:

- The administrator role should be the highest system role.
- Administrators need control over faculty and student access.
- Administrator accounts should not be accidentally removed or disabled because that could lock the system out of full control.

How it was done:

- A stricter admin-only check was added for Database Status.
- User management actions now block any attempt to activate, deactivate, or delete administrator accounts.
- The Manage Users page shows administrator accounts as:

```text
Permanent admin
```

- The Add User page no longer allows anyone to create another administrator from the web form.

### 3. Verification Performed

The following behavior was tested:

- Faculty cannot access Database Status.
- Faculty can add students only.
- Faculty cannot create faculty users.
- Faculty cannot deactivate faculty users.
- Faculty can deactivate and delete allowed student users.
- Administrator can access Database Status.
- Administrator can add students and faculty.
- Administrator can deactivate and delete allowed faculty users.
- Administrator account `A1001` cannot be deactivated or deleted.

### Current Result

The role model is now clearer:

```text
Student: normal system user
Faculty: manages students and inventory workflows
Administrator: manages students, faculty, and system-level status
Administrator account: permanent and protected
```

This update improves security and role clarity before moving the project toward barcode scanner testing and cloud deployment.

## Scan Form Fix: Prevent Incomplete Transactions - June 30, 2026

### 1. Problem Addressed

What was happening:

- On the Scan Item page, pressing Enter could submit the form before all the fields were filled in.
- This was especially easy to trigger with a barcode scanner. Most scanners type the barcode and then automatically send an Enter keystroke. Because the barcode box is focused when the page loads, that Enter submitted the form right away.
- When this happened, a transaction row was still recorded and the item quantity was changed, even though the Lab Instructor, Topic of the Day, and Notes were empty.

Why it needed to change:

- A transaction should only be recorded when all of its entries are filled in.
- Incomplete rows in the transaction history make the audit log less trustworthy and harder to read.
- The accidental Enter submit caused confusion during scanning.

### 2. What Was Changed

Where: `templates/scan.html`

- The Lab Instructor, Topic of the Day, and Notes fields are now marked as required, so the browser will not submit the form until they are filled in.
- A small script was added at the bottom of the page. When the user presses Enter inside the barcode box, the form no longer submits. Instead, focus moves to the Action dropdown so the user can continue filling out the rest of the form. This is the standard fix for barcode scanners that send an Enter keystroke after the barcode.

Where: `app.py` (the `/scan` POST handler)

- Server-side checks were added so the application refuses to record a transaction unless the Lab Instructor, Topic of the Day, and Notes fields are all filled in.
- These checks run before any change is made to the item quantity or the transactions table. If a required field is missing, the page shows a clear error message and nothing is saved.

How the two layers work together:

- The form (browser) is the first line of defense and gives the user immediate feedback.
- The server checks are the guarantee. Even if the browser checks are bypassed (for example by a stray Enter, an older browser, or disabled JavaScript), no transaction row is written until every entry is filled.

### 3. Why It Was Done This Way

- Client-side checks alone can always be bypassed, so the same rules are enforced on the server to fully protect the transaction history.
- Moving focus on Enter (instead of just blocking it) keeps the scanning workflow fast: scan the barcode, then continue straight into the rest of the form.

### 4. Verification Performed

The following behavior was tested:

- Scanning a barcode (which sends Enter) no longer submits the form; focus moves to the Action dropdown.
- Submitting with an empty Lab Instructor, Topic of the Day, or Notes field is blocked and shows an error.
- No transaction row is created and no item quantity changes when a required field is missing.
- A fully filled form still records the transaction and updates the quantity as before.

### Current Result

Transactions on the Scan Item page are now only recorded when every entry is filled in, and accidental Enter key presses (including from barcode scanners) no longer create incomplete records.

## Scan Form Update: Highlight Empty Fields on Enter - June 30, 2026

### 1. Problem Addressed

What was happening:

- The previous Enter-key fix on the Scan Item page worked by moving focus to the Action dropdown whenever the user pressed Enter inside the barcode box.
- Jumping focus to the dropdown took the user away from where they were and only pointed them at one field, even though several other entries (Quantity, Lab Instructor, Topic of the Day, Notes) could still be empty.
- The user could not see, at a glance, everything that still needed to be filled in before the form could be submitted.

Why it needed to change:

- Pulling focus to the dropdown was disruptive and did not communicate the full set of missing entries.
- It is clearer and less jarring to show the user every empty required field at once and let them stay where they are.

### 2. What Was Changed

Where: `templates/scan.html`

- The barcode Enter handler no longer moves focus to the Action dropdown. Instead, pressing Enter in the barcode box now highlights every still-empty required field (Barcode, Action, Quantity, Lab Instructor, Topic of the Day, and Notes) in place, without changing focus.
- Each highlighted field clears its highlight automatically as soon as the user fills it in (on input or change).
- The same highlight runs on a real submit attempt, so any field left empty is marked.

Where: `static/css/styles.css`

- Added a `.field-error` class that gives an empty required field a red border, a light red background, and a red focus outline so missing entries are easy to spot.

Where: `app.py` (the `/scan` POST handler)

- No new change in this update. The server-side checks that reject a transaction when Lab Instructor, Topic of the Day, or Notes is empty remain in place and continue to act as the final guarantee.

How the layers work together:

- The browser highlight is immediate visual feedback that points out every missing entry without moving the user's focus.
- The server checks remain the guarantee: even if the browser checks are bypassed (stray Enter, old browser, or disabled JavaScript), no transaction row is written until every required entry is filled.

### 3. Why It Was Done This Way

- Highlighting all empty fields at once gives the user a complete picture of what is missing, instead of nudging them toward a single field.
- Keeping focus in the barcode box avoids the disruptive focus jump while still blocking the accidental Enter submit.
- Clearing the highlight on input keeps the feedback honest, so a field stops looking like an error the moment it is filled.

### 4. Verification Performed

The following behavior was tested:

- Pressing Enter in the barcode box no longer submits the form and no longer moves focus to the Action dropdown; instead, all empty required fields are highlighted in red.
- Filling in a highlighted field removes its highlight immediately.
- Attempting to submit with any empty required field highlights the missing fields, and the server still blocks the transaction.
- A fully filled form still records the transaction and updates the quantity as before.

### Current Result

Pressing Enter on the Scan Item page now clearly highlights every empty required field in place rather than moving focus to the dropdown, making it obvious what still needs to be filled in while the server continues to guarantee that no incomplete transaction is ever recorded.

## Update: July 1, 2026 — QR Code Integration Step 1 (Dependencies and Configuration)

This update starts the QR code system described in `QR_CODE_SYSTEM_INTEGRATION_PLAN.md`. It covers only Step 1 of the recommended implementation order: "Add Dependencies And Config." No routes, database changes, or templates were touched in this step. The goal was to put the QR library and its configuration values in place safely, without changing any existing behavior.

### 1. What Was Changed

Where: `requirements.txt`

- Added the `qrcode[pil]>=7.4,<8.0` dependency. The `[pil]` extra pulls in Pillow so the library can render QR codes as PNG images later.

Where: `.env.example`

- Added `APP_BASE_URL=http://127.0.0.1:5001`. This is the public base URL that future QR links will be built from.
- Added `BARCODE_PREFIX=KATZ-NURS`. This is the prefix for auto-generated internal item codes (for example, `KATZ-NURS-000014`).

Where: `app.py`

- Added two configuration variables read from the environment, next to the existing `APP_ENV` and `SECRET_KEY` config:
  - `APP_BASE_URL = os.environ.get("APP_BASE_URL")` — left as `None` when unset so later QR routes can fall back to the current request host.
  - `BARCODE_PREFIX = os.environ.get("BARCODE_PREFIX", "KATZ-NURS")` — defaults to `KATZ-NURS` when unset.

### 2. How It Was Done

- The dependency was added to `requirements.txt` and installed into the existing project virtual environment with `pip install -r requirements.txt`. This installed `qrcode 7.4.2` along with `pillow`, `pypng`, and `typing-extensions`.
- The new environment variables were added to `.env.example` only. Real secrets and machine-specific values still live in the untracked `.env` file; `.env.example` documents the expected keys for anyone setting up the project.
- The two config values in `app.py` follow the same `os.environ.get(...)` pattern already used for `DATABASE_URL`, `APP_ENV`, and `SECRET_KEY`, so configuration stays consistent and centralized.
- No existing imports, routes, templates, or database objects were modified. The QR library is installed and configured but not yet used anywhere, keeping this step isolated and low-risk.

### 3. Why It Was Done This Way

- Following the plan's recommended order (config first) keeps each change small and easy to verify, and lets the QR feature be built up in reviewable pieces.
- `APP_BASE_URL` is required because a QR code that encodes `127.0.0.1` only works on the same computer. A phone camera needs a real network or cloud URL, so the base URL must be configurable per environment (local, local network, and production) rather than hard-coded.
- Leaving `APP_BASE_URL` as `None` by default (instead of forcing a value) lets the app fall back to the live request host during local development, so the feature works out of the box without extra setup.
- `BARCODE_PREFIX` is configurable so the university can change the code scheme later (for example, `YU-KATZ-NURS`) without editing application code.
- Keeping the value in `.env.example` documents the setting without committing any environment-specific value into version control.

### 4. Verification Performed

- Installed dependencies with `pip install -r requirements.txt`; `qrcode 7.4.2` and Pillow installed successfully into `.venv/`.
- Ran `python -m py_compile app.py` (the plan's Step 1 verification command); it compiled with no errors.
- Confirmed the library works at runtime: `import qrcode` succeeds and `qrcode.make("test")` produces an image object.
- Imported the app module and confirmed the new config loads correctly: `BARCODE_PREFIX` reads as `KATZ-NURS`, and `APP_BASE_URL` is `None` (expected, since it is unset locally and is meant to fall back to the request host).

### Current Result

The QR code library and its configuration are now installed and available in the project. `requirements.txt`, `.env.example`, and `app.py` are ready for the next steps, and none of the existing login, item, scan, transaction, or admin functionality was changed or affected by this step.

## Update: July 1, 2026 — QR Code Integration Step 2 (Barcode Sequence)

This update covers Step 2 of `QR_CODE_SYSTEM_INTEGRATION_PLAN.md`: "Add Barcode Sequence." It adds a PostgreSQL sequence that will be used later to generate unique internal item codes (for example, `KATZ-NURS-000014`). No barcode is generated yet and no existing behavior changed; this step only creates the sequence and makes sure it exists safely on both new and existing databases.

### 1. What Was Changed

Where: `schema.sql`

- Added `CREATE SEQUENCE item_barcode_number_seq START WITH 1;` immediately after the `items` table. This is the counter that future item-code generation will draw from.
- Added `DROP SEQUENCE IF EXISTS item_barcode_number_seq;` alongside the existing `DROP TABLE IF EXISTS ...` statements at the top of the file, so re-running `init-db` does not fail with an "already exists" error.

Where: `app.py`

- Added a new helper, `ensure_barcode_sequence(db)`, next to the existing `ensure_transaction_columns(db)` helper. It runs `CREATE SEQUENCE IF NOT EXISTS item_barcode_number_seq START WITH 1` and commits.
- Called `ensure_barcode_sequence(db)` inside the `init-db` CLI command (after loading `schema.sql`) so the sequence is guaranteed to exist even on a database that was created before this feature.

### 2. How It Was Done

- The plain `CREATE SEQUENCE ... START WITH 1` lives in `schema.sql` so a fresh database gets the sequence when the schema is first loaded. The matching `DROP SEQUENCE IF EXISTS` keeps `init-db` idempotent, following the same drop-then-create pattern already used for the tables.
- The `IF NOT EXISTS` variant lives in `app.py` as `ensure_barcode_sequence(db)`. This mirrors the existing `ensure_transaction_columns(db)` runtime-migration pattern, so an already-running database that predates this feature can gain the sequence without a destructive re-initialization.
- `ensure_barcode_sequence(db)` is wired into `init-db` for now. When Step 3 adds automatic barcode generation, the same helper can be called right before the first `nextval(...)` so the sequence is always present at the moment it is needed.
- `python -m py_compile app.py` was run to confirm the file still compiles.

### 3. Why It Was Done This Way

- A PostgreSQL sequence is used instead of `COUNT(*) + 1` because the database guarantees each `nextval(...)` returns a unique, ever-increasing number even when two users add items at the same time. `COUNT(*) + 1` can hand out the same number twice under concurrent inserts and would produce duplicate barcodes.
- The sequence is defined in both `schema.sql` (plain create) and `app.py` (`IF NOT EXISTS`) to cover both cases the plan calls out: a brand-new database built from the schema, and an existing database that must be upgraded safely at runtime without dropping data.
- Adding `DROP SEQUENCE IF EXISTS` was a deliberate safety choice so that `flask --app app init-db` remains safe to re-run, exactly like it already is for the tables.
- The change is intentionally isolated: the sequence exists but nothing consumes it yet, so no current login, item, scan, transaction, admin, or CSV-export behavior is affected. Barcode generation is deferred to Step 3.

### 4. Verification Performed

- Ran `python -m py_compile app.py`; it compiled with no errors.
- Reviewed `schema.sql` to confirm the create statement follows the `items` table and the matching drop is grouped with the other `DROP ... IF EXISTS` statements.
- Confirmed the new `ensure_barcode_sequence(db)` helper uses `CREATE SEQUENCE IF NOT EXISTS` and is invoked from the `init-db` command.

### Current Result

The database now has an `item_barcode_number_seq` sequence that will feed automatic internal item codes in later steps. New databases get it from `schema.sql`, existing databases get it from the `ensure_barcode_sequence(db)` runtime-safety helper, and re-running `init-db` is still safe. No existing functionality was changed by this step.

## Update: July 1, 2026 — QR Code Integration Step 3 (Optional Barcode On Add Item)

This update covers Step 3 of `QR_CODE_SYSTEM_INTEGRATION_PLAN.md`: "Make Barcode Optional On Add Item." The barcode field on the Add Item form is now optional. If it is left blank, the app automatically generates a unique internal code (for example, `KATZ-NURS-000001`) using the sequence added in Step 2. If a barcode is typed in, that exact value is still used as before. Editing an existing item continues to require a barcode.

### 1. What Was Changed

Where: `app.py`

- Added a new helper, `generate_next_item_barcode(db)`, next to `ensure_barcode_sequence(db)`. It calls `ensure_barcode_sequence(db)` first (runtime safety), then reads the next value with `SELECT nextval('item_barcode_number_seq')` and formats it as `f"{BARCODE_PREFIX}-{number:06d}"`, which produces codes like `KATZ-NURS-000001`.
- Changed `get_item_form_data()` to `get_item_form_data(require_barcode=True)`. When `require_barcode` is `False`, a blank barcode no longer triggers a validation error; the other required fields (name, bin location, room) are still enforced, with a matching error message ("Name, bin location, and room are required.").
- Updated the `item_new` route to call `get_item_form_data(require_barcode=False)` and, when the submitted barcode is blank, generate one with `generate_next_item_barcode(db)` before inserting the row.
- Left the `item_edit` route calling `get_item_form_data()` with the default `require_barcode=True`, so editing still requires an explicit barcode.

Where: `templates/item_new.html`

- Renamed the label from "Barcode" to "Barcode / Internal Code".
- Removed the `required` attribute from the barcode input and changed the placeholder to "Leave blank to auto-generate".
- Added helper text under the field: "Leave blank to auto-generate a Katz Nursing inventory code."

### 2. How It Was Done

- The generation helper mirrors the exact approach in the integration plan (`nextval` + zero-padded formatting), and reuses the existing `BARCODE_PREFIX` config and `item_barcode_number_seq` sequence from Steps 1 and 2, so no new configuration or schema was introduced.
- Rather than duplicating the validation logic, the shared `get_item_form_data()` gained a single `require_barcode` flag. This keeps one source of truth for item form parsing while letting "add" and "edit" differ only in whether a barcode is mandatory.
- Barcode generation happens in the route (not in the form parser) and only after validation succeeds, so a sequence number is consumed only when an item is actually about to be created. Manual barcodes bypass generation entirely.
- The existing duplicate-barcode safeguard was left untouched: if a generated or manual code collides, the `psycopg2.IntegrityError` handler still shows "An item with this barcode already exists."

### 3. Why It Was Done This Way

- Auto-generating codes removes the need for staff to invent unique barcodes by hand and guarantees every item has a scannable code, which is the foundation the later QR label/scan steps depend on.
- Using the database sequence (instead of `COUNT(*) + 1`) keeps codes unique even under simultaneous item creation, matching the reasoning documented in Step 2.
- Keeping the manual-entry path working means pre-labeled or vendor-barcoded items can still be registered with their existing codes, so the change is additive and backward-compatible.
- Editing still requires a barcode because an existing item already has one; a blank value there would more likely be a mistake than a request to regenerate.

### 4. Verification Performed

- Ran `python -m py_compile app.py`; it compiled with no errors.
- Used the Flask test client (logged in as the seeded `F1001` faculty user) against the local PostgreSQL database:
  - Created an item with a blank barcode and confirmed the stored value was `KATZ-NURS-000001`.
  - Created an item with a manual barcode (`MANUAL-ZZ2-001`) and confirmed that exact value was stored unchanged.
  - Removed the two temporary test items afterward.
- Reset `item_barcode_number_seq` back to `1` after testing (verified no real items use the `KATZ-NURS-` format yet), so the first real auto-generated item will still be `KATZ-NURS-000001`.

### Current Result

Staff can now add an item without typing a barcode and the system assigns the next `KATZ-NURS-######` code automatically, while manually entered barcodes continue to work exactly as before. Editing behavior, duplicate protection, and all other login, item, scan, transaction, admin, and CSV-export functionality are unchanged.

## Update: July 1, 2026 — QR Code Integration Step 4 (Item Detail Page)

This update covers Step 4 of `QR_CODE_SYSTEM_INTEGRATION_PLAN.md`: "Add Item Detail Page." There is now a read-only page at `/items/<barcode>` that shows every stored field for a single item, plus a low-stock status. It is reachable from a new "View" link on the All Items table. Any logged-in user (including students) can view it; only faculty/administrators see the Edit button. This page is the destination that the upcoming QR labels will point to.

### 1. What Was Changed

Where: `app.py`

- Added a new route and view function `item_detail(barcode)` mapped to `/items/<barcode>`. It requires login (via the existing `require_login()` guard), looks up a single item by its `barcode`, and renders the new `item_detail.html` template.
- If no item matches the barcode, it calls `abort(404, description="Not recognized")`, so an unknown code returns a 404 instead of a blank or error page.

Where: `templates/item_detail.html` (new file)

- Displays all item fields: name, internal code (barcode), vendor, room, bin, general location, current quantity, minimum quantity, expiration date, and notes, along with a plain-language "Stock Status" row.
- Shows a "Low stock" badge in the page header when `quantity <= minimum_quantity`.
- Provides action buttons: "Stock Action" (links to the existing `/scan` page), "Edit Item" (faculty/administrator only, links to the existing edit page), and "All Items".

Where: `templates/items.html`

- The Action column is now always shown (previously it only appeared for faculty/administrators).
- Every row now has a "View" link (visible to all logged-in users, including students) pointing to the item's detail page, with the "Edit" link still shown only to faculty/administrators.

### 2. How It Was Done

- The route uses a string `<barcode>` converter rather than the numeric `<int:item_id>` used by the edit route, because QR codes and scanners work with the human-readable barcode/internal code, not the internal database id. The detail lookup therefore queries `WHERE barcode = %s`.
- Flask/Werkzeug matches the more specific static routes (`/items/new`, `/items/low-stock`) and the `/items/<int:item_id>/edit` route ahead of the generic `/items/<barcode>` route, so adding this route does not shadow or break any existing item URLs.
- The template reuses existing CSS classes only (`page-header`, `status-badge`, `table`, `action-group`, `button-link`, `secondary-link`), so no stylesheet changes were needed for this step.
- The "View" link is built with `url_for('item_detail', barcode=item['barcode'])`, keeping URL generation consistent with the rest of the app instead of hard-coding paths.

### 3. Why It Was Done This Way

- The plan sequences the detail page before QR label/PNG generation on purpose: QR codes need a useful, verified destination, and this page confirms that looking an item up by its code works end to end.
- Access is intentionally read-only for everyone and edit-only for faculty/administrators, matching the plan's access rule and the existing role model (students can view inventory but not change item records).
- The "Stock Action" button points to the existing `/scan` page for now because the dedicated per-item stock route (`/items/<barcode>/stock`) and the printable label route (`/items/<barcode>/label`) are scheduled for later steps (Steps 6-7). Linking only to routes that already exist keeps this step self-contained and avoids `url_for` build errors; those buttons can be repointed when the later routes are added.

### 4. Verification Performed

- Ran `python -m py_compile app.py`; it compiled with no errors.
- Confirmed via the code that a valid barcode (e.g. a seeded/added item) renders the detail page and an unknown barcode triggers `abort(404, description="Not recognized")`.
- Confirmed the All Items "View" link is present for all roles and that the "Edit" link/button on both the list and the detail page remain gated to faculty/administrators.

### Current Result

Users can open any item's full details from the All Items list, students included, while editing stays restricted to faculty/administrators. The new `/items/<barcode>` page gives QR labels a working destination in the next steps, and all existing login, item, scan, transaction, admin, and CSV-export behavior is unchanged.

## Update: July 1, 2026 — QR Code Integration Step 5 (QR PNG Route)

This update covers Step 5 of `QR_CODE_SYSTEM_INTEGRATION_PLAN.md`: "Add QR PNG Route." The app now serves a live QR-code image at `/items/<barcode>/qr.png`. The image is generated in memory on each request (no files are saved) and encodes the per-item stock URL, so scanning the QR with a phone opens that item's stock page.

### 1. What Was Changed

Where: `app.py`

- Added `import qrcode` to the imports.
- Added a new route and view function `item_qr_png(barcode)` mapped to `/items/<barcode>/qr.png`. It requires login (via `require_login()`), confirms the barcode belongs to a real item, and returns a PNG.
- If no item matches the barcode, it calls `abort(404, description="Not recognized")`, consistent with the detail page from Step 4.
- The route builds the target URL as `{base_url}/items/{barcode}/stock`, where `base_url` is the configured `APP_BASE_URL` or, if unset, the current request host (`request.host_url`). It then renders a QR code with `qrcode.QRCode(...)`, saves the image to an in-memory `io.BytesIO` buffer, and returns it with `Response(..., mimetype="image/png")`.

### 2. How It Was Done

- The QR settings mirror the existing `testQR/generate_qr.py` prototype (`version=1`, `ERROR_CORRECT_M`, `box_size=10`, `border=4`, black on white) so the production route matches the already-validated sample.
- The image is streamed from an in-memory buffer rather than written to disk. This keeps the server stateless, avoids filesystem cleanup, and means the QR always reflects the item's current barcode because it is regenerated on every request.
- The stock URL is assembled as a plain string (`f"{base_url}/items/{barcode}/stock"`) instead of `url_for('item_stock', ...)`. The dedicated stock route is scheduled for a later step (Step 6), and using `url_for` for a route that does not exist yet would raise a `BuildError`. Assembling the string lets the QR encode the correct final URL now, so the image and its contents can be fully tested before the stock page is built.
- `APP_BASE_URL` (already defined in config) is preferred so that printed labels point at the real deployed hostname; the `request.host_url` fallback keeps local development working without extra configuration.

### 3. Why It Was Done This Way

- A dynamic PNG route is the simplest reliable way to put a QR on a web page or a printed label: the browser loads it like any normal image (`<img src=".../qr.png">`), and there are no stored files to manage or serve.
- Encoding the stock URL (rather than just the barcode) means a phone camera can scan the label and jump straight to the correct action page, which is the core goal of the QR workflow.
- Requiring login and validating the barcode keeps the image route consistent with the rest of the app's access rules and prevents QR images from being generated for codes that do not exist.

### 4. Verification Performed

- Ran `python -m py_compile app.py`; it compiled with no errors.
- Confirmed `qrcode` and `Pillow` import in the project virtual environment (both are already pinned in `requirements.txt` as `qrcode[pil]`).
- Reproduced the route's image logic in isolation and confirmed it returns a valid PNG (correct `\x89PNG` header, ~900 bytes) that encodes `http://127.0.0.1:5000/items/KATZ-NURS-000001/stock`.
- Manual browser check (to run locally): start the app, log in, open `/items/<barcode>/qr.png` for a real item — the QR image renders; scanning it with a phone shows the `.../items/<barcode>/stock` URL. An unknown barcode returns 404 "Not recognized".

### Current Result

Each item now has an on-demand QR image at `/items/<barcode>/qr.png` that encodes its stock URL and is generated fresh in memory on every request. This is the image the printable label page will embed in the next step. All existing login, item, detail, scan, transaction, admin, and CSV-export behavior is unchanged. Note: the URL the QR points to (`/items/<barcode>/stock`) becomes a working page in Step 6; until then, scanning resolves to the correct address but that page does not exist yet.

## Update: July 1, 2026 — QR Code Integration Step 6 (Printable Label Page)

This update covers Step 6 of `QR_CODE_SYSTEM_INTEGRATION_PLAN.md`: "Add Printable Label Page." There is now a page at `/items/<barcode>/label` that shows a compact, print-ready label containing the Katz Nursing heading, the item name, its internal code, the QR image from Step 5, and the room and bin. A "Print Label" button opens the browser's print dialog, and print CSS hides the site chrome so only the label prints.

### 1. What Was Changed

Where: `app.py`

- Added a new route and view function `item_label(barcode)` mapped to `/items/<barcode>/label`. It requires login (via `require_login()`), looks up the item's label fields (`barcode`, `name`, `room`, `bin_location`, `company`, `expiration_date`) by barcode, and renders the new `item_label.html` template. An unknown barcode returns `abort(404, description="Not recognized")`, consistent with Steps 4 and 5.

Where: `templates/item_label.html` (new file)

- Renders a `.qr-label` block containing: "Katz Nursing Inventory" heading, item name, internal code, the QR `<img>` (sourced from `url_for('item_qr_png', ...)`, the Step 5 route), plus Room and Bin. Vendor and Expiration Date are shown only when present (expiration is hidden when it is still the `00/00/0000` placeholder).
- Adds a "Print Label" button that calls `window.print()`, plus "Back to Item" and "Back to All Items" links. These controls and the page header are wrapped in `.no-print` so they do not appear on the printed output.

Where: `static/css/styles.css`

- Added `.qr-label` styles (white background, thin dark border, fixed 2.4in width) and `.qr-label img` sizing (1.1in square), matching the plan's recommended label dimensions, plus small helper classes for the label's title, name, code, and meta lines.
- Added an `@media print` block that hides `header`, `footer`, `nav`, and any `.no-print` element, resets the page background to white, and strips the `main`/`section` margins, borders, and shadows so the label prints cleanly on its own.

Where: `templates/items.html`

- Added a "Print Label" link to each row's Action group (visible to all logged-in users), alongside the existing "View" and faculty/admin-only "Edit" links.

Where: `templates/item_detail.html`

- Added a "Print Label" button to the item detail action group, pointing at the new label route. (In Step 4 this button was intentionally omitted because the route did not exist yet.)

### 2. How It Was Done

- The label embeds the QR by pointing an `<img>` at the existing `/items/<barcode>/qr.png` route via `url_for('item_qr_png', ...)`, so the label page does not regenerate the QR itself — it reuses the Step 5 image route as the single source of truth.
- Printing uses the browser's built-in `window.print()` rather than any library or server-side PDF generation, which is the simplest reliable approach and matches the plan's "start with browser print" guidance.
- The separation between screen and print is handled entirely with the `.no-print` class and the `@media print` rule, so the same page serves both the on-screen preview (with buttons) and the clean printed label (label only).
- CSS was appended to the end of `styles.css` next to the existing responsive block, and reuses the plan's recommended values so the label size is predictable for common label printers.

### 3. Why It Was Done This Way

- A dedicated label page keeps printing separate from the detail/stock views, so staff can print without accidentally triggering stock changes, and the print CSS guarantees the surrounding site UI never ends up on the label.
- Reusing the Step 5 QR route (instead of embedding image bytes in the page) keeps one code path for QR generation and ensures the printed QR always matches what a scan would open.
- Showing Vendor and Expiration only when meaningful keeps small labels uncluttered, while Room and Bin are always shown because they are the fields staff use to physically locate and restock an item.
- Access is allowed for any logged-in user because printing a label is a low-risk, read-only action; it does not modify inventory.

### 4. Verification Performed

- Ran `python -m py_compile app.py`; it compiled with no errors, and no linter errors were reported for the changed files.
- Confirmed the label route selects and passes the fields the template uses, and that the QR `<img>` resolves through the working `item_qr_png` route added in Step 5.
- Manual browser check (to run locally): start the app, log in, open `/items/<barcode>/label` for a real item — the label page opens, the QR image appears, and "Print Label" opens the browser print dialog showing only the label with the item name, code, room, and bin. An unknown barcode returns 404 "Not recognized".

### Current Result

Every item now has a printable label page at `/items/<barcode>/label`, reachable from both the All Items list and the item detail page. The label shows the item name, internal code, QR image, room, and bin, prints cleanly via the browser with site navigation hidden, and the QR on it opens the item's stock URL. All existing login, item, detail, QR-image, scan, transaction, admin, and CSV-export behavior is unchanged. The per-item stock page that the QR ultimately targets (`/items/<barcode>/stock`) is still scheduled for a later step.

## Update: July 1, 2026 — QR Code Integration Step 7 (QR Stock Page)

This update covers Step 7 of `QR_CODE_SYSTEM_INTEGRATION_PLAN.md`: "Add QR Stock Page." Scanning an item's QR code now opens `/items/<barcode>/stock`, a page that already knows which item it is (no barcode typing). It shows the item name, internal code, current quantity, room, and bin, then offers the same add/remove transaction form as the scan page. This completes the QR workflow: the QR on the printed label from Step 6 now points to a working, item-specific stock page.

### 1. What Was Changed

Where: `app.py`

- Refactored the shared add/remove logic out of the `scan()` route into a new helper `process_stock_transaction(barcode, form)`. The helper validates the action, quantity, lab instructor, topic, and notes; finds the item by barcode; blocks removing more than is available; updates `items.quantity`; and inserts the `transactions` row for the logged-in user. It returns a `(message, error, status_code)` tuple.
- Rewrote `scan()` to call `process_stock_transaction(...)` (reading the barcode from the submitted form) instead of containing the logic inline. Its behavior and error/status codes are unchanged.
- Added a small helper `get_stock_item(db, barcode)` that selects the fields the stock page displays (`id`, `barcode`, `name`, `room`, `bin_location`, `quantity`).
- Added a new route `item_stock(barcode)` at `/items/<barcode>/stock` supporting GET and POST. GET renders the prefilled page; POST runs `process_stock_transaction(barcode, request.form)`, re-reads the item so the page shows the updated quantity, and renders the result. An unknown barcode returns `abort(404, description="Not recognized")`.

Where: `templates/item_stock.html` (new file)

- Displays the item summary (name, internal code, current quantity, room, bin) and the transaction form: Action (Add/Remove), Quantity, Lab Instructor, Topic of the Day, Notes, and a Submit button. Shows success and error messages like the scan page.
- The form posts to `url_for('item_stock', barcode=item['barcode'])` and contains no barcode field.

### 2. How It Was Done

- Per the plan, the transaction logic now lives in one shared helper used by both `/scan` and `/items/<barcode>/stock`, so the two pages cannot drift apart or develop inconsistent validation bugs. Extracting it also kept `scan()` behaving exactly as before.
- The stock page takes the barcode from the URL, not from a hidden form field. This matches the plan's "better" recommendation: the route already identifies the item, and there is no browser-submitted barcode to tamper with.
- After a POST, the route re-reads the item with `get_stock_item(...)` before rendering, so the "Current Quantity" shown always reflects the change that was just made (or the unchanged value if the action was rejected).
- The helper returns the HTTP status code (200/400/404) alongside the message/error so both routes preserve the original status semantics (for example, a rejected over-removal is still a 400 and a missing item is a 404).

### 3. Why It Was Done This Way

- A per-item stock page is the destination of the whole QR system: a user scans the label, lands directly on that item's stock form, and never has to type or scan a barcode into a field, which is faster and less error-prone in a busy lab.
- Sharing one transaction function guarantees the QR path enforces the exact same rules the scan path already does — required instructor/topic/notes, positive quantities, and the no-negative-stock guard — so audit records stay complete and consistent no matter how a transaction is started.
- Any logged-in user (including students) can use the stock page, matching the existing scan page's access model; recording who performed the action is handled by the transaction's `user_id`.

### 4. Verification Performed

- Ran `python -m py_compile app.py`; it compiled with no errors, and no linter errors were reported for the changed files.
- Confirmed the route registers as `('/items/<barcode>/stock', 'item_stock', ['GET', 'POST'])` and that `url_for('item_stock', barcode=...)` resolves; this is also the exact URL the Step 5 QR image encodes, so scanned labels now reach a real page.
- Ran an end-to-end test through the Flask test client against the local PostgreSQL database using a temporary item (`TEST-STOCK-STEP7`, starting quantity 5), logged in as the seeded student `S1001`:
  - GET `/items/<barcode>/stock` returned 200 and showed the item name and current quantity (prefilled).
  - Add 3 succeeded and reported the new quantity 8.
  - Remove 2 succeeded and reported the new quantity 6.
  - Remove 100 was rejected with HTTP 400 and the message "Cannot remove 100...", and created no transaction.
  - The `transactions` table recorded both successful actions with `user_id`, transaction type, quantity, `transaction_date`, `transaction_time`, `lab_instructor`, `topic_of_day`, and `notes` populated.
  - Deleted the temporary item and its transactions afterward, leaving the database as it was.

### Current Result

The QR workflow is now complete end to end: staff print a label (Step 6), a user scans its QR (Step 5 image), and lands on `/items/<barcode>/stock` (this step) where the item is already identified and they can add or remove stock. Both the scan page and the QR stock page share one transaction function, so they behave identically, and every action is recorded against the acting user with full date/time/instructor/topic/notes detail. All existing login, item, detail, QR-image, label, transaction, admin, and CSV-export behavior is unchanged.

## Update: July 1, 2026 — QR Code Integration Step 8 (Refactor Stock Logic Safely — Verification)

This update covers Step 8 of `QR_CODE_SYSTEM_INTEGRATION_PLAN.md`: "Refactor Stock Logic Safely." The goal of this step is to remove duplication by moving the shared add/remove logic into a single `process_stock_transaction()` function used by both `/scan` and `/items/<barcode>/stock`.

### 1. What Was Changed

- No new code changes were required for this step. The refactor it describes was performed as part of Step 7, because building the QR stock page and duplicating the entire scan logic would have been the exact "do not duplicate all logic long term" problem the plan warns about. Rather than copy ~90 lines into the new route and then delete them again here, the shared helper was introduced when the second caller was added.
- Current state confirmed for this step: `process_stock_transaction(barcode, form)` is the single source of truth for validation, item lookup, the no-negative-stock guard, the `items.quantity` update, and the `transactions` insert. Both `scan()` (barcode read from the submitted form) and `item_stock(barcode)` (barcode read from the URL) call it, and neither route contains its own copy of the transaction logic.

### 2. How It Was Done

- The helper returns a `(message, error, status_code)` tuple so each route only decides which template to render, while all business rules and database writes live in one place.
- Because the extraction already happened in Step 7, the work for Step 8 was focused on verification: confirming the duplication is gone and that the older `/scan` page still behaves exactly as it did before the QR feature existed.

### 3. Why It Was Done This Way

- A single shared function means the manual scan page and the QR stock page can never drift apart or develop inconsistent validation, which is the core reason the plan sequences this refactor as its own safety step.
- Doing the extraction at the moment the second caller appeared (Step 7) avoided a throwaway period of duplicated code and kept every commit in a working state, which is the "refactor safely" intent of this step.

### 4. Verification Performed

- Ran `python -m py_compile app.py`; it compiled with no errors, and no linter errors were reported.
- Confirmed in the source that `scan()` and `item_stock()` both delegate to `process_stock_transaction(...)` and that no transaction logic is duplicated between them.
- Ran an end-to-end regression test of the older `/scan` page through the Flask test client against the local PostgreSQL database, using a temporary item (`TEST-SCAN-STEP8`, starting quantity 10), logged in as the seeded faculty user `F1001`:
  - GET `/scan` returned 200.
  - Add 4 succeeded and reported new quantity 14.
  - Remove 5 succeeded and reported new quantity 9.
  - Remove 999 was rejected with HTTP 400 ("Cannot remove 999...").
  - An unknown barcode returned HTTP 404 ("No item was found for that barcode.").
  - A submission missing the lab instructor returned HTTP 400 ("Lab Instructor is required.").
  - Final quantity was 9 with exactly 2 recorded transactions (the rejected attempts recorded nothing).
  - Deleted the temporary item and its transactions afterward, leaving the database unchanged.

### Current Result

Stock logic exists in exactly one place, `process_stock_transaction()`, and both the manual scan page and the QR stock page use it, so they are guaranteed to behave identically. The older `/scan` page was regression-tested and works exactly as before, including all validation and the no-negative-stock guard. All existing login, item, detail, QR-image, label, transaction, admin, and CSV-export behavior is unchanged.

## Update: July 4, 2026 — Security Hardening: CSRF Protection On All POST Forms

This update adds Cross-Site Request Forgery (CSRF) protection to every state-changing request, as the first item from the production-readiness review. Before this change, any POST (stock changes, item add/edit, and user deactivate/activate/delete) could be forged by another website while a user was logged in. Now every such request must carry a valid, per-session CSRF token or it is rejected.

### 1. What Was Changed

Where: `requirements.txt`

- `Flask-WTF>=1.2,<2.0` is listed as a dependency (installed version 1.3.0).

Where: `app.py`

- Imported `CSRFProtect` and `CSRFError` from `flask_wtf.csrf`.
- Initialized `csrf = CSRFProtect(app)` immediately after the session/cookie configuration. This globally requires a valid CSRF token on all unsafe methods (POST/PUT/PATCH/DELETE); safe methods (GET/HEAD/OPTIONS) are unaffected.
- Added an `@app.errorhandler(CSRFError)` that re-renders the login page with a friendly message ("Your session expired or the form was invalid. Please try again.") and a 400 status, instead of Flask's raw 400 error page.
- Changed the `logout` route from `@app.route("/logout")` (implicitly GET) to `@app.route("/logout", methods=["POST"])`, so logging out is itself a protected action and cannot be triggered by a cross-site GET.

Where: templates (hidden token added to every POST form)

- Added `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` inside all ten POST forms: `login.html`, `scan.html`, `item_stock.html`, `item_new.html`, `item_edit.html`, `user_new.html`, and the three inline forms in `admin_users.html` (deactivate, activate, delete).
- `base.html`: the logout control was changed from a GET link (`<a href=...>`) to a small POST form with its own `csrf_token` field and a submit button.

Where: `static/css/styles.css`

- Added `.nav-logout-form` and `.nav-logout-form button` rules so the new logout button matches the look of the other navigation buttons (the global `form` styles would otherwise have distorted the nav layout).

### 2. How It Was Done

- Because the app uses hand-written HTML forms (not `FlaskForm`/WTForms classes), the `CSRFProtect` extension was the right fit: it enforces tokens app-wide without requiring every form to be rewritten as a form class. Each template only needed the one hidden `csrf_token` field that `Flask-WTF` exposes via the `csrf_token()` template helper.
- Tokens are signed with the app's existing `SECRET_KEY`, so no new configuration was introduced; this also reinforces why a strong production `SECRET_KEY` (already required by the startup check) matters.
- Logout was converted to POST so that it is covered by the same protection as every other state change, closing the one remaining GET-based state-changing endpoint.

### 3. Why It Was Done This Way

- CSRF tokens ensure a POST actually originated from a page the app served to this specific session, not from a malicious third-party page abusing the user's logged-in cookies. This directly addresses the "forged from another site" risk called out in the production-readiness analysis.
- Enabling the global protection and adding the token to all forms had to happen in the same change: turning on `CSRFProtect` without the hidden fields would immediately break every form, so they were done together.
- Rendering a clean message on `CSRFError` (rather than a raw 400) keeps the experience understandable when a token legitimately expires (for example, a form left open for a long time).

### 4. Verification Performed

- Ran `python -m py_compile app.py`; it compiled with no errors, and no linter errors were reported for the changed files.
- Confirmed `Flask-WTF` (1.3.0) installs and imports in the project virtual environment.
- Ran an end-to-end test through the Flask test client with CSRF fully enabled:
  - `GET /login` renders a form containing a `csrf_token`.
  - `POST /login` without a token is rejected with HTTP 400 (handled by the friendly CSRF error page); with the token it succeeds (HTTP 302 to the dashboard).
  - `POST /scan` without a token is rejected with HTTP 400.
  - The logout form on an authenticated page includes a token; `POST /logout` without a token is rejected (400) and with the token succeeds (302).
  - `GET /logout` now returns HTTP 405 (method not allowed), confirming logout is POST-only.

### Note For Future Testing

With CSRF enabled, automated tests that POST through the Flask test client must either include a valid `csrf_token` (read from the rendered form) or set `app.config["WTF_CSRF_ENABLED"] = False` in a dedicated testing configuration. Production code was intentionally left with CSRF always on; no bypass flag was added to the app itself.

### Current Result

Every state-changing request in the app — login, scan, QR stock actions, item create/edit, user create/deactivate/activate/delete, and logout — now requires a valid CSRF token, so these actions can no longer be forged from another site. Legitimate use is unchanged: the forms carry the token automatically, and expired tokens produce a clear "please try again" message. All other login, item, detail, QR-image, label, transaction, admin, and CSV-export behavior is unchanged.

---

## Update: July 7, 2026 — Invite Email Feedback, Password Visibility, and Dashboard Camera QR Scanner

This update improves user onboarding and the QR scanning workflow. The system is still running locally, so the work was done carefully to keep the existing PostgreSQL database, login flow, manual scan page, QR label pages, and stock transaction logic working without resetting or breaking the app.

### 1. New User Invite Email Behavior

What was changed:

- The new-user invite flow now clearly tells the administrator what happened after a user is created.
- In local development, if real email is not configured, the app displays the generated invite link on the Manage Users page.
- SMTP email support was added so the same invite flow can send real emails later when the correct email settings are provided.
- If email sending fails, the user account is still created and the page shows an error explaining that the invite email could not be sent.

Why it was needed:

- The invite link was being generated, but no real email provider was connected, so it looked like the invite was broken.
- Local development still needs a usable way to test invited users without setting up production email.
- Future production use needs a clear path for real invite and password-reset email delivery.

How it was done:

- Added SMTP environment variables in `.env.example`.
- Updated `send_email()` so it sends through SMTP when `EMAIL_PROVIDER=smtp` is configured.
- Kept local development safe by showing/logging the invite link instead of silently pretending email was sent.
- Added flashed success, warning, and error messages so the result appears on the web page.

### 2. Page-Level Feedback Messages

What was changed:

- Added shared flash-message rendering to the base layout.
- Added styles for success, warning, and error messages.

Why it was needed:

- Invite sending can have several outcomes: sent, not configured locally, or failed.
- The user needs to see this result directly on the page instead of checking only the Flask terminal.

How it was done:

- `base.html` now displays flashed messages above each page's main content.
- `styles.css` includes visual styling for:
  - Success messages.
  - Warning messages.
  - Error messages.

### 3. Show/Hide Password Option

What was changed:

- Added a Show/Hide password button to password fields on:
  - Login page.
  - Set password page from invite link.
  - Reset password page.
  - Re-authentication page used before sensitive actions.

Why it was needed:

- Passwords were shown only as dots.
- Users needed an option to check what they typed before submitting.

How it was done:

- Wrapped password inputs with a small password-control layout.
- Added a shared JavaScript toggle in `base.html`.
- Added CSS so the password input and Show/Hide button align cleanly.

### 4. Dashboard Camera QR Scanner

What was changed:

- Added camera-based QR scanning to the dashboard.
- Moved the camera scanner out of the Items / Scan Item page and placed it at the top of the dashboard.
- The dashboard now has:
  - Start Camera button.
  - Stop Camera button.
  - Camera preview that is hidden until the camera starts.
- When a QR code is scanned successfully, the camera stops and the system automatically opens the matching item stock action page.
- The manual Scan Item page remains available as a fallback for typed or hardware-scanned barcodes.

Why it was needed:

- The printed QR labels should work directly with the local device camera.
- The dashboard is the best first screen for quick daily inventory actions.
- Users should not need to manually type the barcode after scanning a QR code.

How it was done:

- Added the `html5-qrcode` browser scanner library to the dashboard page.
- The scanner reads QR codes generated by the system, including URLs like:

```text
/items/<barcode>/stock
```

- After scanning, the JavaScript extracts the item barcode from the QR URL.
- The browser redirects to the already-existing stock route:

```text
/items/<barcode>/stock
```

- The stock transaction form itself was not duplicated or rewritten; it still uses the shared `process_stock_transaction()` backend helper.

### 5. Current Dashboard QR Workflow

The current workflow is:

```text
User logs in
Dashboard opens
User clicks Start Camera
Browser asks for camera permission if needed
User shows the printed item QR code to the camera
System reads the QR code
Camera stops automatically
System opens the item's stock action page
User chooses Add Stock or Remove Stock
User enters quantity, lab instructor, topic, and notes
System updates inventory and records the transaction
```

If the camera does not work, the fallback workflow remains:

```text
Items > Scan Item
Enter or hardware-scan the barcode manually
Submit the stock action form
```

### 6. Verification Performed

The following checks were completed:

- Ran Python syntax checks with:

```bash
python -m py_compile app.py
```

- Rendered the dashboard through the Flask test client and confirmed:
  - The camera card is above the dashboard metric cards.
  - Start Camera button is present.
  - Stop Camera button is present.
  - The old barcode-entry field and Open Stock Action button are not present.
  - The camera preview is hidden before the camera starts.
- Rendered the Scan Item page and confirmed:
  - The camera scanner was removed from that page.
  - Manual barcode entry remains available.
- Ran JavaScript syntax checks for the dashboard scanner code.
- Confirmed the local Flask server was reachable at:

```text
http://127.0.0.1:5002
```

### Current Result

The system now has a smoother QR-based workflow for local use. The dashboard is the main place to start camera scanning, and a successful scan sends the user directly to the correct item's stock action page. Invite links are no longer confusing during local testing because the app clearly shows the invite link when email is not configured. Password forms are easier to use because users can reveal what they typed when needed. Existing inventory, transaction, QR label, user-management, and manual scan behavior remains available.

## Update: July 7, 2026 — Login Attempt Limits, Lockout, and Rate Limiting

This update documents the brute-force protections now guarding the login and other sensitive endpoints, and the small on-screen warning users see before they are locked out. These come from Security & Authentication Steps C and D (see `SECURITY_AND_AUTH_PLAN.md`), and this entry records the resulting limitations so the behavior is not surprising during use or testing.

### 1. What Was Changed

Where: `app.py`

- **Per-email failed-login lockout (Step C).** After a configurable number of consecutive failed logins for the same email address, further attempts for that email are refused with an HTTP 429 response until a cooldown period passes. A successful login clears the counter.
  - `LOGIN_MAX_ATTEMPTS` — number of allowed consecutive failures (default `5`).
  - `LOGIN_LOCKOUT_SECONDS` — how long the cooldown lasts once tripped (default `300` seconds / 5 minutes).
- **"Last attempt" warning.** Added `remaining_login_attempts(email)`. When a failed login leaves exactly one attempt before lockout, the login page shows a small notification line: "This is your last attempt before your account is temporarily locked."
- **IP-based rate limiting (Step D, Flask-Limiter).** Independently of the per-email lockout, each client IP is rate-limited on sensitive endpoints. Exceeding a limit returns a friendly HTTP 429 "Too Many Attempts" page.
  - `RATELIMIT_LOGIN` — `POST /login` (default `10 per minute`).
  - `RATELIMIT_PASSWORD` — `POST /forgot-password`, `/set-password/<token>`, `/reset-password/<token>` (default `5 per minute`).
  - `RATELIMIT_STOCK` — `/scan` and `/items/<barcode>/stock` (default `60 per minute`).
  - `RATELIMIT_ENABLED` (default on) and `RATELIMIT_STORAGE_URI` (default `memory://`).

Where: `templates/login.html`, `static/css/login.css`

- Added a small inline notification line (`.login-warning`) that appears only on the last remaining attempt, styled as a modest amber banner above the form (separate from the existing error modal).

Where: `templates/rate_limited.html`

- Added a friendly "Too Many Attempts" page shown when a rate limit is exceeded.

### 2. How It Was Done

- The per-email lockout uses a small in-memory tracker keyed by email. Each failed login increments a counter; when it reaches `LOGIN_MAX_ATTEMPTS`, a `locked_until` timestamp is set, and `is_locked_out()` refuses attempts until it passes.
- The login route computes `remaining_login_attempts(email)` after recording a failure and passes a `warning` to `login.html` only when exactly one attempt remains. The warning is shown for any email (registered or not), so it never reveals whether an email is registered.
- Flask-Limiter is initialized keyed by client IP with no global default limits; each sensitive route opts in with a `@limiter.limit(...)` decorator. A single `@app.errorhandler(429)` renders the friendly page for both the lockout and the rate limiter.

### 3. Why It Was Done This Way

- **Two complementary limits.** The per-email lockout stops repeated guessing against one account; the per-IP rate limit stops one client hammering many accounts or scraping stock pages. Together they cover both attack shapes.
- **A visible warning before lockout** reduces support friction: a legitimate user who mistypes their password is told they have one try left, instead of being surprised by a sudden lockout.
- **Generic, non-revealing messages.** The failure text stays "Invalid email or password" and the warning is shown regardless of whether the email exists, so the system never discloses which emails are registered.
- **Everything is environment-configurable**, so limits can be tightened or relaxed per deployment, and rate limiting can be disabled (used by the automated tests) or pointed at Redis for multi-worker production.

### 4. Known Limitations

- **The per-email lockout counter is in-memory and per-process.** It resets if the app restarts and is not shared across multiple Gunicorn workers or hosts. For a multi-worker or multi-host production deployment, the shared-store (Redis) rate limiter is the durable defense; set `RATELIMIT_STORAGE_URI` to a Redis URL so limits are shared.
- **The default `memory://` rate-limit store is also per-process** for the same reason.
- **A locked-out user must wait for the cooldown** (`LOGIN_LOCKOUT_SECONDS`); there is no admin "unlock now" button yet. Restarting the app clears in-memory lockouts.
- The lockout is keyed by the submitted email, so a determined attacker rotating through many different emails is bounded by the per-IP rate limit rather than the per-email lockout.

### 5. Verification Performed

- Ran `python -m py_compile app.py`; compiled with no errors.
- Ran the automated authentication test suite (`python -m pytest tests/`): **37 passed**, including tests for lockout after repeated failures (429), the "last attempt" warning appearing only on the final try, reset of the counter on successful login, rate-limit throttling, and the friendly 429 page.
- Manual check with `LOGIN_MAX_ATTEMPTS = 5`: attempts 1–3 returned 401 with no warning; attempt 4 returned 401 with the "last attempt" warning; attempt 5 returned 401; attempt 6 returned 429 (locked out).
- Manual check with `RATELIMIT_LOGIN="2 per minute"`: statuses were `401, 401, 429, 429`, confirming the limits are environment-configurable.

### Current Result

Login and other sensitive endpoints are now protected against brute-force and scraping through a per-email lockout and per-IP rate limiting, both configurable via environment variables. Users are warned on their final attempt before lockout, and both protections return a clear "too many attempts" message. The main limitation to keep in mind is that the in-memory counters are per-process; production deployments with multiple workers should use the Redis-backed rate limiter so the limits are shared.

---

## Update: July 8, 2026 — Data, Migrations & Reliability (Phase 2, Steps F–H)

This update records the second deployment phase, described in `DATA_MIGRATIONS_RELIABILITY_PLAN.md`. It makes the data layer production-grade: schema changes stop running on every request, the transaction history stays fast as it grows, and dates are stored as real dates. Three of the four planned improvements are complete (Steps F, G, H); the fourth — automated backups + point-in-time recovery (Step I) — is a deploy-time task and is intentionally left for the hosting step. The whole phase is covered by an automated test suite that now stands at **54 passing tests**.

### 1. Step F — Real migrations with Alembic (replacing per-request `ALTER TABLE`)

What was changed:

- Adopted **Alembic** (raw-SQL migration mode, no SQLAlchemy models) as the single source of truth for schema changes.
- Removed the old `ensure_transaction_columns()`, `ensure_auth_columns()`, and `ensure_barcode_sequence()` "runtime migration" helpers and every call to them from the request/view paths.
- Wired migrations into deploy: `alembic upgrade head` runs once per release (already in the `Procfile` release phase), with a `flask db-upgrade` / `flask db-downgrade` CLI wrapper for operators.

Why it was needed:

- The `ensure_*` helpers ran `ALTER TABLE` / `CREATE INDEX` / `UPDATE` on ordinary page loads (dashboard, scan, transactions, login, admin). That is fragile (a failed DDL could break a normal page), slow (extra DDL on the hot path), and racy under real concurrent traffic.
- Production schema management needs to be explicit, versioned, and run once per deploy — not on every request.

How it was done (substeps F1–F5):

- **F1** — Added `alembic` to `requirements.txt`, scaffolded `alembic.ini` + `migrations/`, and configured `migrations/env.py` to read `DATABASE_URL` from the environment (no secrets in `alembic.ini`).
- **F2** — Authored `0001_baseline` capturing the exact current schema (users/items/transactions, the `item_barcode_number_seq` sequence, all columns the `ensure_*` helpers used to guarantee); existing databases adopt it with `alembic stamp 0001_baseline`.
- **F3** — Confirmed the baseline covered everything, then deleted the `ensure_*` functions and all their call sites from `app.py` and the test setup.
- **F4** — Documented `alembic upgrade head` as the production schema command, added the `flask db-upgrade`/`db-downgrade` wrappers, and clarified that `flask init-db` is local-dev bootstrap only.
- **F5** — Added `tests/test_migrations.py`: a from-zero `upgrade head` schema check, an upgrade→downgrade→upgrade round-trip, and a single-head check.

### 2. Step G — `expiration_date` stored as a real `DATE`

What was changed:

- Converted `items.expiration_date` from free-text `TEXT DEFAULT '00/00/0000'` to a real, nullable `DATE`.
- The add/edit forms now use `<input type="date">`; an unset date is stored as SQL `NULL` (shown as "Not set"), and the `00/00/0000` sentinel is gone from the UI and database.

Why it was needed:

- Free-text dates cannot be reliably sorted, filtered, or used for "expiring soon" logic, and the `00/00/0000` sentinel leaked into templates.

How it was done (substeps G1–G3):

- **G1** — Migration `0003_expiration_date_to_date`: adds a `DATE` column, backfills it in Python by parsing the old text (empty / `00/00/0000` / unparseable → `NULL`; valid dates → the parsed date), then swaps columns. The reverse migration restores the text format. A Python backfill was used deliberately because PostgreSQL's `to_date()` silently produces a bogus date for junk like `00/00/0000` instead of failing.
- **G2** — Updated `app.py` (`parse_expiration_date`, `get_item_form_data`), the item forms/detail/label templates, and `schema.sql` so the whole app speaks `DATE`/`NULL`.
- **G3** — Added `tests/test_item_form.py` covering create-with-date, create-without-date (NULL / "Not set"), unparseable → NULL, edit persistence, and a sentinel-never-appears check.

### 3. Step H — Indexes + server-side pagination on transactions

What was changed:

- Added indexes supporting the transaction history query and filters, and added server-side pagination to the `/transactions` page.

Why it was needed:

- `/transactions` loaded the entire (filtered) table into one page and sorted it with no supporting index, so performance degraded as history grew.

How it was done (substeps H1–H3):

- **H1** — Migration `0004_transaction_indexes` adds `transactions(item_id)`, `transactions(user_id)`, `transactions(transaction_date)`, a composite `(transaction_date DESC, transaction_time DESC, id DESC)` matching the list `ORDER BY`, and `items(name)`. The `CREATE INDEX CONCURRENTLY` caveat (cannot run inside a transaction block) is documented for large-table production use.
- **H2** — Added `LIMIT`/`OFFSET` pagination (page size configurable via `TRANSACTIONS_PAGE_SIZE`, default 50) with page controls that preserve the active filters; the CSV export stays **unpaginated** (full filtered set).
- **H3** — Added `tests/test_transactions_pagination.py`: seeds 5,000 transactions and verifies the page-count math at the edges (first/last/out-of-range/empty), that filters combine with paging, that the paginated query uses the composite index (via `EXPLAIN`, no seq-scan + sort), and that a page load stays fast. Also synced the `schema.sql` dev bootstrap with the `0004` indexes so it matches the migrated head.

### 4. What Is Still Left Before Deployment

- **Step I — Automated DB backups + point-in-time recovery** is intentionally deferred to the hosting step (`DEPLOYMENT_INFRASTRUCTURE_PLAN.md`, Step J1). It is provisioned on managed PostgreSQL rather than in application code, and requires a tested restore drill before launch.
- Migrations must be run at deploy time (`alembic upgrade head` in the release phase); `flask init-db` must not be used against a database under Alembic control.
- With more than one Gunicorn worker, Flask-Limiter should be backed by a shared store (Redis), as noted in the earlier security update.

### 5. Verification Performed

- Ran `python -m py_compile app.py`; compiled with no errors, and no linter errors were reported on the changed files.
- Ran the full automated suite (`python -m pytest`): **54 passed** (auth, migrations, item form, and transaction pagination).
- Migration integrity: from an empty database, `alembic upgrade head` builds the full schema (0001 → 0004); `upgrade → downgrade → upgrade` round-trips cleanly; the migration graph has a single head.
- Data conversion (Step G) checked on a scratch database with mixed inputs: `00/00/0000`, empty, and unparseable values became `NULL`; real dates (including a leap day) converted correctly; no rows were lost; the column type afterwards is `date`.
- Index usage (Step H) confirmed with `EXPLAIN (ANALYZE)` on 100,000 seeded rows: the paginated ordered query uses the composite index with no explicit sort, and the item/user/date filters use their matching indexes.

### Current Result

The data layer is now production-grade: schema is managed entirely by Alembic migrations run once per deploy (never per request), `expiration_date` is a real `DATE`, and the transaction history is indexed and paginated so it stays fast as it grows — all covered by a 54-test automated suite. The only remaining Phase 2 item, automated backups + point-in-time recovery, is a deploy-time task handled during hosting setup. All existing login, item, QR, scan, transaction, admin, and export behavior is unchanged.
