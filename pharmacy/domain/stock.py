"""Domain representation of a pharmacy stock row."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StockRow:
    medicine_name: str
    dosage: str
    batch_number: str
    expiry_date: str
    quantity: int
