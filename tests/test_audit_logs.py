"""Admin audit trail regression tests for Step R3."""

import json
import re

import app as app_module


def _location(response):
    return response.headers.get("Location", "")


def _login_as(login, users, role):
    response = login(users[role]["email"], users[role]["password"])
    assert response.status_code == 302


def _audit_logs(action=None):
    with app_module.app.app_context():
        db = app_module.get_db()
        if action is None:
            return db.execute(
                "SELECT * FROM audit_logs ORDER BY created_at DESC, id DESC"
            ).fetchall()
        return db.execute(
            """
            SELECT *
            FROM audit_logs
            WHERE action = %s
            ORDER BY created_at DESC, id DESC
            """,
            (action,),
        ).fetchall()


def _latest_audit_log(action):
    rows = _audit_logs(action)
    assert rows, f"missing audit log for {action}"
    return rows[0]


def _seed_item(barcode="AUDIT-ITEM", quantity=5):
    with app_module.app.app_context():
        db = app_module.get_db()
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
                "Audit Test Item",
                "A1",
                "101",
                "Audit Vendor",
                quantity,
                1,
                "Shelf",
                "Seed item",
            ),
        ).fetchone()
        db.commit()
        return row["id"], barcode


def _seed_user(role="student", active=True):
    with app_module.app.app_context():
        db = app_module.get_db()
        row = db.execute(
            """
            INSERT INTO users (email, name, role, is_active, password_hash)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                f"audit.{role}.{active}@test.edu",
                f"Audit {role.title()}",
                role,
                active,
                app_module.hash_password("Password123"),
            ),
        ).fetchone()
        db.commit()
        return row["id"]


def _valid_item_form(**overrides):
    data = {
        "barcode": "AUDIT-NEW",
        "name": "Audit New Item",
        "bin_location": "B2",
        "room": "202",
        "company": "Audit Vendor",
        "quantity": "4",
        "minimum_quantity": "1",
        "location": "Shelf",
        "expiration_date": "",
        "notes": "Operational note",
    }
    data.update(overrides)
    return data


def _valid_stock_form(action="add", quantity="2"):
    return {
        "transaction_type": action,
        "quantity": quantity,
        "lab_instructor": "Dr. Audit",
        "topic_of_day": "Audit Lab",
        "notes": "Stock audit test.",
    }


def test_user_create_creates_audit_log(client, users, login, captured_emails):
    _login_as(login, users, "admin")

    response = client.post(
        "/admin/users/new",
        data={
            "institution_id": "AUDIT-S100",
            "email": "audit.created@test.edu",
            "name": "Audit Created",
            "role": "student",
            "department": "Nursing",
        },
    )

    assert response.status_code == 302
    audit = _latest_audit_log("user_created")
    assert audit["actor_user_id"] == users["admin"]["id"]
    assert audit["actor_email_snapshot"] == users["admin"]["email"]
    assert audit["actor_role_snapshot"] == "administrator"
    assert audit["target_type"] == "user"
    assert audit["target_label"] == "audit.created@test.edu"
    details = json.loads(audit["details_json"])
    assert details["created_role"] == "student"
    assert details["has_institution_id"] is True


def test_user_deactivate_and_delete_create_audit_logs(client, users, login):
    target_id = _seed_user("student", active=True)
    _login_as(login, users, "admin")

    response = client.post(f"/admin/users/{target_id}/deactivate")
    assert response.status_code == 302
    deactivated = _latest_audit_log("user_deactivated")
    assert deactivated["target_id"] == str(target_id)

    response = client.post(f"/admin/users/{target_id}/activate")
    assert response.status_code == 302
    activated = _latest_audit_log("user_activated")
    assert activated["target_id"] == str(target_id)

    response = client.post(f"/admin/users/{target_id}/deactivate")
    assert response.status_code == 302

    response = client.post(f"/admin/users/{target_id}/delete")
    assert response.status_code == 302
    deleted = _latest_audit_log("user_deleted")
    assert deleted["target_id"] == str(target_id)
    assert deleted["target_label"] == "audit.student.True@test.edu"


def test_item_edit_creates_audit_log(client, users, login):
    item_id, _barcode = _seed_item()
    _login_as(login, users, "faculty")

    response = client.post(
        f"/items/{item_id}/edit",
        data=_valid_item_form(
            barcode="AUDIT-ITEM-EDITED",
            name="Audit Item Edited",
            room="303",
        ),
    )

    assert response.status_code == 302
    audit = _latest_audit_log("item_updated")
    assert audit["actor_user_id"] == users["faculty"]["id"]
    assert audit["target_type"] == "item"
    assert audit["target_id"] == str(item_id)
    details = json.loads(audit["details_json"])
    assert "barcode" in details["changed_fields"]
    assert "name" in details["changed_fields"]
    assert "room" in details["changed_fields"]


def test_stock_action_creates_transaction_and_audit_log(client, users, login):
    _item_id, barcode = _seed_item(quantity=5)
    _login_as(login, users, "student")

    response = client.post(f"/items/{barcode}/stock", data=_valid_stock_form("add"))

    assert response.status_code == 200
    with app_module.app.app_context():
        db = app_module.get_db()
        transaction_count = db.execute(
            "SELECT COUNT(*) AS total FROM transactions"
        ).fetchone()["total"]
    assert transaction_count == 1

    audit = _latest_audit_log("stock_added")
    assert audit["actor_user_id"] == users["student"]["id"]
    assert audit["target_type"] == "item"
    assert audit["target_label"] == f"Audit Test Item ({barcode})"
    details = json.loads(audit["details_json"])
    assert details["quantity"] == 2
    assert details["new_quantity"] == 7


def test_csv_exports_create_audit_logs(client, users, login):
    _seed_item()
    _login_as(login, users, "admin")

    transaction_response = client.get("/transactions/export")
    inventory_response = client.get("/reports/export")

    assert transaction_response.status_code == 200
    assert inventory_response.status_code == 200
    assert _latest_audit_log("transactions_csv_exported")
    assert _latest_audit_log("inventory_csv_exported")


def test_audit_logs_view_is_system_admin_only(client, users, login):
    for role in ("student", "faculty"):
        _login_as(login, users, role)
        response = client.get("/admin/audit-logs")
        assert response.status_code == 302
        assert "/dashboard" in _location(response)
        client.post("/logout")

    _login_as(login, users, "admin")
    response = client.get("/admin/audit-logs")
    assert response.status_code == 200
    assert b"Audit Logs" in response.data


def test_set_password_cli_creates_audit_log(users):
    cli_runner = app_module.app.test_cli_runner()
    result = cli_runner.invoke(
        args=[
            "set-password",
            users["student"]["email"],
            "ChangedPass123",
        ]
    )

    assert result.exit_code == 0, result.output
    audit = _latest_audit_log("password_set_by_cli")
    assert audit["actor_email_snapshot"] == "cli"
    assert audit["actor_role_snapshot"] == "operator"
    assert audit["target_id"] == str(users["student"]["id"])
    assert audit["target_label"] == users["student"]["email"]
    assert "ChangedPass123" not in audit["details_json"]


def test_invite_resent_creates_audit_log(client, users, login, captured_emails):
    _login_as(login, users, "admin")
    response = client.post("/admin/users/new", data={
        "institution_id": "",
        "email": "audit.invite@test.edu",
        "name": "Audit Invite",
        "role": "student",
        "department": "Nursing",
    })
    assert response.status_code == 302
    token_match = re.search(r"/set-password/(\S+)", captured_emails[-1]["body"])
    assert token_match

    with app_module.app.app_context():
        db = app_module.get_db()
        user_id = db.execute(
            "SELECT id FROM users WHERE email = %s",
            ("audit.invite@test.edu",),
        ).fetchone()["id"]

    response = client.post(f"/admin/users/{user_id}/resend-invite")
    assert response.status_code == 302
    audit = _latest_audit_log("invite_resent")
    assert audit["target_id"] == str(user_id)
    assert audit["target_label"] == "audit.invite@test.edu"
