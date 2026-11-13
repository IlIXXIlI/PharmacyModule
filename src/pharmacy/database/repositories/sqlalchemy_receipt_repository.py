from sqlalchemy.orm import Session

from ...contracts.dto.receiving import ReceiptRequest
from ...contracts.database import ReceiptRepository
from ..models import (
    Batch as BatchModel,
    Receipt as ReceiptModel,
    ReceiptItem as ReceiptItemModel,
)


class SQLAlchemyReceiptRepository(ReceiptRepository[Session]):
    def record_receipt(self, request: ReceiptRequest) -> int:
        receipt = ReceiptModel(
            supplier_id=request.supplier_id,
            pharmacy_id=request.pharmacy_id,
            user_id=request.user_id,
            receipt_date=request.receipt_date,
            document_number=request.document_number,
        )
        self.connection.add(receipt)
        self.connection.flush()

        for line in request.items:
            receipt_item = ReceiptItemModel(
                receipt_id=receipt.id,
                medicine_id=line.medicine_id,
                quantity=line.quantity,
                purchase_price=line.purchase_price,
            )
            self.connection.add(receipt_item)
            self.connection.flush()
            for received_batch in line.batches:
                self.connection.add(BatchModel(
                    medicine_id=line.medicine_id,
                    pharmacy_id=request.pharmacy_id,
                    receipt_item_id=receipt_item.id,
                    batch_number=received_batch.batch_number,
                    production_date=received_batch.production_date,
                    expiry_date=received_batch.expiry_date,
                    initial_quantity=received_batch.quantity,
                    current_quantity=received_batch.quantity,
                ))

        self.connection.flush()
        return receipt.id
