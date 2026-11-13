from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class SaleLine:
    medicine_id: int
    quantity: int
    sale_price: Decimal


@dataclass(frozen=True)
class SaleRequest:
    pharmacy_id: int
    user_id: int
    items: tuple[SaleLine, ...]
    sale_date: datetime


@dataclass(frozen=True)
class SaleResult:
    sale_id: int
    total_amount: Decimal

