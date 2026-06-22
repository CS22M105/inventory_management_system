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

The project is in the early skeleton stage.

Completed so far:

- Created the project plan.
- Created `requirements.txt`.
- Installed Flask in the `invent` virtual environment.
- Created the main project folders.
- Created this `README.md` setup file.

## Technology

This project will use:

- **Python** for backend logic.
- **Flask** for the web application.
- **SQLite** for the first local database.
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

Currently, the main dependency is Flask.

## Check Flask Installation

To confirm Flask is installed, run:

```bash
python -m flask --version
```

Expected result should show Flask version information.

## Planned Project Structure

```text
inventory/
  app.py
  requirements.txt
  README.md
  schema.sql
  PROJECT_DOCUMENTATION.md
  data/
  templates/
  static/
    css/
    js/
```

## Next Development Step

The next small task is to create the main Flask application file:

```text
app.py
```

That file will eventually start the web app and define the first pages.
