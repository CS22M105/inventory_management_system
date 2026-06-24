# Progress Report: Nursing Inventory Management System

## Project Summary

This project is a barcode-based inventory management system for nursing education, simulation labs, medication rooms, and healthcare training environments.

The goal is to replace manual Excel-based tracking with a web application that supports registered user login, item management, barcode-based stock updates, and transaction history.

## Current Status

The project has moved from planning into a working Flask prototype.

The system now has:

- A Flask application structure.
- A SQLite database.
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
  invent/
  ```
- Created project folders:
  ```text
  templates/
  static/css/
  static/js/
  data/
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
- Created SQLite database:
  ```text
  data/inventory.db
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
