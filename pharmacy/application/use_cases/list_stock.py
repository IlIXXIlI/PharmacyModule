"""Application use cases depend on ports, not on a specific database."""

from ..ports.database import DatabaseProvider
from ...domain.stock import StockRow


class ListStock:
    def __init__(self, database: DatabaseProvider) -> None:
        self._database = database

    def execute(self) -> list[StockRow]:
        with self._database.unit_of_work() as work:
            return list(work.inventory.list_stock())

