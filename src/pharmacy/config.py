from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    database_backend: str
    sqlite_database_path: str
    postgres_dsn: str
    persistence_strategy: str = "sqlalchemy"

    @classmethod
    def from_environment(cls) -> "Settings":
        # Переменные окружения имеют приоритет над значениями из файла .env.
        load_dotenv()
        return cls(
            database_backend=os.getenv("DATABASE_BACKEND", "sqlite"),
            persistence_strategy=os.getenv("PERSISTENCE_STRATEGY", "sqlalchemy"),
            sqlite_database_path=os.getenv("SQLITE_DATABASE_PATH", "data/pharmacy.db"),
            postgres_dsn=os.getenv("POSTGRES_DSN", ""),
        )

