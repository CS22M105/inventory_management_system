# University Market Readiness Plan

Date: July 10, 2026

Project: Katz Nursing School Inventory Management System

Audience: university pilot teams, IT/security reviewers, project maintainers,
and future production operators.

## Purpose

This document defines what should be added or verified before this inventory
system is offered as a serious university product. The app already has a strong
technical foundation: Flask, PostgreSQL, Alembic migrations, real authentication,
roles, QR stock workflow, tests, Gunicorn, deployment files, observability
support, and a package layout.

For a university-facing product, the next goal is not only "the app works." The
next goal is:

```text
The app is trustworthy enough for a university IT team to approve,
safe enough for student/faculty data, accessible enough for campus use,
and operable enough that outages and data loss are not handled manually.
```

This plan is intentionally broader than code. It includes compliance,
accessibility, auditability, hosting, operations, support, documentation, and
procurement readiness.

---

## Current Readiness Assessment

Current technical status:

```text
Codebase health: strong
Local functionality: working
Automated tests: 82 passing
Database: PostgreSQL with Alembic migrations
Deployment preparation: Procfile, Gunicorn, CI, deploy workflow skeleton
Observability preparation: Sentry optional, structured request logs, /health
Architecture: package layout with blueprints and thin app.py entrypoint
```

Current market-launch status:

```text
Ready for internal demo: yes
Ready for controlled university pilot: close, after staging deployment and docs
Ready for paid production rollout: not yet
```

The remaining work is mostly in these areas:

```text
1. Accessibility
2. Privacy / FERPA-aware data handling
3. Admin audit trail
4. Production hosting and managed database
5. Backups and restore drill
6. Email delivery
7. Monitoring and incident response
8. Procurement/security documentation
9. Pilot support process
10. Longer-term SSO / enterprise access controls
```

---

## Guiding Standards and References

Use these as the external anchors for university readiness:

```text
FERPA / student privacy:
    U.S. Department of Education Student Privacy Policy Office
    https://studentprivacy.ed.gov/ferpa

Accessibility:
    W3C Web Content Accessibility Guidelines (WCAG) 2.2
    https://www.w3.org/TR/WCAG22/

Cybersecurity program framing:
    NIST Cybersecurity Framework
    https://www.nist.gov/cyberframework

Render Flask deployment:
    https://render.com/docs/deploy-flask

Render Postgres:
    https://render.com/docs/postgresql-creating-connecting

Render deploy hooks:
    https://render.com/docs/deploy-hooks

Render health checks:
    https://render.com/docs/health-checks

Railway Flask deployment:
    https://docs.railway.com/guides/flask

Railway PostgreSQL:
    https://docs.railway.com/databases/postgresql
```

Important note:

```text
This document is a product/engineering readiness plan, not legal advice.
Before a real sale or campus-wide launch, the university's IT/security/privacy
team should review the app, hosting architecture, data fields, retention rules,
and vendor/security documents.
```

---

## Recommended Execution Order

The best path is:

```text
Step R1   Accessibility readiness
Step R2   FERPA-aware privacy and data classification
Step R3   Admin audit trail
Step R4   Data retention and export control policy
Step R5   Production hosting decision and staging setup
Step R6   Managed PostgreSQL backups + restore drill
Step R7   Production email delivery
Step R8   Monitoring, incident response, and support workflow
Step R9   Procurement/security documentation package
Step R10  Pilot launch checklist
Step R11  Future enterprise features
```

Steps R1-R4 can happen before cloud deployment. Steps R5-R8 require a hosting
provider. Steps R9-R10 prepare the product for real users and stakeholders.

---

## Step R1 - Accessibility Readiness

Priority: Critical for universities.

Target:

```text
WCAG 2.2 AA where practical.
```

Why:

```text
Universities serve students, staff, faculty, and visitors with different
accessibility needs. Accessibility is also a procurement concern. A product that
cannot be navigated by keyboard or screen reader will be difficult to approve.
```

Add:

