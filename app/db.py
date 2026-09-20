"""Database adapter contract.

Callers (ingest, retrieve) type-hint this Protocol, open a connection with
connect(), and run their own SQL. The Protocol does not expose ingest or
retrieve queries.

The connection returned by connect() must accept Python lists of floats as
bind parameters for PostgreSQL vector(384) columns.
"""

from contextlib import AbstractContextManager
from typing import Any, Protocol


class DatabaseAdapter(Protocol):
    def connect(self) -> AbstractContextManager[Any]:
        """Yield a connection, or return one that the caller can close().

        Bind params for embeddings are Python lists of 384 floats.
        """
        ...
