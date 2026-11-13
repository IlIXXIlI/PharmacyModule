from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...contracts.dto.stock import StockRow
from ...contracts.dto.sale_candidate import SaleCandidate
from ...contracts.database import InventoryRepository
from ..models import Batch as BatchModel
from ..models import Medicine as MedicineModel


class SQLAlchemyInventoryRepository(InventoryRepository[Session]):
    def list_stock(self, pharmacy_id: int | None = None) -> list[StockRow]:
        conditions = [BatchModel.current_quantity > 0]
        if pharmacy_id is not None:
            conditions.append(BatchModel.pharmacy_id == pharmacy_id)
        return self._list_stock(conditions)

    def list_expired_stock(
        self, current_date: date, pharmacy_id: int | None = None
    ) -> list[StockRow]:
        conditions = [
            BatchModel.current_quantity > 0,
            BatchModel.expiry_date < current_date,
        ]
        if pharmacy_id is not None:
            conditions.append(BatchModel.pharmacy_id == pharmacy_id)
        return self._list_stock(conditions)

    def _list_stock(self, conditions) -> list[StockRow]:
        statement = (
            select(
                MedicineModel.id,
                MedicineModel.name,
                MedicineModel.dosage,
                BatchModel.pharmacy_id,
                BatchModel.batch_number,
                BatchModel.expiry_date,
                BatchModel.current_quantity,
            )
            .join(BatchModel, BatchModel.medicine_id == MedicineModel.id)
            .where(*conditions)
            .order_by(BatchModel.expiry_date, MedicineModel.name)
        )
        rows = self.connection.execute(statement)
        return [
            StockRow(pharmacy_id, medicine_id, name, dosage, number, expiry.isoformat(), quantity)
            for medicine_id, name, dosage, pharmacy_id, number, expiry, quantity in rows
        ]

    def list_sale_candidates(
        self, pharmacy_id: int, current_date: date
    ) -> list[SaleCandidate]:
        statement = (
            select(
                BatchModel.pharmacy_id,
                MedicineModel.id,
                MedicineModel.name,
                MedicineModel.dosage,
                func.sum(BatchModel.current_quantity),
            )
            .join(BatchModel, BatchModel.medicine_id == MedicineModel.id)
            .where(
                BatchModel.pharmacy_id == pharmacy_id,
                BatchModel.current_quantity > 0,
                BatchModel.expiry_date >= current_date,
            )
            .group_by(
                BatchModel.pharmacy_id,
                MedicineModel.id,
                MedicineModel.name,
                MedicineModel.dosage,
            )
            .order_by(MedicineModel.name)
        )
        rows = self.connection.execute(statement)
        return [
            SaleCandidate(pharmacy, medicine_id, name, dosage, quantity)
            for pharmacy, medicine_id, name, dosage, quantity in rows
        ]
