from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal
from typing import Generic, Protocol, Sequence, TypeVar

from .dto.stock import StockRow
from .dto.sale_candidate import SaleCandidate
from .dto.receiving import ReceiptRequest
from ..entities import Batch, Medicine, Supplier

ConnectionT = TypeVar("ConnectionT")


class BaseRepository(ABC, Generic[ConnectionT]):
    def __init__(self, connection: ConnectionT) -> None:
        self.connection = connection


class InventoryRepository(BaseRepository[ConnectionT], ABC):
    @abstractmethod
    def list_stock(self, pharmacy_id: int | None = None) -> Sequence[StockRow]:
        ...

    @abstractmethod
    def list_expired_stock(
        self, current_date: date, pharmacy_id: int | None = None
    ) -> Sequence[StockRow]: ...

    @abstractmethod
    def list_sale_candidates(
        self, pharmacy_id: int, current_date: date
    ) -> Sequence[SaleCandidate]: ...


class MedicineRepository(BaseRepository[ConnectionT], ABC):
    @abstractmethod
    def get(self, medicine_id: int) -> Medicine | None: ...

    @abstractmethod
    def list_all(self) -> Sequence[Medicine]: ...

    @abstractmethod
    def add(self, medicine: Medicine) -> Medicine: ...

    @abstractmethod
    def update(self, medicine: Medicine) -> Medicine: ...

    @abstractmethod
    def delete(self, medicine_id: int) -> None: ...


class SupplierRepository(BaseRepository[ConnectionT], ABC):
    @abstractmethod
    def get(self, supplier_id: int) -> Supplier | None: ...

    @abstractmethod
    def list_all(self) -> Sequence[Supplier]: ...

    @abstractmethod
    def add(self, supplier: Supplier) -> Supplier: ...

    @abstractmethod
    def update(self, supplier: Supplier) -> Supplier: ...

    @abstractmethod
    def delete(self, supplier_id: int) -> None: ...


class ReceiptRepository(BaseRepository[ConnectionT], ABC):
    @abstractmethod
    def record_receipt(self, request: ReceiptRequest) -> int: ...


class SalesRepository(BaseRepository[ConnectionT], ABC):
    @abstractmethod
    def lock_available_batches(
        self, pharmacy_id: int, medicine_id: int, current_date: date
    ) -> Sequence[Batch]: ...

    @abstractmethod
    def decrease_batch_quantity(self, batch_id: int, quantity: int) -> bool: ...

    @abstractmethod
    def create_sale(
        self, pharmacy_id: int, user_id: int, sale_date: datetime, total_amount: Decimal
    ) -> int: ...

    @abstractmethod
    def add_sale_item(
        self, sale_id: int, medicine_id: int, quantity: int, sale_price: Decimal
    ) -> int: ...

    @abstractmethod
    def add_batch_allocation(self, sale_item_id: int, batch_id: int, quantity: int) -> None: ...


class BaseUnitOfWork(ABC):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        try:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
        finally:
            self.close()
        return False

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...


class InventoryUnitOfWork(Protocol):
    inventory: InventoryRepository

    def __enter__(self): ...

    def __exit__(self, exc_type, exc, traceback) -> bool: ...


class InventoryUnitOfWorkFactory(Protocol):
    def unit_of_work(self) -> InventoryUnitOfWork: ...


class CatalogUnitOfWork(Protocol):
    medicines: MedicineRepository
    suppliers: SupplierRepository

    def __enter__(self): ...

    def __exit__(self, exc_type, exc, traceback) -> bool: ...


class CatalogUnitOfWorkFactory(Protocol):
    def unit_of_work(self) -> CatalogUnitOfWork: ...


class ReceiptUnitOfWork(Protocol):
    medicines: MedicineRepository
    suppliers: SupplierRepository
    receipts: ReceiptRepository

    def __enter__(self): ...

    def __exit__(self, exc_type, exc, traceback) -> bool: ...


class ReceiptUnitOfWorkFactory(Protocol):
    def unit_of_work(self) -> ReceiptUnitOfWork: ...


class SaleUnitOfWork(Protocol):
    medicines: MedicineRepository
    sales: SalesRepository

    def __enter__(self): ...

    def __exit__(self, exc_type, exc, traceback) -> bool: ...


class SaleUnitOfWorkFactory(Protocol):
    def unit_of_work(self) -> SaleUnitOfWork: ...


class BaseDatabaseProvider(ABC):
    @abstractmethod
    def initialize(self) -> None: ...

    @abstractmethod
    def unit_of_work(self) -> BaseUnitOfWork: ...


DatabaseProvider = BaseDatabaseProvider
UnitOfWork = BaseUnitOfWork

