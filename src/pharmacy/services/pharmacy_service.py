from datetime import date, datetime
from decimal import Decimal

from ..contracts.database import BaseDatabaseProvider
from ..contracts.dto.receiving import ReceiptRequest
from ..contracts.dto.sale_candidate import SaleCandidate
from ..contracts.dto.sales import SaleResult
from ..contracts.dto.stock import StockRow
from ..entities import Medicine, Supplier
from .catalog_service import CatalogService
from .receipt_service import ReceiptService
from .sale_service import SaleService
from .stock_service import StockService


class PharmacyService:
    def __init__(self, database: BaseDatabaseProvider) -> None:
        self._stock = StockService(database)
        self._receipts = ReceiptService(database)
        self._sales = SaleService(database)
        self._catalog = CatalogService(database)

    def list_medicines(self) -> list[Medicine]:
        return self._catalog.list_medicines()

    def add_medicine(self, medicine: Medicine) -> Medicine:
        return self._catalog.add_medicine(medicine)

    def list_suppliers(self) -> list[Supplier]:
        return self._catalog.list_suppliers()

    def add_supplier(self, supplier: Supplier) -> Supplier:
        return self._catalog.add_supplier(supplier)

    def get_stock(self, pharmacy_id: int | None = None) -> list[StockRow]:
        return self._stock.get_stock(pharmacy_id)

    def get_items_for_write_off(
        self, pharmacy_id: int | None = None, current_date: date | None = None
    ) -> list[StockRow]:
        return self._stock.get_items_for_write_off(pharmacy_id, current_date)

    def get_goods_for_sale(
        self, pharmacy_id: int, current_date: date | None = None
    ) -> list[SaleCandidate]:
        return self._stock.get_goods_for_sale(pharmacy_id, current_date)

    def add_goods(self, request: ReceiptRequest) -> int:
        return self._receipts.add_goods(request)

    def sell_goods(
        self,
        pharmacy_id: int,
        user_id: int,
        medicine_id: int,
        quantity: int,
        sale_price: Decimal,
        sale_date: datetime | None = None,
    ) -> SaleResult:
        return self._sales.sell_goods(
            pharmacy_id,
            user_id,
            medicine_id,
            quantity,
            sale_price,
            sale_date,
        )
