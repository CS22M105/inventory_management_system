"""CSV export smoke/regression tests.

These tests parse the generated CSV instead of checking raw strings. The
transaction export uses more rows than the default page size so it guards the
H2 requirement that CSV exports are full filtered sets, not paginated pages.
"""

import csv
import io
import json

import app as app_module


TRANSACTION_HEADER = [
    "Date",
    "Time",
    "Action",
    "Item",
    "Barcode",
    "Quantity",
    "Lab Instructor",
    "Topic",
    "User",
    "Notes",
]

INVENTORY_HEADER = [
    "Barcode",
    "Item Name",
    "Bin Location",
    "Room",
    "Vendor",
    "Quantity",
    "Minimum Quantity",
    "General Location",
    "Expiration Date",
    "Notes",
]


def _location(response):
    return response.headers.get("Location", "")


def _login_as(login, users, role):
    response = login(users[role]["email"], users[role]["password"])
    assert response.status_code == 302


def _read_csv(response):
    return list(csv.reader(io.StringIO(response.get_data(as_text=True))))


def _seed_items_and_transactions(user_id, total_transactions=60):
    with app_module.app.app_context():
        db = app_module.get_db()
        item_ids = []
        for idx, barcode in enumerate(("EXP-A", "EXP-B"), start=1):
            row = db.execute(
                """
                INSERT INTO items (
                    barcode, name, bin_location, room, company,
                    quantity, minimum_quantity, location, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    barcode,
                    f"Export Item {idx}",
                    f"Bin {idx}",
                    "101",
                    "Export Vendor",
                    10 + idx,
                    1,
                    "Export Shelf",
                    f"Item {idx} notes",
                ),
            ).fetchone()
            item_ids.append(row["id"])

        for idx in range(total_transactions):
            item_id = item_ids[idx % len(item_ids)]
            db.execute(
                """
                INSERT INTO transactions (
                    user_id,
                    item_id,
                    transaction_type,
                    quantity,
                    transaction_date,
                    transaction_time,
                    lab_instructor,
                    topic_of_day,
                    notes
                )
                VALUES (
                    %s, %s, %s, %s,
                    DATE '2026-07-01' + (%s * INTERVAL '1 day'),
                    TIME '09:00:00' + (%s * INTERVAL '1 minute'),
                    %s, %s, %s
                )
                """,
                (
                    user_id,
                    item_id,
                    "add" if idx % 2 == 0 else "remove",
                    (idx % 4) + 1,
                    idx,
                    idx,
                    "Dr. Export",
                    "CSV Safety",
                    f"Export note {idx}",
                ),
            )

        db.commit()
        return item_ids


def _latest_audit_log(action):
    with app_module.app.app_context():
        db = app_module.get_db()
        return db.execute(
            """
            SELECT
                actor_user_id,
                actor_email_snapshot,
                actor_role_snapshot,
                action,
                target_type,
                target_label,
                details_json,
                ip_address,
                request_id
            FROM audit_logs
            WHERE action = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (action,),
        ).fetchone()


def test_transactions_export_returns_full_csv(client, users, login):
    _seed_items_and_transactions(users["faculty"]["id"], total_transactions=60)
    _login_as(login, users, "faculty")

    response = client.get("/transactions/export")

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "transaction_history_export.csv" in response.headers["Content-Disposition"]

    rows = _read_csv(response)
    assert rows[0] == TRANSACTION_HEADER
    # Regression guard: export is not paginated to the default page size of 50.
    assert len(rows) == 61
    assert {row[4] for row in rows[1:]} == {"EXP-A", "EXP-B"}

    audit = _latest_audit_log("transactions_csv_exported")
    assert audit["actor_user_id"] == users["faculty"]["id"]
    assert audit["actor_email_snapshot"] == users["faculty"]["email"]
    assert audit["actor_role_snapshot"] == "faculty"
    assert audit["target_type"] == "transactions"
    details = json.loads(audit["details_json"])
    assert details["row_count"] == 60
    assert details["filters"] == {}
    assert details["path"] == "/transactions/export"


def test_transactions_export_item_filter_returns_only_matching_rows(
    client, users, login
):
    item_ids = _seed_items_and_transactions(
        users["faculty"]["id"],
        total_transactions=60,
    )
    _login_as(login, users, "faculty")

    response = client.get(f"/transactions/export?item_id={item_ids[0]}")

    assert response.status_code == 200
    assert response.mimetype == "text/csv"

    rows = _read_csv(response)
    assert rows[0] == TRANSACTION_HEADER
    assert len(rows) == 31
    assert {row[4] for row in rows[1:]} == {"EXP-A"}

    audit = _latest_audit_log("transactions_csv_exported")
    details = json.loads(audit["details_json"])
    assert details["row_count"] == 30
    assert details["filters"] == {"item_id": str(item_ids[0])}


def test_inventory_export_returns_csv_columns_and_rows(client, users, login):
    _seed_items_and_transactions(users["admin"]["id"], total_transactions=3)
    _login_as(login, users, "admin")

    response = client.get("/reports/export")

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "inventory_export.csv" in response.headers["Content-Disposition"]

    rows = _read_csv(response)
    assert rows[0] == INVENTORY_HEADER
    assert len(rows) == 3
    assert {row[0] for row in rows[1:]} == {"EXP-A", "EXP-B"}
    assert {row[4] for row in rows[1:]} == {"Export Vendor"}

    audit = _latest_audit_log("inventory_csv_exported")
    assert audit["actor_user_id"] == users["admin"]["id"]
    assert audit["actor_email_snapshot"] == users["admin"]["email"]
    assert audit["actor_role_snapshot"] == "administrator"
    assert audit["target_type"] == "inventory"
    details = json.loads(audit["details_json"])
    assert details["row_count"] == 2
    assert details["path"] == "/reports/export"


def test_export_routes_redirect_to_login_when_unauthenticated(client, users):
    for path in ("/transactions/export", "/reports/export"):
        response = client.get(path)
        assert response.status_code == 302, path
        assert "/login" in _location(response), path


def test_student_cannot_export_transactions_csv(client, users, login):
    _seed_items_and_transactions(users["student"]["id"], total_transactions=2)
    _login_as(login, users, "student")

    response = client.get("/transactions/export")

    assert response.status_code == 302
    assert "/dashboard" in _location(response)
