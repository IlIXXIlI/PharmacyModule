from datetime import date

from ..contracts.database import InventoryUnitOfWorkFactory
from ..contracts.dto.sale_candidate import SaleCandidate
from ..contracts.dto.stock import StockRow


class StockService:
    def __init__(self, database: InventoryUnitOfWorkFactory) -> None:
        self._database = database

    def get_stock(self, pharmacy_id: int | None = None) -> list[StockRow]:
        with self._database.unit_of_work() as work:
            return list(work.inventory.list_stock(pharmacy_id))

    def get_items_for_write_off(
        self, pharmacy_id: int | None = None, current_date: date | None = None
    ) -> list[StockRow]:
        as_of = current_date or date.today()
        with self._database.unit_of_work() as work:
            return list(work.inventory.list_expired_stock(as_of, pharmacy_id))

    def get_goods_for_sale(
        self, pharmacy_id: int, current_date: date | None = None
    ) -> list[SaleCandidate]:
        if pharmacy_id <= 0:
            raise ValueError("ID аптеки должен быть положительным")
        as_of = current_date or date.today()
        with self._database.unit_of_work() as work:
            return list(work.inventory.list_sale_candidates(pharmacy_id, as_of))
