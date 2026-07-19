# Inventory Management System Documentation

## Purpose of This File

This file is the main learning and documentation record for the inventory management system project.

The goal is to document each important project decision in a beginner-friendly way:

- What was added.
- Why it was added.
- How it works.
- How it connects to the rest of the project.
- What we should remember before changing it later.

This file should be updated as the project grows so that someone new to the project can understand the system step by step.

## Project Idea

The project is a barcode-based inventory management system for nursing education, simulation labs, medication rooms, and healthcare training environments.

Instead of tracking supplies manually in Excel, the system will allow users to:

- Log in using a student, faculty, or staff ID.
- Add new inventory items.
- Assign or scan barcodes for item types.
- Record how many items are added or removed.
- Automatically update the inventory database.
- View reports and transaction history.

The long-term goal is to create low-cost software that can run on simple hardware, such as a basic laptop, tablet, or small computer with a barcode scanner.

## Current Project Folder

The working folder for this project is:

```text
inventory/
```

This folder contains all planning files, future source code files, templates, styles, scripts, and database files for the inventory project.

## Current Documentation Set

The earlier proposal, high-level design, architecture, and system diagram files
were consolidated into:

```text
design_docx/SOFTWARE_REQUIREMENTS_SPECIFICATION.md
```

Those older source documents were removed to reduce redundancy. Use the SRS as
the current single document for requirements, architecture, workflows, diagrams,
and product scope.

### `PLAN.md`

This file contains the project skeleton plan.

It explains:

- Which files need to be created.
- Which app pages/routes are planned.
- Which database tables are needed.
- What should be tested in the first version.

Why this file exists:

The plan acts like a map before coding. It helps us avoid randomly creating files without understanding their purpose.

How it should be used:

This file should guide the early build process. When a task is completed, we can compare the project against this plan.

### `requirements.txt`

This file lists the Python packages needed to run the project.

Current content:

```text
Flask>=3.0,<4.0
```

What this means:

The project needs Flask version 3 or newer, but not Flask version 4.

Why Flask is used:

Flask is a Python web framework. A web framework helps us build web pages, handle forms, manage routes, and connect the user interface to backend logic.

Why Flask is a good choice for this project:

- It is beginner-friendly.
- It is lightweight.
- It is good for small prototypes.
- It works well with PostgreSQL.
- It can run locally on a basic computer.
- It does not require a complicated setup.

How `requirements.txt` is used:

When setting up the project, a developer can install the required packages by running:

```bash
pip install -r requirements.txt
```

This command tells Python to read `requirements.txt` and install the listed packages.

## Important Technologies

### Python

Python will be used for the backend of the application.

Why Python:

- It is easy to read.
- It is beginner-friendly.
- It has strong support for web apps and databases.
- It is commonly used for prototypes and academic projects.

How Python fits into the project:

Python will handle the logic behind the system, such as:

- Checking login IDs.
- Saving new items.
- Updating quantities.
- Recording transactions.
- Exporting reports.

### Flask

Flask will be used to create the web application.

Why Flask:

Flask lets us create pages such as:

- Login page.
- Dashboard page.
- Inventory list page.
- Add item page.
- Scan barcode page.
- Transaction history page.

How Flask works in simple words:

Flask listens for a user visiting a URL, such as `/login` or `/items`, then runs Python code and returns a web page.

Example:

```text
User opens /login
Flask receives the request
Flask runs the login page code
Flask shows the login page in the browser
```

### PostgreSQL

PostgreSQL will be used as the database.

Why PostgreSQL:

- It is free and open source.
- It is reliable and stores data safely.
- It handles multiple users at the same time.
- It is suitable for both prototypes and production deployment.
- It works well for a demo system and scales beyond it.

How PostgreSQL fits into the project:

PostgreSQL will store:

- Users.
- Inventory items.
- Barcode values.
- Quantity counts.
- Transaction history.

### Barcode Scanner

The first version will treat a barcode scanner like a keyboard.

Why this is simple:

Many USB barcode scanners work by typing the scanned barcode into the selected input box. This means we do not need complicated scanner software at the beginning.

How it will work:

```text
User clicks barcode input field
User scans item barcode
Scanner types barcode number automatically
Application searches for matching item
User enters quantity added or removed
Database updates inventory count
```

## Planned Project Structure

The planned structure is:

```text
inventory/
  app.py
  requirements.txt
  schema.sql
  README.md
  PROJECT_DOCUMENTATION.md
  templates/
    base.html
    login.html
    dashboard.html
    items.html
    item_new.html
    scan.html
    transactions.html
  static/
    css/
      styles.css
    js/
      scan.js
```

What each planned file or folder will do:

### `app.py`

This will be the main Python file for the Flask app.

It will define:

- App setup.
- Page routes.
- Login behavior.
- Inventory actions.
- Database connection logic.

