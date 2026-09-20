from contextlib import AbstractContextManager
from typing import Any, Protocol


class DatabaseAdapter(Protocol):
    def connect(self) -> AbstractContextManager[Any]:
        ...
