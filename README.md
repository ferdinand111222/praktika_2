# Практическая работа №2, вариант 15

Веб-приложение с HTTP API для асинхронного преобразования файлов
из формата OGG в формат MP3.

## Общее описание

Проект сделан в три этапа:

1. **Утилита командной строки** `src/tool.py`. Принимает аудиофайл OGG
   и пишет тот же звук в формате MP3 в стандартный вывод
   (`python src/tool.py in.ogg > out.mp3`). Для чтения и записи звука
   используется библиотека `soundfile`, ffmpeg не нужен.
2. **HTTP API** на Bottle `src/app.py` с файловой СУБД (JSON-файл)
   `src/file_storage.py`. Задача на преобразование (`message-submit`)
   ставится в очередь, и ответ приходит сразу. Файл преобразуется
   в фоновом потоке утилитой из этапа 1 через `subprocess`, а готовый
   MP3 сохраняется в папку `media`. Ответы приходят в формате XML,
   доступ закрыт Basic-авторизацией (RFC 7617).
3. **Слой данных на SQLite** `src/sql_storage.py` через ORM SQLAlchemy.
   У него те же методы, что у файлового хранилища, поэтому API
   не меняется. Хранилище выбирается в `config.ini`.

Схема данных (рис. 15): `Account 1 — N Message 1 — N Feedback`.

| Таблица  | Поля                                                       |
|----------|------------------------------------------------------------|
| Account  | uid, timestamp, ip                                         |
| Message  | uid, timestamp, argument, account → Account, completed     |
| Feedback | uid, timestamp, result, status, failure, message → Message |

- `Message` — задача на преобразование. В `argument` лежит путь
  к OGG-файлу на компьютере, где работает сервер (относительный путь
  считается от папки проекта, например `examples/1.ogg`). Пока файл
  преобразуется, `completed = 0`. Когда работа закончена, в `completed`
  записывается время окончания.
- `Feedback` — результат преобразования:
  - `status` — `done` (готово), `error` (ошибка) или `test` (тестовый
    режим);
  - `result` — путь к готовому MP3-файлу;
  - `failure` — текст ошибки.

### Как работает асинхронное преобразование

1. Клиент отправляет `POST message-submit?account=1&argument=путь.ogg`.
2. Сервер сохраняет сообщение с `completed = 0`, ставит задачу в очередь
   пула из двух фоновых потоков (`ThreadPoolExecutor`) и **сразу**
   отвечает.
3. Фоновый поток запускает `tool.py` через `subprocess`, сохраняет MP3
   в `media/<uid сообщения>.mp3`, добавляет запись в Feedback
   и проставляет `completed`.
4. Клиент периодически запрашивает `message-inspect?uid=...`. Когда
   `completed` стал не `0`, результат лежит в `feedback-collect/<uid>`.

## Структура проекта

```
src/
  tool.py          этап 1: утилита OGG -> MP3
  samples.py       создание примеров OGG (тоны, аккорд, стерео, тишина)
  schema.py        таблицы и типы полей (рис. 15)
  file_storage.py  этап 2: файловая СУБД (JSON)
  app.py           этап 2: обработчики HTTP API и фоновое преобразование
  client.py        этап 2: клиент к HTTP API
  sql_storage.py   этап 3: SQLite + SQLAlchemy
  server.py        запуск сервера с настройками из config.ini
tests/
  test_tool.py     тесты утилиты (hypothesis)
  test_api.py      тесты HTTP API на основе модели (hypothesis)
examples/          описание примеров; сами OGG создаются командой
config.ini         настройки (логин, пароль, порт, хранилище)
run.bat, run.sh    команды запуска
```

Аудиофайлы — двоичные, поэтому в репозитории их нет. Примеры
создаёт `src/samples.py`, а MP3 появляются в `examples/` и `media/`
при работе программы.

## Настройки (config.ini)

