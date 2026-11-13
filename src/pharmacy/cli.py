import argparse
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Sequence

from .config import Settings
from .contracts.dto.receiving import ReceivedBatch, ReceiptLine, ReceiptRequest
from .database.providers import create_database
from .entities import Medicine, Supplier
from .services import PharmacyService


def main(argv: Sequence[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        database = create_database(Settings.from_environment())
        if args.command == "init":
            database.initialize()
            print("Структура базы данных создана.")
            return

        database.initialize()
        if args.command == "seed":
            from .database.seed import seed_demo_data

            with database.unit_of_work() as work:
                seed_demo_data(work.session)
            print("Демонстрационные данные добавлены.")
            return

        service = PharmacyService(database)
        _run_command(args, service)
    except Exception as error:
        expected = isinstance(error, (ValueError, LookupError, RuntimeError))
        database_error = error.__class__.__module__.startswith(("sqlalchemy", "psycopg"))
        if expected or database_error:
            parser.exit(2, f"Ошибка: {error}\n")
        raise


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 -m pharmacy")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="создать таблицы базы данных")
    commands.add_parser("seed", help="добавить демонстрационные записи")

    stock = commands.add_parser("stock", help="показать складские остатки")
    stock.add_argument("--pharmacy-id", type=int)

    write_off = commands.add_parser(
        "writeoff", help="показать партии с истёкшим сроком годности"
    )
    write_off.add_argument("--pharmacy-id", type=int)
    write_off.add_argument("--date", type=_parse_date, default=date.today())

    candidates = commands.add_parser(
        "sale-candidates", help="показать товары, доступные для продажи"
    )
    candidates.add_argument("--pharmacy-id", type=int, required=True)
    candidates.add_argument("--date", type=_parse_date, default=date.today())

    medicine = commands.add_parser("medicine", help="справочник препаратов")
    medicine_commands = medicine.add_subparsers(dest="action", required=True)
    medicine_commands.add_parser("list", help="показать препараты")
    medicine_add = medicine_commands.add_parser("add", help="добавить препарат")
    medicine_add.add_argument("--name", required=True)
    medicine_add.add_argument("--manufacturer", required=True)
    medicine_add.add_argument("--dosage", required=True)
    medicine_add.add_argument("--form", required=True)
    medicine_add.add_argument("--barcode")

    supplier = commands.add_parser("supplier", help="справочник поставщиков")
    supplier_commands = supplier.add_subparsers(dest="action", required=True)
    supplier_commands.add_parser("list", help="показать поставщиков")
    supplier_add = supplier_commands.add_parser("add", help="добавить поставщика")
    supplier_add.add_argument("--name", required=True)
    supplier_add.add_argument("--phone")
    supplier_add.add_argument("--email")
    supplier_add.add_argument("--address")

    receipt = commands.add_parser("receive", help="принять товар и зарегистрировать партии")
    receipt.add_argument("--supplier-id", type=int, required=True)
    receipt.add_argument("--pharmacy-id", type=int, required=True)
    receipt.add_argument("--user-id", type=int, required=True)
    receipt.add_argument("--date", type=_parse_date, default=date.today())
    receipt.add_argument("--document", required=True)
    receipt.add_argument(
        "--item", action="append", required=True, metavar="ID:QTY:PRICE",
        help="строка поступления; формат ID_препарата:количество:цена",
    )
    receipt.add_argument(
        "--batch", action="append", required=True,
        metavar="ID:NUMBER:PRODUCTION:EXPIRY:QTY",
        help="партия; даты в формате ГГГГ-ММ-ДД",
    )

    sale = commands.add_parser("sell", help="продать выбранный препарат по FEFO")
    sale.add_argument("--pharmacy-id", type=int, required=True)
    sale.add_argument("--user-id", type=int, required=True)
    sale.add_argument("--medicine-id", type=int, required=True)
    sale.add_argument("--quantity", type=int, required=True)
    sale.add_argument("--price", type=_parse_decimal, required=True)
    sale.add_argument(
        "--date", type=_parse_datetime,
        help="дата и время ISO с часовым поясом; по умолчанию текущее время UTC",
    )
    return parser


def _run_command(args: argparse.Namespace, service: PharmacyService) -> None:
    if args.command == "stock":
        rows = service.get_stock(args.pharmacy_id)
        for row in rows:
            print(
                f"Аптека {row.pharmacy_id} | ID товара {row.medicine_id} | "
                f"{row.medicine_name} {row.dosage} | партия {row.batch_number} | "
                f"годен до {row.expiry_date} | остаток {row.quantity}"
            )
        if not rows:
            print("Остатков нет.")
    elif args.command == "writeoff":
        rows = service.get_items_for_write_off(args.pharmacy_id, args.date)
        for row in rows:
            print(
                f"Аптека {row.pharmacy_id} | ID товара {row.medicine_id} | "
                f"{row.medicine_name} | партия {row.batch_number} | "
                f"срок истёк {row.expiry_date} | остаток {row.quantity}"
            )
        if not rows:
            print("Просроченных партий нет.")
        print("Это список для проверки; акт списания команда не оформляет.")
    elif args.command == "sale-candidates":
        items = service.get_goods_for_sale(args.pharmacy_id, args.date)
        for item in items:
            print(
                f"ID товара {item.medicine_id} | {item.medicine_name} {item.dosage} | "
                f"доступно {item.available_quantity}"
            )
        if not items:
            print("Товаров для продажи нет.")
    elif args.command == "medicine":
        _medicine_command(args, service)
    elif args.command == "supplier":
        _supplier_command(args, service)
    elif args.command == "receive":
        receipt_id = service.add_goods(_make_receipt_request(args))
        print(f"Поступление зарегистрировано. ID: {receipt_id}")
    elif args.command == "sell":
        result = service.sell_goods(
            pharmacy_id=args.pharmacy_id,
            user_id=args.user_id,
            medicine_id=args.medicine_id,
            quantity=args.quantity,
            sale_price=args.price,
            sale_date=args.date or datetime.now(timezone.utc),
        )
        print(f"Продажа №{result.sale_id} зарегистрирована. Сумма: {result.total_amount}")


def _medicine_command(args: argparse.Namespace, service: PharmacyService) -> None:
    if args.action == "list":
        for medicine in service.list_medicines():
            print(
                f"ID {medicine.id} | {medicine.name} {medicine.dosage} | {medicine.form} | "
                f"производитель: {medicine.manufacturer}"
            )
        return
    medicine = service.add_medicine(Medicine(
        id=None,
        name=args.name,
        manufacturer=args.manufacturer,
        dosage=args.dosage,
        form=args.form,
        barcode=args.barcode,
    ))
    print(f"Препарат добавлен. ID: {medicine.id}")


def _supplier_command(args: argparse.Namespace, service: PharmacyService) -> None:
    if args.action == "list":
        for supplier in service.list_suppliers():
            print(f"ID {supplier.id} | {supplier.name} | телефон: {supplier.phone or '—'}")
        return
    supplier = service.add_supplier(Supplier(
        id=None,
        name=args.name,
        phone=args.phone,
        email=args.email,
        address=args.address,
    ))
    print(f"Поставщик добавлен. ID: {supplier.id}")


def _make_receipt_request(args: argparse.Namespace) -> ReceiptRequest:
    items: dict[int, tuple[int, Decimal]] = {}
    batches: dict[int, list[ReceivedBatch]] = {}

    for value in args.item:
        parts = value.split(":")
        if len(parts) != 3:
            raise ValueError(f"Неверный формат строки поступления: {value}")
        medicine_id = int(parts[0])
        if medicine_id in items:
            raise ValueError(f"Препарат {medicine_id} указан в поступлении повторно")
        items[medicine_id] = (int(parts[1]), _parse_decimal(parts[2]))
        batches[medicine_id] = []

    for value in args.batch:
        parts = value.split(":")
        if len(parts) != 5:
            raise ValueError(f"Неверный формат партии: {value}")
        medicine_id = int(parts[0])
        if medicine_id not in items:
            raise ValueError(f"Для партии {parts[1]} не указана строка поступления")
        batches[medicine_id].append(ReceivedBatch(
            batch_number=parts[1],
            production_date=_parse_date(parts[2]),
            expiry_date=_parse_date(parts[3]),
            quantity=int(parts[4]),
        ))

    receipt_lines = tuple(
        ReceiptLine(
            medicine_id=medicine_id,
            quantity=quantity,
            purchase_price=price,
            batches=tuple(batches[medicine_id]),
        )
        for medicine_id, (quantity, price) in items.items()
    )
    return ReceiptRequest(
        supplier_id=args.supplier_id,
        pharmacy_id=args.pharmacy_id,
        user_id=args.user_id,
        receipt_date=args.date,
        document_number=args.document,
        items=receipt_lines,
    )


def _parse_decimal(value: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as error:
        raise argparse.ArgumentTypeError("Цена должна быть числом, например 12.50") from error


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Дата должна быть в формате ГГГГ-ММ-ДД") from error


def _parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "Укажите дату ISO, например 2026-11-13T12:00:00+03:00"
        ) from error
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("В дате продажи укажите часовой пояс")
    return parsed
