"""Route-level role/permission regression tests.

These complement test_auth.py by checking item, stock, reporting, DB-status, and
user-management edges through HTTP routes. The test users come from conftest.py;
no schema.sql demo IDs are used.
"""

import app as app_module


def _location(response):
    return response.headers.get("Location", "")


def _login_as(login, users, role):
    response = login(users[role]["email"], users[role]["password"])
    assert response.status_code == 302


def _seed_item(barcode="PERM-001", quantity=5):
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
                "Permission Test Item",
                "A1",
                "101",
                "Test Vendor",
                quantity,
                1,
                "Shelf",
                "Permission seed item",
            ),
        ).fetchone()
        db.commit()
        return row["id"], barcode


def _seed_user(role, email, active=True):
    with app_module.app.app_context():
        db = app_module.get_db()
        row = db.execute(
            """
            INSERT INTO users (email, name, role, is_active, password_hash)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                email,
                f"Seed {role.title()}",
                role,
                active,
                app_module.hash_password("Password123"),
            ),
        ).fetchone()
        db.commit()
        return row["id"]


def _user_row(user_id):
    with app_module.app.app_context():
        db = app_module.get_db()
        return db.execute(
            "SELECT id, role, is_active FROM users WHERE id = %s",
            (user_id,),
        ).fetchone()


def test_student_page_access_and_denials(client, users, login):
    item_id, barcode = _seed_item()
    _login_as(login, users, "student")

    allowed_paths = [
        "/items",
        f"/items/{barcode}",
        "/scan",
        f"/items/{barcode}/stock",
        "/transactions",
    ]
    for path in allowed_paths:
        response = client.get(path)
        assert response.status_code == 200, path

    blocked_paths = [
        ("/items/new", "/items"),
        (f"/items/{item_id}/edit", "/items"),
        ("/admin/users", "/dashboard"),
        ("/db-status", "/dashboard"),
        ("/transactions/export", "/dashboard"),
        ("/reports/export", "/dashboard"),
    ]
    for path, redirect_target in blocked_paths:
        response = client.get(path)
        assert response.status_code == 302, path
        assert redirect_target in _location(response), path


def test_faculty_item_management_and_system_admin_denial(client, users, login):
    item_id, barcode = _seed_item()
    _login_as(login, users, "faculty")

    allowed_paths = [
        "/items/new",
        f"/items/{item_id}/edit",
        "/admin/users",
        f"/items/{barcode}/label",
        f"/items/{barcode}/qr-label",
        f"/items/{barcode}/qr.png",
    ]
    for path in allowed_paths:
        response = client.get(path)
        assert response.status_code == 200, path

    response = client.get(f"/items/{barcode}/qr.png")
    assert response.mimetype == "image/png"

    response = client.get("/db-status")
    assert response.status_code == 302
    assert "/dashboard" in _location(response)

    transaction_export = client.get("/transactions/export")
    assert transaction_export.status_code == 200
    assert transaction_export.mimetype == "text/csv"


def test_administrator_can_access_system_status_and_inventory_export(
    client, users, login
):
    _seed_item()
    _login_as(login, users, "admin")

    status_response = client.get("/db-status")
    assert status_response.status_code == 200

    export_response = client.get("/reports/export")
    assert export_response.status_code == 200
    assert export_response.mimetype == "text/csv"


def test_faculty_cannot_deactivate_or_delete_faculty_account(client, users, login):
    other_faculty_id = _seed_user(
        "faculty",
        "other.faculty.permissions@test.edu",
        active=True,
    )
    _login_as(login, users, "faculty")

    deactivate_response = client.post(f"/admin/users/{other_faculty_id}/deactivate")
    assert deactivate_response.status_code == 302
    assert _user_row(other_faculty_id)["is_active"] is True

    with app_module.app.app_context():
        db = app_module.get_db()
        db.execute(
            "UPDATE users SET is_active = FALSE WHERE id = %s",
            (other_faculty_id,),
        )
        db.commit()

    delete_response = client.post(f"/admin/users/{other_faculty_id}/delete")
    assert delete_response.status_code == 302
    row = _user_row(other_faculty_id)
    assert row is not None
    assert row["role"] == "faculty"


def test_faculty_cannot_deactivate_or_delete_administrator_account(
    client, users, login
):
    admin_id = users["admin"]["id"]
    _login_as(login, users, "faculty")

    deactivate_response = client.post(f"/admin/users/{admin_id}/deactivate")
    assert deactivate_response.status_code == 302
    assert _user_row(admin_id)["is_active"] is True

    delete_response = client.post(f"/admin/users/{admin_id}/delete")
    assert delete_response.status_code == 302
    row = _user_row(admin_id)
    assert row is not None
    assert row["role"] == "administrator"
    assert row["is_active"] is True


def test_administrator_cannot_deactivate_or_delete_own_protected_account(
    client, users, login
):
    admin_id = users["admin"]["id"]
    _login_as(login, users, "admin")

    deactivate_response = client.post(f"/admin/users/{admin_id}/deactivate")
    assert deactivate_response.status_code == 302
    assert _user_row(admin_id)["is_active"] is True

    delete_response = client.post(f"/admin/users/{admin_id}/delete")
    assert delete_response.status_code == 302
    row = _user_row(admin_id)
    assert row is not None
    assert row["role"] == "administrator"
    assert row["is_active"] is True