| Секция  | Ключ      | Значение                                         |
|---------|-----------|--------------------------------------------------|
| auth    | username  | логин для доступа к API                          |
| auth    | password  | пароль для доступа к API                         |
| app     | host      | адрес сервера, по умолчанию 127.0.0.1            |
| app     | port      | порт сервера, по умолчанию 8000                  |
| app     | test_mode | `yes` — не преобразовывать файлы (тестовый режим) |
| storage | kind      | `file` (JSON, этап 2) или `sqlite` (этап 3)      |
| storage | path      | файл базы, например `data.json` или `data.db`    |
| storage | media     | папка для готовых MP3-файлов                     |

## HTTP API

Все обработчики требуют заголовок `Authorization: Basic ...`. Без него
или с неверным паролем ответ — `401 Unauthorized`. Ошибки тоже
приходят в XML: `<error><status>404</status><message>...</message></error>`.

| №   | Метод | Маршрут                                     | Что делает |
|-----|-------|---------------------------------------------|------------|
| 1.1 | POST  | /core/api/account-submit?ip=&timestamp=     | создать аккаунт |
| 1.2 | GET   | /core/api/account-collect?ip=               | поиск аккаунтов |
| 1.3 | GET   | /core/api/account-inspect?uid=              | прочитать аккаунт |
| 1.4 | PATCH | /core/api/account-modify/:uid (XML)         | изменить аккаунт |
| 2.1 | POST  | /core/api/message-submit?account=&argument= | поставить OGG в очередь на преобразование |
| 2.2 | GET   | /core/api/message-collect/:account?argument= | задачи аккаунта |
| 2.3 | GET   | /core/api/message-inspect?uid=              | прочитать задачу (готова ли) |
| 2.4 | PATCH | /core/api/message-modify/:uid (XML)         | изменить задачу |
| 3.1 | GET   | /core/api/feedback-collect/:message?status= | результаты задачи |
| 3.2 | GET   | /core/api/feedback-inspect?uid=             | прочитать результат |
| 4.1 | GET   | /core/api/report-collect                    | отчёт по формуле (15) |

В поиске (`collect`) можно передать любое поле таблицы: вернутся записи,
у которых это поле совпадает. Без параметров вернутся все записи.

Отчёт 4.1 — это π<sub>A.ip, M.argument</sub>(σ<sub>A.timestamp ≥ now − 8
min</sub>(A ⟗<sub>A.uid = M.account</sub> M)): пары (ip, путь к OGG) для
аккаунтов, созданных за последние 8 минут. Аккаунт без задач даёт
пару с пустым `argument`, повторы убираются.

## Функции

- `tool.py`: `convert(path)` читает OGG и возвращает MP3 в байтах,
  `main()` разбирает аргументы и пишет MP3 в стандартный вывод.
- `samples.py`: `tone(...)` делает звук из синусоид, `samples()`
  описывает 5 примеров, `make_samples(folder)` записывает их в OGG.
- `app.py`: `make_app(storage, username, password, media, test_mode)`
  собирает приложение. В классе `Api` по одному методу на строку
  таблицы. `Api.convert` — фоновая задача, а `run_task` запускает
  утилиту и сохраняет MP3. `full_join` делает соединение для отчёта.
  `parse_fields`, `query_fields`, `body_fields` читают параметры,
  а `to_xml`, `reply`, `reply_many` формируют XML.
- `file_storage.py` и `sql_storage.py`: классы `FileStorage` и `SqlStorage`
  с одинаковыми методами `add`, `find`, `get`, `change`, `close`.
- `client.py`: класс `Client` с методами вида `метод_таблица_действие`:
  `post_account_submit`, `get_account_collect`, `get_account_inspect`,
  `patch_account_modify`, `post_message_submit`, `get_message_collect`,
  `get_message_inspect`, `patch_message_modify`, `get_feedback_collect`,
  `get_feedback_inspect`, `get_report_collect`.

## Команды

Нужен Python 3.10+. Windows — `run.bat` (в PowerShell `.\run.bat`),
Linux/macOS — `./run.sh`.

