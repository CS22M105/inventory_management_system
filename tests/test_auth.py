"""Authentication tests for Substep A6.

Covers: login success / wrong password / inactive / invited; the full
invite -> set-password -> login flow; reset token validity, purpose and expiry;
protected routes redirecting to /login when logged out; and role-based access
(student blocked from admin routes).
"""

import re
from datetime import timedelta

import app as app_module
from inventory.services.email import send_email


def _location(response):
    return response.headers.get("Location", "")


def _is_active(user_id):
    with app_module.app.app_context():
        db = app_module.get_db()
        return db.execute(
            "SELECT is_active FROM users WHERE id = %s", (user_id,)
        ).fetchone()["is_active"]


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def test_login_success_redirects_to_dashboard(client, users, login):
    resp = login(users["admin"]["email"], users["admin"]["password"])
    assert resp.status_code == 302
    assert "/dashboard" in _location(resp)


def test_login_sets_session(client, users, login):
    login(users["faculty"]["email"], users["faculty"]["password"])
    with client.session_transaction() as sess:
        assert sess["user_id"] == users["faculty"]["id"]
        assert sess["user_role"] == "faculty"


def test_login_wrong_password_rejected(client, users, login):
    resp = login(users["admin"]["email"], "WrongPassword999")
    assert resp.status_code == 401
    assert b"Invalid email or password" in resp.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_login_unknown_email_rejected(client, users, login):
    resp = login("nobody@test.edu", "Password123")
    assert resp.status_code == 401
    assert b"Invalid email or password" in resp.data


def test_login_inactive_user_rejected(client, users, login):
    # Correct password, but the account is deactivated -> same generic 401.
    resp = login(users["inactive"]["email"], "Password123")
    assert resp.status_code == 401
    assert b"Invalid email or password" in resp.data


def test_login_invited_user_without_password_rejected(client, users, login):
    # Invited account has a NULL password_hash and must not be able to log in.
    resp = login(users["invited"]["email"], "Password123")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Invite -> set-password -> login
# ---------------------------------------------------------------------------

def test_invite_then_set_password_then_login(client, users, login, captured_emails):
    # Admin creates a new user, which sends an invite email with a set-password link.
    login(users["admin"]["email"], users["admin"]["password"])
    resp = client.post(
        "/admin/users/new",
        data={
            "name": "New Hire",
            "email": "newhire@test.edu",
            "role": "faculty",
            "institution_id": "",
            "department": "Nursing",
        },
    )
    assert resp.status_code == 302
    assert len(captured_emails) == 1

    match = re.search(r"/set-password/(\S+)", captured_emails[0]["body"])
    assert match, "invite email should contain a set-password link"
    token = match.group(1)

    # The invited user opens the link (no login required) and sees the form.
    resp = client.get(f"/set-password/{token}")
    assert resp.status_code == 200

    # They set a password.
    resp = client.post(
        f"/set-password/{token}",
        data={"password": "BrandNew123", "confirm_password": "BrandNew123"},
    )
    assert resp.status_code == 302
    assert "/login" in _location(resp)

    # And can now log in with it.
    resp = login("newhire@test.edu", "BrandNew123")
    assert resp.status_code == 302
    assert "/dashboard" in _location(resp)


def test_set_password_rejects_invalid_token(client, users):
    resp = client.get("/set-password/not-a-real-token")
    assert resp.status_code == 400
    assert b"invalid" in resp.data.lower()


# ---------------------------------------------------------------------------
# Reset token: validity, purpose, and expiry
# ---------------------------------------------------------------------------

def test_reset_token_roundtrips_for_correct_purpose(users):
    with app_module.app.app_context():
        token = app_module.make_token(users["student"]["id"], "reset")
        assert (
            app_module.read_token(token, "reset", app_module.RESET_TOKEN_MAX_AGE)
            == users["student"]["id"]
        )


