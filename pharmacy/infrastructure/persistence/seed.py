"""Shared ORM demo data for every configured SQLAlchemy backend."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain.models import (
    Batch, Medicine, Pharmacy, Receipt, ReceiptItem, Supplier, User,
)


def seed_demo_data(session: Session) -> None:
    if session.scalar(select(Pharmacy.id).limit(1)) is not None:
        return

    pharmacy = Pharmacy(name="Аптека № 1", address="Москва, ул. Примерная, 1", phone="+7 495 000-00-00")
    supplier = Supplier(name="ФармПоставка", phone="+7 495 111-11-11",
                        email="supply@example.ru", address="Москва")
    medicines = [
        Medicine(name="Парацетамол", manufacturer="Фармстандарт", dosage="500 мг",
                 form="таблетки", barcode="460000000001"),
        Medicine(name="Ибупрофен", manufacturer="Озон", dosage="200 мг",
                 form="таблетки", barcode="460000000002"),
    ]
    session.add_all([pharmacy, supplier, *medicines])
    session.flush()
    user = User(pharmacy_id=pharmacy.id, full_name="Иванова Анна", login="pharmacist",
                password_hash="demo-only", role="pharmacist")
    session.add(user)
    session.flush()
    receipt = Receipt(supplier_id=supplier.id, pharmacy_id=pharmacy.id, user_id=user.id,
                      receipt_date=date(2026, 11, 10), document_number="ПР-0001")
    session.add(receipt)
    session.flush()
    receipt_items = [
        ReceiptItem(receipt_id=receipt.id, medicine_id=medicines[0].id,
                    quantity=100, purchase_price=Decimal("12.50")),
        ReceiptItem(receipt_id=receipt.id, medicine_id=medicines[1].id,
                    quantity=60, purchase_price=Decimal("25.00")),
    ]
    session.add_all(receipt_items)
    session.flush()
    session.add_all([
        Batch(medicine_id=medicines[0].id, pharmacy_id=pharmacy.id,
              receipt_item_id=receipt_items[0].id, batch_number="PAR-2026-A",
              production_date=date(2026, 8, 1), expiry_date=date(2028, 8, 1),
              initial_quantity=100, current_quantity=100),
        Batch(medicine_id=medicines[1].id, pharmacy_id=pharmacy.id,
              receipt_item_id=receipt_items[1].id, batch_number="IBU-2026-B",
              production_date=date(2026, 9, 1), expiry_date=date(2027, 9, 1),
              initial_quantity=60, current_quantity=60),
    ])
