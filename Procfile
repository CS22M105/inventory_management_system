# The release phase runs ONCE per deploy, before the new web process starts
# serving traffic. Migrations run here -- never on a per-request basis.
# (Equivalent: `flask --app app db-upgrade`.)
release: alembic upgrade head
web: gunicorn app:app -c gunicorn.conf.py
