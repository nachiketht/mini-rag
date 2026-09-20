import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector
from pgvector.psycopg.vector import VectorBinaryDumper, VectorDumper
from psycopg import Connection
from psycopg.types import TypeInfo

from app.config import DATABASE_URL

ENSURE_POSTGRES = Path(__file__).resolve().parent.parent / "scripts" / "ensure-postgres.sh"


def _register_list_as_vector(conn: Connection) -> None:
    info = TypeInfo.fetch(conn, "vector")
    if info is None:
        raise psycopg.ProgrammingError("vector type not found in the database")
    conn.adapters.register_dumper(list, type("", (VectorDumper,), {"oid": info.oid}))
    conn.adapters.register_dumper(list, type("", (VectorBinaryDumper,), {"oid": info.oid}))


def _is_unavailable(exc: BaseException) -> bool:
    message = str(exc).lower()
    return any(
        token in message
        for token in (
            "connection refused",
            "connection failed",
            "does not exist",
            "the database system is starting up",
        )
    )


def _ensure_local_postgres() -> None:
    if not ENSURE_POSTGRES.is_file():
        return
    subprocess.run(
        ["bash", str(ENSURE_POSTGRES)],
        check=False,
        capture_output=True,
        text=True,
    )


class PgAdapter:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or DATABASE_URL

    def _connect(self) -> Connection:
        try:
            return psycopg.connect(self.database_url)
        except psycopg.OperationalError as exc:
            if not _is_unavailable(exc):
                raise
            _ensure_local_postgres()
            return psycopg.connect(self.database_url)

    @contextmanager
    def connect(self) -> Iterator[Connection]:
        conn = self._connect()
        register_vector(conn)
        _register_list_as_vector(conn)
        try:
            yield conn
        finally:
            conn.close()