### `schema.sql`

This will define the database tables.

It will describe how data should be stored for:

- Users.
- Items.
- Transactions.

### `README.md`

This will explain how to set up and run the project.

It should include commands for:

- Installing dependencies.
- Initializing the database.
- Starting the app.
- Logging in with demo users.

### Database connection

The app connects to a PostgreSQL database using a connection string provided by the `DATABASE_URL` environment variable, for example:

```text
postgresql://localhost/inventory_management_system
```

The database tables are created by running the `init-db` command, which executes `schema.sql` against PostgreSQL.

### `templates/`

This folder will store HTML pages.

HTML pages are the screens users see in the browser.

### `static/`

This folder will store frontend assets.

Examples:

- CSS files for styling.
- JavaScript files for small interactive behavior.

## Planned Database Tables

### Users Table

Purpose:

Stores people who can log in and use the system.

Example fields:

- User ID.
- Institutional ID.
- Name.
- Role.
- Department.
- Active status.

Why this table is needed:

Every inventory action should be connected to a user. This creates accountability.

### Items Table

Purpose:

Stores inventory items.

Example fields:

- Item ID.
- Barcode.
- Item name.
- Category.
- Unit.
- Quantity.
- Minimum quantity.
- Location.
- Expiration date.
- Notes.

Why this table is needed:

The system needs one central place to know what items exist and how many are available.

### Transactions Table

Purpose:

Stores every inventory movement.

Example transaction types:

- Added.
- Removed.
- Returned.
- Adjusted.

Why this table is needed:

The current quantity only shows the present state. The transaction table shows the history of what happened.

Example:

```text
User 12345 removed 2 boxes of gloves on June 20 at 10:30 AM.
```

This is important for tracking, reporting, and accountability.

## Planned Pages

### Login Page

Purpose:

Allows a student, faculty member, or staff member to enter an ID and access the system.

Why it is needed:

The system needs to know who is using inventory items.

### Dashboard Page

Purpose:

Shows a quick overview of inventory.

Possible information:

- Total items.
- Low-stock items.
- Recent transactions.

Why it is needed:

Users should quickly understand the current inventory status.

### Items Page

Purpose:

Shows the list of inventory items.

Why it is needed:

Users need a place to search and review existing supplies.

### Add Item Page

Purpose:

Allows authorized users to add a new item type.

Why it is needed:

New supplies must be entered before they can be scanned and tracked.

### Scan Page

Purpose:

Allows users to scan or type a barcode.

Why it is needed:

Barcode scanning is the main automation feature of the project.

### Transactions Page

Purpose:

Shows the history of added and removed items.

Why it is needed:

Faculty and staff need to review who used items, when, and how many.

## Development Rule for This Project

Because this project is being built step by step for learning, the development rule is:

```text
Edit one file at a time.
Complete one small task at a time.
Explain what changed and why.
```

This keeps the project understandable and prevents too many changes from happening at once.

## Change Log

### Step 1: Added `requirements.txt`

What changed:

Created:

```text
requirements.txt
```

Added:

```text
Flask>=3.0,<4.0
```

Why:

The project needs Flask to build a local web application.

How it helps:

This allows the project to later create pages, routes, forms, and backend logic.

### Step 2: Added `PROJECT_DOCUMENTATION.md`

What changed:

Created this documentation file.

Why:

The project needs one central place to explain each file, tool, technology, decision, and development step.

How it helps:

This file will make the project easier to understand, maintain, present, and continue building.

### Step 3: Installed Flask in the `invent` Virtual Environment

What changed:

Installed Flask inside the project virtual environment named:

```text
invent
```

The virtual environment is located at:

```text
inventory/invent/
```

Command used:

```bash
inventory/invent/bin/python -m pip install -r inventory/requirements.txt
```

Why this command was used:

This command uses the Python interpreter inside the `invent` virtual environment. That means Flask is installed for this project environment only, instead of being installed globally on the computer.

Why a virtual environment is important:

A virtual environment keeps project packages separate from other Python projects. This helps avoid version conflicts and makes the project easier to reproduce later.

How it connects to `requirements.txt`:

The command reads this file:

```text
requirements.txt
```

The file currently contains:

```text
Flask>=3.0,<4.0
```

That line tells Python to install Flask version 3 or newer, but not Flask version 4.

How the installation was verified:

After installation, Flask was checked with:

```bash
inventory/invent/bin/python -m flask --version
```

Result:

```text
Python 3.14.5
Flask 3.1.3
Werkzeug 3.1.8
```

What this means:

Flask is installed correctly in the `invent` virtual environment and is ready to be used for the web app.

## Next Recommended Step

The next small implementation task should be creating:

```text
README.md
```

Why:

`README.md` will explain how to install and run the project. This is useful before writing the actual application code because it gives the project a clear setup path.
