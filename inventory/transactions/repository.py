"""Transaction query helpers."""


def build_transaction_filter_clause(filters):
    conditions = []
    params = []

    if filters["date_from"]:
        conditions.append("transactions.transaction_date >= %s")
        params.append(filters["date_from"])

    if filters["date_to"]:
        conditions.append("transactions.transaction_date <= %s")
        params.append(filters["date_to"])

    if filters["item_id"].isdigit():
        conditions.append("transactions.item_id = %s")
        params.append(int(filters["item_id"]))

    if filters["user_id"].isdigit():
        conditions.append("transactions.user_id = %s")
        params.append(int(filters["user_id"]))

    if filters["lab_instructor"]:
        conditions.append("transactions.lab_instructor = %s")
        params.append(filters["lab_instructor"])

    if filters["topic_of_day"]:
        conditions.append("transactions.topic_of_day = %s")
        params.append(filters["topic_of_day"])

    if filters["transaction_type"] in {"add", "remove"}:
        conditions.append("transactions.transaction_type = %s")
        params.append(filters["transaction_type"])

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    return where_clause, params


def count_transaction_rows(db, filters):
    where_clause, params = build_transaction_filter_clause(filters)

    return db.execute(
        "SELECT COUNT(*) AS total FROM transactions {where_clause}".format(
            where_clause=where_clause
        ),
        params,
    ).fetchone()["total"]


def get_transaction_rows(db, filters, limit=None, offset=None):
    where_clause, params = build_transaction_filter_clause(filters)

    pagination = ""
    if limit is not None:
        pagination = "LIMIT %s OFFSET %s"
        params = params + [limit, offset or 0]

    return db.execute(
        """
        SELECT
            transactions.id,
            transactions.transaction_type,
            transactions.quantity,
            TO_CHAR(transactions.transaction_date, 'YYYY-MM-DD') AS transaction_date,
            TO_CHAR(transactions.transaction_time, 'HH24:MI:SS') AS transaction_time,
            transactions.lab_instructor,
            transactions.topic_of_day,
            transactions.notes,
            items.name AS item_name,
            items.barcode,
            users.name AS user_name
        FROM transactions
        JOIN items ON items.id = transactions.item_id
        JOIN users ON users.id = transactions.user_id
        {where_clause}
        ORDER BY transactions.transaction_date DESC, transactions.transaction_time DESC, transactions.id DESC
        {pagination}
        """.format(where_clause=where_clause, pagination=pagination),
        params,
    ).fetchall()
