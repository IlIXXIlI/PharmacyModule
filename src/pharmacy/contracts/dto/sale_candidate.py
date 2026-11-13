from dataclasses import dataclass


@dataclass(frozen=True)
class SaleCandidate:
    pharmacy_id: int
    medicine_id: int
    medicine_name: str
    dosage: str
    available_quantity: int
