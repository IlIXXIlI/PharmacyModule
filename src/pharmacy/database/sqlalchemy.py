from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from .repositories.sqlalchemy_inventory_repository import SQLAlchemyInventoryRepository
from .repositories.sqlalchemy_medicine_repository import SQLAlchemyMedicineRepository
from .repositories.sqlalchemy_receipt_repository import SQLAlchemyReceiptRepository
from .repositories.sqlalchemy_sales_repository import SQLAlchemySalesRepository
from .repositories.sqlalchemy_supplier_repository import SQLAlchemySupplierRepository
from ..contracts.database import BaseDatabaseProvider, BaseUnitOfWork
from .models import Base


class SQLAlchemyUnitOfWork(BaseUnitOfWork):
    def __init__(self, session: Session) -> None:
        self.session = session
        self.inventory = SQLAlchemyInventoryRepository(session)
        self.medicines = SQLAlchemyMedicineRepository(session)
        self.suppliers = SQLAlchemySupplierRepository(session)
        self.receipts = SQLAlchemyReceiptRepository(session)
        self.sales = SQLAlchemySalesRepository(session)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def close(self) -> None:
        self.session.close()


class SQLAlchemyProvider(BaseDatabaseProvider):
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def initialize(self) -> None:
        Base.metadata.create_all(self.engine)

    def unit_of_work(self) -> SQLAlchemyUnitOfWork:
        return SQLAlchemyUnitOfWork(self._session_factory())

