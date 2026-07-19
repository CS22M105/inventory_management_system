# Privacy and Data Handling

Date: July 12, 2026

Project: Katz Nursing School Inventory Management System

## Purpose

This document describes what data the inventory system stores, why it is stored,
who should access it, how exports should be controlled, and what still needs
confirmation from university stakeholders before production launch.

The system is FERPA-aware because some activity records may be tied to students
and maintained by an educational institution. This document is not legal advice;
the university should review it with its privacy, IT, and compliance teams.

## Data Minimization Rules

The system should store only information needed for inventory tracking,
accountability, support, security, and required reporting.

Do not store these values in the app:

```text
- Social Security numbers
- grades
- diagnoses
- patient information
- clinical notes about real patients
- financial account numbers
- government ID numbers
- unnecessary student personal details
```

Free-text notes should stay operational. For example, use "Used for wound care
simulation lab" instead of any patient-specific or diagnosis-specific detail.

## Data Inventory

| Data area | Fields | Classification | Purpose | Primary access |
| --- | --- | --- | --- | --- |
| Account data | name, email, institution ID, role, department, active/inactive status | Sensitive university account data | Login, accountability, user management, role-based access | Administrator; faculty for student management where approved |
| Authentication data | password hash, reset/invite token validity through signed links, failed-login counters | Security-sensitive | Secure login, password setup/reset, brute-force protection | System only; administrators should not see passwords |
| Inventory data | item name, vendor, room, bin, quantity, minimum quantity, expiration date, notes | Internal operational data | Track supplies, locations, stock levels, and reorder needs | Logged-in users; create/edit limited to faculty/admin |
| Transaction data | user, item, action type, quantity, date, time, lab instructor, topic of day, notes | Sensitive student/activity-related data when tied to a student | Accountability for add/remove stock events and lab usage history | Logged-in users under current policy; final visibility must be confirmed by university |
| Operational data | request IDs, login attempts, app logs, error events, export audit events | Security/operations data | Troubleshooting, security monitoring, incident investigation | System administrators and approved operators |
| Exports | inventory CSV, transaction CSV | Sensitive when containing names, emails, activity, notes, or locations | Reporting, review, audit, operational recordkeeping | Authorized roles only; export events are audited |

## Role-Based Access Policy

Current application behavior:

```text
- Students can use item lookup, scan/stock workflows, and transaction history.
- Faculty can add/edit items and manage student accounts.
- Administrators can manage faculty/student accounts, access database status,
  and export inventory reports.
- Faculty and administrators can use the inventory management workflows.
- Database status is administrator-only.
```

University stakeholders must confirm whether students should continue seeing
transaction history. If the university wants transaction history restricted,
the route and export permissions should be tightened before launch.

## Export Policy

CSV exports can contain sensitive operational or student-related data. The
following rules apply:

```text
1. Export only when there is a legitimate university/inventory purpose.
2. Do not email exported CSV files casually or store them on shared personal
   drives.
3. Store exports only in approved university storage.
4. Delete local copies when they are no longer needed.
5. Treat transaction exports as sensitive because they include users, lab
   instructors, topics, dates, times, and notes.
6. Review notes before exporting to avoid disclosing information that should not
   have been entered.
```

The app records export audit events in `audit_logs`. Each export event
records:

```text
- acting user ID
- action
- target type
- actor email/role snapshot
- row count
- filters applied, if any
- request path
- request IP address
- request ID, when available
- user agent, when available
- timestamp
```

The audit event does not store the exported CSV contents.

## Retention Policy

Retention must be approved by the university. Recommended starting point:

| Record type | Suggested retention | Reason |
| --- | --- | --- |
| User accounts | Keep while active; deactivate instead of deleting when historical accountability is needed | Transactions reference users |
| Inventory records | Keep while item is active; archive/delete only after operational review | Inventory continuity |
| Transaction records | 3-7 years, or university policy | Accountability, audit, lab operations |
| Audit logs | 1-3 years, or university security policy | Detect misuse and answer audit questions |
| Application logs | 30-90 days unless needed for an incident | Operational troubleshooting |
| Error monitoring events | 30-90 days unless needed for an incident | Production debugging |

Deletion should not break historical records. If a person leaves the university,
prefer deactivation over deletion when transaction history must remain accurate.

## Privacy Notice Draft

Suggested user-facing notice for a production deployment:

```text
This system stores your name, email address, role, institution identifier, and
inventory activity to support nursing school inventory tracking and
accountability. Inventory activity may include item actions, quantities, dates,
times, lab instructor, topic of day, and operational notes. Access is limited by
role. CSV exports and security-relevant actions may be logged for audit and
operational purposes. Do not enter patient data, diagnoses, grades, Social
Security numbers, or other unnecessary sensitive information into this system.
```

## Vendor Review Summary

For university IT/security review, prepare:

```text
- data inventory and classifications from this document
- authentication and role model
- database hosting and backup plan
- logging/monitoring plan
- export/audit policy
- incident response contact
- accessibility statement
- known limitations and stakeholder decisions still pending
```

## Stakeholder Decisions Required

Before production launch, the university must confirm:

```text
- which fields are allowed
- whether institution_id is required for all users
- who may view transaction history
- who may export transaction CSV files
- whether notes need stricter validation or guidance
- transaction retention period
- audit log retention period
- approved storage location for downloaded CSV files
- privacy notice wording
```
