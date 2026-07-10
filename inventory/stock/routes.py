"""Stock scan and per-item stock routes."""

from flask import Blueprint, abort, render_template, request

from app import (
    RATELIMIT_STOCK,
    get_db,
    get_stock_item,
    limiter,
    process_stock_transaction,
    require_login,
)


bp = Blueprint("stock", __name__)


@bp.route("/scan", methods=["GET", "POST"])
@limiter.limit(RATELIMIT_STOCK)
def scan():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    if request.method == "POST":
        message, error, status = process_stock_transaction(
            request.form.get("barcode", "").strip(),
            request.form,
        )

        if error:
            return render_template("scan.html", error=error), status

        return render_template("scan.html", message=message)

    return render_template("scan.html")


@bp.route("/items/<barcode>/stock", methods=["GET", "POST"])
@limiter.limit(RATELIMIT_STOCK)
def item_stock(barcode):
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    db = get_db()
    item = get_stock_item(db, barcode)

    if item is None:
        abort(404, description="Not recognized")

    if request.method == "POST":
        message, error, status = process_stock_transaction(barcode, request.form)
        item = get_stock_item(db, barcode)

        if error:
            return render_template("item_stock.html", item=item, error=error), status

        return render_template("item_stock.html", item=item, message=message)

    return render_template("item_stock.html", item=item)
