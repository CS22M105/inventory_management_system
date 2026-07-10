"""Home, dashboard, and health-check routes."""

from flask import Blueprint, jsonify, redirect, render_template, url_for

import inventory.core as app_module


bp = Blueprint("dashboard", __name__)


@bp.route("/")
def home():
    return redirect(url_for("auth.login"))


@bp.route("/health")
def health():
    try:
        app_module.get_db().execute("SELECT 1").fetchone()
    except Exception:
        return jsonify({"status": "error", "database": "error"}), 503

    return jsonify({"status": "ok", "database": "ok"})


@bp.route("/dashboard")
def dashboard():
    login_redirect = app_module.require_login()

    if login_redirect is not None:
        return login_redirect

    db = app_module.get_db()
    total_items = db.execute("SELECT COUNT(*) AS total FROM items").fetchone()["total"]
    low_stock_items = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM items
        WHERE quantity <= minimum_quantity
        """
    ).fetchone()["total"]
    total_transactions = db.execute("SELECT COUNT(*) AS total FROM transactions").fetchone()["total"]
    recent_transactions = db.execute(
        """
        SELECT
            transactions.transaction_type,
            transactions.quantity,
            TO_CHAR(transactions.transaction_date, 'YYYY-MM-DD') AS transaction_date,
            TO_CHAR(transactions.transaction_time, 'HH24:MI:SS') AS transaction_time,
            transactions.lab_instructor,
            transactions.topic_of_day,
            items.name AS item_name,
            users.name AS user_name
        FROM transactions
        JOIN items ON items.id = transactions.item_id
        JOIN users ON users.id = transactions.user_id
        ORDER BY transactions.transaction_date DESC, transactions.transaction_time DESC, transactions.id DESC
        LIMIT 5
        """
    ).fetchall()

    return render_template(
        "dashboard.html",
        total_items=total_items,
        low_stock_items=low_stock_items,
        total_transactions=total_transactions,
        recent_transactions=recent_transactions,
    )
