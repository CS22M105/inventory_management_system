# Proposal: QR-Code-Based Inventory Management System for Nursing Education and Healthcare Settings

## 1. Project Overview

Manual inventory management is still common in nursing academic programs, simulation labs, medication rooms, hospitals, and healthcare-related organizations. Many teams rely on paper notes, handwritten sign-out sheets, or Excel spreadsheets to track supplies. This process is time-consuming, prone to human error, difficult to audit, and often does not provide real-time visibility into current stock levels.

This project delivers a low-cost, QR-code-based inventory management system designed specifically for nursing education and healthcare training environments. The system allows authorized users, such as students, faculty, lab coordinators, and staff, to sign in with an email and password, scan an item's QR code with any smartphone camera, and automatically update inventory records when items are added, removed, or restocked.

The product is a hosted web application that is reachable from anywhere over the internet (its own domain, served over HTTPS), rather than a tool tied to a single institution's network. The goal is a practical, affordable, and secure software solution that replaces manual Excel-based tracking with an accurate, automated, and accountable workflow.

## 2. Problem Statement

Current inventory workflows in many nursing and healthcare education environments involve:

- Manual entry of supply usage into Excel sheets.
- Delayed updates when items are removed or added.
- Difficulty identifying who used specific items and when.
- Frequent counting errors and missing stock information.
- Limited visibility into low-stock or frequently used items.
- Extra workload for faculty, staff, and lab coordinators.

These challenges can lead to supply shortages, wasted time, inaccurate records, and difficulty preparing for classes, simulations, clinical skills practice, and medication-room activities.

## 3. Proposed Solution

The system works similarly to a grocery-store checkout process, but adapted for nursing supplies and medication-room inventory. Each item type receives a unique internal code and a matching QR code. The QR code encodes a direct link to that item's stock page. When a user points a phone camera at the label, the phone opens the item's stock page in the browser, where the user enters the quantity and submits an add or remove transaction. The system updates the inventory database and records a detailed activity log entry.

Because scanning is done with the camera in any smartphone or tablet, no dedicated USB barcode scanner is required. The end product is a lightweight web application that can run on affordable hardware and be accessed from:

- A basic laptop or desktop computer (web browser).
- A tablet or phone (web browser + built-in camera for QR scanning).
- A PostgreSQL database with Excel/CSV export.

## 4. Project Objectives

The main objectives are to:

- Replace manual spreadsheet-based inventory tracking with automated QR-code scanning.
- Provide secure, individual accounts (email and password) with role-based permissions.
- Track item additions, removals, and restocking activities in real time.
- Capture lab-specific context on every transaction (lab instructor and topic of the day).
- Maintain an accurate database of available inventory.
- Generate exportable reports for auditing, planning, and supply ordering.
- Support low-cost implementation using devices already on hand (any camera phone).
- Deliver a secure, hosted product suitable for launch as a commercial web application.

## 5. Target Users

The system is intended for:

- Nursing students using supplies for practice or simulation.
- Faculty members supervising lab or medication-room activities.
- Simulation lab staff managing equipment and consumables.
- Inventory or administrative staff responsible for restocking.
- Healthcare training organizations that need simple, secure supply tracking.

## 6. Core Features

### 6.1 Authentication and User Accounts

Users sign in with an **email address and password**. Passwords are never stored in plain text; they are salted and hashed. The system records the individual user associated with each inventory transaction.

Account and session security includes:

- **Invite-only account creation.** An administrator (or faculty, for students) creates an account by entering the person's name, email, and role. The system emails a secure, time-limited link, and the invited user chooses their own password. Administrators never set or see user passwords.
- **Self-service password reset.** A "Forgot password?" link emails a signed, one-hour reset link. To avoid revealing which emails are registered, the same confirmation is shown whether or not the email exists.
- **Session idle-timeout with a sliding window.** Sessions expire after a configurable period of inactivity (default 30 minutes) but are refreshed while the user is active, so no one is logged out mid-task. This protects shared lab computers.
- **Re-authentication for destructive admin actions ("sudo mode").** Deactivating or deleting a user requires re-entering the password if the session has been idle.
- **Brute-force cooldown.** Repeated failed logins for an email are temporarily locked out.
- **CSRF protection** on every state-changing form.

