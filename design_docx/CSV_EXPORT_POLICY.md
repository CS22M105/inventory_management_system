# CSV Export Policy

Date: July 12, 2026

Project: Katz Nursing School Inventory Management System

## Purpose

CSV exports are useful for reporting, review, and audits, but they can contain
sensitive university data. This policy defines who may export data, how exports
should be handled, and what users must avoid.

## Export Types

| Export | Current route | Data included | Risk |
| --- | --- | --- | --- |
| Transaction CSV | `/transactions/export` | date, time, action, item, code, quantity, lab instructor, topic, user, notes | May contain student/activity-related data |
| Inventory CSV | `/reports/export` | code, item name, room, bin, vendor, quantity, minimum quantity, location, expiration date, notes | Internal operational inventory data |

## Access Policy

Recommended production rule:

```text
- Students: no CSV export access.
- Faculty: CSV export access only if approved by the university.
- Administrators: CSV export access for approved operational/reporting needs.
```

Current implementation:

```text
- Transaction CSV export is limited to faculty and administrators.
- Inventory CSV export is limited to faculty and administrators.
- Unauthenticated users are redirected to login.
- Export actions are recorded in audit_logs.
```

## Audit Logging

Each export creates an audit log entry containing metadata such as:

```text
- actor user ID,
- actor email/role snapshot,
- action,
- target type,
- row count,
- filters used,
- request path,
- request ID,
- IP address,
- user agent,
- timestamp.
```

Audit logs do not store the exported CSV contents.

## Handling Rules

Users who export CSV files must:

```text
1. Export only for legitimate university/inventory work.
2. Store files only in approved university storage.
3. Avoid personal email, personal cloud drives, or unapproved tools.
4. Delete local copies when the purpose is complete.
5. Share exports only with authorized university personnel.
6. Review free-text notes before sharing/exporting broadly.
7. Report accidental disclosure according to university policy.
```

## What Not To Export Casually

Transaction exports deserve extra care because they can include:

```text
- student/faculty names,
- lab instructor names,
- topic of day,
- dates and times of activity,
- operational notes.
```

## Approval Questions

Before production launch, confirm:

```text
- whether faculty may export transaction CSV files,
- whether faculty may export inventory CSV files,
- whether export access should be limited to administrators only,
- where exported CSV files may be stored,
- how long exported CSV files may be retained,
- who receives export-related audit reviews.
```
