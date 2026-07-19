"""Item browsing, editing, QR, and label routes."""

import io

from flask import Blueprint, Response, abort, redirect, render_template, request, url_for
from PIL import Image, ImageDraw, ImageFont
import psycopg2
import qrcode

from inventory.core import (
    APP_BASE_URL,
    generate_next_item_barcode,
    get_db,
    get_item_form_data,
    log_audit_event,
    require_item_manager,
    require_login,
)


bp = Blueprint("items", __name__)


def _stock_url(barcode):
    base_url = APP_BASE_URL or request.host_url.rstrip("/")
    return f"{base_url}/items/{barcode}/stock"


def _make_qr_image(barcode, box_size=10, border=4):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(_stock_url(barcode))
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def _png_response(image, filename=None):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    headers = {}
    if filename:
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return Response(buffer.getvalue(), mimetype="image/png", headers=headers)


def _bounded_int(value, default, minimum, maximum):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(number, maximum))


def _make_qr_label_image(item):
    qr_image = _make_qr_image(item["barcode"], box_size=12, border=2)
    qr_image = qr_image.resize((213, 213), Image.Resampling.NEAREST)

    width = 288
    height = 258
    image = Image.new("RGB", (width, height), "white")
    image.paste(qr_image, ((width - qr_image.width) // 2, 4))

    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    label = item["barcode"]
    text_box = draw.textbbox((0, 0), label, font=font)
    text_width = text_box[2] - text_box[0]
    draw.text(
        ((width - text_width) // 2, 224),
        label,
        fill="black",
        font=font,
    )
    return image


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

    filename = None
    if request.args.get("download") == "1":
        filename = f"{barcode}-qr.png"

    return _png_response(_make_qr_image(barcode), filename=filename)


@bp.route("/items/<barcode>/qr-label.png")
def item_qr_label_png(barcode):
    login_redirect = require_item_manager()

    if login_redirect is not None:
        return login_redirect

    db = get_db()
    item = db.execute(
        """
        SELECT id, barcode, name
        FROM items
        WHERE barcode = %s
        """,
        (barcode,),
    ).fetchone()

    if item is None:
        abort(404, description="Not recognized")

    log_audit_event(
        db,
        "qr_label_viewed",
        target_type="item",
        target_id=item["id"],
        target_label=f"{item['name']} ({item['barcode']})",
        details={"barcode": item["barcode"], "format": "png_download"},
    )
    db.commit()

    return _png_response(
        _make_qr_label_image(item),
        filename=f"{barcode}-qr-label.png",
    )


@bp.route("/items/<barcode>/label")
def item_label(barcode):
    login_redirect = require_item_manager()

    if login_redirect is not None:
        return login_redirect

    db = get_db()
    item = db.execute(
        """
        SELECT id, barcode, name, room, bin_location, company, expiration_date
        FROM items
        WHERE barcode = %s
        """,
        (barcode,),
    ).fetchone()

    if item is None:
        abort(404, description="Not recognized")

    log_audit_event(
        db,
        "qr_label_viewed",
        target_type="item",
        target_id=item["id"],
        target_label=f"{item['name']} ({item['barcode']})",
        details={"barcode": item["barcode"]},
    )
    db.commit()

    return render_template("item_label.html", item=item)


@bp.route("/items/<barcode>/qr-label")
def item_qr_label(barcode):
    login_redirect = require_item_manager()

    if login_redirect is not None:
        return login_redirect

    db = get_db()
    item = db.execute(
        """
        SELECT id, barcode, name
        FROM items
        WHERE barcode = %s
        """,
        (barcode,),
    ).fetchone()

    if item is None:
        abort(404, description="Not recognized")

    log_audit_event(
        db,
        "qr_label_viewed",
        target_type="item",
        target_id=item["id"],
        target_label=f"{item['name']} ({item['barcode']})",
        details={"barcode": item["barcode"], "format": "qr_only"},
    )
    db.commit()

    return render_template("item_qr_label.html", item=item)


@bp.route("/items/<barcode>/label-sheet")
def item_label_sheet(barcode):
    login_redirect = require_item_manager()

    if login_redirect is not None:
        return login_redirect

    db = get_db()
    item = db.execute(
        """
        SELECT id, barcode, name
        FROM items
        WHERE barcode = %s
        """,
        (barcode,),
    ).fetchone()

    if item is None:
        abort(404, description="Not recognized")

    copies = _bounded_int(request.args.get("copies"), 20, 1, 100)
    qr_size_mm = _bounded_int(request.args.get("qr_size_mm"), 18, 10, 40)
    spacing_mm = _bounded_int(request.args.get("spacing_mm"), 3, 0, 20)
    label_text = request.args.get("label_text", item["barcode"]).strip()
    if not label_text:
        label_text = item["barcode"]

    log_audit_event(
        db,
        "qr_label_viewed",
        target_type="item",
        target_id=item["id"],
        target_label=f"{item['name']} ({item['barcode']})",
        details={
            "barcode": item["barcode"],
            "format": "label_sheet",
            "copies": copies,
        },
    )
    db.commit()

    return render_template(
        "item_label_sheet.html",
        item=item,
        copies=copies,
        qr_size_mm=qr_size_mm,
        spacing_mm=spacing_mm,
        label_text=label_text,
    )


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
            new_item = db.execute(
                """
                INSERT INTO items (
                    barcode, name, bin_location, room, company,
                    quantity, minimum_quantity, location, expiration_date, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
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
            ).fetchone()
            log_audit_event(
                db,
                "item_created",
                target_type="item",
                target_id=new_item["id"],
                target_label=f"{item_data['name']} ({item_data['barcode']})",
                details={
                    "barcode": item_data["barcode"],
                    "room": item_data["room"],
                    "bin_location": item_data["bin_location"],
                    "quantity": item_data["quantity"],
                    "minimum_quantity": item_data["minimum_quantity"],
                },
            )
            db.commit()
        except psycopg2.IntegrityError:
            db.rollback()
            return render_template(
                "item_new.html",
                error="An item with this code already exists.",
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
            changed_fields = []
            for field in (
                "barcode",
                "name",
                "bin_location",
                "room",
                "company",
                "quantity",
                "minimum_quantity",
                "location",
                "expiration_date",
            ):
                if item[field] != item_data[field]:
                    changed_fields.append(field)
            if (item["notes"] or "") != (item_data["notes"] or ""):
                changed_fields.append("notes")

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
            log_audit_event(
                db,
                "item_updated",
                target_type="item",
                target_id=item_id,
                target_label=f"{item_data['name']} ({item_data['barcode']})",
                details={"changed_fields": changed_fields},
            )
            db.commit()
        except psycopg2.IntegrityError:
            db.rollback()
            item_data["id"] = item_id
            return render_template(
                "item_edit.html",
                error="An item with this code already exists.",
                item=item_data,
            ), 400

        return redirect(url_for("items.items"))

    return render_template("item_edit.html", item=item)