Recommended user roles:

- **Student:** Can view items and record stock add/remove transactions.
- **Faculty:** Everything a student can do, plus add/edit item records, generate QR codes and printable labels, and invite/manage student accounts.
- **Administrator:** Everything faculty can do, plus manage all users (including faculty), review reports, and access system status.

### 6.2 Item Registration

Authorized users (faculty and administrators) can add new item types. Each item record includes:

- Item name.
- Internal item code (auto-generated with a configurable prefix, e.g. `KATZ-NURS-000001`, or entered manually).
- Bin location and room.
- Company/supplier (optional).
- Storage location (optional).
- Current quantity.
- Minimum stock threshold.
- Expiration date (optional).
- Notes (optional).

### 6.3 QR Codes and Labels

Each item is assigned a unique internal code, and the system generates a matching **QR code** on demand:

- A QR PNG image is available for every item (`/items/<code>/qr.png`).
- A **printable label page** renders the item name, code, room, and bin location alongside the QR code, with a one-click browser print button.
- The QR code encodes a direct URL to the item's stock page, so scanning it with a phone camera immediately opens the correct add/remove screen — no manual searching or typing.

Users interact with the QR code when:

- Adding new stock.
- Removing items from inventory.
- Checking current item details.

### 6.4 Quantity Updates

After opening an item (by scanning its QR code or browsing to it), the user selects Add Stock or Remove Stock, enters the quantity, and provides the required lab context (lab instructor and topic of the day) plus optional notes. The system updates the inventory count immediately and stores the transaction in the activity log. Removals are validated so a user cannot remove more than the quantity on hand.

The same shared transaction logic powers both the QR/per-item stock page and the general scan page, so both behave identically.

Example transactions:

- Add 20 boxes of gloves.
- Remove 5 IV start kits.
- Adjust item count after a physical inventory check.

### 6.5 Automated Database and Spreadsheet Updates

The PostgreSQL database is the single source of truth. Excel/CSV reports can be generated on demand. This avoids the risk of multiple people manually editing the same spreadsheet while still allowing staff to download familiar spreadsheet-style reports.

### 6.6 Inventory Dashboard

The dashboard shows:

- Total inventory items.
- Low-stock items.
- Recent transactions.
- Search and filter options by name, code, or location.

### 6.7 Reporting

Reports support:

- Current stock levels.
- Usage history by date range.
- Transactions by user, lab instructor, or topic of the day.
- Low-stock report.
- Export to Excel or CSV.

## 7. System Workflow

### 7.1 Removing an Item

1. User signs in with their email and password.
2. User scans the item's QR code with a phone camera (or browses to the item), which opens the item's stock page.
3. System displays the item name and available quantity.
4. User selects "Remove Stock," enters the quantity, and fills in lab instructor, topic of the day, and any notes.
5. System validates the quantity, updates inventory, and records the transaction with user, date, and time.

### 7.2 Adding or Restocking an Item

1. Authorized user signs in.
2. User scans the QR code or searches for the item.
3. User selects "Add Stock" and enters the quantity plus lab context.
4. System updates the database and records the date, time, user, item, and quantity.

### 7.3 Registering a New Item

1. Faculty or administrator signs in.
2. User selects "New Item" and enters item details.
3. System assigns (or accepts) an internal item code.
4. The user opens the item's printable label page and prints the QR label, which is attached to the shelf, bin, or package.

## 8. Product Scope and Status

The core workflow is implemented and verified: secure authentication, item management, QR generation and labels, QR-driven stock updates, transaction history, inventory views, and CSV/Excel export.

