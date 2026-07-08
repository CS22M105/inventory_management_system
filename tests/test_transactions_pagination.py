"""Volume / pagination verification for /transactions (Substep H3).

Seeds a few thousand transactions into the shared throwaway test DB, then checks:
- pagination math at the edges (first/last/out-of-range/empty),
- that filters combine with paging and preserve across pages,
- that the paginated query uses the composite index (no full seq scan + sort),
- that a page load stays fast on the seeded volume.

The test DB is built from schema.sql (which now mirrors migration 0004's
indexes), so EXPLAIN sees the same indexes production gets from Alembic.
"""

import time

import pytest

import app as app_module

PAGE_SIZE = 50            # matches TRANSACTIONS_PAGE_SIZE default
TOTAL = 5000
N_USERS = 6               # 1 admin + 5 students -> ids 1..6
N_ITEMS = 20              # ids 1..20
ADMIN_EMAIL = "admin@vol.edu"
ADMIN_PASSWORD = "Password123"


def _data_rows(html):
    # Number of <tr> rows in the rendered table, minus the header row.
    return max(0, html.count("</tr>") - 1)


@pytest.fixture(scope="module", autouse=True)
def _seed_volume():
    with app_module.app.app_context():
        db = app_module.get_db()
        db.execute("TRUNCATE transactions, items, users RESTART IDENTITY CASCADE")

        db.execute(
            "INSERT INTO users (email, name, role, is_active, password_hash) "
            "VALUES (%s, %s, 'administrator', TRUE, %s)",
            (ADMIN_EMAIL, "Vol Admin", app_module.hash_password(ADMIN_PASSWORD)),
        )
        for i in range(1, N_USERS):
            db.execute(
                "INSERT INTO users (email, name, role) VALUES (%s, %s, 'student')",
                (f"u{i}@vol.edu", f"User {i}"),
            )
        for i in range(1, N_ITEMS + 1):
            db.execute(
                "INSERT INTO items (barcode, name, bin_location, room) "
                "VALUES (%s, %s, 'A', '101')",
                (f"V{i:04d}", f"VItem {i}"),
            )

        # Bulk-load transactions with generate_series (fast, one round trip).
        db.execute(
            """
            INSERT INTO transactions
                (user_id, item_id, transaction_type, quantity,
                 transaction_date, transaction_time)
            SELECT
                1 + (g %% %s),
                1 + (g %% %s),
                CASE WHEN g %% 2 = 0 THEN 'add' ELSE 'remove' END,
                1 + (g %% 5),
                DATE '2023-01-01' + (g %% 700),
                TIME '08:00:00' + ((g %% 3600) * INTERVAL '1 second')
            FROM generate_series(1, %s) g
            """,
            (N_USERS, N_ITEMS, TOTAL),
        )
        db.execute("ANALYZE transactions")
        db.execute("ANALYZE items")
        db.commit()
    yield


@pytest.fixture()
def admin_client(client, login):
    assert login(ADMIN_EMAIL, ADMIN_PASSWORD).status_code == 302
    return client


def test_first_page(admin_client):
    html = admin_client.get("/transactions").get_data(as_text=True)
    assert "Page 1 of 100" in html          # 5000 / 50 = 100 pages
    assert _data_rows(html) == PAGE_SIZE
    assert f"{TOTAL} transactions" in html
    # First page: Previous is disabled, Next is a live link.
    assert 'aria-disabled="true">&larr; Previous' in html
    assert "Next &rarr;" in html


def test_last_page_full(admin_client):
    html = admin_client.get("/transactions?page=100").get_data(as_text=True)
    assert "Page 100 of 100" in html
    assert _data_rows(html) == PAGE_SIZE     # 5000 divides evenly by 50
    assert 'aria-disabled="true">Next &rarr;' in html


def test_out_of_range_page_clamps_to_last(admin_client):
    html = admin_client.get("/transactions?page=99999").get_data(as_text=True)
    assert "Page 100 of 100" in html


def test_non_numeric_or_low_page_clamps_to_first(admin_client):
    for bad in ("0", "-5", "abc"):
        html = admin_client.get(f"/transactions?page={bad}").get_data(as_text=True)
        assert "Page 1 of 100" in html


def test_partial_last_page(admin_client):
    # user_id = 1 (the admin) gets rows where g % N_USERS == 0 -> 833 of 5000.
    # 833 / 50 = 17 pages; last page holds 833 - 16*50 = 33 rows.
    expected_total = TOTAL // N_USERS
    expected_pages = (expected_total + PAGE_SIZE - 1) // PAGE_SIZE
    last_rows = expected_total - (expected_pages - 1) * PAGE_SIZE

    first = admin_client.get("/transactions?user_id=1").get_data(as_text=True)
    assert f"Page 1 of {expected_pages}" in first
    assert f"{expected_total} transactions" in first

    last = admin_client.get(
        f"/transactions?user_id=1&page={expected_pages}"
    ).get_data(as_text=True)
    assert f"Page {expected_pages} of {expected_pages}" in last
    assert _data_rows(last) == last_rows
    # Filter is preserved in the page links.
    assert "user_id=1" in last


def test_empty_result(admin_client):
    # A filter that matches nothing (item id beyond what we seeded).
    html = admin_client.get("/transactions?item_id=999999").get_data(as_text=True)
    assert "No transactions match the current filters." in html
    assert _data_rows(html) == 0
    # No pagination nav when there are zero results.
    assert "pagination-status" not in html


def test_export_is_unpaginated(admin_client):
    body = admin_client.get("/transactions/export").get_data(as_text=True)
    lines = [ln for ln in body.splitlines() if ln.strip()]
    assert len(lines) - 1 == TOTAL           # header + every matching row


def test_paginated_query_uses_composite_index():
    explain_sql = (
        "EXPLAIN (ANALYZE, COSTS OFF) "
        "SELECT transactions.id "
        "FROM transactions "
        "JOIN items ON items.id = transactions.item_id "
        "JOIN users ON users.id = transactions.user_id "
        "ORDER BY transactions.transaction_date DESC, "
        "transactions.transaction_time DESC, transactions.id DESC "
        "LIMIT %s OFFSET %s"
    )
    with app_module.app.app_context():
        db = app_module.get_db()
        rows = db.execute(explain_sql, (PAGE_SIZE, 0)).fetchall()
    plan = "\n".join(r["QUERY PLAN"] for r in rows)

    assert "ix_transactions_date_time_id" in plan, plan
    # The index provides order, so there must be no explicit sort of the table.
    assert "Sort Method" not in plan, plan
    assert "Seq Scan on transactions" not in plan, plan


def test_page_load_is_fast(admin_client):
    start = time.perf_counter()
    resp = admin_client.get("/transactions?page=50")
    elapsed = time.perf_counter() - start
    assert resp.status_code == 200
    # Generous ceiling to avoid CI flakiness; real time is a few ms.
    assert elapsed < 2.0, f"page load took {elapsed:.3f}s"
