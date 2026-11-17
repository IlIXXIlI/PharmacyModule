from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from pharmacy.contracts.dto.receiving import ReceivedBatch, ReceiptLine, ReceiptRequest
from pharmacy.database.models import (
    Batch,
    Receipt,
    WriteOff,
    WriteOffBatchItem,
)
from pharmacy.database.seed import seed_demo_data
from pharmacy.database.sqlite import SQLiteProvider
from pharmacy.services.pharmacy_service import PharmacyService


@pytest.fixture
def seeded_pharmacy(tmp_path):
    provider = SQLiteProvider(tmp_path / "pharmacy.db")
    provider.initialize()
    with provider.unit_of_work() as work:
        seed_demo_data(work.session)
    return provider, PharmacyService(provider)


def test_receipt_adds_batch_and_increases_stock(seeded_pharmacy):
    provider, pharmacy = seeded_pharmacy

    receipt_id = pharmacy.add_goods(ReceiptRequest(
        supplier_id=1,
        pharmacy_id=1,
        user_id=1,
        receipt_date=date(2026, 11, 13),
        document_number="TEST-RECEIPT-1",
        items=(ReceiptLine(
            medicine_id=1,
            quantity=8,
            purchase_price=Decimal("7.25"),
            batches=(ReceivedBatch(
                "PAR-TEST-1", date(2026, 10, 1), date(2027, 10, 1), 8
            ),),
        ),),
    ))

    stock = pharmacy.get_stock(1)
    assert receipt_id > 0
    assert sum(row.quantity for row in stock if row.medicine_id == 1) == 108
    assert {row.batch_number for row in stock} >= {"PAR-TEST-1"}
    with provider.unit_of_work() as work:
        assert work.session.scalar(select(Receipt).where(Receipt.document_number == "TEST-RECEIPT-1"))


def test_invalid_receipt_does_not_create_receipt_or_change_stock(seeded_pharmacy):
    provider, pharmacy = seeded_pharmacy
    request = ReceiptRequest(
        supplier_id=1,
        pharmacy_id=1,
        user_id=1,
        receipt_date=date(2026, 11, 13),
        document_number="TEST-RECEIPT-INVALID",
        items=(ReceiptLine(
            medicine_id=1,
            quantity=5,
            purchase_price=Decimal("7.25"),
            batches=(ReceivedBatch(
                "PAR-TEST-BAD", date(2026, 10, 1), date(2026, 10, 31), 5
            ),),
        ),),
    )

    with pytest.raises(ValueError, match="Просроченную партию нельзя принять"):
        pharmacy.add_goods(request)

    assert sum(row.quantity for row in pharmacy.get_stock(1) if row.medicine_id == 1) == 100
    with provider.unit_of_work() as work:
        assert work.session.scalar(
            select(Receipt).where(Receipt.document_number == "TEST-RECEIPT-INVALID")
        ) is None


def test_write_off_creates_document_allocations_and_reduces_stock(seeded_pharmacy):
    provider, pharmacy = seeded_pharmacy

    write_off_id = pharmacy.write_off_goods(
        pharmacy_id=1,
        user_id=1,
        medicine_id=1,
        quantity=4,
        reason="Повреждена упаковка",
        write_off_date=date(2026, 11, 13),
    )

    assert sum(row.quantity for row in pharmacy.get_stock(1) if row.medicine_id == 1) == 96
    with provider.unit_of_work() as work:
        document = work.session.get(WriteOff, write_off_id)
        allocations = work.session.scalars(
            select(WriteOffBatchItem).where(WriteOffBatchItem.write_off_id == write_off_id)
        ).all()
        allocated_batch = work.session.get(Batch, allocations[0].batch_id)
    assert document is not None
    assert document.reason == "Повреждена упаковка"
    assert sum(item.quantity for item in allocations) == 4
    assert allocated_batch.batch_number == "PAR-2026-A"


def test_sales_report_filters_by_period_and_pharmacy(seeded_pharmacy):
    _, pharmacy = seeded_pharmacy
    pharmacy.sell_goods(
        pharmacy_id=1,
        user_id=1,
        medicine_id=1,
        quantity=3,
        sale_price=Decimal("12.00"),
        sale_date=datetime(2026, 11, 12, 10, tzinfo=timezone.utc),
    )

    report = pharmacy.get_sales_report(date(2026, 11, 12), date(2026, 11, 12), 1)

    assert report.sales_count == 1
    assert report.total_amount == Decimal("36.00")
    assert report.items == (("Парацетамол", 3, Decimal("36.00")),)


def test_sales_report_rejects_reversed_date_range(seeded_pharmacy):
    _, pharmacy = seeded_pharmacy

    with pytest.raises(ValueError, match="Начало отчётного периода позже"):
        pharmacy.get_sales_report(date(2026, 11, 13), date(2026, 11, 12))
