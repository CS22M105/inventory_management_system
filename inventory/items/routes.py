"""Item browsing, editing, QR, and label routes."""

import io

from flask import Blueprint, Response, abort, redirect, render_template, request, url_for
import psycopg2
import qrcode

from app import (
    APP_BASE_URL,
    generate_next_item_barcode,
    get_db,
    get_item_form_data,
    require_item_manager,
    require_login,
)


bp = Blueprint("items", __name__)


@bp.route("/items")
def items():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    db = get_db()
    inventory_items = db.execute(
        """
        SELECT id, barcode, name, bin_location, room, company, quantity, minimum_quantity
        FROM items
        ORDER BY name
        """
    ).fetchall()

    return render_template("items.html", items=inventory_items)


@bp.route("/items/low-stock")
def low_stock_items():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    db = get_db()
    inventory_items = db.execute(
        """
        SELECT id, barcode, name, bin_location, room, company, quantity, minimum_quantity
        FROM items
        WHERE quantity <= minimum_quantity
        ORDER BY quantity ASC, name
        """
    ).fetchall()

    return render_template("low_stock_items.html", items=inventory_items)


@bp.route("/items/<barcode>")
def item_detail(barcode):
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    db = get_db()
    item = db.execute(
        """
        SELECT
            id,
            barcode,
            name,
            bin_location,
            room,
            company,
            quantity,
            minimum_quantity,
            location,
            expiration_date,
            notes
        FROM items
        WHERE barcode = %s
        """,
        (barcode,),
    ).fetchone()

    if item is None:
        abort(404, description="Not recognized")

    return render_template("item_detail.html", item=item)


@bp.route("/items/<barcode>/qr.png")
def item_qr_png(barcode):
    login_redirect = require_item_manager()

    if login_redirect is not None:
        return login_redirect

    db = get_db()
    item = db.execute(
        "SELECT id FROM items WHERE barcode = %s",
        (barcode,),
    ).fetchone()

    if item is None:
        abort(404, description="Not recognized")

    base_url = APP_BASE_URL or request.host_url.rstrip("/")
    stock_url = f"{base_url}/items/{barcode}/stock"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(stock_url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    return Response(buffer.getvalue(), mimetype="image/png")


@bp.route("/items/<barcode>/label")
def item_label(barcode):
    login_redirect = require_item_manager()

    if login_redirect is not None:
        return login_redirect

    db = get_db()
    item = db.execute(
        """
        SELECT barcode, name, room, bin_location, company, expiration_date
        FROM items
        WHERE barcode = %s
        """,
        (barcode,),
    ).fetchone()

    if item is None:
        abort(404, description="Not recognized")

    return render_template("item_label.html", item=item)


@bp.route("/items/new", methods=["GET", "POST"])
def item_new():
    manager_redirect = require_item_manager()

    if manager_redirect is not None:
        return manager_redirect

    if request.method == "POST":
        item_data, error = get_item_form_data(require_barcode=False)

        if error:
            return render_template("item_new.html", error=error, item=item_data), 400

        db = get_db()

        if not item_data["barcode"]:
            item_data["barcode"] = generate_next_item_barcode(db)

        try:
            db.execute(
                """
                INSERT INTO items (
                    barcode, name, bin_location, room, company,
                    quantity, minimum_quantity, location, expiration_date, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    item_data["barcode"],
                    item_data["name"],
                    item_data["bin_location"],
                    item_data["room"],
                    item_data["company"],
                    item_data["quantity"],
                    item_data["minimum_quantity"],
                    item_data["location"],
                    item_data["expiration_date"],
                    item_data["notes"],
                ),
            )
            db.commit()
        except psycopg2.IntegrityError:
            db.rollback()
            return render_template(
                "item_new.html",
                error="An item with this barcode already exists.",
                item=item_data,
            ), 400

        return redirect(url_for("items.items"))

    return render_template("item_new.html", item={})


@bp.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
def item_edit(item_id):
    manager_redirect = require_item_manager()

    if manager_redirect is not None:
        return manager_redirect

    db = get_db()
    item = db.execute(
        """
        SELECT
            id,
            barcode,
            name,
            bin_location,
            room,
            company,
            quantity,
            minimum_quantity,
            location,
            expiration_date,
            notes
        FROM items
        WHERE id = %s
        """,
        (item_id,),
    ).fetchone()

    if item is None:
        abort(404)

    if request.method == "POST":
        item_data, error = get_item_form_data()

        if error:
            item_data["id"] = item_id
            return render_template("item_edit.html", error=error, item=item_data), 400

        try:
            db.execute(
                """
                UPDATE items
                SET
                    barcode = %s,
                    name = %s,
                    bin_location = %s,
                    room = %s,
                    company = %s,
                    quantity = %s,
                    minimum_quantity = %s,
                    location = %s,
                    expiration_date = %s,
                    notes = %s
                WHERE id = %s
                """,
                (
                    item_data["barcode"],
                    item_data["name"],
                    item_data["bin_location"],
                    item_data["room"],
                    item_data["company"],
                    item_data["quantity"],
                    item_data["minimum_quantity"],
                    item_data["location"],
                    item_data["expiration_date"],
                    item_data["notes"],
                    item_id,
                ),
            )
            db.commit()
        except psycopg2.IntegrityError:
            db.rollback()
            item_data["id"] = item_id
            return render_template(
                "item_edit.html",
                error="An item with this barcode already exists.",
                item=item_data,
            ), 400

        return redirect(url_for("items.items"))

    return render_template("item_edit.html", item=item)
