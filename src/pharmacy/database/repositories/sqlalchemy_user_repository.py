from sqlalchemy import select
from sqlalchemy.orm import Session

from ...contracts.database import UserRepository
from ...entities import User
from ..models import User as UserModel


class SQLAlchemyUserRepository(UserRepository[Session]):
    def get_by_login(self, login: str) -> User | None:
        model = self.connection.scalar(select(UserModel).where(UserModel.login == login))
        return _to_entity(model) if model else None

    def get(self, user_id: int) -> User | None:
        model = self.connection.get(UserModel, user_id)
        return _to_entity(model) if model else None

    def list_all(self) -> list[User]:
        rows = self.connection.scalars(select(UserModel).order_by(UserModel.id))
        return [_to_entity(row) for row in rows]

    def add(self, user: User) -> User:
        model = UserModel(pharmacy_id=user.pharmacy_id, full_name=user.full_name,
                          login=user.login, password_hash=user.password_hash, role=user.role)
        self.connection.add(model)
        self.connection.flush()
        return _to_entity(model)

    def update(self, user: User) -> User:
        model = self.connection.get(UserModel, user.id)
        if model is None:
            raise LookupError(f"Пользователь {user.id} не найден")
        model.pharmacy_id = user.pharmacy_id
        model.full_name = user.full_name
        model.login = user.login
        model.password_hash = user.password_hash
        model.role = user.role
        self.connection.flush()
        return _to_entity(model)

    def delete(self, user_id: int) -> None:
        model = self.connection.get(UserModel, user_id)
        if model is None:
            raise LookupError(f"Пользователь {user_id} не найден")
        self.connection.delete(model)


def _to_entity(model: UserModel) -> User:
    return User(id=model.id, pharmacy_id=model.pharmacy_id, full_name=model.full_name,
                login=model.login, password_hash=model.password_hash, role=model.role)
