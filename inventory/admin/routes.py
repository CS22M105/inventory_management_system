"""User administration and database-status routes."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
import psycopg2

from inventory.core import (
    allowed_user_roles_to_manage,
    app,
    can_manage_user_role,
    get_db,
    require_admin,
    require_sudo,
    require_system_admin,
    send_invite,
)


bp = Blueprint("admin", __name__)


@bp.route("/admin/users")
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
            email,
            name,
            role,
            department,
            is_active,
            password_hash IS NULL AS invite_pending,
            (
                SELECT COUNT(*)
                FROM transactions
                WHERE transactions.user_id = users.id
            ) AS transaction_count
        FROM users
        ORDER BY name
        """
    ).fetchall()

    return render_template(
        "admin_users.html",
        users=users,
        can_manage_user_role=can_manage_user_role,
    )


@bp.route("/admin/users/new", methods=["GET", "POST"])
def admin_user_new():
    admin_redirect = require_admin()

    if admin_redirect is not None:
        return admin_redirect

    allowed_roles = allowed_user_roles_to_manage()
    role_options = [
        ("student", "Student"),
        ("faculty", "Faculty"),
    ]
    role_options = [role for role in role_options if role[0] in allowed_roles]

    if request.method == "POST":
        institution_id = request.form.get("institution_id", "").strip()
        email = request.form.get("email", "").strip().lower()
        name = request.form.get("name", "").strip()
        role = request.form.get("role", "").strip()
        department = request.form.get("department", "").strip()

        if not email or not name or role not in allowed_roles:
            return render_template(
                "user_new.html",
                error="Name, email, and an allowed role are required.",
                role_options=role_options,
            ), 400

        db = get_db()

        try:
            new_user = db.execute(
                """
                INSERT INTO users (institution_id, email, name, role, department)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (institution_id or None, email, name, role, department),
            ).fetchone()
            db.commit()
        except psycopg2.IntegrityError:
            db.rollback()
            return render_template(
                "user_new.html",
                error="A user with this email or institution ID already exists.",
                role_options=role_options,
            ), 400

        try:
            invite = send_invite(new_user["id"], email)
        except Exception as error:
            app.logger.exception("Invite email failed for %s", email)
            flash(
                "User was created, but the invite email could not be sent. "
                f"Please check email settings and use Resend invite. Error: {error}",
                "error",
            )
        else:
            if invite["sent"]:
                flash(f"Invite email sent to {email}.", "success")
            else:
                flash(
                    "User was created. Email is not configured locally, so no "
                    f"message was sent. Invite link: {invite['link']}",
                    "warning",
                )
        return redirect(url_for("admin.admin_users"))

    return render_template("user_new.html", role_options=role_options)


@bp.route("/admin/users/<int:user_id>/resend-invite", methods=["POST"])
def admin_user_resend_invite(user_id):
    admin_redirect = require_admin()

    if admin_redirect is not None:
        return admin_redirect

    db = get_db()
    user = db.execute(
        "SELECT id, email, role, password_hash FROM users WHERE id = %s",
        (user_id,),
    ).fetchone()

    if user is None or not can_manage_user_role(user["role"]) or user["password_hash"] is not None:
        return redirect(url_for("admin.admin_users"))

    try:
        invite = send_invite(user["id"], user["email"])
    except Exception as error:
        app.logger.exception("Invite email failed for %s", user["email"])
        flash(
            "Invite email could not be sent. Please check email settings and "
            f"try again. Error: {error}",
            "error",
        )
    else:
        if invite["sent"]:
            flash(f"Invite email sent to {user['email']}.", "success")
        else:
            flash(
                "Email is not configured locally, so no message was sent. "
                f"Invite link: {invite['link']}",
                "warning",
            )

    return redirect(url_for("admin.admin_users"))


@bp.route("/admin/users/<int:user_id>/deactivate", methods=["POST"])
def admin_user_deactivate(user_id):
    admin_redirect = require_admin()

    if admin_redirect is not None:
        return admin_redirect

    sudo_redirect = require_sudo()
    if sudo_redirect is not None:
        return sudo_redirect

    if user_id == session.get("user_id"):
        return redirect(url_for("admin.admin_users"))

    db = get_db()
    user = db.execute(
        """
        SELECT id, role
        FROM users
        WHERE id = %s
        """,
        (user_id,),
    ).fetchone()

    if user is None or not can_manage_user_role(user["role"]):
        return redirect(url_for("admin.admin_users"))

    db.execute(
        """
        UPDATE users
        SET is_active = FALSE
        WHERE id = %s
        """,
        (user_id,),
    )
    db.commit()

    return redirect(url_for("admin.admin_users"))


@bp.route("/admin/users/<int:user_id>/activate", methods=["POST"])
def admin_user_activate(user_id):
    admin_redirect = require_admin()

    if admin_redirect is not None:
        return admin_redirect

    db = get_db()
    user = db.execute(
        """
        SELECT id, role
        FROM users
        WHERE id = %s
        """,
        (user_id,),
    ).fetchone()

    if user is None or not can_manage_user_role(user["role"]):
        return redirect(url_for("admin.admin_users"))

    db.execute(
        """
        UPDATE users
        SET is_active = TRUE
        WHERE id = %s
        """,
        (user_id,),
    )
    db.commit()

    return redirect(url_for("admin.admin_users"))


@bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
def admin_user_delete(user_id):
    admin_redirect = require_admin()

    if admin_redirect is not None:
        return admin_redirect

    sudo_redirect = require_sudo()
    if sudo_redirect is not None:
        return sudo_redirect

    if user_id == session.get("user_id"):
        return redirect(url_for("admin.admin_users"))

    db = get_db()
    user = db.execute(
        """
        SELECT id, role, is_active
        FROM users
        WHERE id = %s
        """,
        (user_id,),
    ).fetchone()

    if user is None or user["is_active"] or not can_manage_user_role(user["role"]):
        return redirect(url_for("admin.admin_users"))

    transaction_count = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM transactions
        WHERE user_id = %s
        """,
        (user_id,),
    ).fetchone()["total"]

    if transaction_count > 0:
        return redirect(url_for("admin.admin_users"))

    db.execute(
        """
        DELETE FROM users
        WHERE id = %s
        """,
        (user_id,),
    )
    db.commit()

    return redirect(url_for("admin.admin_users"))


@bp.route("/db-status")
def db_status():
    admin_redirect = require_system_admin()

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
