# Phase 1 and Phase 2 Build Plan

## Summary

Create a new Markdown file at `inventory/phase_1_2_build_plan.md`. Do not edit `planning_and_proposal.md`.

The new file will break the project into small, trackable tasks for:
- **Phase 1: Requirements and Design** from June 11-16, 2026.
- **Phase 2: Prototype Setup** from June 17-23, 2026.

The selected prototype direction is a **Python web app with PostgreSQL**, using a simple architecture suitable for low-cost hardware and a July 20 demo.

## Key Changes

- Add `inventory/phase_1_2_build_plan.md` with sections for:
  - Project goal for Phases 1 and 2.
  - Daily/small-task checklist.
  - MVP assumptions.
  - Proposed app structure.
  - Initial database schema.
  - Initial screens/routes.
  - Phase acceptance criteria.

- Phase 1 content will define:
  - User roles: Student, Faculty/Staff, Administrator.
  - Core workflows: login, add item, scan item, add stock, remove stock, view inventory.
  - Required data fields for users, items, and transactions.
  - Hardware assumptions: existing laptop/tablet, USB barcode scanner, printable barcode labels.
  - MVP boundaries: educational inventory prototype, not full medication compliance software.

- Phase 2 content will plan the prototype foundation:
  - Python web app scaffold.
  - PostgreSQL database.
  - Basic local login by user ID.
  - Inventory item table.
  - Add-item form.
  - Quantity add/remove workflow.
  - Transaction log table.
  - Basic CSV export placeholder.

## Interfaces and Data Model

Use these initial database tables:

- `users`
  - `id`
  - `institution_id`
  - `name`
  - `role`
  - `department`
  - `is_active`

- `items`
  - `id`
  - `barcode`
  - `name`
  - `category`
  - `unit`
  - `quantity`
  - `minimum_quantity`
  - `location`
  - `expiration_date`
  - `notes`

- `transactions`
  - `id`
  - `user_id`
  - `item_id`
  - `transaction_type`
  - `quantity`
  - `created_at`
  - `notes`

Initial app routes/screens:

- `/login` for entering student/faculty/staff ID.
- `/dashboard` for inventory overview.
- `/items` for current inventory.
- `/items/new` for adding a new item.
- `/scan` for barcode entry/scanning.
- `/transactions` for activity history.
- `/reports/export` for CSV export later.

## Test Plan

Phase 1 checks:
- Confirm all MVP workflows are documented.
- Confirm all required database fields are listed.
- Confirm phase tasks fit the July 20 deadline.

Phase 2 checks:
- App starts locally.
- PostgreSQL database initializes successfully.
- A sample user can log in with an ID.
- A new item can be created with a barcode.
- Inventory list displays saved items.
- Adding stock increases quantity.
- Removing stock decreases quantity.
- Each quantity change creates a transaction record.

## Assumptions

- The first prototype will be a Python web app using PostgreSQL.
- Barcode scanner input will be treated like keyboard text input for the MVP.
- CSV/Excel export will be included as a simple report feature before advanced analytics.
- Authentication will start with ID-based local login, not institutional single sign-on.
- The new file name will be `phase_1_2_build_plan.md`.
- The existing proposal file will remain unchanged.