def test_reset_token_rejected_for_wrong_purpose(users):
    # A token minted for "invite" must not be accepted as a "reset" token.
    with app_module.app.app_context():
        token = app_module.make_token(users["student"]["id"], "invite")
        assert app_module.read_token(token, "reset", app_module.RESET_TOKEN_MAX_AGE) is None


def test_reset_token_rejected_when_expired(users):
    with app_module.app.app_context():
        token = app_module.make_token(users["student"]["id"], "reset")
        # A negative max_age makes any token immediately "too old".
        assert app_module.read_token(token, "reset", -1) is None


def test_reset_token_rejected_when_tampered(users):
    with app_module.app.app_context():
        token = app_module.make_token(users["student"]["id"], "reset")
        assert app_module.read_token(token + "x", "reset", app_module.RESET_TOKEN_MAX_AGE) is None


def test_forgot_password_flow_changes_password(client, users, login, captured_emails):
    # Requesting a reset for a real account emails a working link.
    resp = client.post("/forgot-password", data={"email": users["student"]["email"]})
    assert resp.status_code == 200
    assert len(captured_emails) == 1

    token = re.search(r"/reset-password/(\S+)", captured_emails[0]["body"]).group(1)
    resp = client.post(
        f"/reset-password/{token}",
        data={"password": "ResetPass123", "confirm_password": "ResetPass123"},
    )
    assert resp.status_code == 302

    # Old password no longer works; new one does.
    assert login(users["student"]["email"], "Password123").status_code == 401
    assert login(users["student"]["email"], "ResetPass123").status_code == 302


def test_forgot_password_unknown_email_sends_nothing(client, users, captured_emails):
    resp = client.post("/forgot-password", data={"email": "ghost@test.edu"})
    assert resp.status_code == 200
    assert len(captured_emails) == 0


def test_production_email_fallback_requires_explicit_flag():
    kwargs = {
        "to": "student@test.edu",
        "subject": "Reset",
        "body": "Reset link",
        "provider": "",
        "email_from": "",
        "smtp_host": "",
        "smtp_port": 587,
        "smtp_username": "",
        "smtp_password": "",
        "smtp_use_tls": True,
        "smtp_use_ssl": False,
        "app_env": "production",
        "logger": app_module.app.logger,
    }

    try:
        send_email(**kwargs, allow_local_auth_links=False)
    except RuntimeError as error:
        assert "EMAIL_PROVIDER=smtp" in str(error)
    else:
        raise AssertionError("production fallback should require explicit opt-in")

    assert send_email(**kwargs, allow_local_auth_links=True) is False


# ---------------------------------------------------------------------------
# Protected routes require login
# ---------------------------------------------------------------------------

def test_protected_routes_redirect_to_login_when_logged_out(client, users):
    for path in ["/dashboard", "/items", "/scan", "/transactions", "/admin/users"]:
        resp = client.get(path)
        assert resp.status_code == 302, f"{path} should redirect when logged out"
        assert "/login" in _location(resp), f"{path} should redirect to /login"


# ---------------------------------------------------------------------------
# Role-based access
# ---------------------------------------------------------------------------

def test_student_blocked_from_admin_users(client, users, login):
    login(users["student"]["email"], users["student"]["password"])
    resp = client.get("/admin/users")
    assert resp.status_code == 302
    assert "/dashboard" in _location(resp)


def test_student_cannot_create_users(client, users, login, captured_emails):
    login(users["student"]["email"], users["student"]["password"])
    resp = client.post(
        "/admin/users/new",
        data={"name": "X", "email": "x@test.edu", "role": "student"},
    )
    assert resp.status_code == 302
    assert "/dashboard" in _location(resp)
    assert len(captured_emails) == 0


def test_admin_can_access_admin_users(client, users, login):
    login(users["admin"]["email"], users["admin"]["password"])
    resp = client.get("/admin/users")
    assert resp.status_code == 200


def test_faculty_can_access_admin_users(client, users, login):
    # require_admin() allows the elevated roles (administrator + faculty).
    login(users["faculty"]["email"], users["faculty"]["password"])
    resp = client.get("/admin/users")
    assert resp.status_code == 200


