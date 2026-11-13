from ..contracts.database import ReceiptUnitOfWorkFactory
from ..contracts.dto.receiving import ReceiptRequest


class ReceiptService:
    def __init__(self, database: ReceiptUnitOfWorkFactory) -> None:
        self._database = database

    def add_goods(self, request: ReceiptRequest) -> int:
        if not request.items:
            raise ValueError("В поступлении должна быть хотя бы одна строка")
        if not request.document_number.strip():
            raise ValueError("Номер документа поступления не должен быть пустым")
        if min(request.supplier_id, request.pharmacy_id, request.user_id) <= 0:
            raise ValueError("ID поставщика, аптеки и пользователя должны быть положительными")

        with self._database.unit_of_work() as work:
            if work.suppliers.get(request.supplier_id) is None:
                raise LookupError(f"Поставщик {request.supplier_id} не найден")

            medicine_ids: set[int] = set()
            for item in request.items:
                if item.medicine_id <= 0 or item.medicine_id in medicine_ids:
                    raise ValueError("Препарат должен быть указан один раз с положительным ID")
                medicine_ids.add(item.medicine_id)
                if work.medicines.get(item.medicine_id) is None:
                    raise LookupError(f"Препарат {item.medicine_id} не найден")
                if item.quantity <= 0 or item.purchase_price < 0:
                    raise ValueError("Количество должно быть положительным, цена — неотрицательной")
                if not item.batches:
                    raise ValueError("Для каждой строки поступления укажите хотя бы одну партию")
                if sum(batch.quantity for batch in item.batches) != item.quantity:
                    raise ValueError("Сумма количеств партий должна совпадать со строкой поступления")

                for batch in item.batches:
                    if batch.quantity <= 0 or not batch.batch_number.strip():
                        raise ValueError("У партии должны быть номер и положительное количество")
                    if batch.expiry_date < batch.production_date:
                        raise ValueError("Срок годности не может быть раньше даты производства")
                    if batch.production_date > request.receipt_date:
                        raise ValueError("Дата производства не может быть позже даты поступления")
                    if batch.expiry_date < request.receipt_date:
                        raise ValueError("Просроченную партию нельзя принять на склад")

            return work.receipts.record_receipt(request)
