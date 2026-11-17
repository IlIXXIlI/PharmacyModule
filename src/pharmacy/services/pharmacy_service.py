from datetime import date, datetime
from decimal import Decimal

from ..contracts.database import BaseDatabaseProvider
from ..contracts.dto.receiving import ReceiptRequest
from ..contracts.dto.sale_candidate import SaleCandidate
from ..contracts.dto.sales import SaleResult
from ..contracts.dto.stock import StockRow
from ..contracts.dto.reports import SalesReport
from ..entities import Medicine, Supplier
from .catalog_service import CatalogService
from .receipt_service import ReceiptService
from .sale_service import SaleService
from .stock_service import StockService


class PharmacyService:
    def __init__(self, database: BaseDatabaseProvider,
                 stock: StockService | None = None,
                 receipts: ReceiptService | None = None,
                 sales: SaleService | None = None,
                 catalog: CatalogService | None = None
                 ) -> None:
        if stock is None:
            self._stock = StockService(database)
        else :
            self._stock = stock

        if receipts is None:
            self._receipts = ReceiptService(database)
        else:
            self._receipts = receipts

        if sales is None:
            self._sales = SaleService(database)
        else:
            self._sales = sales

        if catalog is None:
            self._catalog = CatalogService(database)
        else:
            self._catalog = catalog


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

    def write_off_goods(self, pharmacy_id: int, user_id: int, medicine_id: int,
                        quantity: int, reason: str, write_off_date: date | None = None) -> int:
        return self._sales.write_off_goods(
            pharmacy_id, user_id, medicine_id, quantity, reason, write_off_date or date.today()
        )

    def get_sales_report(self, start_date: date, end_date: date,
                         pharmacy_id: int | None = None) -> SalesReport:
        return self._sales.sales_report(start_date, end_date, pharmacy_id)
