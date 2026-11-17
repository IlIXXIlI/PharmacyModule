from datetime import date, datetime, timezone
from decimal import Decimal

from ..contracts.database import SaleUnitOfWorkFactory
from ..contracts.dto.reports import SalesReport
from ..contracts.dto.sales import SaleLine, SaleRequest, SaleResult
from .fefo import plan_fefo_allocation


class StockChangedDuringSale(RuntimeError):
    pass


class SaleService:
    def __init__(self, database: SaleUnitOfWorkFactory) -> None:
        self._database = database

    def sell_goods(
        self,
        pharmacy_id: int,
        user_id: int,
        medicine_id: int,
        quantity: int,
        sale_price: Decimal,
        sale_date: datetime | None = None,
    ) -> SaleResult:
        request = SaleRequest(
            pharmacy_id=pharmacy_id,
            user_id=user_id,
            items=(SaleLine(medicine_id, quantity, sale_price),),
            sale_date=sale_date or datetime.now(timezone.utc),
        )
        return self.execute(request)

    def sales_report(self, start_date: date, end_date: date,
                     pharmacy_id: int | None = None) -> SalesReport:
        if start_date > end_date:
            raise ValueError("Начало отчётного периода позже его окончания")
        with self._database.unit_of_work() as work:
            return work.sales.sales_report(start_date, end_date, pharmacy_id)

    def execute(self, request: SaleRequest) -> SaleResult:
        if not request.items:
            raise ValueError("В продаже должен быть указан конкретный товар")
        if min(request.pharmacy_id, request.user_id) <= 0:
            raise ValueError("ID аптеки и пользователя должны быть положительными")
        if request.sale_date.tzinfo is None:
            raise ValueError("Дата продажи должна содержать часовой пояс")
        if len({item.medicine_id for item in request.items}) != len(request.items):
            raise ValueError("Один препарат указывается в продаже только один раз")
        for item in request.items:
            if item.medicine_id <= 0 or item.quantity <= 0 or item.sale_price < 0:
                raise ValueError("Укажите препарат, положительное количество и цену не ниже нуля")

        sale_date = request.sale_date.astimezone(timezone.utc)
        sale_day = sale_date.date()
        plans = {}
        total = Decimal("0.00")

        with self._database.unit_of_work() as work:
            for item in sorted(request.items, key=lambda line: line.medicine_id):
                if work.medicines.get(item.medicine_id) is None:
                    raise LookupError(f"Препарат {item.medicine_id} не найден")
                batches = work.sales.lock_available_batches(
                    request.pharmacy_id, item.medicine_id, sale_day
                )
                plans[item.medicine_id] = plan_fefo_allocation(
                    batches, item.quantity, sale_day
                )
                total += item.sale_price * item.quantity

            sale_id = work.sales.create_sale(
                request.pharmacy_id, request.user_id, sale_date, total
            )
            for item in request.items:
                sale_item_id = work.sales.add_sale_item(
                    sale_id, item.medicine_id, item.quantity, item.sale_price
                )
                for allocation in plans[item.medicine_id]:
                    if not work.sales.decrease_batch_quantity(
                        allocation.batch_id, allocation.quantity
                    ):
                        raise StockChangedDuringSale(
                            f"Остаток партии {allocation.batch_id} изменился во время продажи"
                        )
                    work.sales.add_batch_allocation(
                        sale_item_id, allocation.batch_id, allocation.quantity
                    )

            return SaleResult(sale_id=sale_id, total_amount=total)

    def write_off_goods(self, pharmacy_id: int, user_id: int, medicine_id: int,
                        quantity: int, reason: str, write_off_date: date) -> int:
        if min(pharmacy_id, user_id, medicine_id, quantity) <= 0:
            raise ValueError("ID должны быть положительными, количество должно быть больше нуля")
        if not reason.strip():
            raise ValueError("Укажите причину списания")
        with self._database.unit_of_work() as work:
            if work.medicines.get(medicine_id) is None:
                raise LookupError(f"Препарат {medicine_id} не найден")
            batches = work.sales.lock_batches_for_write_off(pharmacy_id, medicine_id)
            allocations = plan_fefo_allocation(batches, quantity, write_off_date, include_expired=True)
            record_id = work.sales.create_write_off(
                pharmacy_id, user_id, datetime.combine(write_off_date, datetime.min.time(), tzinfo=timezone.utc), reason.strip()
            )
            for allocation in allocations:
                if not work.sales.decrease_batch_quantity(allocation.batch_id, allocation.quantity):
                    raise StockChangedDuringSale(f"Остаток партии {allocation.batch_id} изменился во время списания")
                work.sales.add_write_off_allocation(record_id, allocation.batch_id, allocation.quantity)
            return record_id
