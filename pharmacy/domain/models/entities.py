"""Portable ORM entities mapped from the pharmacy ER model."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer,
    Numeric, String, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

IdType = BigInteger().with_variant(Integer(), "sqlite")


class Pharmacy(Base):
    __tablename__ = "PHARMACIES"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))


class User(Base):
    __tablename__ = "USERS"
    __table_args__ = (CheckConstraint("role IN ('admin', 'pharmacist', 'manager')", name="ck_users_role"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    pharmacy_id: Mapped[int] = mapped_column(ForeignKey("PHARMACIES.id"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    login: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)


class Medicine(Base):
    __tablename__ = "MEDICINES"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    manufacturer: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[str] = mapped_column(String(100), nullable=False)
    form: Mapped[str] = mapped_column(String(100), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True)


class Supplier(Base):
    __tablename__ = "SUPPLIERS"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(500))


class Receipt(Base):
    __tablename__ = "RECEIPTS"

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("SUPPLIERS.id"), nullable=False)
    pharmacy_id: Mapped[int] = mapped_column(ForeignKey("PHARMACIES.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("USERS.id"), nullable=False)
    receipt_date: Mapped[date] = mapped_column(Date, nullable=False)
    document_number: Mapped[str] = mapped_column(String(100), nullable=False)


class ReceiptItem(Base):
    __tablename__ = "RECEIPT_ITEMS"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_receipt_items_quantity"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    receipt_id: Mapped[int] = mapped_column(ForeignKey("RECEIPTS.id"), nullable=False)
    medicine_id: Mapped[int] = mapped_column(ForeignKey("MEDICINES.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)


class Batch(Base):
    __tablename__ = "BATCHES"
    __table_args__ = (
        CheckConstraint("initial_quantity > 0", name="ck_batches_initial_quantity"),
        CheckConstraint("current_quantity >= 0 AND current_quantity <= initial_quantity", name="ck_batches_current_quantity"),
        UniqueConstraint("pharmacy_id", "medicine_id", "batch_number", name="uq_batches_pharmacy_medicine_number"),
        Index("idx_batches_stock_fefo", "pharmacy_id", "medicine_id", "expiry_date", "current_quantity"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    medicine_id: Mapped[int] = mapped_column(ForeignKey("MEDICINES.id"), nullable=False)
    pharmacy_id: Mapped[int] = mapped_column(ForeignKey("PHARMACIES.id"), nullable=False)
    receipt_item_id: Mapped[int] = mapped_column(ForeignKey("RECEIPT_ITEMS.id"), nullable=False)
    batch_number: Mapped[str] = mapped_column(String(100), nullable=False)
    production_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    initial_quantity: Mapped[int] = mapped_column(nullable=False)
    current_quantity: Mapped[int] = mapped_column(nullable=False)


class Sale(Base):
    __tablename__ = "SALES"
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="ck_sales_total_amount"),
        CheckConstraint("status IN ('completed', 'cancelled')", name="ck_sales_status"),
        Index("idx_sales_date", "pharmacy_id", "sale_date"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    pharmacy_id: Mapped[int] = mapped_column(ForeignKey("PHARMACIES.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("USERS.id"), nullable=False)
    sale_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(30), nullable=False)


class SaleItem(Base):
    __tablename__ = "SALE_ITEMS"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_sale_items_quantity"),
        CheckConstraint("sale_price >= 0", name="ck_sale_items_price"),
    )

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("SALES.id"), nullable=False)
    medicine_id: Mapped[int] = mapped_column(ForeignKey("MEDICINES.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    sale_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)


class SaleBatchItem(Base):
    __tablename__ = "SALE_BATCH_ITEMS"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_sale_batch_items_quantity"),)

    id: Mapped[int] = mapped_column(IdType, primary_key=True, autoincrement=True)
    sale_item_id: Mapped[int] = mapped_column(ForeignKey("SALE_ITEMS.id"), nullable=False)
    batch_id: Mapped[int] = mapped_column(ForeignKey("BATCHES.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
