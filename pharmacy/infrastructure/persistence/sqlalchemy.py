"""SQLAlchemy-backed persistence shared by SQLite, PostgreSQL, and other SQL engines."""

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from ...application.ports.database import BaseDatabaseProvider, BaseUnitOfWork, InventoryRepository
from ...domain.models import Base
from ...domain.stock import StockRow
from .seed import seed_demo_data


class SQLAlchemyUnitOfWork(BaseUnitOfWork):
    def __init__(self, session: Session) -> None:
        self.session = session
        self.inventory = SQLAlchemyInventoryRepository(session)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def close(self) -> None:
        self.session.close()


class SQLAlchemyInventoryRepository(InventoryRepository):
    """ORM repository shared by all SQLAlchemy-compatible databases."""

    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def list_stock(self) -> list[StockRow]:
        """Return positive stock balances ordered by expiry date."""
        from sqlalchemy import select

        from ...domain.models import Batch, Medicine
        statement = (
            select(Medicine.name, Medicine.dosage, Batch.batch_number,
                   Batch.expiry_date, Batch.current_quantity)
            .join(Batch, Batch.medicine_id == Medicine.id)
            .where(Batch.current_quantity > 0)
            .order_by(Batch.expiry_date, Medicine.name)
        )
        return [StockRow(name, dosage, number, expiry.isoformat(), quantity)
                for name, dosage, number, expiry, quantity in self.connection.execute(statement)]


class SQLAlchemyProvider(BaseDatabaseProvider):
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def initialize(self) -> None:
        Base.metadata.create_all(self.engine)

    def unit_of_work(self) -> SQLAlchemyUnitOfWork:
        return SQLAlchemyUnitOfWork(self._session_factory())

    def seed_demo(self) -> None:
        with self.unit_of_work() as work:
            seed_demo_data(work.session)

