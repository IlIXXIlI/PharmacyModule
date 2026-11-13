from dataclasses import dataclass


@dataclass(frozen=True)
class Supplier:
    id: int | None
    name: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None