```text
1. Keyboard-only navigation audit
    - Login
    - Dashboard
    - Items dropdown
    - Add/edit item forms
    - Scan page
    - Transaction filters
    - Admin users page
    - CSV export buttons

2. Focus visibility
    - Every link, button, dropdown, form field, and nav item must show a clear
      focus state.

3. Form labels and errors
    - Every input has an explicit label.
    - Error messages identify the field and problem.
    - Required fields are communicated visually and programmatically.

4. Color contrast
    - Text/background combinations meet WCAG AA contrast.
    - Low-stock warnings must not rely only on color.

5. Screen-reader names
    - Icon buttons, QR print actions, scanner controls, dropdowns, and nav
      menus have accessible names.

6. Responsive/mobile accessibility
    - Pages work on phone and tablet.
    - Camera/QR scanning controls remain reachable and understandable.

7. Accessible authentication
    - Password show/hide control has an accessible label.
    - Reset/set-password flows do not require memory puzzles or inaccessible
      interaction patterns.
```

Verify:

```text
Manual:
    - Navigate all critical workflows using only Tab, Shift+Tab, Enter, Space.
    - Test with VoiceOver on macOS or NVDA on Windows.
    - Test mobile layout on a phone.

Automated:
    - Run a browser accessibility checker such as axe DevTools.
    - Record issues and fixes in PROGRESS_REPORT.md.

Acceptance:
    - No keyboard traps.
    - All forms usable without a mouse.
    - No critical color-contrast failures.
    - Main workflows usable with a screen reader.
```

Deliverables:

```text
ACCESSIBILITY_STATEMENT.md
Accessibility test checklist in README or design_docx
Open list of any known limitations
```

---

## Step R2 - FERPA-Aware Privacy and Data Classification

Priority: Critical.

Why:

```text
The app stores names, emails, institution IDs, roles, item transactions,
lab instructors, topic of day, and activity history. In a university setting,
some of this may be tied to students and maintained by an educational
institution, so it should be treated as sensitive student-related data.
```

Data classification:

```text
Account data:
    - name
    - email
    - institution_id
    - role
    - department
    - active/inactive status

Inventory data:
    - item name
    - vendor
    - room
    - bin
    - quantity
    - expiration date
    - notes

Transaction data:
    - user
    - item
    - action type
    - quantity
    - date
    - time
    - lab instructor
    - topic of day
    - notes

Operational data:
    - login attempts
    - request IDs
    - logs
    - exports
```

Best choices:

```text
1. Data minimization
    - Store only fields needed for inventory and accountability.
    - Avoid sensitive medical/clinical details in notes.
    - Do not store Social Security numbers, grades, diagnoses, or patient data.

2. Privacy notice
    - Explain what data is stored and why.
    - Explain who can access it.
    - Explain retention and deletion/deactivation rules.

3. Role-based access
    - Students should not access admin/user-management pages.
    - Faculty can manage students if required.
    - Admin can manage faculty/students and system status.

4. Export control
    - CSV exports can contain personal data.
    - Export actions should be logged.
    - Only authorized roles should export.

5. Vendor review package
    - Prepare a privacy/security summary for university IT.
```

Add:

```text
PRIVACY_AND_DATA_HANDLING.md
Data inventory table
Export policy
Retention policy
Admin audit trail for data exports
```

Verify:

```text
University stakeholder confirms:
    - Which fields are allowed.
    - Who may see transaction history.
    - Who may export CSV.
    - How long transaction records must be retained.
```

---

## Step R3 - Admin Audit Trail

Priority: High.

Why:

```text
Production systems need to answer "who did what, when, and from where?"
This is especially important for user management, exports, item edits, and
stock adjustments.
```

Add a new audit log table:

```text
audit_logs
    id
    actor_user_id
    actor_email_snapshot
    actor_role_snapshot
    action
    target_type
    target_id
    target_label
    request_id
    ip_address
    user_agent
    details_json
    created_at
```

Actions to log:

```text
User administration:
    - user_created
    - invite_resent
    - user_deactivated
    - user_activated
    - user_deleted
    - password_set_by_cli

Inventory:
    - item_created
    - item_updated
    - qr_label_viewed or qr_label_printed if feasible

Stock:
    - stock_added
    - stock_removed
    Already captured in transactions, but audit can store request context.

Reports:
    - transactions_csv_exported
    - inventory_csv_exported

System:
    - db_status_viewed
    - config_check_run if exposed operationally
```

