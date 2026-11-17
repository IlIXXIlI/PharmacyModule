import re
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.schema import CreateTable

from pharmacy.services.list_stock import ListStock
from pharmacy.config import Settings
from pharmacy.database.models import (
    Base,
    Batch as BatchModel,
    Medicine,
    Pharmacy,
    Sale,
    SaleBatchItem,
    SaleItem,
    User,
)
from pharmacy.database.providers import (
    PersistenceDependencyError,
    PersistenceStrategyRegistry,
)
from pharmacy.database.seed import seed_demo_data
from pharmacy.database.sqlite import SQLiteProvider
from pharmacy.cli import main as cli_main
from pharmacy.contracts.dto.receiving import ReceivedBatch, ReceiptLine, ReceiptRequest
from pharmacy.entities import Batch as BatchEntity
from pharmacy.services.fefo import InsufficientStock, plan_fefo_allocation
from pharmacy.services.pharmacy_service import PharmacyService


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
    "WRITE_OFFS",
    "WRITE_OFF_BATCH_ITEMS",
}


def test_shared_base_contains_all_er_tables():
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_er_source_matches_orm_table_names_and_columns():
    diagram_path = Path(__file__).parents[1] / "docs" / "diagrams" / "er-model.mmd"
    source = diagram_path.read_text(encoding="utf-8")
    entities = re.findall(
        r"^    ([A-Z_]+) \{\n(.*?)^    \}", source,
        flags=re.MULTILINE | re.DOTALL,
    )
    diagram_columns = {
        table: {line.split()[1] for line in body.splitlines() if line.strip()}
        for table, body in entities
    }
    model_columns = {
        table_name: set(table.columns.keys())
        for table_name, table in Base.metadata.tables.items()
    }

    assert set(diagram_columns) == EXPECTED_TABLES
    assert diagram_columns == model_columns


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


def test_seed_and_stock_query_use_the_same_database(tmp_path):
    provider = SQLiteProvider(tmp_path / "pharmacy.db")
    provider.initialize()

    with provider.unit_of_work() as work:
        seed_demo_data(work.session)
    stock = ListStock(provider).execute()

    assert len(stock) == 2
    assert [row.medicine_name for row in stock] == ["Ибупрофен", "Парацетамол"]
    assert [row.quantity for row in stock] == [60, 100]


def test_unit_of_work_rolls_back_on_exception(tmp_path):
    provider = SQLiteProvider(tmp_path / "pharmacy.db")
    provider.initialize()

    with pytest.raises(RuntimeError, match="force rollback"):
        with provider.unit_of_work() as work:
            work.session.add(Pharmacy(name="Temporary", address="Temporary"))
            raise RuntimeError("force rollback")

    with provider.unit_of_work() as work:
        pharmacies = work.session.scalars(select(Pharmacy)).all()
    assert pharmacies == []


def test_unit_of_work_persists_database_records(tmp_path):
    provider = SQLiteProvider(tmp_path / "pharmacy.db")
    provider.initialize()

    with provider.unit_of_work() as work:
        pharmacy = Pharmacy(name="Аптека тест", address="Москва")
        work.session.add(pharmacy)
        work.session.flush()
        user = User(
            pharmacy_id=pharmacy.id,
            full_name="Тестовый пользователь",
            login="test-user",
            password_hash="test-hash",
            role="pharmacist",
        )
        medicine = Medicine(
            name="Тестовый препарат",
            manufacturer="Тест",
            dosage="100 мг",
            form="таблетки",
            barcode="test-001",
        )
        work.session.add_all([user, medicine])

    with provider.unit_of_work() as work:
        saved_pharmacy = work.session.scalar(
            select(Pharmacy).where(Pharmacy.name == "Аптека тест")
        )
        saved_user = work.session.scalar(select(User).where(User.login == "test-user"))
        saved_medicine = work.session.scalar(
            select(Medicine).where(Medicine.barcode == "test-001")
        )

    assert saved_pharmacy is not None
    assert saved_user is not None
    assert saved_user.pharmacy_id == saved_pharmacy.id
    assert saved_medicine is not None


def test_persistence_strategy_registry_selects_registered_implementation():
    marker = object()

    class MarkerStrategy:
        def create_provider(self, settings, database_backend):
            assert settings.database_backend == "sqlite"
            assert database_backend == "sqlite"
            return marker

    settings = Settings(
        database_backend="sqlite",
        sqlite_database_path=":memory:",
        postgres_dsn="",
        persistence_strategy="marker",
    )
    registry = PersistenceStrategyRegistry()
    registry.register("marker", MarkerStrategy())

    assert registry.create_provider("marker", settings, "sqlite") is marker


def test_missing_persistence_dependency_raises_actionable_error():
    class MissingDependencyStrategy:
        def create_provider(self, settings, database_backend):
            raise ModuleNotFoundError("missing ORM package", name="example_orm")

    registry = PersistenceStrategyRegistry()
    registry.register("example", MissingDependencyStrategy())
    settings = Settings("sqlite", ":memory:", "", "example")

    with pytest.raises(PersistenceDependencyError, match="example_orm"):
        registry.create_provider("example", settings, "sqlite")


