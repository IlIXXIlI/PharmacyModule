from dataclasses import dataclass
from datetime import date
from typing import Sequence

from ..entities import Batch


class InsufficientStock(ValueError):
    pass


@dataclass(frozen=True)
class BatchAllocation:
    batch_id: int
    quantity: int


def plan_fefo_allocation(
    batches: Sequence[Batch], quantity: int, current_date: date, *, include_expired: bool = False
) -> list[BatchAllocation]:
    """Распределяет количество по годным партиям, не изменяя их остатки."""
    if quantity <= 0:
        raise ValueError("Количество для продажи должно быть положительным")

    eligible = sorted(
        (batch for batch in batches if batch.current_quantity > 0 and (include_expired or batch.expiry_date >= current_date)),
        key=lambda batch: (batch.expiry_date, batch.id),
    )
    if sum(batch.current_quantity for batch in eligible) < quantity:
        raise InsufficientStock("Недостаточно товара для операции")

    remaining = quantity
    allocation: list[BatchAllocation] = []
    for batch in eligible:
        amount = min(batch.current_quantity, remaining)
        allocation.append(BatchAllocation(batch_id=batch.id, quantity=amount))
        remaining -= amount
        if remaining == 0:
            break
    return allocation
