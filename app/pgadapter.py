from contextlib import contextmanager
from collections.abc import Iterator

import psycopg
from pgvector.psycopg import register_vector
from pgvector.psycopg.vector import VectorBinaryDumper, VectorDumper
from psycopg import Connection
from psycopg.types import TypeInfo

from app.config import DATABASE_URL


def _register_list_as_vector(conn: Connection) -> None:
    """Make Python lists dump as vector(384), not float[]."""
    info = TypeInfo.fetch(conn, "vector")
    if info is None:
        raise psycopg.ProgrammingError("vector type not found in the database")
    text_dumper = type("", (VectorDumper,), {"oid": info.oid})
    binary_dumper = type("", (VectorBinaryDumper,), {"oid": info.oid})
    conn.adapters.register_dumper(list, text_dumper)
    conn.adapters.register_dumper(list, binary_dumper)


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
        _register_list_as_vector(conn)
        try:
            yield conn
        finally:
            conn.close()