Best choices:

```text
1. Append-only audit table
    Do not let ordinary admin UI edit/delete audit rows.

2. Snapshot important actor details
    Store email/role snapshots because users can later be renamed/deactivated.

3. Avoid sensitive payloads
    Do not log passwords, reset tokens, invite tokens, CSRF tokens, SMTP values,
    DATABASE_URL, or full request bodies.

4. Add admin-only audit viewer later
    Filter by date, actor, action, target type.
```

Verify:

```text
Tests:
    - creating a user creates audit log
    - deactivating/deleting user creates audit log
    - item edit creates audit log
    - stock action creates transaction and optional audit context
    - CSV export creates audit log
    - students cannot view audit logs
    - faculty/admin access follows policy
```

---

## Step R4 - Data Retention and Export Control

Priority: High.

Decisions required:

```text
1. Transaction retention
    Recommended default: keep transaction history for 3-7 years, depending on
    university policy.

2. Audit-log retention
    Recommended default: keep for at least 1 year; 3-7 years if required by
    university IT/security policy.

3. User deletion
    Best default: deactivate users instead of hard-delete when records exist.
    This preserves accountability.

4. Export control
    Exports should be limited to admin/faculty as approved.
    Export events should be audit logged.

5. Notes policy
    Notes should not contain patient names, diagnoses, grades, or sensitive
    student information.
```

Deliverables:

```text
DATA_RETENTION_POLICY.md
CSV_EXPORT_POLICY.md
Admin training note: what not to type into Notes
```

---

## Step R5 - Best Hosting Platform Choice

Priority: Critical.

Selection criteria:

```text
1. Supports Python/Flask + Gunicorn easily.
2. Supports managed PostgreSQL.
3. Supports automatic deploys from GitHub.
4. Supports environment variables/secrets.
5. Supports custom domain and managed TLS.
6. Supports health checks and logs.
7. Supports backups/PITR or integrates cleanly with a DB that does.
8. Has clear rollback story.
9. Is simple enough for a small team to operate.
10. Can satisfy university IT/security review.
```

Recommended choice for this project:

```text
Best first production choice: Render
Best alternate: Railway
Best advanced/devops choice: Fly.io
Best enterprise/cloud choice: AWS/Azure/GCP
Not preferred for first launch: self-managed VM unless university IT requires it
```

### Option 1 - Render

Fit:

```text
Best practical choice for the first hosted university pilot.
```

Why it fits:

```text
- Official Flask deployment path.
- Supports GitHub-connected web services.
- Supports Gunicorn start command.
- Supports managed Render Postgres.
- Supports deploy hooks, which match the existing GitHub deploy workflow.
- Supports health checks and operational logs.
- Supports custom domains and TLS.
- Lower operational complexity than AWS/Azure/GCP.
```

Recommended Render setup:

```text
Service type:
    Web Service

Build command:
    pip install -r requirements.txt

Start command:
    gunicorn app:app -c gunicorn.conf.py

Release/predeploy command:
    alembic upgrade head
    or use the Procfile release phase if the selected Render flow supports it.

Database:
    Render Postgres paid plan with backups/PITR.

Health check:
    /health

Environment:
    APP_ENV=production
    SECRET_KEY=<generated 64+ char secret>
    DATABASE_URL=<Render internal Postgres URL>
    APP_BASE_URL=https://<custom-domain>
    EMAIL_PROVIDER=smtp
    EMAIL_FROM=<approved sender>
    SMTP_*
    SENTRY_DSN=<optional but recommended>
    RATELIMIT_STORAGE_URI=<Redis URL if multi-worker/shared limits are required>
```

Important Render notes:

```text
- Put web service and database in the same region.
- Prefer the internal database URL for app-to-database traffic.
- Use a paid database plan for production backup/PITR expectations.
- Add the Render deploy hook to GitHub as DEPLOY_HOOK_URL only after the service
  exists.
```

### Option 2 - Railway

Fit:

```text
Good alternate for quick deployment and simple projects.
```

Why it fits:

```text
- Official Flask guide.
- PostgreSQL support.
- Environment variable workflow is simple.
- Good developer experience.
```

Risks/considerations:

