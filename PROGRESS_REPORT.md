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
