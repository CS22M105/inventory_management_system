from flask import Flask, Response, abort, g, redirect, render_template, request, session, url_for
import csv
import io
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import click
from pathlib import Path

# holds the parent path to the current script we are running.
BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/inventory_management_system")
ELEVATED_ROLES = {"administrator", "faculty"}
ELEVATED_LOGIN_MODES = {"admin", "faculty"}
SCHEMA = BASE_DIR / "schema.sql"

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-key-change-before-production"


class Database:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, params=None):
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return cursor

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()


def get_db():
    if "db" not in g: # g is for Global, it is a 
        # special object that Flask provides to store data during the 
        # request lifecycle.
        connection = psycopg2.connect(
            DATABASE_URL,
            connect_timeout=5,
            cursor_factory=RealDictCursor,
        )
        g.db = Database(connection)
        # This allows us to access columns by name.
    return g.db

def ensure_transaction_columns(db):
    db.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS transaction_date DATE")
    db.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS transaction_time TIME(0)")
    db.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS lab_instructor TEXT")
    db.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS topic_of_day TEXT")
    db.execute("ALTER TABLE transactions ALTER COLUMN transaction_date SET DEFAULT CURRENT_DATE")
    db.execute("ALTER TABLE transactions ALTER COLUMN transaction_time SET DEFAULT LOCALTIME(0)")
    db.execute(
        """
        UPDATE transactions
        SET transaction_date = created_at::date
        WHERE transaction_date IS NULL
        """
    )
    db.execute(
        """
        UPDATE transactions
        SET transaction_time = created_at::time(0)
        WHERE transaction_time IS NULL
        """
    )
    db.execute("ALTER TABLE transactions ALTER COLUMN transaction_date SET NOT NULL")
    db.execute("ALTER TABLE transactions ALTER COLUMN transaction_time SET NOT NULL")
    db.commit()

def require_login():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return None

def require_admin():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    if session.get("user_role") not in ELEVATED_ROLES or session.get("login_mode") not in ELEVATED_LOGIN_MODES:
        return redirect(url_for("dashboard"))

    return None

def require_item_manager():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    if session.get("user_role") not in ELEVATED_ROLES:
        return redirect(url_for("items"))

    return None

def get_item_form_data():
    expiration_date = request.form.get("expiration_date", "").strip() or "00/00/0000"

    data = {
        "barcode": request.form.get("barcode", "").strip(),
        "name": request.form.get("name", "").strip(),
        "bin_location": request.form.get("bin_location", "").strip(),
        "room": request.form.get("room", "").strip(),
        "company": request.form.get("company", "").strip(),
        "location": request.form.get("location", "").strip(),
        "expiration_date": expiration_date,
        "notes": request.form.get("notes", "").strip(),
    }

    try:
        data["quantity"] = int(request.form.get("quantity", "0"))
        data["minimum_quantity"] = int(request.form.get("minimum_quantity", "0"))
    except ValueError:
        data["quantity"] = 0
        data["minimum_quantity"] = 0
        return data, "Quantity values must be numbers."

    if not data["barcode"] or not data["name"] or not data["bin_location"] or not data["room"]:
        return data, "Barcode, name, bin location, and room are required."

    if data["quantity"] < 0 or data["minimum_quantity"] < 0:
        return data, "Quantity values cannot be negative."

    return data, None

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()

