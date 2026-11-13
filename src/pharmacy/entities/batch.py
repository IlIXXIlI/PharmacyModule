from dataclasses import dataclass
from datetime import date


class InsufficientBatchStock(ValueError):
    pass


@dataclass
class Batch:
    id: int
    pharmacy_id: int
    medicine_id: int
    batch_number: str
    expiry_date: date
    initial_quantity: int
    current_quantity: int

    def is_available_on(self, current_date: date) -> bool:
        return self.current_quantity > 0 and self.expiry_date >= current_date

    def withdraw(self, quantity: int, current_date: date) -> None:
        if quantity <= 0:
            raise ValueError("Withdrawal quantity must be positive")
        if not self.is_available_on(current_date):
            raise InsufficientBatchStock("Batch is expired or has no available stock")
        if quantity > self.current_quantity:
            raise InsufficientBatchStock("Requested quantity exceeds batch stock")
        self.current_quantity -= quantity
