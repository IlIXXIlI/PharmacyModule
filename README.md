# Модуль учёта лекарственных препаратов

Консольное приложение для учёта лекарств в аптеке: справочники препаратов и поставщиков, поступления с партиями и сроками годности, складские остатки, продажи, списания и отчёты. Продажа и списание распределяются по партиям по FEFO — сначала используются партии с ближайшим сроком годности. Просроченные партии нельзя продать.

Исходный код размещён в репозитории [PharmacyModule на GitHub](https://github.com/IlIXXIlI/PharmacyModule). Проект можно запускать как CLI-приложение, подключать как Python-пакет или разворачивать в Docker-контейнере.

## Возможности

- Работа с препаратами, поставщиками и пользователями.
- Регистрация поступления и партий с датами производства и окончания срока годности.
- Просмотр складских остатков и партий, подлежащих списанию.
- Продажа выбранного препарата с контролем доступного количества и автоматическим FEFO-распределением.
- Оформление списания с причиной и фиксацией затронутых партий.
- Отчёт по числу продаж, выручке и товарам за период.
- Роли администратора, фармацевта и руководителя; команды CLI проверяют полномочия пользователя и аптеку.
- Хранение данных в SQLite или PostgreSQL.

## Требования

- Python 3.10 или новее для локальной установки.
- Docker Engine с плагином Docker Compose для контейнерного запуска.
- Для PostgreSQL — доступный сервер PostgreSQL и строка подключения.

## Установка из исходного кода

Клонируйте репозиторий, создайте виртуальное окружение и установите пакет:

```bash
git clone https://github.com/IlIXXIlI/PharmacyModule.git
cd PharmacyModule
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Команда `-e .` устанавливает пакет в режиме разработки: изменения в `src/` сразу доступны импортам, а команда `python -m pharmacy` запускает CLI. Установите пример конфигурации и проверьте доступные команды:

```bash
cp .env.example .env
python -m pharmacy --help
```

В стандартной конфигурации используется SQLite-файл `data/pharmacy.db`. Приложение создаёт нужную папку для файла базы.

### Первый запуск

Создайте схему и демонстрационные записи:

```bash
python -m pharmacy init
python -m pharmacy seed
```

Для демонстрационной базы создан пользователь `pharmacist` с ролью фармацевта. Чтобы создать администратора и управлять пользователями, выполните:

```bash
python -m pharmacy user bootstrap-admin \
  --pharmacy-id 1 \
  --full-name "Администратор" \
  --login admin
```

Команда доступна, пока в базе ещё нет пользователя с ролью администратора. После этого откройте интерактивное меню:

```bash
python -m pharmacy
```

Или вызовите подкоманду явно:

```bash
python -m pharmacy interactive
```

В интерактивном режиме приложение запросит логин. Для демонстрационных данных используйте `pharmacist`; для команд администратора — `admin`, если администратор уже создан. Приложение не хранит и не запрашивает пароль: команды CLI идентифицируют пользователя по логину, а затем проверяют его роль и принадлежность к аптеке.

### Переменные конфигурации

Настройки загружаются из `.env`; переменные окружения имеют приоритет над файлом.

| Переменная | Значение по умолчанию | Назначение |
|---|---|---|
| `DATABASE_BACKEND` | `sqlite` | Тип базы: `sqlite` или `postgres` |
| `SQLITE_DATABASE_PATH` | `data/pharmacy.db` | Путь к SQLite-файлу |
| `PERSISTENCE_STRATEGY` | `sqlalchemy` | Стратегия хранения данных |
| `POSTGRES_DSN` | пусто | Строка подключения PostgreSQL |

Для PostgreSQL установите пакет драйвера и настройте `.env`:

```bash
python -m pip install '.[postgres]'
```

```dotenv
DATABASE_BACKEND=postgres
POSTGRES_DSN=postgresql://user:password@localhost:5432/pharmacy
```

Затем примените `init` и `seed` как при первом запуске. `seed` добавляет демонстрационный набор, если в базе ещё нет аптеки.

## Команды CLI

Рабочие команды принимают `--as-user` с логином вошедшего пользователя. Ниже показаны примеры для демобазы.

Просмотр остатков, просроченных партий и товаров для продажи:

```bash
python -m pharmacy stock --pharmacy-id 1 --as-user admin
python -m pharmacy writeoff --pharmacy-id 1 --as-user pharmacist
python -m pharmacy sale-candidates --pharmacy-id 1 --as-user pharmacist
```

Оформление продажи. `sale-candidates` выводит ID препарата, который нужно передать в команду продажи:

```bash
python -m pharmacy sell \
  --pharmacy-id 1 \
  --medicine-id 1 \
  --quantity 2 \
  --price 20.00 \
  --as-user pharmacist
```

Система проверит остаток и срок годности и спишет количество по FEFO.

Регистрация поступления:

```bash
python -m pharmacy receive \
  --supplier-id 1 \
  --pharmacy-id 1 \
  --date 2026-11-13 \
  --document PR-0002 \
  --item 1:10:5.50 \
  --batch 1:PAR-2026-C:2026-10-01:2027-10-01:10 \
  --as-user pharmacist
```

Формат `--item`: `ID_препарата:количество:цена_закупки`. Формат `--batch`: `ID_препарата:номер_партии:дата_производства:срок_годности:количество`. Даты вводятся в формате `ГГГГ-ММ-ДД`. Для одной строки поступления можно повторить `--batch`, указав несколько партий; сумма количеств партий должна совпадать с количеством в `--item`.

Оформление списания с причиной:

```bash
python -m pharmacy writeoff \
  --pharmacy-id 1 \
  --medicine-id 1 \
  --quantity 2 \
  --reason "Бой" \
  --as-user pharmacist
```

Управление справочниками и пользователями:

```bash
python -m pharmacy medicine list --as-user admin
python -m pharmacy supplier list --as-user admin
python -m pharmacy user list --as-user admin
python -m pharmacy user add \
  --pharmacy-id 1 \
  --full-name "Иван Иванов" \
  --login ivan \
  --role pharmacist \
  --as-user admin
```

Формирование отчёта за период:

```bash
python -m pharmacy sales-report \
  --from 2026-11-01 \
  --to 2026-11-30 \
  --as-user manager
```

Полную справку по аргументам можно получить для любой команды через `--help`, например `python -m pharmacy receive --help`.

## Распространение и сборка

### Вариант 1: Python-пакет

Проект можно установить в другом Python-окружении из исходников:

```bash
python -m pip install .
```

Чтобы собрать wheel и архив исходников, установите инструмент сборки и запустите его из корня проекта:

```bash
python -m pip install build
python -m build
```

Готовые файлы появятся в `dist/`. Установка wheel выполняется командой:

```bash
python -m pip install dist/pharmacy_accounting_module-*.whl
```

Дополнительные зависимости для PostgreSQL устанавливаются через extra: `python -m pip install '.[postgres]'` при установке из исходного каталога или соответствующим extra при публикации пакета.

### Вариант 2: Docker Compose

В корне проекта находятся `Dockerfile` и `docker-compose.yml`. Compose собирает образ приложения и подключает именованный том `pharmacy-data`, поэтому база SQLite сохраняется между запусками контейнера.

Соберите образ, создайте базу и загрузите демоданные:

```bash
docker compose build
docker compose run --rm pharmacy init
docker compose run --rm pharmacy seed
```

Создайте администратора в первый раз:

```bash
docker compose run --rm pharmacy user bootstrap-admin \
  --pharmacy-id 1 \
  --full-name "Администратор" \
  --login admin
```

Запустите интерактивное приложение в терминале:

```bash
docker compose run --rm pharmacy interactive
```

Чтобы выполнить отдельную команду, передайте её после имени сервиса:

```bash
docker compose run --rm pharmacy stock --pharmacy-id 1 --as-user admin
```

Данные базы находятся в Docker volume `pharmacy-data`. Список томов и их состояние можно посмотреть командами `docker volume ls` и `docker volume inspect pharmacymodule_pharmacy-data`. Удаление тома удаляет сохранённую базу данных.

Образ по умолчанию настроен на SQLite. Чтобы включить драйвер PostgreSQL в образ, пересоберите его с аргументом:

```bash
INSTALL_POSTGRES=true docker compose build
```

Затем передайте приложению `DATABASE_BACKEND=postgres` и `POSTGRES_DSN` через `.env` или окружение Docker Compose. PostgreSQL-сервер должен быть доступен контейнеру приложения; Compose-конфигурация проекта не создаёт отдельный сервер базы.

## Python API

Установите проект в целевое окружение через `pip install .`, затем создайте провайдер базы и экземпляр `PharmacyService`:

```python
from pharmacy.database.sqlite import SQLiteProvider
from pharmacy.services.pharmacy_service import PharmacyService

database = SQLiteProvider("data/pharmacy.db")
database.initialize()
pharmacy = PharmacyService(database)

for row in pharmacy.get_stock(pharmacy_id=1):
    print(row.medicine_name, row.batch_number, row.quantity)
```

В `PharmacyService` доступны методы для получения остатков и доступных для продажи препаратов, приёма товара, продажи, списания, отчётов и ведения справочников. DTO поступления и продажи определены в `pharmacy.contracts.dto`. Примеры регистрации поступления, продажи, работы с отчётом, исключения и прямого подключения PostgreSQL приведены в [руководстве по Python API](docs/api-usage.md).

Прямой Python API предназначен для вызова из доверенного кода: аутентификация и проверка ролей выполняются CLI-слоем, поэтому при интеграции через сервис вызывающая программа должна выполнять собственные проверки доступа.

## Тестирование

Установите dev-зависимости и запустите автоматические тесты:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Тесты проверяют структуру и транзакции базы данных, поступления, продажи, FEFO, списания, отчёты и CLI. Описание сценариев находится в [результатах тестирования](docs/testing-results.md).

## Документация проекта

- [Структура проекта](docs/project-structure.md)
- [Python API](docs/api-usage.md)
- [Результаты тестирования](docs/testing-results.md)
