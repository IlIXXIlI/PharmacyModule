from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class ReceivedBatch:
    batch_number: str
    production_date: date
    expiry_date: date
    quantity: int


@dataclass(frozen=True)
class ReceiptLine:
    medicine_id: int
    quantity: int
    purchase_price: Decimal
    batches: tuple[ReceivedBatch, ...]


@dataclass(frozen=True)
class ReceiptRequest:
    supplier_id: int
    pharmacy_id: int
    user_id: int
    receipt_date: date
    document_number: str
    items: tuple[ReceiptLine, ...]

