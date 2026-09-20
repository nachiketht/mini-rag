from contextlib import contextmanager
from collections.abc import Iterator

import psycopg
from pgvector.psycopg import register_vector
from psycopg import Connection

from app.config import DATABASE_URL


class PgAdapter:
    """Postgres implementation of DatabaseAdapter.

    Opens a connection, registers pgvector so Python lists bind as vector(384),
    and returns the connection. Does not run ingest or retrieve SQL.
    """

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or DATABASE_URL

    @contextmanager
    def connect(self) -> Iterator[Connection]:
        conn = psycopg.connect(self.database_url)
        register_vector(conn)
        try:
            yield conn
        finally:
            conn.close()
