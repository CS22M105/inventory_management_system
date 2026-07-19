# Data Retention Policy

Date: July 12, 2026

Project: Katz Nursing School Inventory Management System

## Purpose

This policy defines recommended retention rules for inventory records,
transaction history, audit logs, user accounts, exports, and operational logs.
The final retention schedule must be approved by the university before
production launch.

## Recommended Retention Schedule

| Data type | Recommended default | Reason |
| --- | --- | --- |
| Transaction history | 3-7 years | Supports lab accountability, inventory review, and university audit needs. |
| Audit logs | At least 1 year; 3-7 years if required by IT/security policy | Supports security investigations and accountability. |
| User accounts | Keep active users; deactivate departed users when history must remain accountable | Transactions and audit logs may reference users. |
| Inventory items | Keep while operationally active; archive/delete only after review | Preserves inventory continuity and historical stock context. |
| CSV exports | Keep only as long as needed for the approved purpose | Exports may contain sensitive user/activity data. |
| Application logs | 30-90 days unless needed for an incident | Useful for troubleshooting without keeping logs forever. |
| Error monitoring events | 30-90 days unless needed for an incident | Useful for debugging production failures. |

## User Deletion Rule

Default behavior should be deactivation, not hard deletion, when a user has
transactions, audit logs, or other accountability history.

Use hard deletion only when all of these are true:

```text
- the account was created by mistake,
- the account has no transaction history,
- the account has no required audit/legal retention need,
- an authorized administrator approves deletion.
```

## Transaction Retention

Transaction records include user, item, action type, quantity, date, time, lab
instructor, topic of day, and notes. These records may become student-related
activity records in a university setting.

Recommended default:

```text
Keep transaction history for 3-7 years, depending on university policy.
```

Do not purge transaction history until the university confirms:

```text
- required retention period,
- who approves deletion,
- whether records must be archived before deletion,
- whether legal hold rules apply.
```

## Audit Log Retention

Audit logs include user administration, item changes, stock actions, exports,
database-status views, and selected operational actions.

Recommended default:

```text
Keep audit logs for at least 1 year.
Keep for 3-7 years if required by university IT/security policy.
```

Audit logs should be append-only from the application UI. Ordinary admins should
not edit or delete audit rows.

## Export Retention

Downloaded CSV files are outside the app after export. Operators must treat them
as controlled university data.

Recommended rules:

```text
- Store exports only in approved university storage.
- Do not keep exports on personal laptops longer than necessary.
- Do not send exports through personal email.
- Delete local copies after the approved purpose is complete.
- Do not upload exports to unapproved tools.
```

## Review Cadence

Review this policy:

```text
- before production launch,
- after the first university pilot,
- annually,
- after any security/privacy incident,
- when university retention requirements change.
```

## Decisions Still Required

University stakeholders must confirm:

```text
- final transaction retention period,
- final audit-log retention period,
- approved storage location for CSV exports,
- who can approve hard deletion,
- whether archived records are required before purge,
- whether legal hold rules apply.
```