@app.cli.command("init-db")
def init_db_command():
    """Initialize the database."""
    db = get_db()

    with SCHEMA.open("r") as schema_file:
        db.execute(schema_file.read())

    db.commit()
    
    click.echo("Initialized the PostgreSQL inventory database.")

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        institution_id = request.form.get("institution_id", "").strip()
        login_mode = request.form.get("login_mode", "user").strip()
        db = get_db()
        user = db.execute(
            """
            SELECT id, institution_id, name, role
            FROM users
            WHERE institution_id = %s AND is_active = TRUE
            """,
            (institution_id,),
        ).fetchone()

        if user is None:
            return render_template(
                "login.html",
                error="You are not registered. Contact your administrator to register.",
            ), 401

        if login_mode in ELEVATED_LOGIN_MODES and user["role"] not in ELEVATED_ROLES:
            return render_template(
                "login.html",
                error="You are not registered as faculty or administrator. Contact your administrator for access.",
            ), 403

        session.clear()
        session["user_id"] = user["id"]
        session["institution_id"] = user["institution_id"]
        session["user_name"] = user["name"]
        session["user_role"] = user["role"]
        session["login_mode"] = login_mode

        return redirect(url_for("dashboard"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    db = get_db()
    ensure_transaction_columns(db)
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

@app.route("/items")
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

@app.route("/items/low-stock")
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

@app.route("/items/new", methods=["GET", "POST"])
def item_new():
    manager_redirect = require_item_manager()

    if manager_redirect is not None:
        return manager_redirect

    if request.method == "POST":
        item_data, error = get_item_form_data()

        if error:
            return render_template("item_new.html", error=error, item=item_data), 400

        db = get_db()

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

        return redirect(url_for("items"))

    return render_template("item_new.html", item={})

@app.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
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

        return redirect(url_for("items"))

    return render_template("item_edit.html", item=item)

@app.route("/scan", methods=["GET", "POST"])
def scan():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    if request.method == "POST":
        barcode = request.form.get("barcode", "").strip()
        transaction_type = request.form.get("transaction_type", "").strip()
        lab_instructor = request.form.get("lab_instructor", "").strip()
        topic_of_day = request.form.get("topic_of_day", "").strip()
        notes = request.form.get("notes", "").strip()

        try:
            quantity = int(request.form.get("quantity", "1"))
        except ValueError:
            return render_template("scan.html", error="Quantity must be a number."), 400

        if not barcode:
            return render_template("scan.html", error="Barcode is required."), 400

        if transaction_type not in {"add", "remove"}:
            return render_template("scan.html", error="Choose Add Stock or Remove Stock."), 400

        if quantity <= 0:
            return render_template("scan.html", error="Quantity must be greater than zero."), 400

        db = get_db()
        ensure_transaction_columns(db)
        item = db.execute(
            """
            SELECT id, name, quantity
            FROM items
            WHERE barcode = %s
            """,
            (barcode,),
        ).fetchone()

        if item is None:
            return render_template("scan.html", error="No item was found for that barcode."), 404

        if transaction_type == "remove" and quantity > item["quantity"]:
            return render_template(
                "scan.html",
                error=f"Cannot remove {quantity}. Only {item['quantity']} available.",
            ), 400

        if transaction_type == "add":
            new_quantity = item["quantity"] + quantity
        else:
            new_quantity = item["quantity"] - quantity

        db.execute(
            """
            UPDATE items
            SET quantity = %s
            WHERE id = %s
            """,
            (new_quantity, item["id"]),
        )
        db.execute(
            """
            INSERT INTO transactions (
                user_id, item_id, transaction_type, quantity,
                lab_instructor, topic_of_day, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                session["user_id"],
                item["id"],
                transaction_type,
                quantity,
                lab_instructor,
                topic_of_day,
                notes,
            ),
        )
        db.commit()

        return render_template(
            "scan.html",
            message=f"{item['name']} updated successfully. New quantity: {new_quantity}.",
        )

    return render_template("scan.html")

@app.route("/transactions")
def transactions():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    db = get_db()
    ensure_transaction_columns(db)

    filters = {
        "date_from": request.args.get("date_from", "").strip(),
        "date_to": request.args.get("date_to", "").strip(),
        "item_id": request.args.get("item_id", "").strip(),
        "user_id": request.args.get("user_id", "").strip(),
        "lab_instructor": request.args.get("lab_instructor", "").strip(),
        "topic_of_day": request.args.get("topic_of_day", "").strip(),
        "transaction_type": request.args.get("transaction_type", "").strip(),
    }
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
        conditions.append("transactions.lab_instructor ILIKE %s")
        params.append(f"%{filters['lab_instructor']}%")

    if filters["topic_of_day"]:
        conditions.append("transactions.topic_of_day ILIKE %s")
        params.append(f"%{filters['topic_of_day']}%")

    if filters["transaction_type"] in {"add", "remove"}:
        conditions.append("transactions.transaction_type = %s")
        params.append(filters["transaction_type"])

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    items = db.execute(
        """
        SELECT id, name, barcode
        FROM items
        ORDER BY name, barcode
        """
    ).fetchall()
    users = db.execute(
        """
        SELECT id, name, institution_id
        FROM users
        ORDER BY name, institution_id
        """
    ).fetchall()
    transaction_rows = db.execute(
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
        """.format(where_clause=where_clause),
        params,
    ).fetchall()

    return render_template(
        "transactions.html",
        transactions=transaction_rows,
        filters=filters,
        items=items,
        users=users,
    )

@app.route("/reports/export")
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

@app.route("/admin/users")
def admin_users():
    admin_redirect = require_admin()

    if admin_redirect is not None:
        return admin_redirect

    db = get_db()
    users = db.execute(
        """
        SELECT
            id,
            institution_id,
            name,
            role,
            department,
            is_active,
            (
                SELECT COUNT(*)
                FROM transactions
                WHERE transactions.user_id = users.id
            ) AS transaction_count
        FROM users
        ORDER BY name
        """
    ).fetchall()

    return render_template("admin_users.html", users=users)

@app.route("/admin/users/new", methods=["GET", "POST"])
def admin_user_new():
    admin_redirect = require_admin()

    if admin_redirect is not None:
        return admin_redirect

    if request.method == "POST":
        institution_id = request.form.get("institution_id", "").strip()
        name = request.form.get("name", "").strip()
        role = request.form.get("role", "").strip()
        department = request.form.get("department", "").strip()

        if not institution_id or not name or role not in {"student", "faculty", "administrator"}:
            return render_template(
                "user_new.html",
                error="Institution ID, name, and a valid role are required.",
            ), 400

        db = get_db()

        try:
            db.execute(
                """
                INSERT INTO users (institution_id, name, role, department)
                VALUES (%s, %s, %s, %s)
                """,
                (institution_id, name, role, department),
            )
            db.commit()
        except psycopg2.IntegrityError:
            db.rollback()
            return render_template(
                "user_new.html",
                error="A user with this Institution ID already exists.",
            ), 400

        return redirect(url_for("admin_users"))

    return render_template("user_new.html")

@app.route("/admin/users/<int:user_id>/deactivate", methods=["POST"])
def admin_user_deactivate(user_id):
    admin_redirect = require_admin()

    if admin_redirect is not None:
        return admin_redirect

    if user_id == session.get("user_id"):
        return redirect(url_for("admin_users"))

    db = get_db()
    db.execute(
        """
        UPDATE users
        SET is_active = FALSE
        WHERE id = %s
        """,
        (user_id,),
    )
    db.commit()

    return redirect(url_for("admin_users"))

@app.route("/admin/users/<int:user_id>/activate", methods=["POST"])
def admin_user_activate(user_id):
    admin_redirect = require_admin()

    if admin_redirect is not None:
        return admin_redirect

    db = get_db()
    db.execute(
        """
        UPDATE users
        SET is_active = TRUE
        WHERE id = %s
        """,
        (user_id,),
    )
    db.commit()

    return redirect(url_for("admin_users"))

@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
def admin_user_delete(user_id):
    admin_redirect = require_admin()

    if admin_redirect is not None:
        return admin_redirect

    if user_id == session.get("user_id"):
        return redirect(url_for("admin_users"))

    db = get_db()
    user = db.execute(
        """
        SELECT id, is_active
        FROM users
        WHERE id = %s
        """,
        (user_id,),
    ).fetchone()

    if user is None or user["is_active"]:
        return redirect(url_for("admin_users"))

    transaction_count = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM transactions
        WHERE user_id = %s
        """,
        (user_id,),
    ).fetchone()["total"]

    if transaction_count > 0:
        return redirect(url_for("admin_users"))

    db.execute(
        """
        DELETE FROM users
        WHERE id = %s
        """,
        (user_id,),
    )
    db.commit()

    return redirect(url_for("admin_users"))

@app.route("/db-status")
def db_status():
    admin_redirect = require_admin()

    if admin_redirect is not None:
        return admin_redirect

    db = get_db()
    user_count = db.execute("SELECT COUNT(*) AS total FROM users").fetchone()["total"]
    item_count = db.execute("SELECT COUNT(*) AS total FROM items").fetchone()["total"]
    transaction_count = db.execute("SELECT COUNT(*) AS total FROM transactions").fetchone()["total"]

    return render_template(
        "db_status.html",
        user_count=user_count,
        item_count=item_count,
        transaction_count=transaction_count,
    )
# to run : invent/bin/python -m flask --app app init-db
