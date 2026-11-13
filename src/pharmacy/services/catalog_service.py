from ..contracts.database import CatalogUnitOfWorkFactory
from ..entities import Medicine, Supplier


class CatalogService:
    def __init__(self, database: CatalogUnitOfWorkFactory) -> None:
        self._database = database

    def list_medicines(self) -> list[Medicine]:
        with self._database.unit_of_work() as work:
            return list(work.medicines.list_all())

    def add_medicine(self, medicine: Medicine) -> Medicine:
        _require_text(medicine.name, "Название препарата")
        _require_text(medicine.manufacturer, "Производитель")
        _require_text(medicine.dosage, "Дозировка")
        _require_text(medicine.form, "Форма выпуска")
        with self._database.unit_of_work() as work:
            return work.medicines.add(medicine)

    def list_suppliers(self) -> list[Supplier]:
        with self._database.unit_of_work() as work:
            return list(work.suppliers.list_all())

    def add_supplier(self, supplier: Supplier) -> Supplier:
        _require_text(supplier.name, "Название поставщика")
        with self._database.unit_of_work() as work:
            return work.suppliers.add(supplier)


def _require_text(value: str, field_name: str) -> None:
    if not value or not value.strip():
        raise ValueError(f"{field_name} не должно быть пустым")