def test_pharmacy_service_lists_sale_candidates_and_sells_selected_medicine(tmp_path):
    provider = SQLiteProvider(tmp_path / "pharmacy.db")
    provider.initialize()
    with provider.unit_of_work() as work:
        seed_demo_data(work.session)
    pharmacy = PharmacyService(provider)

    candidates = pharmacy.get_goods_for_sale(1, date(2026, 11, 11))
    assert sum(row.quantity for row in pharmacy.get_stock(1)) == 160
    paracetamol = next(item for item in candidates if item.medicine_id == 1)
    assert paracetamol.available_quantity == 100

    pharmacy.add_goods(ReceiptRequest(
        supplier_id=1,
        pharmacy_id=1,
        user_id=1,
        receipt_date=date(2026, 11, 11),
        document_number="RECEIPT-FEFO-1",
        items=(ReceiptLine(
            medicine_id=1,
            quantity=10,
            purchase_price=Decimal("5.00"),
            batches=(ReceivedBatch(
                "PAR-EARLIER-EXPIRY", date(2026, 1, 1), date(2027, 4, 1), 10
            ),),
        ),),
    ))
    result = pharmacy.sell_goods(
        pharmacy_id=1,
        user_id=1,
        medicine_id=paracetamol.medicine_id,
        quantity=3,
        sale_price=Decimal("20.00"),
        sale_date=datetime(2026, 11, 11, 12, tzinfo=timezone.utc),
    )

    assert result.total_amount == Decimal("60.00")
    with provider.unit_of_work() as work:
        sale_item = work.session.scalar(select(SaleItem).where(SaleItem.sale_id == result.sale_id))
        allocation = work.session.scalar(
            select(BatchModel.batch_number)
            .join(SaleBatchItem, SaleBatchItem.batch_id == BatchModel.id)
            .where(SaleBatchItem.sale_item_id == sale_item.id)
        )
    assert sale_item.medicine_id == 1
    assert sale_item.quantity == 3
    assert allocation == "PAR-EARLIER-EXPIRY"


def test_expired_batches_are_reported_for_write_off_and_hidden_from_sale(tmp_path):
    provider = SQLiteProvider(tmp_path / "pharmacy.db")
    provider.initialize()
    with provider.unit_of_work() as work:
        seed_demo_data(work.session)
    pharmacy = PharmacyService(provider)
    pharmacy.add_goods(ReceiptRequest(
        supplier_id=1,
        pharmacy_id=1,
        user_id=1,
        receipt_date=date(2026, 1, 15),
        document_number="RECEIPT-EXPIRED-1",
        items=(ReceiptLine(
            medicine_id=1,
            quantity=4,
            purchase_price=Decimal("4.00"),
            batches=(ReceivedBatch(
                "PAR-EXPIRED", date(2026, 1, 1), date(2026, 2, 1), 4
            ),),
        ),),
    ))

    write_off_items = pharmacy.get_items_for_write_off(
        pharmacy_id=1, current_date=date(2026, 11, 13)
    )
    sale_items = pharmacy.get_goods_for_sale(1, date(2026, 11, 13))

    assert any(item.batch_number == "PAR-EXPIRED" for item in write_off_items)
    assert all(item.medicine_id != 1 or item.available_quantity == 100 for item in sale_items)


def test_fefo_planner_skips_expired_batches():
    expired = BatchEntity(1, 1, 1, "expired", date(2026, 11, 10), 10, 10)
    available = BatchEntity(2, 1, 1, "available", date(2026, 12, 1), 10, 6)

    allocation = plan_fefo_allocation([expired, available], 4, date(2026, 11, 13))

    assert [(part.batch_id, part.quantity) for part in allocation] == [(2, 4)]
    assert available.current_quantity == 6


def test_sale_with_insufficient_stock_does_not_create_records(tmp_path):
    provider = SQLiteProvider(tmp_path / "pharmacy.db")
    provider.initialize()
    with provider.unit_of_work() as work:
        seed_demo_data(work.session)
    pharmacy = PharmacyService(provider)

    with pytest.raises(InsufficientStock):
        pharmacy.sell_goods(1, 1, 1, 1_000, Decimal("10.00"))

    with provider.unit_of_work() as work:
        sales = work.session.scalars(select(Sale)).all()
        stock = work.inventory.list_stock(1)
    assert sales == []
    assert sum(row.quantity for row in stock) == 160


def test_cli_lists_sale_candidates_and_sells_selected_medicine(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("DATABASE_BACKEND", "sqlite")
    monkeypatch.setenv("SQLITE_DATABASE_PATH", str(tmp_path / "cli.db"))

    cli_main(["init"])
    cli_main(["seed"])
    cli_main(["sale-candidates", "--pharmacy-id", "1", "--as-user", "pharmacist"])
    cli_main([
        "sell", "--pharmacy-id", "1", "--medicine-id", "1",
        "--quantity", "2", "--price", "20.00", "--as-user", "pharmacist",
    ])
    cli_main(["stock", "--pharmacy-id", "1", "--as-user", "pharmacist"])

    output = capsys.readouterr().out
    assert "ID товара 1" in output
    assert "Продажа №1 зарегистрирована" in output
    assert "остаток 98" in output