def test_faculty_cannot_access_system_admin_route(client, users, login):
    # /db-status uses require_system_admin() (administrator only).
    login(users["faculty"]["email"], users["faculty"]["password"])
    resp = client.get("/db-status")
    assert resp.status_code == 302
    assert "/dashboard" in _location(resp)


# ---------------------------------------------------------------------------
# Step C: session idle-timeout
# ---------------------------------------------------------------------------

def test_session_idle_timeout_configured():
    assert app_module.app.config["PERMANENT_SESSION_LIFETIME"] == timedelta(
        minutes=app_module.SESSION_IDLE_MINUTES
    )
    # Sliding window: the cookie is refreshed on every request.
    assert app_module.app.config["SESSION_REFRESH_EACH_REQUEST"] is True


def test_login_marks_session_permanent_and_sudo(client, users, login):
    login(users["admin"]["email"], users["admin"]["password"])
    with client.session_transaction() as sess:
        assert sess.permanent is True
        assert "sudo_at" in sess


# ---------------------------------------------------------------------------
# Step C: failed-login lockout / cooldown
# ---------------------------------------------------------------------------

def test_lockout_after_repeated_failures(client, users, login):
    email = users["admin"]["email"]
    for _ in range(app_module.LOGIN_MAX_ATTEMPTS):
        assert login(email, "WrongPassword").status_code == 401
    # Now locked out: even the correct password is refused with 429.
    resp = login(email, users["admin"]["password"])
    assert resp.status_code == 429
    assert b"Too many failed attempts" in resp.data


def test_last_attempt_warning_shown_before_lockout(client, users, login):
    email = users["admin"]["email"]
    # The first (MAX - 2) failures show no warning.
    for _ in range(app_module.LOGIN_MAX_ATTEMPTS - 2):
        resp = login(email, "WrongPassword")
        assert b"last attempt" not in resp.data
    # The next failure leaves exactly one attempt -> the warning appears.
    resp = login(email, "WrongPassword")
    assert resp.status_code == 401
    assert b"last attempt" in resp.data


def test_successful_login_resets_failed_attempts(client, users, login):
    email = users["admin"]["email"]
    for _ in range(app_module.LOGIN_MAX_ATTEMPTS - 1):
        login(email, "WrongPassword")
    # A success before the threshold clears the counter.
    assert login(email, users["admin"]["password"]).status_code == 302
    # So a single later failure is just a 401, not an immediate lockout.
    assert login(email, "WrongPassword").status_code == 401


# ---------------------------------------------------------------------------
# Step C: admin re-auth ("sudo mode") for destructive actions
# ---------------------------------------------------------------------------

def test_deactivate_works_with_fresh_sudo(client, users, login):
    # A fresh login counts as recent password proof, so the action proceeds.
    login(users["admin"]["email"], users["admin"]["password"])
    target = users["student"]["id"]
    resp = client.post(f"/admin/users/{target}/deactivate")
    assert resp.status_code == 302
    assert "/reauth" not in _location(resp)
    assert _is_active(target) is False


def test_deactivate_requires_reauth_when_sudo_stale(client, users, login):
    login(users["admin"]["email"], users["admin"]["password"])
    with client.session_transaction() as sess:
        sess.pop("sudo_at", None)  # simulate the sudo window having expired

    target = users["student"]["id"]
    resp = client.post(f"/admin/users/{target}/deactivate")
    assert resp.status_code == 302
    assert "/reauth" in _location(resp)
    # The action must NOT have happened.
    assert _is_active(target) is True


def test_reauth_get_renders_form(client, users, login):
    login(users["admin"]["email"], users["admin"]["password"])
    resp = client.get("/reauth?next=/admin/users")
    assert resp.status_code == 200
    assert b"Confirm Your Password" in resp.data


def test_reauth_wrong_password_rejected(client, users, login):
    login(users["admin"]["email"], users["admin"]["password"])
    resp = client.post(
        "/reauth", data={"password": "WrongPassword", "next": "/admin/users"}
    )
    assert resp.status_code == 401
    assert b"Incorrect password" in resp.data


