from sqlalchemy import inspect, select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.schema import CreateTable

from pharmacy.domain.models import Base, Medicine, Pharmacy, User
from pharmacy.infrastructure.persistence.sqlite.adapter import SQLiteProvider


EXPECTED_TABLES = {
    "PHARMACIES",
    "USERS",
    "MEDICINES",
    "SUPPLIERS",
    "RECEIPTS",
    "RECEIPT_ITEMS",
    "BATCHES",
    "SALES",
    "SALE_ITEMS",
    "SALE_BATCH_ITEMS",
}


def test_shared_base_contains_all_er_tables():
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_model_ddl_compiles_for_sqlite_and_postgres():
    sqlite_ddl = str(CreateTable(Pharmacy.__table__).compile(dialect=sqlite.dialect()))
    postgres_ddl = str(CreateTable(Pharmacy.__table__).compile(dialect=postgresql.dialect()))

    assert "PHARMACIES" in sqlite_ddl
    assert "PHARMACIES" in postgres_ddl
    assert "BIGSERIAL" in postgres_ddl or "IDENTITY" in postgres_ddl


def test_sqlite_provider_creates_all_tables(tmp_path):
    provider = SQLiteProvider(tmp_path / "pharmacy.db")

    provider.initialize()

    with provider.engine.connect() as connection:
        actual_tables = set(inspect(connection).get_table_names())
    assert EXPECTED_TABLES <= actual_tables


def test_seed_and_list_stock_share_the_same_repository(tmp_path):
    provider = SQLiteProvider(tmp_path / "pharmacy.db")
    provider.initialize()

    provider.seed_demo()
    with provider.unit_of_work() as work:
        stock = work.inventory.list_stock()

    assert len(stock) == 2
    assert [row.medicine_name for row in stock] == ["Ибупрофен", "Парацетамол"]
    assert [row.quantity for row in stock] == [60, 100]


def test_unit_of_work_rolls_back_on_exception(tmp_path):
    provider = SQLiteProvider(tmp_path / "pharmacy.db")
    provider.initialize()

    try:
        with provider.unit_of_work() as work:
            work.session.add(Pharmacy(name="Temporary", address="Temporary"))
            raise RuntimeError("force rollback")
    except RuntimeError:
        pass

    with provider.unit_of_work() as work:
        pharmacies = work.session.scalars(select(Pharmacy)).all()
    assert pharmacies == []


def test_unit_of_work_creates_and_persists_database_records(tmp_path):
    provider = SQLiteProvider(tmp_path / "pharmacy.db")
    provider.initialize()

    with provider.unit_of_work() as work:
        pharmacy = Pharmacy(name="Аптека тест", address="Москва")
        work.session.add(pharmacy)
        work.session.flush()
        user = User(pharmacy_id=pharmacy.id, full_name="Тестовый пользователь",
                    login="test-user", password_hash="test-hash", role="pharmacist")
        medicine = Medicine(name="Тестовый препарат", manufacturer="Тест",
                            dosage="100 мг", form="таблетки", barcode="test-001")
        work.session.add_all([user, medicine])

    with provider.unit_of_work() as work:
        saved_pharmacy = work.session.scalar(select(Pharmacy).where(Pharmacy.name == "Аптека тест"))
        saved_user = work.session.scalar(select(User).where(User.login == "test-user"))
        saved_medicine = work.session.scalar(select(Medicine).where(Medicine.barcode == "test-001"))

    assert saved_pharmacy is not None
    assert saved_user is not None
    assert saved_user.pharmacy_id == saved_pharmacy.id
    assert saved_medicine is not None
