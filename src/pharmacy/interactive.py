from datetime import date
from decimal import Decimal, InvalidOperation

from .contracts.dto.receiving import ReceivedBatch, ReceiptLine, ReceiptRequest
from .entities import Medicine, Supplier, User
from .services import PharmacyService, UserService


def run_interactive(service: PharmacyService, users: UserService) -> None:
    print("Учёт лекарственных препаратов")
    print("Введите логин для входа. Для выхода введите q вместо логина.\n")
    while True:
        login = input("Логин: ").strip()
        if login.lower() == "q":
            print("Работа завершена.")
            return
        try:
            actor = users.authenticate_login(login)
        except PermissionError as error:
            actor = users.ensure_default_admin(login)
            if actor is None:
                print(f"{error}\n")
                continue
            print("Создан пользователь admin с ролью администратора.")
        print(f"\nЗдравствуйте, {actor.full_name}. Роль: {_role_name(actor.role)}. Аптека: {actor.pharmacy_id}.\n")
        if not _user_session(actor, service, users):
            print("Работа завершена.")
            return


def _user_session(actor: User, service: PharmacyService, users: UserService) -> bool:
    while True:
        actions = _actions_for(actor.role)
        print("Меню")
        for key, (label, _) in actions.items():
            print(f"  {key}. {label}")
        print("  0. Выйти из учётной записи")
        print("  q. Завершить работу")
        choice = input("Выберите действие: ").strip().lower()
        if choice == "q":
            return False
        if choice == "0":
            print()
            return True
        action = actions.get(choice)
        if action is None:
            print("Такого пункта нет. Выберите номер из меню.\n")
            continue
        try:
            action[1](actor, service, users)
        except (ValueError, LookupError, RuntimeError, PermissionError) as error:
            print(f"Ошибка: {error}")
        except Exception as error:
            if error.__class__.__module__.startswith(("sqlalchemy", "psycopg")):
                print(f"Ошибка базы данных: {error}")
            else:
                raise
        print()


def _actions_for(role: str):
    common = {"1": ("Показать остатки", _show_stock)}
    if role == "admin":
        return {
            **common,
            "2": ("Справочник препаратов", _medicine_menu),
            "3": ("Поставщики", _supplier_menu),
            "4": ("Пользователи и роли", _users_menu),
            "5": ("Отчёт по продажам", _sales_report),
        }
    if role == "pharmacist":
        return {
            **common,
            "2": ("Справочник препаратов", _medicine_menu),
            "3": ("Список товаров для продажи", _show_sale_candidates),
            "4": ("Принять товар", _receive_goods),
            "5": ("Оформить продажу", _sell_goods),
            "6": ("Просроченные партии / списание", _write_off_menu),
        }
    if role == "manager":
        return {
            **common,
            "2": ("Контроль сроков годности", _show_expired),
            "3": ("Аналитика продаж", _sales_report),
        }
    return common


def _show_stock(actor: User, service: PharmacyService, users: UserService) -> None:
    rows = service.get_stock(actor.pharmacy_id)
    if not rows:
        print("Остатков нет.")
        return
    for row in rows:
        print(f"ID {row.medicine_id} | {row.medicine_name} {row.dosage} | партия {row.batch_number} | "
              f"годен до {row.expiry_date} | количество {row.quantity}")


def _medicine_menu(actor: User, service: PharmacyService, users: UserService) -> None:
    while True:
        print("Препараты: 1 — список, 2 — добавить, 0 — назад")
        choice = input("Выберите действие: ").strip()
        if choice == "0":
            return
        if choice == "1":
            medicines = service.list_medicines()
            for medicine in medicines:
                print(f"ID {medicine.id} | {medicine.name} {medicine.dosage} | {medicine.form} | {medicine.manufacturer}")
            if not medicines:
                print("Справочник пуст.")
            continue
        if choice == "2":
            medicine = service.add_medicine(Medicine(
                id=None,
                name=_ask_text("Название: "),
                manufacturer=_ask_text("Производитель: "),
                dosage=_ask_text("Дозировка: "),
                form=_ask_text("Форма выпуска: "),
                barcode=input("Штрихкод (можно пропустить): ").strip() or None,
            ))
            print(f"Препарат добавлен. ID: {medicine.id}")
            continue
        print("Такого пункта нет.")


