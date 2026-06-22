# High-Level Design: Nursing Inventory Management System

## 1. Purpose

This document explains the inventory system from a systems design perspective.

The goal is to understand the system as a set of connected parts, not only as individual files or pages. This helps us decide how users, the web application, the database, and the barcode scanner will work together.

## 2. Problem Being Solved

Nursing labs, medication rooms, simulation labs, and healthcare training spaces often track supplies manually using paper notes or Excel sheets.

This creates problems such as:

- Inventory counts may not be updated immediately.
- Staff may not know who removed or added an item.
- Low-stock items may be discovered too late.
- Manual entry can cause mistakes.
- Reports take extra time to prepare.

The system should make inventory tracking faster, more accurate, and easier to audit.

## 3. System Goals

The system should:

- Allow users to log in with an institutional ID.
- Track inventory items by barcode.
- Allow users to add or remove item quantities.
- Save every inventory action as a transaction.
- Show current inventory status.
- Support low-cost hardware and local deployment.
- Be simple enough for students, faculty, and staff to use.

## 4. Users and Roles

### Student

Students can use inventory items during practice, skills labs, or simulation activities.

Expected permissions:

- Log in.
- Scan an item.
- Remove approved items.
- Return unused items, if allowed.

### Faculty or Staff

Faculty and staff supervise inventory usage and help manage supplies.

Expected permissions:

- Log in.
- Add new stock.
- Remove stock.
- Add new inventory items.
- Review transaction history.
- View low-stock items.

### Administrator

Administrators manage the system setup and higher-level controls.

Expected permissions:

- Manage users.
- Manage item records.
- Review all activity.
- Export reports.
- Adjust inventory counts when needed.

## 5. High-Level Architecture

The first version will use a simple local web application architecture.

```text
User
  |
  v
Web Browser
  |
  v
Flask Web Application
  |
  v
SQLite Database
```

### Browser

The browser displays the pages users interact with, such as:

- Login page.
- Dashboard page.
- Inventory page.
- Barcode scan page.
- Transaction history page.

### Flask Application

The Flask application is the main controller of the system.

It will:

- Receive user requests.
- Show pages.
- Process form submissions.
- Validate basic input.
- Read data from the database.
- Save changes to the database.

### SQLite Database

SQLite stores the system data in a local database file.

It will store:

- Users.
- Items.
- Transactions.

SQLite is a good starting choice because it is free, local, simple, and does not require a separate database server.

## 6. Barcode Scanner Design

For the MVP, the barcode scanner will be treated like a keyboard.

Most USB barcode scanners work this way:

```text
Scanner reads barcode
Scanner types barcode value into the selected input box
User submits the form
Application searches for the matching item
```

This keeps the system simple because we do not need special barcode-scanner software at the beginning.

## 7. Main Data Entities

### Users

Represents people who can access the system.

Important fields:

- Institutional ID.
- Name.
- Role.
- Department.
- Active status.

Why this matters:

Every inventory action should be connected to a user for accountability.

### Items

Represents inventory supplies or equipment.

Important fields:

- Barcode.
- Item name.
- Category.
- Unit.
- Current quantity.
- Minimum quantity.
- Location.
- Expiration date.
- Notes.

Why this matters:

The item record tells the system what exists in inventory and how much is available.

### Transactions

Represents inventory activity.

Important fields:

- User.
- Item.
- Transaction type.
- Quantity.
- Date and time.
- Notes.

Why this matters:

The transaction history explains how inventory changed over time. This is important for auditing and reports.

## 8. Core System Flows

### Flow 1: User Login

```text
User enters institutional ID
Application checks the users table
If user exists and is active, login succeeds
User is sent to dashboard
```

Purpose:

The system must know who is performing each inventory action.

### Flow 2: Add New Item

```text
Faculty, staff, or administrator opens Add Item page
User enters item details and barcode
Application validates required fields
Application saves item to database
Item becomes available for scanning
```

Purpose:

An item must exist in the database before barcode-based tracking can work.

### Flow 3: Add Stock

```text
User scans or enters barcode
Application finds matching item
User enters quantity being added
Application increases item quantity
Application creates transaction record
```

Purpose:

The database should update automatically when new supplies are stocked.

### Flow 4: Remove Stock

```text
User scans or enters barcode
Application finds matching item
User enters quantity being removed
Application checks available quantity
Application decreases item quantity
Application creates transaction record
```

Purpose:

The system should track supply usage and prevent accidental negative inventory counts.

### Flow 5: View Reports

```text
User opens report or transaction page
Application reads database records
Application displays inventory history or current stock
User can export data later
```

Purpose:

Reports help faculty and staff understand usage patterns, low-stock items, and restocking needs.

## 9. MVP Boundaries

The first version should focus on the core inventory workflow.

Included in MVP:

- Local login by institutional ID.
- Add new item.
- Scan or type barcode.
- Add stock.
- Remove stock.
- View current inventory.
- View transaction history.

Not included in MVP:

- Institutional single sign-on.
- Cloud hosting.
- Email alerts.
- Purchase order automation.
- Advanced compliance controls.
- Multi-campus deployment.

These features can be added later after the basic system works.

## 10. Important Design Decisions

### Decision 1: Use a Web App

Why:

A web app can run in a browser, which makes it easier to use on laptops, desktops, tablets, or small local devices.

### Decision 2: Use Flask

Why:

Flask is lightweight, beginner-friendly, and good for building a small prototype quickly.

### Decision 3: Use SQLite First

Why:

SQLite does not need a separate database server. This keeps setup simple and low-cost.

### Decision 4: Treat Barcode Scanner as Keyboard Input

Why:

This avoids complicated scanner integration during the MVP. The scanner can simply fill a barcode input field.

### Decision 5: Save Transactions Separately from Items

Why:

The item table shows the current quantity. The transaction table shows how that quantity changed over time.

Both are needed.

## 11. Future Scalability

If the system grows, it can later move from:

```text
Local Flask app + SQLite
```

to:

```text
Hosted web app + PostgreSQL or MySQL
```

Possible future improvements:

- Multi-user access across departments.
- Cloud database.
- Role-based dashboard.
- Expiration-date alerts.
- Low-stock email notifications.
- Supplier and purchasing integration.
- More detailed audit logs.

## 12. First Version Success Criteria

The high-level design is successful if the first version can show this complete loop:

```text
User logs in
User adds an item with a barcode
User scans or enters barcode
User adds or removes quantity
Database updates current inventory
Transaction history records the action
```

This loop proves that the core system idea works.
