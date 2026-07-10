"""Authentication and password-link routes."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from inventory.core import (
    INVITE_TOKEN_MAX_AGE,
    RATELIMIT_LOGIN,
    RATELIMIT_PASSWORD,
    RESET_TOKEN_MAX_AGE,
    app,
    clear_failed_login,
    get_db,
    hash_password,
    is_locked_out,
    limiter,
    mark_sudo,
    read_token,
    record_failed_login,
    remaining_login_attempts,
    require_login,
    safe_next,
    send_reset,
    validate_password_strength,
    verify_password,
)


bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit(RATELIMIT_LOGIN, methods=["POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if is_locked_out(email):
            return render_template(
                "login.html",
                error="Too many failed attempts. Please try again later.",
            ), 429

        db = get_db()
        user = db.execute(
            """
            SELECT id, email, name, role, password_hash
            FROM users
            WHERE LOWER(email) = %s AND is_active = TRUE
            """,
            (email,),
        ).fetchone()

        if user is None or not verify_password(user["password_hash"], password):
            record_failed_login(email)
            warning = None
            if remaining_login_attempts(email) == 1:
                warning = "This is your last attempt before your account is temporarily locked."
            return render_template(
                "login.html",
                error="Invalid email or password.",
                warning=warning,
            ), 401

        clear_failed_login(email)

        db.execute(
            "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = %s",
            (user["id"],),
        )
        db.commit()

        session.clear()
        session.permanent = True
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_role"] = user["role"]
        session["email"] = user["email"]
        mark_sudo()

        return redirect(url_for("dashboard.dashboard"))

    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/reauth", methods=["GET", "POST"])
def reauth():
    login_redirect = require_login()
    if login_redirect is not None:
        return login_redirect

    next_url = safe_next(request.values.get("next"))

    if request.method == "POST":
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute(
            "SELECT password_hash FROM users WHERE id = %s AND is_active = TRUE",
            (session.get("user_id"),),
        ).fetchone()

        if user is None or not verify_password(user["password_hash"], password):
            return render_template(
                "reauth.html",
                next=next_url,
                error="Incorrect password.",
            ), 401

        mark_sudo()
        return redirect(next_url)

    return render_template("reauth.html", next=next_url)


@bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit(RATELIMIT_PASSWORD, methods=["POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        db = get_db()
        user = db.execute(
            "SELECT id, email FROM users WHERE LOWER(email) = %s AND is_active = TRUE",
            (email,),
        ).fetchone()

        if user is not None:
            try:
                reset = send_reset(user["id"], user["email"])
            except Exception as error:
                app.logger.exception("Password reset email failed for %s", user["email"])
                flash(
                    "Password reset email could not be sent. Please check email "
                    f"settings and try again. Error: {error}",
                    "error",
                )
            else:
                if reset["sent"]:
                    flash("Password reset email sent.", "success")
                else:
                    flash(
                        "Email is not configured locally, so no message was sent. "
                        f"Reset link: {reset['link']}",
                        "warning",
                    )

        return render_template("forgot_password.html", sent=True)

    return render_template("forgot_password.html")


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit(RATELIMIT_PASSWORD, methods=["POST"])
def reset_password(token):
    user_id = read_token(token, "reset", RESET_TOKEN_MAX_AGE)

    if user_id is None:
        return render_template("reset_password.html", invalid=True), 400

    db = get_db()
    user = db.execute(
        "SELECT id, email FROM users WHERE id = %s AND is_active = TRUE",
        (user_id,),
    ).fetchone()

    if user is None:
        return render_template("reset_password.html", invalid=True), 400

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        error = validate_password_strength(password)
        if not error and password != confirm_password:
            error = "Passwords do not match."

        if error:
            return render_template("reset_password.html", token=token, error=error), 400

        db.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (hash_password(password), user["id"]),
        )
        db.commit()

        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", token=token)


@bp.route("/set-password/<token>", methods=["GET", "POST"])
@limiter.limit(RATELIMIT_PASSWORD, methods=["POST"])
def set_password(token):
    user_id = read_token(token, "invite", INVITE_TOKEN_MAX_AGE)

    if user_id is None:
        return render_template("set_password.html", invalid=True), 400

    db = get_db()
    user = db.execute(
        "SELECT id, email, name FROM users WHERE id = %s AND is_active = TRUE",
        (user_id,),
    ).fetchone()

    if user is None:
        return render_template("set_password.html", invalid=True), 400

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        error = validate_password_strength(password)
        if not error and password != confirm_password:
            error = "Passwords do not match."

        if error:
            return render_template(
                "set_password.html", user=user, token=token, error=error
            ), 400

        db.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (hash_password(password), user["id"]),
        )
        db.commit()

        return redirect(url_for("auth.login"))

    return render_template("set_password.html", user=user, token=token)