def _supplier_menu(actor: User, service: PharmacyService, users: UserService) -> None:
    while True:
        print("Поставщики: 1 — список, 2 — добавить, 0 — назад")
        choice = input("Выберите действие: ").strip()
        if choice == "0":
            return
        if choice == "1":
            suppliers = service.list_suppliers()
            for supplier in suppliers:
                print(f"ID {supplier.id} | {supplier.name} | телефон: {supplier.phone or '—'}")
            if not suppliers:
                print("Справочник пуст.")
            continue
        if choice == "2":
            supplier = service.add_supplier(Supplier(
                id=None,
                name=_ask_text("Название: "),
                phone=input("Телефон (можно пропустить): ").strip() or None,
                email=input("Электронная почта (можно пропустить): ").strip() or None,
                address=input("Адрес (можно пропустить): ").strip() or None,
            ))
            print(f"Поставщик добавлен. ID: {supplier.id}")
            continue
        print("Такого пункта нет.")


def _show_sale_candidates(actor: User, service: PharmacyService, users: UserService) -> None:
    candidates = service.get_goods_for_sale(actor.pharmacy_id)
    if not candidates:
        print("Товаров для продажи нет.")
        return
    for item in candidates:
        print(f"ID {item.medicine_id} | {item.medicine_name} {item.dosage} | доступно {item.available_quantity}")


def _sell_goods(actor: User, service: PharmacyService, users: UserService) -> None:
    _show_sale_candidates(actor, service, users)
    result = service.sell_goods(
        pharmacy_id=actor.pharmacy_id,
        user_id=actor.id,
        medicine_id=_ask_int("ID препарата: "),
        quantity=_ask_int("Количество: "),
        sale_price=_ask_decimal("Цена за единицу: "),
    )
    print(f"Продажа №{result.sale_id} оформлена. Сумма: {result.total_amount}")


def _receive_goods(actor: User, service: PharmacyService, users: UserService) -> None:
    suppliers = service.list_suppliers()
    if not suppliers:
        print("Список поставщиков пуст. Обратитесь к администратору.")
        return
    print("Поставщики:")
    for supplier in suppliers:
        print(f"  {supplier.id}. {supplier.name}")
    supplier_id = _ask_int("ID поставщика: ")
    medicines = service.list_medicines()
    for medicine in medicines:
        print(f"  {medicine.id}. {medicine.name} {medicine.dosage}")
    if not medicines:
        print("Сначала добавьте препарат в справочник.")
        return
    receipt_date = _ask_date("Дата поступления [сегодня]: ", default=date.today())
    document = _ask_text("Номер документа: ")
    lines = []
    while True:
        medicine_value = input("ID препарата (пусто — завершить ввод): ").strip()
        if not medicine_value:
            break
        medicine_id = _parse_int_value(medicine_value, "ID препарата")
        quantity = _ask_int("Количество: ")
        price = _ask_decimal("Цена закупки за единицу: ")
        batch_number = _ask_text("Номер партии: ")
        production_date = _ask_date("Дата производства: ")
        expiry_date = _ask_date("Срок годности: ")
        lines.append(ReceiptLine(
            medicine_id=medicine_id,
            quantity=quantity,
            purchase_price=price,
            batches=(ReceivedBatch(batch_number, production_date, expiry_date, quantity),),
        ))
    request = ReceiptRequest(
        supplier_id=supplier_id,
        pharmacy_id=actor.pharmacy_id,
        user_id=actor.id,
        receipt_date=receipt_date,
        document_number=document,
        items=tuple(lines),
    )
    receipt_id = service.add_goods(request)
    print(f"Поступление №{receipt_id} оформлено.")