def test_reauth_success_sets_sudo_and_redirects(client, users, login):
    login(users["admin"]["email"], users["admin"]["password"])
    with client.session_transaction() as sess:
        sess.pop("sudo_at", None)

    resp = client.post(
        "/reauth",
        data={"password": users["admin"]["password"], "next": "/admin/users"},
    )
    assert resp.status_code == 302
    assert "/admin/users" in _location(resp)
    with client.session_transaction() as sess:
        assert "sudo_at" in sess


def test_reauth_blocks_open_redirect(client, users, login):
    login(users["admin"]["email"], users["admin"]["password"])
    resp = client.post(
        "/reauth",
        data={"password": users["admin"]["password"], "next": "http://evil.example/x"},
    )
    assert resp.status_code == 302
    assert "evil.example" not in _location(resp)
    assert "/admin/users" in _location(resp)


def test_reauth_requires_login(client, users):
    resp = client.get("/reauth")
    assert resp.status_code == 302
    assert "/login" in _location(resp)


# ---------------------------------------------------------------------------
# Step D: rate limiting / brute-force protection
# ---------------------------------------------------------------------------

def test_rate_limit_settings_configurable():
    # Limits come from env-configurable module constants, and the limiter exists.
    assert app_module.RATELIMIT_LOGIN
    assert app_module.RATELIMIT_PASSWORD
    assert app_module.RATELIMIT_STOCK
    assert app_module.limiter is not None


def test_rapid_logins_are_throttled_with_429(client, users):
    # Enable the limiter for this test only (conftest disables it by default).
    app_module.limiter.enabled = True
    app_module.limiter._storage.reset()
    try:
        ip = {"REMOTE_ADDR": "203.0.113.10"}
        # Distinct emails each attempt so the per-email lockout never trips —
        # this isolates the IP-based rate limiter as the source of the 429.
        codes = [
            client.post(
                "/login",
                data={"email": f"probe{i}@test.edu", "password": "nope"},
                environ_overrides=ip,
            ).status_code
            for i in range(12)
        ]
        assert 429 in codes, f"expected a 429 among {codes}"
        # Early attempts are the normal 401, not throttled.
        assert codes[0] == 401
    finally:
        app_module.limiter.enabled = False


def test_429_response_is_friendly(client, users):
    app_module.limiter.enabled = True
    app_module.limiter._storage.reset()
    try:
        ip = {"REMOTE_ADDR": "203.0.113.11"}
        last = None
        for i in range(12):
            last = client.post(
                "/login",
                data={"email": f"probe{i}@test.edu", "password": "nope"},
                environ_overrides=ip,
            )
        assert last.status_code == 429
        assert b"Too Many Attempts" in last.data
    finally:
        app_module.limiter.enabled = False


def test_normal_login_usage_not_throttled(client, users):
    # A handful of requests (well under the limit) from one IP are never 429.
    app_module.limiter.enabled = True
    app_module.limiter._storage.reset()
    try:
        ip = {"REMOTE_ADDR": "203.0.113.12"}
        for _ in range(3):
            resp = client.post(
                "/login",
                data={
                    "email": users["admin"]["email"],
                    "password": users["admin"]["password"],
                },
                environ_overrides=ip,
            )
            assert resp.status_code != 429
    finally:
        app_module.limiter.enabled = False


def test_forgot_password_is_throttled(client, users):
    app_module.limiter.enabled = True
    app_module.limiter._storage.reset()
    try:
        ip = {"REMOTE_ADDR": "203.0.113.13"}
        # RATELIMIT_PASSWORD default is stricter (5/min); 7 rapid POSTs trip it.
        codes = [
            client.post(
                "/forgot-password",
                data={"email": "ghost@test.edu"},
                environ_overrides=ip,
            ).status_code
            for _ in range(7)
        ]
        assert 429 in codes, f"expected a 429 among {codes}"
    finally:
        app_module.limiter.enabled = False
