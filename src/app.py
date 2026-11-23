"""Этап 2. HTTP API на Bottle для управления вычислительными задачами.

Все ответы - в формате XML. Доступ - по логину и паролю
(Basic-авторизация, RFC 7617).
"""
import os
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

from bottle import Bottle, abort, auth_basic, request, response

from src.schema import TABLES

TOOL = os.path.join(os.path.dirname(__file__), "tool.py")
REPORT_PERIOD = 8 * 60
XML_TYPE = "application/xml; charset=utf-8"

ROUTES = [
    ("POST", "/core/api/account-submit", "account_submit"),
    ("GET", "/core/api/account-collect", "account_collect"),
    ("GET", "/core/api/account-inspect", "account_inspect"),
    ("PATCH", "/core/api/account-modify/<uid:int>", "account_modify"),
    ("POST", "/core/api/message-submit", "message_submit"),
    ("GET", "/core/api/message-collect/<account:int>", "message_collect"),
    ("GET", "/core/api/message-inspect", "message_inspect"),
    ("PATCH", "/core/api/message-modify/<uid:int>", "message_modify"),
    ("GET", "/core/api/feedback-collect/<message:int>", "feedback_collect"),
    ("GET", "/core/api/feedback-inspect", "feedback_inspect"),
    ("GET", "/core/api/report-collect", "report_collect"),
]


def now():
    """Текущее время в секундах (Unix time)."""
    return int(time.time())


def convert(kind, value):
    """Привести строку к типу kind (int или str), иначе ответить 400."""
    try:
        return kind(value)
    except ValueError:
        abort(400, f"Неверное значение: '{value}'")


def parse_fields(table, source):
    """Взять из словаря source только поля таблицы нужных типов."""
    fields = TABLES[table]
    return {key: convert(fields[key], value)
            for key, value in source.items() if key in fields}


def query_fields(table):
    """Поля таблицы из строки запроса: ?ip=...&timestamp=..."""
    return parse_fields(table, request.query.decode())


def query_uid():
    """Параметр uid из строки запроса: ?uid=5"""
    return convert(int, request.query.get("uid", ""))


def body_fields(table):
    """Поля таблицы из XML в теле: <account><ip>...</ip></account>"""
    try:
        root = ET.fromstring(request.body.read())
    except ET.ParseError:
        abort(400, "Тело запроса - не XML")
    return parse_fields(table, {item.tag: item.text or "" for item in root})


def new_record(table):
    """Новая запись: пустые поля, timestamp=сейчас, поля из запроса."""
    empty = {name: kind() for name, kind in TABLES[table].items()}
    return {**empty, "timestamp": now(), **query_fields(table)}


def to_xml(tag, record):
    """Словарь -> XML-элемент <tag><поле>значение</поле>...</tag>."""
    node = ET.Element(tag)
    for key, value in record.items():
        ET.SubElement(node, key).text = str(value)
    return node


def reply(node):
    """Отправить XML-элемент клиенту."""
    response.content_type = XML_TYPE
    return ET.tostring(node, encoding="unicode")


def reply_many(root_tag, tag, records):
    """Список записей -> <root_tag><tag>...</tag>...</root_tag>."""
    root = ET.Element(root_tag)
    root.extend(to_xml(tag, record) for record in records)
    return reply(root)


def error_page(error):
    """Ответ с ошибкой (400, 401, 404) тоже в формате XML."""
    info = {"status": error.status_code, "message": error.body}
    return reply(to_xml("error", info))


def run_task(argument, test_mode):
    """Выполнить задачу утилитой tool.py через subprocess.

    В тестовом режиме утилита не запускается, статус результата - test.
    """
    if test_mode:
        return {"result": "", "status": "test", "failure": ""}
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "input.txt")
        with open(path, "w", encoding="utf-8") as file:
            file.write(argument)
        done = subprocess.run([sys.executable, "-X", "utf8", TOOL, path],
                              capture_output=True, encoding="utf-8")
    return {"result": done.stdout.strip(),
            "status": "error" if done.returncode else "done",
            "failure": done.stderr.strip()}


def full_join(accounts, messages):
    """Полное внешнее соединение A и M по условию A.uid = M.account.

    Возвращает пары (account, message); если пары нет - вместо записи
    стоит None.
    """
    pairs = []
    for account in accounts:
        linked = [msg for msg in messages if msg["account"] == account["uid"]]
        pairs += [(account, msg) for msg in linked] or [(account, None)]
    known = {account["uid"] for account in accounts}
    pairs += [(None, msg) for msg in messages if msg["account"] not in known]
    return pairs