Delivered features:

- Email/password login with hashed passwords and role-based access.
- Invite-based account creation and self-service password reset via email links.
- Session idle-timeout, admin re-authentication, login lockout, and CSRF protection.
- Add/edit item records with auto-generated internal codes.
- On-demand QR code images and printable QR labels.
- QR-driven add/remove stock with required lab-context capture.
- Transaction history with user, date/time, instructor, topic, and notes.
- Current inventory table and low-stock view.
- CSV/Excel export of inventory and transactions.
- An automated authentication test suite (pytest).

Features that can be added next:

- Expiration-date alerts.
- Supplier management and purchase-order generation.
- Rate limiting backed by a shared store (Redis) for multi-worker deployments.
- Multi-room or multi-campus (multi-tenant) inventory tracking.
- Advanced analytics dashboard.
- Native mobile app (the current web app already supports phone-camera scanning).

## 9. Technical Approach

The system is a web application that runs behind a domain over HTTPS and can be hosted on a small server or managed platform.

Software structure:

- **Frontend:** Server-rendered web interface (Jinja2 templates) for login, item management, QR labels, stock updates, inventory tables, and reports.
- **Backend:** Flask application server handling authentication, item lookups, QR generation, inventory updates, and reports.
- **Database:** PostgreSQL, a free and open-source relational database suitable for both local prototyping and production.
- **QR codes:** Generated server-side with the `qrcode` library; scanned with any smartphone/tablet camera (no dedicated hardware).
- **Security libraries:** Flask-WTF (CSRF), Werkzeug (password hashing), and `itsdangerous` (signed, time-limited invite/reset tokens).
- **Serving:** Gunicorn behind a reverse proxy that terminates TLS.
- **Export:** CSV and Excel-compatible reports.

This approach keeps the project affordable while supporting a secure, publicly reachable deployment.

## 10. Data to Track

The database includes the following core records (as implemented).

### Users

- ID.
- Email (unique, used for login).
- Password hash (null while an invite is pending).
- Name.
- Role (student, faculty, administrator).
- Department (optional).
- Institution ID (optional; no longer used for login).
- Active/inactive status.
- Created-at and last-login timestamps.

### Items

- Item ID.
- Internal code (unique; used to build the QR link).
- Item name.
- Bin location and room.
- Company/supplier (optional).
- Storage location (optional).
- Current quantity.
- Minimum stock quantity.
- Expiration date (optional).
- Notes (optional).

### Transactions

- Transaction ID.
- User ID.
- Item ID.
- Transaction type: add or remove.
- Quantity.
- Date and time.
- Lab instructor.
- Topic of the day.
- Notes.

## 11. Security and Accountability

Because this system may be used in medication-room or healthcare training environments and is reachable over the public internet, it includes the following safeguards:

- Login required before any inventory action; no account can log in without a verified, hashed password.
- Role-based permissions for students, faculty, and administrators.
- Invite-only account creation; passwords are chosen by the user via a secure link and never set or seen by administrators.
- Self-service password reset with signed, time-limited links.
- CSRF protection on every state-changing form.
- Session idle-timeout with activity-based refresh, plus re-authentication for destructive admin actions.
- Brute-force cooldown after repeated failed logins.
- HTTPS/TLS in production, with secure session cookies and a strong, environment-provided secret key.
- Transaction history that records who added or removed each item, when, and in what lab context, and that regular users cannot casually delete.

## 12. Timeline

Deadline: **July 20, 2026**

