from ..contracts.database import UserUnitOfWorkFactory
from ..entities import User


ROLES = {"admin", "pharmacist", "manager"}


class UserService:
    def __init__(self, database: UserUnitOfWorkFactory) -> None:
        self._database = database

    def list_users(self) -> list[User]:
        with self._database.unit_of_work() as work:
            return list(work.users.list_all())

    def get_user(self, user_id: int) -> User:
        with self._database.unit_of_work() as work:
            user = work.users.get(user_id)
            if user is None:
                raise LookupError(f"Пользователь {user_id} не найден")
            return user

    def add_user(self, user: User) -> User:
        _validate_user(user)
        with self._database.unit_of_work() as work:
            return work.users.add(user)

    def update_user(self, user: User) -> User:
        if user.id is None:
            raise ValueError("Для изменения пользователя нужен ID")
        _validate_user(user)
        with self._database.unit_of_work() as work:
            return work.users.update(user)

    def delete_user(self, user_id: int) -> None:
        if user_id <= 0:
            raise ValueError("ID пользователя должен быть положительным")
        with self._database.unit_of_work() as work:
            work.users.delete(user_id)

    def authenticate_login(self, login: str) -> User:
        with self._database.unit_of_work() as work:
            user = work.users.get_by_login(login)
        if user is None:
            raise PermissionError("Пользователь с таким логином не найден")
        return user

    def bootstrap_admin(self, pharmacy_id: int, full_name: str = "Администратор",
                        login: str = "admin") -> User:
        if any(user.role == "admin" for user in self.list_users()):
            raise PermissionError("Администратор уже существует")
        return self.add_user(User(None, pharmacy_id, full_name, login, "", "admin"))

    def ensure_default_admin(self, login: str) -> User | None:
        if login != "admin":
            return None
        users = self.list_users()
        admin = next((user for user in users if user.role == "admin"), None)
        if admin is not None:
            return admin if admin.login == login else None
        if users:
            return self.bootstrap_admin(users[0].pharmacy_id)
        return None


def _validate_user(user: User) -> None:
    if user.pharmacy_id <= 0:
        raise ValueError("ID аптеки должен быть положительным")
    if not user.full_name.strip() or not user.login.strip():
        raise ValueError("Имя и логин обязательны")
    if user.role not in ROLES:
        raise ValueError("Роль должна быть admin, pharmacist или manager")

