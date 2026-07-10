from inventory import core as _core
from inventory import create_app
from inventory.core import *  # noqa: F401,F403

app = create_app()


def __getattr__(name):
    return getattr(_core, name)
