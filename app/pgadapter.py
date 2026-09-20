from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from pgvector.psycopg import register_vector
from pgvector.psycopg.vector import VectorBinaryDumper, VectorDumper
from psycopg import Connection
from psycopg.types import TypeInfo

from app.config import DATABASE_URL


def _register_list_as_vector(conn: Connection) -> None:
    info = TypeInfo.fetch(conn, "vector")
    if info is None:
        raise psycopg.ProgrammingError("vector type not found in the database")
    conn.adapters.register_dumper(list, type("", (VectorDumper,), {"oid": info.oid}))
    conn.adapters.register_dumper(list, type("", (VectorBinaryDumper,), {"oid": info.oid}))


class PgAdapter:
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