```
run.bat install          установить зависимости (requirements.txt)
run.bat examples         создать 5 примеров OGG и преобразовать их в MP3
run.bat tool FILE.ogg    преобразовать свой файл (MP3 появится рядом)
run.bat server           запустить сервер (настройки из config.ini)
run.bat test             тесты hypothesis + отчёт coverage по ветвям
```

Если запустить `run.bat` двойным щелчком, откроется меню с номерами.

Тесты:
- `tests/test_tool.py` проверяет утилиту на случайных звуках
  от hypothesis: MP3 должен совпадать с OGG по частоте, числу каналов
  и длительности.
- `tests/test_api.py` использует `RuleBasedStateMachine` из hypothesis.
  Модель хранит ожидаемые таблицы в словарях, а hypothesis составляет
  случайные цепочки запросов через `Client` и сверяет ответы с моделью.
  После отправки файла модель ждёт окончания фонового преобразования
  и проверяет, что получился настоящий MP3.
- Модель гоняется дважды: с `FileStorage` в тестовом режиме
  и с `SqlStorage` с реальным преобразованием.
- Покрытие считается по ветвям (`.coveragerc`). `tool.py`, `samples.py`
  и `server.py` в покрытие не входят: это не обработчики API.

hypothesis закреплена на версии 6.141.1: более новые версии не работают
на Python 3.10.0 из-за ошибки `dataclass(slots=True)`, исправленной
в Python 3.10.1.

## Примеры использования

Утилита (в cmd; в PowerShell 5.1 перенаправление `>` портит двоичные
данные, поэтому используйте `run.bat`):

```
> python -m src.samples
> python src/tool.py examples/1.ogg > examples/1.mp3
> python src/tool.py examples/error.ogg > out.mp3
Ошибка: файл повреждён или это не звук: examples/error.ogg
> python src/tool.py examples/none.ogg > out.mp3
Ошибка: файл не найден: examples/none.ogg
```

HTTP API через curl в cmd (логин `admin`, пароль `qwerty` из `config.ini`;
сначала `run.bat examples`, чтобы появились файлы OGG):

```
curl -u admin:qwerty -X POST "http://127.0.0.1:8000/core/api/account-submit?ip=10.0.0.5"
<account><uid>1</uid><timestamp>1795516975</timestamp><ip>10.0.0.5</ip></account>

curl -u admin:qwerty -X POST "http://127.0.0.1:8000/core/api/message-submit?account=1&argument=examples/3.ogg"
<message><uid>1</uid>...<argument>examples/3.ogg</argument><account>1</account><completed>0</completed></message>

curl -u admin:qwerty "http://127.0.0.1:8000/core/api/message-inspect?uid=1"
<message><uid>1</uid>...<completed>1795516975</completed></message>

curl -u admin:qwerty "http://127.0.0.1:8000/core/api/feedback-collect/1"
<feedbacks><feedback><uid>1</uid>...<result>media\1.mp3</result><status>done</status><failure />...</feedback></feedbacks>

curl -u admin:qwerty -X POST "http://127.0.0.1:8000/core/api/message-submit?account=1&argument=examples/error.ogg"
curl -u admin:qwerty "http://127.0.0.1:8000/core/api/feedback-collect/2"
<feedbacks><feedback>...<status>error</status><failure>Ошибка: файл повреждён или это не звук: examples/error.ogg</failure>...</feedbacks>

curl "http://127.0.0.1:8000/core/api/report-collect"
<error><status>401</status><message>Access denied</message></error>
```

Русские буквы в адресе curl из cmd может отправить в неправильной
кодировке: тогда сервер ответит `400 Строка запроса не в кодировке UTF-8`
или получит искажённый путь. Для путей с русскими буквами используйте
Python-клиент (он кодирует адрес правильно) или относительные пути.

Клиент на Python:

```python
import time
from src.client import Client

api = Client("http://127.0.0.1:8000", "admin", "qwerty")
account = api.post_account_submit(ip="10.0.0.5")
message = api.post_message_submit(account=account["uid"],
                                  argument="examples/1.ogg")
while api.get_message_inspect(message["uid"])["completed"] == "0":
    time.sleep(0.5)
print(api.get_feedback_collect(message["uid"]))
```
