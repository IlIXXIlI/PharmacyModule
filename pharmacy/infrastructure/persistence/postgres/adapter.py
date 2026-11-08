"""PostgreSQL engine configuration for the shared SQLAlchemy persistence layer."""

from sqlalchemy import create_engine

from ..sqlalchemy import SQLAlchemyProvider


class PostgresProvider(SQLAlchemyProvider):
    def __init__(self, dsn: str) -> None:
        if not dsn:
            raise ValueError("Set POSTGRES_DSN in the .env file to use PostgreSQL")
        normalized_dsn = dsn
        if normalized_dsn.startswith("postgres://"):
            normalized_dsn = normalized_dsn.replace("postgres://", "postgresql+psycopg://", 1)
        elif normalized_dsn.startswith("postgresql://"):
            normalized_dsn = normalized_dsn.replace("postgresql://", "postgresql+psycopg://", 1)
        super().__init__(create_engine(normalized_dsn))
