from dataclasses import dataclass


@dataclass(frozen=True)
class Medicine:
    id: int | None
    name: str
    manufacturer: str
    dosage: str
    form: str
    barcode: str | None = None
