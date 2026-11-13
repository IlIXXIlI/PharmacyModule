from typing import Protocol

from ..contracts.database import BaseDatabaseProvider
from ..config import Settings


class PersistenceStrategy(Protocol):
    def create_provider(
        self, settings: Settings, database_backend: str
    ) -> BaseDatabaseProvider: ...


class PersistenceDependencyError(RuntimeError):
    pass


class PersistenceStrategyRegistry:
    def __init__(self) -> None:
        self._strategies: dict[str, PersistenceStrategy] = {}

    def register(self, name: str, strategy: PersistenceStrategy) -> None:
        normalized_name = name.strip().lower()
        if not normalized_name:
            raise ValueError("Persistence strategy name must not be empty")
        if normalized_name in self._strategies:
            raise ValueError(f"Persistence strategy '{normalized_name}' is already registered")
        self._strategies[normalized_name] = strategy

    def create_provider(
        self,
        name: str,
        settings: Settings,
        database_backend: str,
    ) -> BaseDatabaseProvider:
        normalized_name = name.strip().lower()
        try:
            strategy = self._strategies[normalized_name]
        except KeyError as error:
            available = ", ".join(sorted(self._strategies)) or "none"
            raise ValueError(
                f"Unknown persistence strategy '{name}'. Registered strategies: {available}"
            ) from error
        try:
            return strategy.create_provider(settings, database_backend)
        except ModuleNotFoundError as error:
            dependency = error.name or "unknown package"
            if dependency == "sqlalchemy":
                install_hint = "Install project dependencies with: pip install -r requirements.txt"
            elif dependency.startswith("psycopg"):
                install_hint = (
                    "Install PostgreSQL dependencies with: "
                    "pip install -r requirements-postgres.txt"
                )
            else:
                install_hint = f"Install the '{dependency}' dependency for this strategy"
            raise PersistenceDependencyError(
                f"Persistence strategy '{normalized_name}' requires '{dependency}'. {install_hint}"
            ) from error


class SQLAlchemyStrategy:
    def create_provider(
        self, settings: Settings, database_backend: str
    ) -> BaseDatabaseProvider:
        from .postgres import PostgresProvider
        from .sqlite import SQLiteProvider

        if database_backend == "sqlite":
            return SQLiteProvider(settings.sqlite_database_path)
        if database_backend == "postgres":
            return PostgresProvider(settings.postgres_dsn)
        raise ValueError(f"Unknown database backend: {database_backend}")


PERSISTENCE_STRATEGIES = PersistenceStrategyRegistry()
PERSISTENCE_STRATEGIES.register("sqlalchemy", SQLAlchemyStrategy())


def register_persistence_strategy(name: str, strategy: PersistenceStrategy) -> None:
    PERSISTENCE_STRATEGIES.register(name, strategy)


def create_database(
    settings: Settings,
    backend: str | None = None,
    persistence_strategy: str | None = None,
) -> BaseDatabaseProvider:
    return PERSISTENCE_STRATEGIES.create_provider(
        persistence_strategy or settings.persistence_strategy,
        settings,
        backend or settings.database_backend,
    )
