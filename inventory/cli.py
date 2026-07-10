"""Flask CLI commands."""

import os

import click

from inventory.config import (
    APP_BASE_URL,
    APP_ENV,
    BASE_DIR,
    DEV_SECRET_KEY,
    EMAIL_FROM,
    EMAIL_PROVIDER,
    HSTS_ENABLED,
    HSTS_MAX_AGE,
    MIN_PRODUCTION_SECRET_KEY_LENGTH,
    PROXY_FIX_ENABLED,
    RATELIMIT_ENABLED,
    RATELIMIT_STORAGE_URI,
    SCHEMA,
    SECRET_KEY,
    SENTRY_DSN,
    SENTRY_TRACES_SAMPLE_RATE,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USERNAME,
)


def _alembic_config():
    from alembic.config import Config as AlembicConfig

    return AlembicConfig(str(BASE_DIR / "alembic.ini"))


def register_cli(flask_app):
    @flask_app.cli.command("check-config")
    def check_config_command():
        checks = []

        def add(name, ok, detail):
            checks.append((name, ok, detail))

        add("APP_ENV", APP_ENV == "production", "production" if APP_ENV == "production" else "not production")
        add("SECRET_KEY", bool(SECRET_KEY), "set" if SECRET_KEY else "missing")
        add(
            "SECRET_KEY_LENGTH",
            bool(SECRET_KEY) and len(SECRET_KEY) >= MIN_PRODUCTION_SECRET_KEY_LENGTH,
            f">= {MIN_PRODUCTION_SECRET_KEY_LENGTH} chars" if SECRET_KEY and len(SECRET_KEY) >= MIN_PRODUCTION_SECRET_KEY_LENGTH else "too short or missing",
        )
        add(
            "SECRET_KEY_NOT_DEV_FALLBACK",
            SECRET_KEY != DEV_SECRET_KEY,
            "ok" if SECRET_KEY != DEV_SECRET_KEY else "uses development fallback",
        )
        add("DATABASE_URL", bool(os.environ.get("DATABASE_URL")), "set" if os.environ.get("DATABASE_URL") else "missing")
        add("APP_BASE_URL", bool(APP_BASE_URL), "set" if APP_BASE_URL else "missing")

        if EMAIL_PROVIDER == "smtp":
            add("EMAIL_PROVIDER", True, "smtp")
            add("EMAIL_FROM", bool(EMAIL_FROM), "set" if EMAIL_FROM else "missing")
            add("SMTP_HOST", bool(SMTP_HOST), "set" if SMTP_HOST else "missing")
            add("SMTP_PORT", bool(SMTP_PORT), "set" if SMTP_PORT else "missing")
            add("SMTP_USERNAME", bool(SMTP_USERNAME), "set" if SMTP_USERNAME else "missing")
            add("SMTP_PASSWORD", bool(SMTP_PASSWORD), "set" if SMTP_PASSWORD else "missing")
        else:
            add("EMAIL_PROVIDER", False, "smtp required in production")

        add("SESSION_COOKIE_SECURE", flask_app.config["SESSION_COOKIE_SECURE"], "enabled" if flask_app.config["SESSION_COOKIE_SECURE"] else "disabled")
        add("SESSION_COOKIE_HTTPONLY", flask_app.config["SESSION_COOKIE_HTTPONLY"], "enabled" if flask_app.config["SESSION_COOKIE_HTTPONLY"] else "disabled")
        add("SESSION_COOKIE_SAMESITE", bool(flask_app.config["SESSION_COOKIE_SAMESITE"]), "set" if flask_app.config["SESSION_COOKIE_SAMESITE"] else "missing")
        add("PROXY_FIX_ENABLED", PROXY_FIX_ENABLED, "enabled" if PROXY_FIX_ENABLED else "disabled")
        add("HSTS_ENABLED", HSTS_ENABLED, "enabled" if HSTS_ENABLED else "disabled")
        add("HSTS_MAX_AGE", HSTS_MAX_AGE > 0, str(HSTS_MAX_AGE))
        add("SENTRY_DSN", True, "set" if SENTRY_DSN else "not configured")
        add("SENTRY_TRACES_SAMPLE_RATE", 0.0 <= SENTRY_TRACES_SAMPLE_RATE <= 1.0, str(SENTRY_TRACES_SAMPLE_RATE))
        add("RATELIMIT_ENABLED", RATELIMIT_ENABLED, "enabled" if RATELIMIT_ENABLED else "disabled")
        add(
            "RATELIMIT_STORAGE_URI",
            bool(RATELIMIT_STORAGE_URI),
            "set; memory:// is single-process only" if RATELIMIT_STORAGE_URI == "memory://" else "set",
        )

        has_errors = False
        click.echo("Production configuration check")
        for name, ok, detail in checks:
            status = "OK" if ok else "MISSING/ATTENTION"
            click.echo(f"- {name}: {status} ({detail})")
            if APP_ENV == "production" and not ok:
                has_errors = True

        if APP_ENV == "production" and RATELIMIT_STORAGE_URI == "memory://":
            click.echo("- RATELIMIT_STORAGE_URI: ATTENTION (use Redis/shared storage for multi-worker or multi-host production)")

        if has_errors:
            raise click.ClickException("Production configuration is incomplete.")

    @flask_app.cli.command("init-db")
    def init_db_command():
        import inventory.core as core

        db = core.get_db()
        with SCHEMA.open("r") as schema_file:
            db.execute(schema_file.read())
        db.commit()
        click.echo("Initialized the PostgreSQL inventory database (local dev bootstrap).")

    @flask_app.cli.command("db-upgrade")
    @click.argument("revision", default="head")
    def db_upgrade_command(revision):
        from alembic import command as alembic_command

        alembic_command.upgrade(_alembic_config(), revision)
        click.echo(f"Database upgraded to {revision}.")

    @flask_app.cli.command(
        "db-downgrade",
        context_settings={"ignore_unknown_options": True},
    )
    @click.argument("revision")
    def db_downgrade_command(revision):
        from alembic import command as alembic_command

        alembic_command.downgrade(_alembic_config(), revision)
        click.echo(f"Database downgraded to {revision}.")

    @flask_app.cli.command("set-password")
    @click.argument("email")
    @click.argument("password")
    def set_password_command(email, password):
        import inventory.core as core

        db = core.get_db()
        error = core.validate_password_strength(password)
        if error:
            raise click.ClickException(error)

        cursor = db.execute(
            "UPDATE users SET password_hash = %s WHERE email = %s",
            (core.hash_password(password), email),
        )
        db.commit()

        if cursor.rowcount == 0:
            raise click.ClickException(f"No user found with email {email}.")

        click.echo(f"Password set for {email}.")
