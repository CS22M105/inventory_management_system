"""Transaction history and export routes."""

import csv
import io

from flask import Blueprint, Response, render_template, request, url_for

from inventory.core import (
    TRANSACTIONS_PAGE_SIZE,
    count_transaction_rows,
    get_db,
    get_transaction_filter_options,
    get_transaction_filters,
    get_transaction_rows,
    log_audit_event,
    require_login,
)


bp = Blueprint("transactions", __name__)


@bp.route("/transactions")
def transactions():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    db = get_db()

    filters = get_transaction_filters()
    items, users, lab_instructors, topics = get_transaction_filter_options(db)

    export_params = {key: value for key, value in filters.items() if value}

    total = count_transaction_rows(db, filters)
    page_size = TRANSACTIONS_PAGE_SIZE
    total_pages = max(1, (total + page_size - 1) // page_size)

    try:
        page = int(request.args.get("page", "1"))
    except ValueError:
        page = 1
    page = max(1, min(page, total_pages))

    offset = (page - 1) * page_size
    transaction_rows = get_transaction_rows(
        db, filters, limit=page_size, offset=offset
    )

    prev_url = (
        url_for("transactions.transactions", page=page - 1, **export_params)
        if page > 1
        else None
    )
    next_url = (
        url_for("transactions.transactions", page=page + 1, **export_params)
        if page < total_pages
        else None
    )

    return render_template(
        "transactions.html",
        transactions=transaction_rows,
        filters=filters,
        items=items,
        users=users,
        lab_instructors=lab_instructors,
        topics=topics,
        export_url=url_for("transactions.export_transactions", **export_params),
        page=page,
        total_pages=total_pages,
        total=total,
        page_size=page_size,
        has_prev=page > 1,
        has_next=page < total_pages,
        prev_url=prev_url,
        next_url=next_url,
    )


@bp.route("/transactions/export")
def export_transactions():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    db = get_db()
    filters = get_transaction_filters()
    transaction_rows = get_transaction_rows(db, filters)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
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
    )

    for transaction in transaction_rows:
        writer.writerow(
            [
                transaction["transaction_date"],
                transaction["transaction_time"],
                transaction["transaction_type"],
                transaction["item_name"],
                transaction["barcode"],
                transaction["quantity"],
                transaction["lab_instructor"],
                transaction["topic_of_day"],
                transaction["user_name"],
                transaction["notes"],
            ]
        )

    active_filters = {key: value for key, value in filters.items() if value}
    log_audit_event(
        db,
        "transactions_csv_exported",
        target_type="transactions",
        details={
            "row_count": len(transaction_rows),
            "filters": active_filters,
            "path": request.path,
        },
    )
    db.commit()

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=transaction_history_export.csv"},
    )
