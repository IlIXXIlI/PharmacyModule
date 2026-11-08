"""Application infrastructure composition root (dependency injection)."""

from ...application.ports.database import DatabaseProvider
from ...config import Settings
from .postgres.adapter import PostgresProvider
from .sqlite.adapter import SQLiteProvider


def create_database(settings: Settings, backend: str | None = None) -> DatabaseProvider:
    """Select a backend. Add a provider branch to support another database."""
    selected_backend = backend or settings.database_backend
    if selected_backend == "sqlite":
        return SQLiteProvider(settings.sqlite_database_path)
    if selected_backend == "postgres":
        return PostgresProvider(settings.postgres_dsn)
    raise ValueError(f"Неизвестный backend БД: {selected_backend}")