def _show_expired(actor: User, service: PharmacyService, users: UserService) -> None:
    rows = service.get_items_for_write_off(actor.pharmacy_id)
    if not rows:
        print("Просроченных партий нет.")
        return
    for row in rows:
        print(f"ID {row.medicine_id} | {row.medicine_name} | партия {row.batch_number} | "
              f"срок истёк {row.expiry_date} | остаток {row.quantity}")


def _write_off_menu(actor: User, service: PharmacyService, users: UserService) -> None:
    _show_expired(actor, service, users)
    if input("Оформить списание? [д/н]: ").strip().lower() not in {"д", "да", "y", "yes"}:
        return
    write_off_id = service.write_off_goods(
        pharmacy_id=actor.pharmacy_id,
        user_id=actor.id,
        medicine_id=_ask_int("ID препарата: "),
        quantity=_ask_int("Количество: "),
        reason=_ask_text("Причина списания: "),
    )
    print(f"Списание №{write_off_id} оформлено.")


def _sales_report(actor: User, service: PharmacyService, users: UserService) -> None:
    start = _ask_date("Дата начала периода: ")
    end = _ask_date("Дата окончания периода: ")
    report = service.get_sales_report(start, end, actor.pharmacy_id)
    print(f"Продаж: {report.sales_count} | выручка: {report.total_amount}")
    for name, quantity, revenue in report.items:
        print(f"{name} | количество: {quantity} | выручка: {revenue}")


def _users_menu(actor: User, service: PharmacyService, users: UserService) -> None:
    while True:
        print("Пользователи: 1 — список, 2 — добавить, 3 — изменить роль, 4 — удалить, 0 — назад")
        choice = input("Выберите действие: ").strip()
        if choice == "0":
            return
        if choice == "1":
            for user in users.list_users():
                print(f"ID {user.id} | {user.full_name} | {user.login} | {_role_name(user.role)} | аптека {user.pharmacy_id}")
        elif choice == "2":
            user = users.add_user(User(
                id=None, pharmacy_id=_ask_int("ID аптеки: "), full_name=_ask_text("ФИО: "),
                login=_ask_text("Логин: "), password_hash="", role=_ask_role(),
            ))
            print(f"Пользователь создан. ID: {user.id}")
        elif choice in {"3", "4"}:
            user = users.get_user(_ask_int("ID пользователя: "))
            if choice == "3":
                updated = User(**{**user.__dict__, "role": _ask_role()})
                users.update_user(updated)
                print("Роль изменена.")
            else:
                if user.id == actor.id:
                    print("Нельзя удалить текущую учётную запись во время работы.")
                elif input(f"Удалить пользователя {user.login}? [д/н]: ").strip().lower() in {"д", "да", "y", "yes"}:
                    users.delete_user(user.id)
                    print("Пользователь удалён.")
        else:
            print("Такого пункта нет.")


def _ask_text(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Поле не должно быть пустым.")


def _ask_int(prompt: str) -> int:
    return _parse_int_value(input(prompt).strip(), prompt.rstrip(": "))


def _parse_int_value(value: str, label: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"{label}: введите целое число") from error
    if parsed <= 0:
        raise ValueError(f"{label}: число должно быть положительным")
    return parsed


def _ask_decimal(prompt: str) -> Decimal:
    try:
        return Decimal(input(prompt).strip().replace(",", "."))
    except InvalidOperation as error:
        raise ValueError("Введите цену числом, например 12.50") from error


def _ask_date(prompt: str, default: date | None = None) -> date:
    value = input(prompt).strip()
    if not value and default is not None:
        return default
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("Введите дату в формате ГГГГ-ММ-ДД") from error


def _ask_role() -> str:
    print("Роли: admin, pharmacist, manager; по умолчанию admin")
    role = input("Роль [admin]: ").strip() or "admin"
    if role not in {"admin", "pharmacist", "manager"}:
        raise ValueError("Неизвестная роль")
    return role


def _role_name(role: str) -> str:
    return {"admin": "администратор", "pharmacist": "фармацевт", "manager": "руководитель"}.get(role, role)