```text
- Confirm backup/PITR behavior and retention for the selected paid plan.
- Confirm custom-domain, health-check, logs, and team controls meet university
  expectations.
```

### Option 3 - Fly.io

Fit:

```text
Good when you want more infrastructure control.
```

Why it may fit:

```text
- Strong deployment/runtime control.
- Good for global/region-aware deployments.
```

Risks/considerations:

```text
- More DevOps complexity.
- Managed Postgres/backup strategy must be reviewed carefully.
- Not the easiest first-launch choice for this project.
```

### Option 4 - Heroku

Fit:

```text
Familiar PaaS model with strong add-on ecosystem.
```

Why it may fit:

```text
- Procfile model matches this project.
- Heroku Postgres is mature.
```

Risks/considerations:

```text
- Cost can rise quickly.
- Confirm current plan availability, support level, backup/rollback, and
  university procurement fit before choosing.
```

### Option 5 - AWS / Azure / Google Cloud

Fit:

```text
Best for enterprise contracts, strict IT governance, private networking,
custom compliance requirements, and campus-wide production.
```

Why it may fit:

```text
- Strong enterprise security controls.
- Managed PostgreSQL options.
- IAM, logging, monitoring, VPC/private networking.
- University IT teams may already have vendor agreements.
```

Risks/considerations:

```text
- More setup work.
- More expensive to operate if not managed carefully.
- Requires stronger cloud operations knowledge.
```

Hosting recommendation:

```text
For a first real university pilot:
    Choose Render.

For a university that already mandates a cloud provider:
    Use that provider's managed app service + managed PostgreSQL.

For a small internal demo:
    Railway is acceptable.

For a paid product:
    Use a paid plan, managed database backups, custom domain, HTTPS, monitoring,
    and documented restore drill. Do not run production on a free/sleeping tier.
```

---

## Step R6 - Managed PostgreSQL Backups and Restore Drill

Priority: Critical.

Production database requirements:

```text
1. Managed PostgreSQL.
2. Daily automated backups.
3. Point-in-time recovery where available.
4. Backup retention window defined, recommended 7-30 days for first launch.
5. Backups stored outside the app host.
6. Restore drill completed before production launch.
```

Restore drill:

```text
1. Pick a staging or scratch database.
2. Create a known row.
3. Trigger/locate a backup or choose a point-in-time restore.
4. Restore to a separate database instance.
5. Confirm schema exists.
6. Confirm known row exists.
7. Record RTO/RPO expectations.
```

Deliverable:

```text
RESTORE_RUNBOOK.md
```

---

## Step R7 - Production Email Delivery

Priority: Critical.

Why:

```text
Invite and password-reset flows depend on email. Local "printed link" behavior
is acceptable for development only.
```

Best choices:

```text
University SMTP:
    Best if the university wants emails from an official campus domain.

SendGrid / Mailgun / Amazon SES:
    Good if university SMTP is not available.

Microsoft 365 SMTP:
    Good if the institution uses Microsoft and approves app-password/SMTP use.
```

Requirements:

```text
EMAIL_PROVIDER=smtp
EMAIL_FROM=<approved sender>
SMTP_HOST=<provider>
SMTP_PORT=587 or 465
SMTP_USERNAME=<secret>
SMTP_PASSWORD=<secret>
SMTP_USE_TLS=true for 587
SMTP_USE_SSL=true for 465
```

Verify:

```text
1. Create a faculty user.
2. Confirm invite email arrives.
3. Open set-password link.
4. Confirm login works.
5. Request password reset.
6. Confirm reset email arrives.
7. Confirm expired/invalid links fail safely.
```

---

## Step R8 - Monitoring, Incident Response, and Support

Priority: High.

Monitoring:

```text
1. Uptime monitor:
    URL: https://<domain>/health
    Interval: 1-5 minutes
    Alert on non-200 or timeout

2. Sentry:
    Capture unhandled errors.
    send_default_pii stays false unless explicitly approved.

3. Structured logs:
    Keep request_id, method, path, status, duration, remote address.
    Do not log passwords, cookies, tokens, full form bodies, or secrets.
```

Incident response plan:

```text
1. Define support contact.
2. Define severity levels.
3. Define response time expectations.
4. Define who can access production logs/database.
5. Define how to rotate SECRET_KEY, SMTP password, and database credentials.
6. Define how to notify the university if data is exposed.
```