| Phase | Dates | Deliverables |
|---|---:|---|
| Phase 1: Requirements and Design | June 11 - June 16 | Finalize item fields, user roles, workflow, database schema, and hosting assumptions |
| Phase 2: Prototype Setup | June 17 - June 23 | Application structure, database, login screen, and basic inventory table |
| Phase 3: QR and Inventory Workflow | June 24 - July 1 | Item detail page, QR image route, printable label page, QR-driven stock page, and shared transaction logging |
| Phase 4: Reports and Dashboard | July 2 - July 8 | Low-stock view, recent activity, inventory reports, and CSV/Excel export |
| Phase 5: Security Hardening | July 9 - July 15 | Real authentication (email/password), invites, password reset, CSRF, session timeout, admin re-auth, lockout, and automated tests |
| Phase 6: Final Proposal and Demo Preparation | July 16 - July 20 | Prepare demo, documentation, final proposal, and presentation-ready summary |

## 13. Expected Benefits

The completed system is expected to:

- Reduce manual data entry.
- Improve inventory accuracy.
- Save time for faculty and staff.
- Create per-user accountability for supply usage.
- Help prevent unexpected supply shortages.
- Make restocking decisions easier.
- Provide professional reports for planning and auditing.
- Offer a secure, scalable foundation for future healthcare inventory automation.

## 14. Cost Considerations

The project minimizes cost by using:

- Existing computers, tablets, or phones (the phone camera is the QR scanner — no dedicated hardware).
- QR labels printed on standard label sheets or a small label printer.
- Open-source software tools.
- PostgreSQL (no license cost).
- Affordable web hosting with a managed TLS certificate.

Estimated cost options:

| Item | Low-Cost Option |
|---|---:|
| Computer, tablet, or phone | Existing device if available |
| QR scanning hardware | None required (built-in camera) |
| QR labels | Standard printable labels or label printer |
| Database | PostgreSQL, free and open source |
| Software hosting | Small server or managed platform with HTTPS |

## 15. Risks and Mitigation

| Risk | Mitigation |
|---|---|
| Users forget to scan items | Keep the scan-to-stock workflow one step; print QR labels and place them on the bins |
| QR labels become damaged | Reprint labels on demand from the item's label page; also attach labels to shelves/bins |
| Inventory count becomes inaccurate | Include periodic physical count and adjustment workflow |
| Staff need Excel reports | Provide CSV/Excel export rather than removing spreadsheet access completely |
| Public exposure invites attacks | Enforce HTTPS, CSRF, hashed passwords, session timeout, and login lockout (implemented) |
| Scope becomes too large | Focus first on the core workflow and defer advanced integrations |
| Medication-related compliance is unclear | Position the product as an educational inventory system until formal compliance rules are reviewed |

## 16. Success Criteria

The project is considered successful if:

- A user can sign in securely with an email and password.
- A new item can be registered and given an internal code and QR label.
- An item can be identified by scanning its QR code with a phone.
- Inventory quantities can be increased or decreased with lab context captured.
- The database updates automatically after each transaction.
- A transaction log records user, item, quantity, date, time, instructor, and topic.
- Current inventory can be exported to CSV or Excel format.
- The system can be demonstrated using realistic nursing or medication-room supplies over a live, HTTPS-served domain.

## 17. Future Expansion

After the initial product, the system can be expanded to include:

- Cloud synchronization and multi-tenant (multi-institution) support.
- Native mobile app.
- Expiration-date monitoring and automated reorder suggestions.
- Role-specific dashboards and advanced audit reports.
- Integration with purchasing systems.
- Shared-store rate limiting for large multi-worker deployments.

## 18. Conclusion

This project delivers a practical, affordable, and secure inventory management system for nursing education and healthcare-related environments. By combining QR-code scanning, individual email/password accounts, automated database updates, and exportable reports, the system significantly reduces manual spreadsheet work and improves accuracy, accountability, and supply readiness.

The core workflow — signing in securely, scanning an item's QR code, adding or removing quantities with lab context, updating inventory automatically, and producing reports — is implemented and verified. With authentication and session hardening in place, the system is positioned to move from prototype to a hosted product suitable for launch, and can be expanded into a broader platform for academic, simulation, and healthcare inventory use.
