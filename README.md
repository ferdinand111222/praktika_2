# Практическая работа №2, вариант 15

HTTP API для выполнения вычислительных задач.

## Общее описание

Проект сделан в три этапа:

1. **Утилита командной строки** `src/tool.py`. Она читает файл с числами
   и печатает их количество, сумму, минимум, максимум и среднее.
2. **HTTP API** на Bottle `src/app.py`. Хранит данные в файловой СУБД
   (JSON-файл) `src/file_storage.py`. Задачи из `message-submit`
   выполняются утилитой из этапа 1 через `subprocess`. Ответы приходят
   в формате XML, доступ закрыт Basic-авторизацией (RFC 7617).
3. **Слой данных на SQLite** `src/sql_storage.py` через ORM SQLAlchemy.
   У него те же методы, что у файлового хранилища, поэтому API
   не меняется. Хранилище выбирается в `config.ini`.

Схема данных (рис. 15): `Account 1 — N Message 1 — N Feedback`.

| Таблица  | Поля                                                    |
|----------|---------------------------------------------------------|
| Account  | uid, timestamp, ip                                      |
| Message  | uid, timestamp, argument, account → Account, completed  |
| Feedback | uid, timestamp, result, status, failure, message → Message |

`Message` — это задача (в `argument` лежат входные данные), а
`Feedback` — результат её выполнения: `status` = `done`, `error`
или `test` (тестовый режим), `result` — вывод утилиты, `failure` — текст
ошибки.

## Структура проекта

```
src/
  tool.py          этап 1: утилита командной строки
  schema.py        таблицы и типы полей (рис. 15)
  file_storage.py  этап 2: файловая СУБД (JSON)
  app.py           этап 2: обработчики HTTP API на Bottle
  client.py        этап 2: клиент к HTTP API
  sql_storage.py   этап 3: SQLite + SQLAlchemy
  server.py        запуск сервера с настройками из config.ini
tests/
  test_tool.py     тесты утилиты (hypothesis)
  test_api.py      тесты HTTP API на основе модели (hypothesis)
examples/          5 примеров входных данных + пример с ошибкой
config.ini         настройки (логин, пароль, порт, хранилище)
run.bat, run.sh    команды запуска
```

## Настройки (config.ini)

| Секция    | Ключ      | Значение                                        |
|-----------|-----------|-------------------------------------------------|
| auth      | username  | логин для доступа к API                         |
| auth      | password  | пароль для доступа к API                        |
| app       | host      | адрес сервера, по умолчанию 127.0.0.1           |
| app       | port      | порт сервера, по умолчанию 8080                 |
| app       | test_mode | `yes` — не запускать утилиту (тестовый режим)   |
| storage   | kind      | `file` (JSON, этап 2) или `sqlite` (этап 3)     |
| storage   | path      | файл базы, например `data.json` или `data.db`   |

## HTTP API

Все обработчики требуют заголовок `Authorization: Basic ...`. Без него
или с неверным паролем ответ — `401 Unauthorized`. Ошибки тоже
приходят в XML: `<error><status>404</status><message>...</message></error>`.

| №   | Метод | Маршрут                                | Что делает |
|-----|-------|----------------------------------------|------------|
| 1.1 | POST  | /core/api/account-submit?ip=&timestamp= | создать аккаунт |
| 1.2 | GET   | /core/api/account-collect?ip=           | поиск аккаунтов |
| 1.3 | GET   | /core/api/account-inspect?uid=          | прочитать аккаунт |
| 1.4 | PATCH | /core/api/account-modify/:uid (XML)     | изменить аккаунт |
| 2.1 | POST  | /core/api/message-submit?account=&argument= | создать задачу и выполнить её |
| 2.2 | GET   | /core/api/message-collect/:account?argument= | поиск сообщений аккаунта |
| 2.3 | GET   | /core/api/message-inspect?uid=          | прочитать сообщение |
| 2.4 | PATCH | /core/api/message-modify/:uid (XML)     | изменить сообщение |
| 3.1 | GET   | /core/api/feedback-collect/:message?status= | поиск результатов сообщения |
| 3.2 | GET   | /core/api/feedback-inspect?uid=         | прочитать результат |
| 4.1 | GET   | /core/api/report-collect                | отчёт по формуле (15) |

В поиске (`collect`) можно передать любое поле таблицы: вернутся записи,
у которых это поле совпадает. Без параметров вернутся все записи.

Отчёт 4.1 — это π<sub>A.ip, M.argument</sub>(σ<sub>A.timestamp ≥ now − 8
min</sub>(A ⟗<sub>A.uid = M.account</sub> M)): пары (ip, argument) для
аккаунтов, созданных за последние 8 минут. Аккаунт без сообщений даёт
пару с пустым `argument`, повторы убираются.

## Функции

- `tool.py`: `solve(text)` считает статистику, `to_number(word)`
  переводит слово в число, `main()` разбирает аргументы командной строки.
