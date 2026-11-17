# Руководство по Python API

Этот документ показывает, как подключить модуль учёта аптеки к другому Python-приложению. Имя дистрибутива для `pip` — `pharmacy-accounting-module`, корневой импортируемый пакет — `pharmacy`.

## Установка

Из каталога с исходным кодом:

```bash
python -m pip install .
```

Для разработки и проверки изменений используйте editable-установку:

```bash
python -m pip install -e .
```

Основные зависимости устанавливаются автоматически. Для подключения PostgreSQL установите extra:

```bash
python -m pip install '.[postgres]'
```

## Подключение к SQLite

`SQLiteProvider` принимает путь к файлу базы. Он создаёт каталог файла при необходимости; `initialize()` создаёт таблицы, если их ещё нет.

```python
from pharmacy.database.sqlite import SQLiteProvider
from pharmacy.services.pharmacy_service import PharmacyService

database = SQLiteProvider("data/pharmacy.db")
database.initialize()
pharmacy = PharmacyService(database)

stock = pharmacy.get_stock(pharmacy_id=1)
for row in stock:
    print(
        f"{row.medicine_name} {row.dosage}: "
        f"партия {row.batch_number}, остаток {row.quantity}, годен до {row.expiry_date}"
    )
```

Чтобы загрузить демонстрационные данные в пустую базу, передайте SQLAlchemy-сессию функции `seed_demo_data`:

```python
from pharmacy.database.seed import seed_demo_data

with database.unit_of_work() as work:
    seed_demo_data(work.session)
```

Повторный вызов не добавляет повторно демонстрационную аптеку, если данные уже есть.

## Подключение к PostgreSQL

`PostgresProvider` принимает DSN SQLAlchemy. Перед импортом провайдера установите extra `postgres`.

```python
from pharmacy.database.postgres import PostgresProvider
from pharmacy.services.pharmacy_service import PharmacyService

database = PostgresProvider(
    "postgresql+psycopg://user:password@localhost:5432/pharmacy"
)
database.initialize()
pharmacy = PharmacyService(database)
```

В приложении не храните пароль в исходном файле: передавайте DSN из переменной окружения или менеджера секретов.

## Просмотр остатков и товаров для продажи

Методы возвращают типизированные объекты DTO:

```python
from datetime import date

stock_rows = pharmacy.get_stock(pharmacy_id=1)
sale_candidates = pharmacy.get_goods_for_sale(
    pharmacy_id=1,
    current_date=date.today(),
)

for candidate in sale_candidates:
    print(candidate.medicine_id, candidate.medicine_name, candidate.available_quantity)
```

Параметр даты можно не передавать: тогда используется текущая дата. В продажу не включаются партии, срок годности которых уже истёк.

## Регистрация поступления

Поступление описывается объектами `ReceiptRequest`, `ReceiptLine` и `ReceivedBatch`. Количество во всех партиях должно в сумме совпасть с количеством строки.

```python
from datetime import date
from decimal import Decimal

from pharmacy.contracts.dto.receiving import (
    ReceivedBatch,
    ReceiptLine,
    ReceiptRequest,
)

receipt_id = pharmacy.add_goods(ReceiptRequest(
    supplier_id=1,
    pharmacy_id=1,
    user_id=1,
    receipt_date=date(2026, 11, 13),
    document_number="API-RECEIPT-001",
    items=(ReceiptLine(
        medicine_id=1,
        quantity=10,
        purchase_price=Decimal("5.50"),
        batches=(ReceivedBatch(
            batch_number="PAR-API-001",
            production_date=date(2026, 10, 1),
            expiry_date=date(2027, 10, 1),
            quantity=10,
        ),),
    ),),
))
```

Метод возвращает ID документа поступления. Он отклоняет отсутствующего поставщика или препарат, пустой номер документа, неположительные количества, некорректные даты и просроченные партии.

## Продажа

Цена передаётся как `Decimal`, а дата продажи — как `datetime` с часовым поясом. Если дата не указана, используется текущее время UTC.

```python
from datetime import datetime, timezone
from decimal import Decimal

result = pharmacy.sell_goods(
    pharmacy_id=1,
    user_id=1,
    medicine_id=1,
    quantity=2,
    sale_price=Decimal("20.00"),
    sale_date=datetime.now(timezone.utc),
)

print(result.sale_id, result.total_amount)
```

В ответе `SaleResult` содержит ID продажи и итоговую сумму. При недостаточном остатке сервис возбуждает `InsufficientStock`; если препарат не найден — `LookupError`. Перед сохранением система проверяет доступные не просроченные партии и распределяет товар по FEFO.

## Списание

```python
from datetime import date

write_off_id = pharmacy.write_off_goods(
    pharmacy_id=1,
    user_id=1,
    medicine_id=1,
    quantity=2,
    reason="Повреждена упаковка",
    write_off_date=date.today(),
)
```

Метод возвращает ID документа списания. Причина обязательна; распределение фиксируется по партиям. В отличие от продажи, списание может включать просроченные партии.

## Отчёт о продажах

```python
from datetime import date

report = pharmacy.get_sales_report(
    start_date=date(2026, 11, 1),
    end_date=date(2026, 11, 30),
    pharmacy_id=1,
)

print(report.sales_count, report.total_amount)
for medicine_name, quantity, revenue in report.items:
    print(medicine_name, quantity, revenue)
```

Если `pharmacy_id` не передать, отчёт агрегирует данные по всем аптекам. Начало периода должно быть не позже окончания.

## Справочники

Методы `list_medicines`, `add_medicine`, `list_suppliers` и `add_supplier` предоставляют операции со справочниками. Они принимают и возвращают сущности из `pharmacy.entities`; например, `Medicine` и `Supplier`.

## Ошибки и граница ответственности

Сервисный слой проверяет ограничения бизнес-операций и использует транзакции провайдера. В зависимости от ошибки операция может возбуждать `ValueError` для неверных данных, `LookupError` для отсутствующей записи, `PermissionError` при ошибке аутентификации CLI или специализированные ошибки операций.

`PharmacyService` не аутентифицирует пользователя и не проверяет, имеет ли переданный `user_id` нужную роль. Эти проверки реализованы в CLI перед вызовом сервиса. Интегрирующее приложение должно самостоятельно проверять пользователя, роль и доступ к конкретной аптеке.
