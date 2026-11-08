"""SQLite engine configuration for the shared SQLAlchemy persistence layer."""

from pathlib import Path

from sqlalchemy import create_engine, event

from ..sqlalchemy import SQLAlchemyProvider


class SQLiteProvider(SQLAlchemyProvider):
    def __init__(self, database_path: str | Path) -> None:
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(f"sqlite:///{path}")

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _record) -> None:
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        super().__init__(engine)
