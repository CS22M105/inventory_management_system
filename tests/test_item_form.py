"""Item add/edit/detail/label regression tests (Substep G3).

These guard the DATE-typed expiration_date work (G1/G2): the add and edit forms,
the item detail page, and the printable label page must all behave correctly with
real dates and with NULL ("not set"), and the old '00/00/0000' sentinel must be
gone from both the DB and the rendered UI.

They use the shared throwaway test database and fixtures from conftest.py (same
pattern as the auth suite).
"""

import datetime

import app as app_module

BASE_ITEM = {
    "name": "Test Gauze",
    "bin_location": "A1",
    "room": "101",
    "company": "Acme",
    "location": "Shelf",
    "quantity": "5",
    "minimum_quantity": "1",
    "notes": "",
}


def _manager_login(login, users):
    resp = login(users["faculty"]["email"], users["faculty"]["password"])
    assert resp.status_code == 302


def _create_item(client, barcode, expiration_date):
    data = dict(BASE_ITEM)
    data["barcode"] = barcode
    data["expiration_date"] = expiration_date
    return client.post("/items/new", data=data)


def _fetch_expiration(barcode):
    with app_module.app.app_context():
        db = app_module.get_db()
        row = db.execute(
            "SELECT expiration_date FROM items WHERE barcode = %s", (barcode,)
        ).fetchone()
    return row["expiration_date"] if row else "MISSING"


def test_create_item_with_real_date(client, users, login):
    _manager_login(login, users)

    resp = _create_item(client, "ITM-DATE", "2025-12-31")
    assert resp.status_code == 302

    stored = _fetch_expiration("ITM-DATE")
    assert isinstance(stored, datetime.date)
    assert stored == datetime.date(2025, 12, 31)

    detail = client.get("/items/ITM-DATE")
    assert detail.status_code == 200
    assert b"2025-12-31" in detail.data

    label = client.get("/items/ITM-DATE/label")
    assert label.status_code == 200
    assert b"Exp:" in label.data
    assert b"2025-12-31" in label.data

    qr_only = client.get("/items/ITM-DATE/qr-label")
    assert qr_only.status_code == 200
    assert b"QR Code Only Label" in qr_only.data
    assert b"ITM-DATE" in qr_only.data
    assert b"Room:" not in qr_only.data
    assert b"Vendor:" not in qr_only.data
    assert b"Exp:" not in qr_only.data


def test_create_item_without_date_is_null(client, users, login):
    _manager_login(login, users)

    resp = _create_item(client, "ITM-NODATE", "")
    assert resp.status_code == 302

    assert _fetch_expiration("ITM-NODATE") is None

    detail = client.get("/items/ITM-NODATE")
    assert detail.status_code == 200
    assert b"Not set" in detail.data

    label = client.get("/items/ITM-NODATE/label")
    assert label.status_code == 200
    # The Exp line is hidden entirely when there is no date.
    assert b"Exp:" not in label.data


def test_unparseable_date_becomes_null(client, users, login):
    _manager_login(login, users)

    resp = _create_item(client, "ITM-JUNK", "not-a-date")
    assert resp.status_code == 302

    # Defensive parsing: junk is stored as NULL rather than rejected/crashing.
    assert _fetch_expiration("ITM-JUNK") is None


def test_edit_item_date_persists(client, users, login):
    _manager_login(login, users)

    assert _create_item(client, "ITM-EDIT", "").status_code == 302
    assert _fetch_expiration("ITM-EDIT") is None

    with app_module.app.app_context():
        db = app_module.get_db()
        item_id = db.execute(
            "SELECT id FROM items WHERE barcode = %s", ("ITM-EDIT",)
        ).fetchone()["id"]

    data = dict(BASE_ITEM)
    data["barcode"] = "ITM-EDIT"
    data["expiration_date"] = "2026-06-01"
    resp = client.post(f"/items/{item_id}/edit", data=data)
    assert resp.status_code == 302

    stored = _fetch_expiration("ITM-EDIT")
    assert stored == datetime.date(2026, 6, 1)


def test_sentinel_never_appears(client, users, login):
    _manager_login(login, users)

    _create_item(client, "ITM-A", "2025-01-15")
    _create_item(client, "ITM-B", "")

    pages = b""
    for barcode in ("ITM-A", "ITM-B"):
        pages += client.get(f"/items/{barcode}").data
        pages += client.get(f"/items/{barcode}/label").data
        pages += client.get(f"/items/{barcode}/qr-label").data
    assert b"00/00/0000" not in pages
