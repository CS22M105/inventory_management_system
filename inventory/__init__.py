"""Application package for the inventory management system."""


def create_app():
    """Return the configured Flask application.

    The app is still built by inventory.core during this refactor phase. Keeping
    registration idempotent lets Flask, Gunicorn, and tests import the entrypoint
    more than once without duplicate blueprint errors.
    """
    from inventory import core

    if not core.app.config.get("_BLUEPRINTS_REGISTERED"):
        core.register_blueprints(core.app)
        core.app.config["_BLUEPRINTS_REGISTERED"] = True

    return core.app
