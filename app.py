from flask import Flask, g, redirect, render_template, request, session, url_for
import sqlite3
import click
from pathlib import Path

# holds the parent path to the current script we are running.
BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "data" / "inventory.db"
SCHEMA = BASE_DIR / "schema.sql"

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-key-change-before-production"


def get_db():
    if "db" not in g: # g is for Global, it is a 
        # special object that Flask provides to store data during the 
        # request lifecycle.
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row 
        # This allows us to access columns by name.
    return g.db

def require_login():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return None

def require_admin():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    if session.get("user_role") != "administrator" or session.get("login_mode") != "admin":
        return redirect(url_for("dashboard"))

    return None

def require_item_manager():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    if session.get("user_role") not in {"faculty", "administrator"}:
        return redirect(url_for("items"))

    return None

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()

@app.cli.command("init-db")
def init_db_command():
    """Initialize the database."""
    DATABASE.parent.mkdir(exist_ok=True) # Create the data directory if it doesn't exist.

    db = get_db()

    with SCHEMA.open("r") as schema_file:
        db.executescript(schema_file.read())
    
    click.echo("Initialized the inventory database.")

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
            WHERE institution_id = ? AND is_active = 1
            """,
            (institution_id,),
        ).fetchone()

        if user is None:
            return render_template(
                "login.html",
                error="You are not registered. Contact your administrator to register.",
            ), 401

        if login_mode == "admin" and user["role"] != "administrator":
            return render_template(
                "login.html",
                error="You are not registered as an administrator. Contact your administrator for access.",
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

    return render_template(
        "dashboard.html",
        total_items=0,
        low_stock_items=0,
        total_transactions=0,
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

@app.route("/items/new", methods=["GET", "POST"])
def item_new():
    manager_redirect = require_item_manager()

    if manager_redirect is not None:
        return manager_redirect

    if request.method == "POST":
        barcode = request.form.get("barcode", "").strip()
        name = request.form.get("name", "").strip()
        bin_location = request.form.get("bin_location", "").strip()
        room = request.form.get("room", "").strip()
        company = request.form.get("company", "").strip()
        location = request.form.get("location", "").strip()
        expiration_date = request.form.get("expiration_date", "").strip()
        notes = request.form.get("notes", "").strip()

        try:
            quantity = int(request.form.get("quantity", "0"))
            minimum_quantity = int(request.form.get("minimum_quantity", "0"))
        except ValueError:
            return render_template("item_new.html", error="Quantity values must be numbers."), 400

        if not barcode or not name or not bin_location or not room:
            return render_template("item_new.html", error="Barcode, name, bin location, and room are required."), 400

        if quantity < 0 or minimum_quantity < 0:
            return render_template("item_new.html", error="Quantity values cannot be negative."), 400

        db = get_db()

        try:
            db.execute(
                """
                INSERT INTO items (
                    barcode, name, bin_location, room, company,
                    quantity, minimum_quantity, location, expiration_date, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    barcode,
                    name,
                    bin_location,
                    room,
                    company,
                    quantity,
                    minimum_quantity,
                    location,
                    expiration_date,
                    notes,
                ),
            )
            db.commit()
        except sqlite3.IntegrityError:
            return render_template("item_new.html", error="An item with this barcode already exists."), 400

        return redirect(url_for("items"))

    return render_template("item_new.html")

@app.route("/scan", methods=["GET", "POST"])
def scan():
    login_redirect = require_login()

    if login_redirect is not None:
        return login_redirect

    if request.method == "POST":
        barcode = request.form.get("barcode", "").strip()
        transaction_type = request.form.get("transaction_type", "").strip()
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
        item = db.execute(
            """
            SELECT id, name, quantity
            FROM items
            WHERE barcode = ?
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
            SET quantity = ?
            WHERE id = ?
            """,
            (new_quantity, item["id"]),
        )
        db.execute(
            """
            INSERT INTO transactions (user_id, item_id, transaction_type, quantity, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session["user_id"], item["id"], transaction_type, quantity, notes),
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
    transaction_rows = db.execute(
        """
        SELECT
            transactions.id,
            transactions.transaction_type,
            transactions.quantity,
            transactions.created_at,
            transactions.notes,
            items.name AS item_name,
            items.barcode,
            users.name AS user_name
        FROM transactions
        JOIN items ON items.id = transactions.item_id
        JOIN users ON users.id = transactions.user_id
        ORDER BY transactions.created_at DESC
        """
    ).fetchall()

    return render_template("transactions.html", transactions=transaction_rows)

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
                VALUES (?, ?, ?, ?)
                """,
                (institution_id, name, role, department),
            )
            db.commit()
        except sqlite3.IntegrityError:
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
        SET is_active = 0
        WHERE id = ?
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
        SET is_active = 1
        WHERE id = ?
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
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()

    if user is None or user["is_active"]:
        return redirect(url_for("admin_users"))

    transaction_count = db.execute(
        """
        SELECT COUNT(*)
        FROM transactions
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()[0]

    if transaction_count > 0:
        return redirect(url_for("admin_users"))

    db.execute(
        """
        DELETE FROM users
        WHERE id = ?
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
    user_count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    item_count = db.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    transaction_count = db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]

    return f"""
    <h1>Database Status</h1>
    <p>Users table rows: {user_count}</p>
    <p>Items table rows: {item_count}</p>
    <p>Transactions table rows: {transaction_count}</p>
    """
# to run : invent/bin/python -m flask --app app init-db
