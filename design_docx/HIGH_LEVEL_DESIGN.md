# High-Level Design: Katz Nursing School Inventory Management System

Date: July 15, 2026

## 1. Purpose

This document describes the current high-level design of the Katz Nursing School
Inventory Management System. It reflects the application as it exists now: a
Flask/PostgreSQL web application with role-based access, QR-code stock
workflows, transaction history, audit logs, CSV exports, production
configuration, deployment readiness, and university privacy/accessibility
planning.

The document is intended for:

- project maintainers,
- university stakeholders,
- IT/security reviewers,
- future developers,
- deployment operators.

## 2. Product Goal

The system replaces spreadsheet/manual inventory tracking for nursing education,
simulation labs, medication rooms, and healthcare training spaces.

The product helps staff answer:

- what items exist,
- where they are stored,
- how many are available,
- which items are low stock,
- who added or removed stock,
- when an action happened,
- which lab instructor/topic was associated with the item use,
- who performed sensitive administrative or export actions.

## 3. System Scope

### In Scope

- Secure login for student, faculty, and administrator users.
- Faculty/admin user management.
- Inventory item creation and editing.
- Automatic internal barcode generation for new items.
- QR-code generation for item labels.
- Full label printing and QR-only compact label printing.
- Camera-based QR scanning from the dashboard.
- Manual scan/stock workflow.
- Per-item QR stock workflow.
- Transaction history with filters and pagination.
- Low-stock item list.
- Inventory and transaction CSV exports.
- Export controls and audit logging.
- Administrator database-status page.
- Administrator audit-log viewer.
- Health endpoint for uptime monitoring.
- PostgreSQL schema managed by Alembic migrations.
- Production configuration through environment variables.

### Out of Scope for the Current Version

- Automated purchasing/reorder integrations.
- Barcode/QR printer direct Bluetooth control from Flask.
- Enterprise SSO/SAML/OIDC.
- Multi-tenant customer isolation.
- Automated retention purge/archive jobs.
- Native mobile app.
- Real-time push notifications.

## 4. User Roles and Permissions

The system currently has three primary roles.

| Role | Main purpose | Key permissions |
| --- | --- | --- |
| Student | Use inventory during labs and simulations | View items, view transaction history, scan/use stock workflows |
| Faculty | Manage lab inventory and students | Student permissions plus add/edit items, print QR labels, manage student accounts, export CSV files |
| Administrator | Operate the system | Faculty permissions plus manage faculty/student accounts, view DB status, view audit logs, export reports |

Important rules:

- Students cannot add/edit items.
- Students cannot manage users.
- Students cannot access database status.
- Students cannot export CSV files.
- Faculty can manage students but cannot manage faculty or administrator users.
- Administrators can manage faculty and students.
- Administrator accounts are protected from deactivation/deletion.
- Database status and audit logs are administrator-only.

## 5. High-Level Architecture

```text
User Browser
    |
    | HTTPS
    v
Render / Cloud Web Service
    |
    | Gunicorn
    v
Flask Application
    |
    | psycopg2
    v
Managed PostgreSQL
```

Supporting services:

```text
GitHub             -> source control and CI/CD
Alembic            -> database migrations
WhiteNoise         -> static asset serving
Sentry optional    -> error monitoring
SMTP provider      -> invite/reset email delivery
Uptime monitor     -> checks /health
Managed Postgres   -> backups and point-in-time recovery
```

## 6. Application Structure

The application is now split into a maintainable package structure.

```text
app.py
    Thin compatibility entrypoint for Flask/Gunicorn.

inventory/
    __init__.py
        create_app() entrypoint.

    core.py
        Application assembly, shared route helpers, security hooks,
        audit helper, and compatibility exports.

    config.py
        Environment-backed configuration and production guards.

    db.py
        PostgreSQL connection helpers.

    cli.py
        Flask CLI commands such as init-db, db-upgrade, db-downgrade,
        set-password, and check-config.

    observability.py
        Sentry initialization and structured request logging.

    auth/
        Login, logout, reauth, forgot/reset password, set-password,
        password hashing, and signed token helpers.

    dashboard/
        Home, dashboard, and /health routes.

    items/
        Item list, low stock list, detail page, add/edit item forms,
        barcode generation, QR image route, full label, and QR-only label.

    stock/
        Manual scan route, per-item stock route, and shared stock
        transaction service.

    transactions/
        Transaction history, filters, pagination, export, and query helpers.

    reports/
        Inventory CSV export.

    admin/
        User management, database status, and audit-log viewer.

    services/
        Email integration helpers.
```

## 7. Main Data Model

### Users

Stores accounts that can log in.

Key fields:

- institution_id,
- email,
- password_hash,
- name,
- role,
- department,
- is_active,
- created_at,
- last_login_at.

Notes:

- Passwords are stored as hashes, never plaintext.
- Invited users may exist without a password_hash until they set a password.
- Deactivation is preferred over deletion when accountability history exists.

### Items

Stores inventory records.

Key fields:

- barcode,
- name,
- bin_location,
- room,
- company/vendor,
- quantity,
- minimum_quantity,
- location,
- expiration_date,
- notes.

Notes:

- The database column is still named `company` for compatibility, but the UI
  shows this as Vendor.
- New items can receive an automatically generated internal barcode.
- Expiration date is a real DATE field; optional/no date is stored as NULL.

### Transactions

Stores stock add/remove history.

Key fields:

- user_id,
- item_id,
- transaction_type,
- quantity,
- created_at,
- transaction_date,
- transaction_time,
- lab_instructor,
- topic_of_day,
- notes.

Notes:

- Transactions are the inventory movement record.
- Transaction history is paginated and filterable.
- Transaction CSV export is limited to faculty/administrators.

### Audit Logs

Stores security and accountability metadata for sensitive actions.

Key fields:

- actor_user_id,
- actor_email_snapshot,
- actor_role_snapshot,
- action,
- target_type,
- target_id,
- target_label,
- request_id,
- ip_address,
- user_agent,
- details_json,
- created_at.

Notes:

- Audit logs are append-only from the application UI.
- Audit logs do not store passwords, invite/reset tokens, CSRF tokens, SMTP
  credentials, DATABASE_URL, full request bodies, or CSV contents.
- Audit logs add request context to actions such as user changes, item changes,
  stock movement, exports, database-status views, and CLI password setting.

## 8. Core Workflows

### 8.1 Login

```text
User opens /login
User enters email/password
Application verifies password hash and active status
Session is created
User is redirected to /dashboard
```

Security behavior:

- Failed login attempts are limited.
- Sessions are signed with SECRET_KEY.
- Session cookies are HTTPOnly and SameSite=Lax.
- Secure cookies are enabled in production.

### 8.2 Invite and Set Password

```text
Faculty/admin creates an allowed user
Application creates user row with no password_hash
Application generates signed invite token
Application sends email through SMTP, or shows link only when explicitly allowed
Invited user opens /set-password/<token>
User sets password
User can log in
```

Production behavior:

- Real production should use SMTP.
- Temporary hosted testing can use `ALLOW_LOCAL_AUTH_LINKS=true`.
- The fallback should be disabled before real users use the system.

### 8.3 Add Item

```text
Faculty/admin opens Add New Item
User enters item details
If barcode is blank, system generates one
Application validates required fields and quantities
Item row is inserted
Audit log records item_created
```

### 8.4 Edit Item

```text
Faculty/admin opens Edit Item
User fixes barcode/vendor/room/bin/minimum quantity/expiration/notes
Application validates form
Item row is updated
Audit log records item_updated and changed fields
```

### 8.5 Print QR Labels

There are two label formats:

1. Full label:
   - item name,
   - barcode,
   - QR code,
   - room,
   - bin,
   - vendor if present,
   - expiration if present.

2. QR-only label:
   - QR code,
   - barcode/internal code below it.

The QR code points to:

```text
/items/<barcode>/stock
```

The browser print dialog sends the label to the printer selected by the local
computer. Flask does not directly control Bluetooth label printers.

### 8.6 Dashboard Camera QR Scan

```text
User opens dashboard
User clicks Start Camera
Browser asks for camera permission
User shows printed QR code to camera
JavaScript reads QR URL
Application opens /items/<barcode>/stock
Camera stops after successful scan
```

### 8.7 Manual Scan / Stock Action

```text
User opens Scan Item or per-item stock page
User enters/scans barcode or lands from QR link
User chooses add/remove
User enters quantity, lab instructor, topic, and notes
Application validates input
Application blocks removing more than available
Application updates item quantity
Application inserts transaction row
Application inserts audit log for stock_added or stock_removed
```

### 8.8 Transaction History

```text
User opens Transaction History
Application applies filters
Application loads one page of results
User can move through pages
Faculty/admin can export filtered or full CSV
Export action is audit logged
```

Supported filters:

- date range,
- item,
- user,
- lab instructor,
- topic,
- action type.

### 8.9 User Administration

```text
Faculty/admin opens Manage Users
Application shows users within allowed management scope
Faculty can manage students
Administrator can manage faculty and students
Sensitive actions may require fresh reauthentication
Audit logs record create/resend/deactivate/activate/delete actions
```

### 8.10 Audit Review

```text
Administrator opens /admin/audit-logs
Application shows recent audit events
Students/faculty are redirected away
```

Current viewer:

- read-only,
- recent entries first,
- no edit/delete action.

Future improvement:

- filters by date, actor, action, and target type.

## 9. Security Design

Security controls already included:

- password hashing,
- signed invite/reset tokens,
- CSRF protection on state-changing forms,
- session idle timeout,
- sudo-mode/fresh reauthentication for destructive admin actions,
- failed-login lockout,
- Flask-Limiter rate limiting,
- secure cookie settings in production,
- production SECRET_KEY guard,
- ProxyFix for TLS-terminating proxies,
- optional HSTS,
- Sentry support,
- structured request logging,
- audit logs,
- role-based access checks.

Secrets and sensitive configuration are supplied through environment variables,
not committed files.

## 10. Privacy and Data Handling

The system is FERPA-aware because transaction and account data may be tied to
students in a university environment.

Sensitive data categories include:

- account data,
- transaction data,
- notes,
- exports,
- audit logs,
- operational logs.

Important rules:

- Do not store patient names, diagnoses, grades, Social Security numbers, or
  unnecessary sensitive student information in notes.
- CSV exports are controlled and audit logged.
- Retention periods must be confirmed by university policy.
- Deactivation is preferred over deletion when records must remain accountable.

Related documents:

- `PRIVACY_AND_DATA_HANDLING.md`
- `DATA_RETENTION_POLICY.md`
- `CSV_EXPORT_POLICY.md`
- `ADMIN_NOTES_TRAINING.md`
- `ACCESSIBILITY_STATEMENT.md`

## 11. Database and Migration Design

PostgreSQL is the application database.

Alembic owns schema changes.

Important rules:

- New/production databases should run `alembic upgrade head`.
- Do not run `flask init-db` against a production/managed database.
- `schema.sql` is a readable local-development/bootstrap reference.
- Migrations must run once per deploy, not per request.

Current migration chain includes:

- baseline users/items/transactions schema,
- expiration date conversion to DATE,
- transaction query indexes,
- initial audit events table,
- expanded audit logs table.

## 12. Performance and Scalability Design

Current scaling controls:

- transaction history pagination,
- transaction filtering,
- transaction date/time indexes,
- item name index,
- audit log indexes,
- Gunicorn worker/thread configuration,
- WhiteNoise static asset serving,
- health endpoint for monitoring.

Expected growth:

- PostgreSQL can handle large transaction/audit tables if indexed and paginated.
- Retention/archive policy should be approved before long-term production use.
- Large CSV exports should remain controlled by role and may later need size/date
  limits.

## 13. Deployment Design

Target first hosting platform:

```text
Render Web Service + Render Managed PostgreSQL
```

Deployment components:

- GitHub repository,
- Render web service,
- managed PostgreSQL,
- environment variables,
- Gunicorn,
- Alembic pre-deploy migration command,
- `/health` health check,
- HTTPS/custom domain,
- SMTP provider for real invite/reset emails.

Important production environment variables:

- APP_ENV,
- SECRET_KEY,
- DATABASE_URL,
- APP_BASE_URL,
- EMAIL_PROVIDER/SMTP settings,
- PROXY_FIX_ENABLED,
- HSTS_ENABLED,
- BARCODE_PREFIX,
- SESSION_IDLE_MINUTES,
- TRANSACTIONS_PAGE_SIZE,
- SENTRY_DSN if used.

## 14. Observability and Operations

Operational features:

- `/health` returns JSON and checks database connectivity.
- `/db-status` is a human administrator page.
- structured request logs include request ID, path, method, status, duration,
  and remote address.
- Sentry can capture unhandled exceptions when configured.
- audit logs capture sensitive administrative/product actions.
- CI runs tests and migration checks.

## 15. Testing Strategy

Automated tests use real PostgreSQL test databases, not SQLite.

Test coverage includes:

- authentication and invite/reset flows,
- role permissions,
- stock add/remove workflows,
- transaction history pagination,
- CSV exports,
- export access control,
- item forms and label pages,
- QR label behavior,
- migrations,
- health endpoint,
- audit logs.

Current expected full test command:

```bash
pytest -q
```

## 16. Remaining Design Decisions

Before full university production launch, stakeholders should confirm:

- final transaction retention period,
- final audit-log retention period,
- whether students should continue seeing transaction history,
- whether faculty CSV export remains approved or should be admin-only,
- official SMTP/email provider,
- approved storage location for downloaded CSV exports,
- production custom domain,
- managed PostgreSQL backup/PITR plan,
- accessibility audit findings,
- incident/support process,
- whether enterprise SSO is required later.

## 17. Current High-Level Result

The system has moved beyond a local prototype into a production-ready foundation:

- maintainable Flask package structure,
- PostgreSQL with Alembic migrations,
- QR-code stock workflow,
- role-based permissions,
- transaction history and exports,
- audit logging,
- health/observability support,
- deployment configuration,
- privacy/accessibility/retention documentation.

The next major step is operational: finish a stable hosted deployment, configure
production SMTP, verify first-admin bootstrap, test QR label printing with the
actual Brother label printer, and complete a live-domain smoke test.
