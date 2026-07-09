"""Stock add/remove regression tests for the scan and QR stock flows.

These exercise process_stock_transaction() through the HTTP routes, not by
calling it directly. Both entry points are covered:
- POST /scan, where the barcode comes from the form body.
- POST /items/<barcode>/stock, where the barcode comes from the URL.
"""

import datetime

import pytest

import app as app_module


BARCODE = "STOCK-001"


def _login_student(login, users):
    response = login(users["student"]["email"], users["student"]["password"])
    assert response.status_code == 302


def _seed_item(quantity=5):
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
                BARCODE,
                "Stock Test Item",
                "A1",
                "101",
                "Test Vendor",
                quantity,
                1,
                "Shelf",
                "Seed item",
            ),
        ).fetchone()
        db.commit()
        return row["id"]


def _valid_stock_form(action="add", quantity="2", barcode=BARCODE):
    return {
        "barcode": barcode,
        "transaction_type": action,
        "quantity": quantity,
        "lab_instructor": "Dr. Avery",
        "topic_of_day": "Medication Safety",
        "notes": "Used during simulation lab.",
    }


def _post_stock(client, entry_point, barcode=BARCODE, data=None):
    form = _valid_stock_form(barcode=barcode)
    if data:
        form.update(data)

    if entry_point == "scan":
        return client.post("/scan", data=form)

    # The item stock route identifies the item from the URL, not the form.
    form.pop("barcode", None)
    return client.post(f"/items/{barcode}/stock", data=form)


def _item_quantity():
    with app_module.app.app_context():
        db = app_module.get_db()
        row = db.execute(
            "SELECT quantity FROM items WHERE barcode = %s", (BARCODE,)
        ).fetchone()
        return row["quantity"]


def _transactions():
    with app_module.app.app_context():
        db = app_module.get_db()
        return db.execute(
            """
            SELECT
                transactions.user_id,
                transactions.transaction_type,
                transactions.quantity,
                transactions.transaction_date,
                transactions.transaction_time,
                transactions.lab_instructor,
                transactions.topic_of_day,
                transactions.notes,
                items.barcode
            FROM transactions
            JOIN items ON items.id = transactions.item_id
            ORDER BY transactions.id
            """
        ).fetchall()


@pytest.mark.parametrize("entry_point", ["scan", "item_stock"])
def test_add_stock_increases_quantity_and_creates_transaction(
    client, users, login, entry_point
):
    _login_student(login, users)
    _seed_item(quantity=5)

    response = _post_stock(client, entry_point, data={"transaction_type": "add"})

    assert response.status_code == 200
    assert _item_quantity() == 7

    rows = _transactions()
    assert len(rows) == 1
    assert rows[0]["user_id"] == users["student"]["id"]
    assert rows[0]["transaction_type"] == "add"
    assert rows[0]["quantity"] == 2
    assert rows[0]["barcode"] == BARCODE


@pytest.mark.parametrize("entry_point", ["scan", "item_stock"])
def test_remove_stock_decreases_quantity_and_creates_transaction(
    client, users, login, entry_point
):
    _login_student(login, users)
    _seed_item(quantity=5)

    response = _post_stock(client, entry_point, data={"transaction_type": "remove"})

    assert response.status_code == 200
    assert _item_quantity() == 3

    rows = _transactions()
    assert len(rows) == 1
    assert rows[0]["transaction_type"] == "remove"
    assert rows[0]["quantity"] == 2


@pytest.mark.parametrize("entry_point", ["scan", "item_stock"])
def test_cannot_remove_more_than_available(client, users, login, entry_point):
    _login_student(login, users)
    _seed_item(quantity=5)

    response = _post_stock(
        client,
        entry_point,
        data={"transaction_type": "remove", "quantity": "6"},
    )

    assert response.status_code == 400
    assert _item_quantity() == 5
    assert _transactions() == []


@pytest.mark.parametrize("entry_point", ["scan", "item_stock"])
@pytest.mark.parametrize(
    "field",
    ["lab_instructor", "topic_of_day", "notes"],
)
def test_required_transaction_context_rejected(
    client, users, login, entry_point, field
):
    _login_student(login, users)
    _seed_item(quantity=5)

    response = _post_stock(client, entry_point, data={field: ""})

    assert response.status_code == 400
    assert _item_quantity() == 5
    assert _transactions() == []


def test_unknown_barcode_returns_404_on_scan(client, users, login):
    _login_student(login, users)

    response = _post_stock(client, "scan", barcode="UNKNOWN")

    assert response.status_code == 404
    assert _transactions() == []


def test_unknown_barcode_returns_404_on_item_stock(client, users, login):
    _login_student(login, users)

    response = _post_stock(client, "item_stock", barcode="UNKNOWN")

    assert response.status_code == 404
    assert _transactions() == []


@pytest.mark.parametrize("entry_point", ["scan", "item_stock"])
def test_transaction_row_records_full_context(client, users, login, entry_point):
    _login_student(login, users)
    _seed_item(quantity=5)

    response = _post_stock(
        client,
        entry_point,
        data={
            "transaction_type": "add",
            "quantity": "4",
            "lab_instructor": "Professor Kim",
            "topic_of_day": "Wound Care",
            "notes": "Restocked after skills lab.",
        },
    )

    assert response.status_code == 200

    rows = _transactions()
    assert len(rows) == 1
    row = rows[0]
    assert row["user_id"] == users["student"]["id"]
    assert row["transaction_type"] == "add"
    assert row["quantity"] == 4
    assert isinstance(row["transaction_date"], datetime.date)
    assert isinstance(row["transaction_time"], datetime.time)
    assert row["lab_instructor"] == "Professor Kim"
    assert row["topic_of_day"] == "Wound Care"
    assert row["notes"] == "Restocked after skills lab."
