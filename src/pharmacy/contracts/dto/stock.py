from dataclasses import dataclass


@dataclass(frozen=True)
class StockRow:
    pharmacy_id: int
    medicine_id: int
    medicine_name: str
    dosage: str
    batch_number: str
    expiry_date: str
    quantity: int
