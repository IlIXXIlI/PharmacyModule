from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: int | None
    pharmacy_id: int
    full_name: str
    login: str
    password_hash: str
    role: str
