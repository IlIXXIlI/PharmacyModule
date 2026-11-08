"""Shared application contracts for all persistence adapters."""

from abc import ABC, abstractmethod
from typing import Generic, Sequence, TypeVar

from ...domain.stock import StockRow

ConnectionT = TypeVar("ConnectionT")


class BaseRepository(ABC, Generic[ConnectionT]):
    """Shared repository base; the concrete adapter supplies its connection."""

    def __init__(self, connection: ConnectionT) -> None:
        self.connection = connection


class InventoryRepository(BaseRepository[ConnectionT], ABC):
    @abstractmethod
    def list_stock(self) -> Sequence[StockRow]:
        """Return available inventory in the application's common format."""


class BaseUnitOfWork(ABC):
    """Shared transaction boundary: commit or rollback, then close resources."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        try:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
        finally:
            self.close()
        return False

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...


class BaseDatabaseProvider(ABC):
    """Infrastructure factory contract implemented by each database backend."""

    @abstractmethod
    def initialize(self) -> None: ...

    @abstractmethod
    def unit_of_work(self) -> BaseUnitOfWork: ...

    @abstractmethod
    def seed_demo(self) -> None: ...


# Aliases retained for dependency wiring and type annotations.
DatabaseProvider = BaseDatabaseProvider
UnitOfWork = BaseUnitOfWork

