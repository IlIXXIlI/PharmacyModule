from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SalesReport:
    sales_count: int
    total_amount: Decimal
    items: tuple[tuple[str, int, Decimal], ...]