- `app.py`: `make_app(storage, username, password, test_mode)` собирает
  приложение. Класс `Api` содержит обработчики (по одному методу на строку
  таблицы). `run_task` запускает утилиту, `full_join` делает полное внешнее
  соединение для отчёта. `parse_fields`, `query_fields`, `body_fields`
  читают параметры, а `to_xml`, `reply`, `reply_many` формируют XML.
- `file_storage.py` и `sql_storage.py`: классы `FileStorage` и `SqlStorage`
  с одинаковыми методами `add`, `find`, `get`, `change`, `close`.
- `client.py`: класс `Client` с методами вида `метод_таблица_действие`:
  `post_account_submit`, `get_account_collect`, `get_account_inspect`,
  `patch_account_modify`, `post_message_submit`, `get_message_collect`,
  `get_message_inspect`, `patch_message_modify`, `get_feedback_collect`,
  `get_feedback_inspect`, `get_report_collect`.

## Команды

Нужен Python 3.10+. Windows — `.\run.bat`, Linux/macOS — `./run.sh`.

```
.\run.bat install      установить зависимости (requirements.txt)
.\run.bat examples     запустить утилиту на всех примерах
.\run.bat tool FILE    запустить утилиту на своём файле
.\run.bat server       запустить сервер (настройки из config.ini)
.\run.bat test         тесты hypothesis + отчёт coverage по ветвям
```

hypothesis закреплена на версии 6.141.1: более новые версии не работают
на Python 3.10.0 из-за ошибки `dataclass(slots=True)`, исправленной
в Python 3.10.1.

`tests/test_tool.py` проверяет функцию `solve` на случайных списках
чисел, которые генерирует hypothesis.

Тесты API (`tests/test_api.py`) используют `RuleBasedStateMachine` из
hypothesis. Модель хранит ожидаемые таблицы в словарях. Hypothesis сам
составляет случайные цепочки запросов через `Client` и после каждого
запроса сверяет ответ сервера с моделью. Модель гоняется дважды: с
`FileStorage` в тестовом режиме и с `SqlStorage` с реальным запуском
утилиты. Покрытие считается по ветвям (`branch = True` в `.coveragerc`).
`tool.py` и `server.py` в покрытие не входят: утилита работает в отдельном
процессе, а `server.py` только читает настройки и запускает сервер.

## Примеры использования

Утилита:

```
> python src/tool.py examples/1.txt
количество: 5, сумма: 15, минимум: 1, максимум: 5, среднее: 3
> python src/tool.py examples/2.txt
количество: 3, сумма: 14.75, минимум: -2.5, максимум: 10, среднее: 4.91667
> python src/tool.py examples/3.txt
количество: 1, сумма: 42, минимум: 42, максимум: 42, среднее: 42
> python src/tool.py examples/4.txt
количество: 8, сумма: 31, минимум: 1, максимум: 9, среднее: 3.875
> python src/tool.py examples/5.txt
количество: 3, сумма: 999950, минимум: -50, максимум: 1e+06, среднее: 333317
> python src/tool.py examples/error.txt
Ошибка: 'abc' - не число
```

HTTP API через curl (логин `admin`, пароль `qwerty` из `config.ini`):

```
curl -u admin:qwerty -X POST "http://127.0.0.1:8080/core/api/account-submit?ip=10.0.0.5"
<account><uid>1</uid><timestamp>1795466096</timestamp><ip>10.0.0.5</ip></account>

curl -u admin:qwerty -X POST "http://127.0.0.1:8080/core/api/message-submit?account=1&argument=1%202%203%2010"
<message><uid>1</uid><timestamp>1795466096</timestamp><argument>1 2 3 10</argument><account>1</account><completed>1795466096</completed></message>

curl -u admin:qwerty "http://127.0.0.1:8080/core/api/feedback-collect/1"
<feedbacks><feedback><uid>1</uid>...<result>количество: 4, сумма: 16, минимум: 1, максимум: 10, среднее: 4</result><status>done</status><failure />...</feedback></feedbacks>

curl -u admin:qwerty -X PATCH -d "<account><ip>10.9.9.9</ip></account>" "http://127.0.0.1:8080/core/api/account-modify/1"
<account><uid>1</uid><timestamp>1795466096</timestamp><ip>10.9.9.9</ip></account>

curl -u admin:qwerty "http://127.0.0.1:8080/core/api/report-collect"
<report><row><ip>10.9.9.9</ip><argument>1 2 3 10</argument></row></report>

curl "http://127.0.0.1:8080/core/api/report-collect"
<error><status>401</status><message>Access denied</message></error>
```

Клиент на Python:

```python
from src.client import Client

api = Client("http://127.0.0.1:8080", "admin", "qwerty")
account = api.post_account_submit(ip="10.0.0.5")
message = api.post_message_submit(account=account["uid"], argument="1 2 3")
print(api.get_feedback_collect(message["uid"]))
print(api.get_report_collect())
```
