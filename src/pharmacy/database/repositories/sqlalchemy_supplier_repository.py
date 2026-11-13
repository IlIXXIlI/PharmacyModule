from sqlalchemy import select
from sqlalchemy.orm import Session

from ...contracts.database import SupplierRepository
from ...entities import Supplier
from ..models import Supplier as SupplierModel


class SQLAlchemySupplierRepository(SupplierRepository[Session]):
    def get(self, supplier_id: int) -> Supplier | None:
        model = self.connection.get(SupplierModel, supplier_id)
        return _to_entity(model) if model else None

    def list_all(self) -> list[Supplier]:
        models = self.connection.scalars(select(SupplierModel).order_by(SupplierModel.name))
        return [_to_entity(model) for model in models]

    def add(self, supplier: Supplier) -> Supplier:
        model = SupplierModel(
            name=supplier.name,
            phone=supplier.phone,
            email=supplier.email,
            address=supplier.address,
        )
        self.connection.add(model)
        self.connection.flush()
        return _to_entity(model)

    def update(self, supplier: Supplier) -> Supplier:
        model = self.connection.get(SupplierModel, supplier.id)
        if model is None:
            raise LookupError(f"Supplier {supplier.id} does not exist")
        model.name = supplier.name
        model.phone = supplier.phone
        model.email = supplier.email
        model.address = supplier.address
        self.connection.flush()
        return _to_entity(model)

    def delete(self, supplier_id: int) -> None:
        model = self.connection.get(SupplierModel, supplier_id)
        if model is None:
            raise LookupError(f"Supplier {supplier_id} does not exist")
        self.connection.delete(model)


def _to_entity(model: SupplierModel) -> Supplier:
    return Supplier(
        id=model.id,
        name=model.name,
        phone=model.phone,
        email=model.email,
        address=model.address,
    )
