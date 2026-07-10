"""Inventory report export routes."""

import csv
import io

from flask import Blueprint, Response

from app import get_db, require_admin


bp = Blueprint("reports", __name__)


@bp.route("/reports/export")
def export_inventory():
    admin_redirect = require_admin()

    if admin_redirect is not None:
        return admin_redirect

    db = get_db()
    inventory_items = db.execute(
        """
        SELECT
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
        ORDER BY name
        """
    ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
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
    )

    for item in inventory_items:
        writer.writerow(
            [
                item["barcode"],
                item["name"],
                item["bin_location"],
                item["room"],
                item["company"],
                item["quantity"],
                item["minimum_quantity"],
                item["location"],
                item["expiration_date"],
                item["notes"],
            ]
        )

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=inventory_export.csv"},
    )