Deliverables:

```text
INCIDENT_RESPONSE_PLAN.md
SUPPORT_RUNBOOK.md
```

---

## Step R9 - Procurement and Security Documentation Package

Priority: High for selling.

Universities may ask for:

```text
1. Product overview.
2. Data flow diagram.
3. Data inventory.
4. Security controls summary.
5. Authentication and authorization summary.
6. Backup and restore policy.
7. Incident response plan.
8. Accessibility statement.
9. Privacy/data handling statement.
10. Hosting architecture.
11. Vendor/subprocessor list.
12. Terms of use / acceptable use statement.
13. Admin user guide.
14. Faculty/student user guide.
15. Support and maintenance policy.
```

Best next documents to create:

```text
PRIVACY_AND_DATA_HANDLING.md
ACCESSIBILITY_STATEMENT.md
SECURITY_CONTROLS_SUMMARY.md
RESTORE_RUNBOOK.md
INCIDENT_RESPONSE_PLAN.md
ADMIN_USER_GUIDE.md
FACULTY_STUDENT_USER_GUIDE.md
```

---

## Step R10 - Pilot Launch Checklist

Pilot goal:

```text
Launch with one university department/lab before full market rollout.
```

Before pilot:

```text
[ ] Staging deploy exists.
[ ] Production deploy exists.
[ ] Custom domain works over HTTPS.
[ ] APP_BASE_URL uses HTTPS domain.
[ ] Managed PostgreSQL is connected.
[ ] Migrations ran successfully.
[ ] First permanent admin created.
[ ] No demo users/passwords enabled.
[ ] Email invite/reset flow works.
[ ] QR labels print correctly.
[ ] Phone scan opens HTTPS stock page.
[ ] Add/remove stock works.
[ ] Transaction history and export work.
[ ] Audit logging is implemented or formally scheduled.
[ ] Accessibility checklist completed.
[ ] Privacy/data handling doc reviewed.
[ ] Backup restore drill completed.
[ ] Uptime monitor is green.
[ ] Sentry test event received.
[ ] Support contact and escalation path defined.
```

During pilot:

```text
Track:
    - login issues
    - QR scanning issues
    - printer/label issues
    - slow pages
    - confusing UI workflows
    - missing item fields
    - faculty/admin permission problems
    - export/report requests
```

After pilot:

```text
1. Review support tickets and feedback.
2. Fix usability issues.
3. Confirm data accuracy.
4. Confirm restore drill still works.
5. Prepare production rollout version.
```

---

## Step R11 - Future Enterprise Features

These are not required for the first pilot, but they make the product stronger
for broader university sales.

```text
1. SSO
    - SAML
    - Microsoft Entra ID / Azure AD
    - Okta
    - Google Workspace

2. Department/lab scoping
    - Users only see inventory for assigned lab/department.

3. Read-only auditor role
    - Can view reports/audit logs but cannot change inventory.

4. Inventory manager role
    - Separate from faculty role.

5. Approval workflows
    - Optional approval before deleting/deactivating users or editing critical
      item fields.

6. Advanced reports
    - usage by lab
    - usage by course/topic
    - vendor restock report
    - expiration/soon-to-expire report

7. Import tools
    - CSV import for initial item catalog.
    - Validation report before import.

8. Label-print templates
    - Brother label printer templates.
    - Avery sheet templates.
    - QR-only compact label templates.

9. Multi-tenant architecture
    - One database per customer is safest for early product sales.
    - Shared multi-tenant database should wait until the product and security
      model are mature.
```

---

## Recommended Immediate Next Step

Do this next:

```text
Create the Accessibility and Privacy mini-phase:
    1. Accessibility review checklist.
    2. Privacy/data inventory document.
    3. Audit-log implementation plan.
```

Then choose hosting:

```text
Recommended first hosting choice: Render
Recommended database: Render Postgres paid plan or another managed Postgres
                     approved by the university.
Recommended first deploy type: staging first, production second.
```

This gives the project the best balance:

```text
Strong enough for university IT review.
Simple enough to operate as a small team.
Ready to evolve into a commercial product.
```