class Api:
    """Обработчики HTTP API из табл. 15."""

    def __init__(self, storage, test_mode):
        """storage - хранилище данных, test_mode - не запускать расчёт."""
        self.storage = storage
        self.test_mode = test_mode

    def record(self, table, uid):
        """Найти запись по uid, иначе ответить 404."""
        found = self.storage.get(table, uid)
        if found is None:
            abort(404, f"{table} {uid} не найден")
        return found

    def account_submit(self):
        """1.1 Создать аккаунт: POST account-submit?ip=...&timestamp=..."""
        added = self.storage.add("account", new_record("account"))
        return reply(to_xml("account", added))

    def account_collect(self):
        """1.2 Найти аккаунты: GET account-collect?ip=..."""
        found = self.storage.find("account", query_fields("account"))
        return reply_many("accounts", "account", found)

    def account_inspect(self):
        """1.3 Прочитать аккаунт: GET account-inspect?uid=..."""
        return reply(to_xml("account", self.record("account", query_uid())))

    def account_modify(self, uid):
        """1.4 Изменить аккаунт: PATCH account-modify/<uid>, тело XML."""
        self.record("account", uid)
        changed = self.storage.change("account", uid, body_fields("account"))
        return reply(to_xml("account", changed))

    def message_submit(self):
        """2.1 Создать сообщение и выполнить задачу из поля argument.

        POST message-submit?account=...&argument=...
        Результат задачи сохраняется в таблицу Feedback.
        """
        data = new_record("message")
        self.record("account", data["account"])
        message = self.storage.add("message", data)
        result = run_task(message["argument"], self.test_mode)
        result.update(timestamp=now(), message=message["uid"])
        self.storage.add("feedback", result)
        done = self.storage.change("message", message["uid"],
                                   {"completed": now()})
        return reply(to_xml("message", done))

    def message_collect(self, account):
        """2.2 Сообщения аккаунта: GET message-collect/<account>?..."""
        filters = {**query_fields("message"), "account": account}
        found = self.storage.find("message", filters)
        return reply_many("messages", "message", found)

    def message_inspect(self):
        """2.3 Прочитать сообщение: GET message-inspect?uid=..."""
        return reply(to_xml("message", self.record("message", query_uid())))

    def message_modify(self, uid):
        """2.4 Изменить сообщение: PATCH message-modify/<uid>, тело XML."""
        self.record("message", uid)
        data = body_fields("message")
        if "account" in data:
            self.record("account", data["account"])
        changed = self.storage.change("message", uid, data)
        return reply(to_xml("message", changed))

    def feedback_collect(self, message):
        """3.1 Результаты сообщения: GET feedback-collect/<message>?..."""
        filters = {**query_fields("feedback"), "message": message}
        found = self.storage.find("feedback", filters)
        return reply_many("feedbacks", "feedback", found)

    def feedback_inspect(self):
        """3.2 Прочитать результат: GET feedback-inspect?uid=..."""
        uid = query_uid()
        return reply(to_xml("feedback", self.record("feedback", uid)))

    def report_collect(self):
        """4.1 Отчёт по формуле (15): ip и argument за последние 8 минут.

        Проекция в реляционной алгебре убирает повторы, поэтому
        одинаковые пары (ip, argument) выводятся один раз.
        """
        accounts = self.storage.find("account", {})
        messages = self.storage.find("message", {})
        border = now() - REPORT_PERIOD
        pairs = [(account["ip"], msg["argument"] if msg else "")
                 for account, msg in full_join(accounts, messages)
                 if account and account["timestamp"] >= border]
        rows = [{"ip": ip, "argument": argument}
                for ip, argument in dict.fromkeys(pairs)]
        return reply_many("report", "row", rows)


def make_app(storage, username, password, test_mode=False):
    """Собрать Bottle-приложение: маршруты, ошибки в XML, авторизация."""
    api = Api(storage, test_mode)
    app = Bottle()
    for method, path, name in ROUTES:
        app.route(path, method, getattr(api, name))
    for code in (400, 401, 404):
        app.error(code)(error_page)
    app.install(auth_basic(lambda user, word: (user, word) ==
                           (username, password)))
    return app
