"""Application settings loaded from .env and process environment."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    database_backend: str
    sqlite_database_path: str
    postgres_dsn: str

    @classmethod
    def from_environment(cls) -> "Settings":
        # Existing process environment variables take precedence over .env values.
        load_dotenv()
        return cls(
            database_backend=os.getenv("DATABASE_BACKEND", "sqlite"),
            sqlite_database_path=os.getenv("SQLITE_DATABASE_PATH", "data/pharmacy.db"),
            postgres_dsn=os.getenv("POSTGRES_DSN", ""),
        )

