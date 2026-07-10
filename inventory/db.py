"""Database connection helpers."""

from flask import g
import psycopg2
from psycopg2.extras import RealDictCursor

from inventory.config import DATABASE_URL


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
    if "db" not in g:
        connection = psycopg2.connect(
            DATABASE_URL,
            connect_timeout=5,
            cursor_factory=RealDictCursor,
        )
        g.db = Database(connection)
    return g.db


def close_db(error=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()
