from ..contracts.database import InventoryUnitOfWorkFactory
from ..contracts.dto.stock import StockRow


class ListStock:
    def __init__(self, database: InventoryUnitOfWorkFactory) -> None:
        self._database = database

    def execute(self, pharmacy_id: int | None = None) -> list[StockRow]:
        with self._database.unit_of_work() as work:
            return list(work.inventory.list_stock(pharmacy_id))

