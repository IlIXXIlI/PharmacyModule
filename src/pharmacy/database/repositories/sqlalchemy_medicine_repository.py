from sqlalchemy import select
from sqlalchemy.orm import Session

from ...contracts.database import MedicineRepository
from ...entities import Medicine
from ..models import Medicine as MedicineModel


class SQLAlchemyMedicineRepository(MedicineRepository[Session]):
    def get(self, medicine_id: int) -> Medicine | None:
        model = self.connection.get(MedicineModel, medicine_id)
        return _to_entity(model) if model else None

    def list_all(self) -> list[Medicine]:
        models = self.connection.scalars(select(MedicineModel).order_by(MedicineModel.name))
        return [_to_entity(model) for model in models]

    def add(self, medicine: Medicine) -> Medicine:
        model = MedicineModel(
            name=medicine.name,
            manufacturer=medicine.manufacturer,
            dosage=medicine.dosage,
            form=medicine.form,
            barcode=medicine.barcode,
        )
        self.connection.add(model)
        self.connection.flush()
        return _to_entity(model)

    def update(self, medicine: Medicine) -> Medicine:
        model = self.connection.get(MedicineModel, medicine.id)
        if model is None:
            raise LookupError(f"Medicine {medicine.id} does not exist")
        model.name = medicine.name
        model.manufacturer = medicine.manufacturer
        model.dosage = medicine.dosage
        model.form = medicine.form
        model.barcode = medicine.barcode
        self.connection.flush()
        return _to_entity(model)

    def delete(self, medicine_id: int) -> None:
        model = self.connection.get(MedicineModel, medicine_id)
        if model is None:
            raise LookupError(f"Medicine {medicine_id} does not exist")
        self.connection.delete(model)


def _to_entity(model: MedicineModel) -> Medicine:
    return Medicine(
        id=model.id,
        name=model.name,
        manufacturer=model.manufacturer,
        dosage=model.dosage,
        form=model.form,
        barcode=model.barcode,
    )
