from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ...contracts.database import SalesRepository
from ...entities import Batch
from ..models import (
    Batch as BatchModel,
    Sale as SaleModel,
    SaleBatchItem as SaleBatchItemModel,
    SaleItem as SaleItemModel,
)


class SQLAlchemySalesRepository(SalesRepository[Session]):
    def lock_available_batches(
        self, pharmacy_id: int, medicine_id: int, current_date: date
    ) -> list[Batch]:
        statement = (
            select(BatchModel)
            .where(
                BatchModel.pharmacy_id == pharmacy_id,
                BatchModel.medicine_id == medicine_id,
                BatchModel.expiry_date >= current_date,
                BatchModel.current_quantity > 0,
            )
            .order_by(BatchModel.expiry_date, BatchModel.id)
            .with_for_update()
        )
        models = self.connection.scalars(statement)
        return [
            Batch(
                id=model.id,
                pharmacy_id=model.pharmacy_id,
                medicine_id=model.medicine_id,
                batch_number=model.batch_number,
                expiry_date=model.expiry_date,
                initial_quantity=model.initial_quantity,
                current_quantity=model.current_quantity,
            )
            for model in models
        ]

    def decrease_batch_quantity(self, batch_id: int, quantity: int) -> bool:
        statement = (
            update(BatchModel)
            .where(BatchModel.id == batch_id, BatchModel.current_quantity >= quantity)
            .values(current_quantity=BatchModel.current_quantity - quantity)
            .execution_options(synchronize_session=False)
        )
        result = self.connection.execute(statement)
        return result.rowcount == 1

    def create_sale(
        self, pharmacy_id: int, user_id: int, sale_date: datetime, total_amount: Decimal
    ) -> int:
        sale = SaleModel(
            pharmacy_id=pharmacy_id,
            user_id=user_id,
            sale_date=sale_date,
            total_amount=total_amount,
            status="completed",
        )
        self.connection.add(sale)
        self.connection.flush()
        return sale.id

    def add_sale_item(
        self, sale_id: int, medicine_id: int, quantity: int, sale_price: Decimal
    ) -> int:
        item = SaleItemModel(
            sale_id=sale_id,
            medicine_id=medicine_id,
            quantity=quantity,
            sale_price=sale_price,
        )
        self.connection.add(item)
        self.connection.flush()
        return item.id

    def add_batch_allocation(self, sale_item_id: int, batch_id: int, quantity: int) -> None:
        self.connection.add(SaleBatchItemModel(
            sale_item_id=sale_item_id,
            batch_id=batch_id,
            quantity=quantity,
        ))
