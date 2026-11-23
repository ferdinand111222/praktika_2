"""Тестирование на основе модели (MBT) для HTTP API варианта 15.

Hypothesis сам придумывает последовательности запросов к API.
Модель - обычные словари в памяти - хранит то, что должно лежать
в базе. После каждого запроса ответ сервера сравнивается с моделью.
"""
import os
import shutil
import tempfile
import threading
import time
import xml.etree.ElementTree as ET
from urllib.error import HTTPError
from wsgiref.simple_server import WSGIRequestHandler, make_server

from hypothesis import settings, strategies as st
from hypothesis.stateful import (Bundle, RuleBasedStateMachine, initialize,
                                 rule)

from src.app import make_app
from src.client import Client
from src.file_storage import FileStorage
from src.sql_storage import SqlStorage
from src.tool import solve

USER = "tester"
PASSWORD = "secret"
MISSING_UID = 0
MINUTE = 60
REPORT_MINUTES = 8
POLL_SECONDS = 0.01

IPS = st.sampled_from(["10.0.0.1", "10.0.0.2", "192.168.0.7"])
AGES = st.sampled_from([0, 1, 7, 9, 60])
ARGUMENTS = st.text(alphabet="0123456789 .-x", max_size=10)
TABLE_NAMES = st.sampled_from(["account", "message", "feedback"])
BAD_NUMBERS = st.sampled_from(["abc", "1.5", ""])


class QuietHandler(WSGIRequestHandler):
    """Обработчик запросов тестового сервера без вывода лога."""

    def log_message(self, *args):
        """Ничего не печатать."""


def expected_feedback(argument, test_mode):
    """Какие (status, result) модель ждёт в Feedback."""
    if test_mode:
        return "test", ""
    try:
        return "done", solve(argument)
    except ValueError:
        return "error", ""


class ApiModel(RuleBasedStateMachine):
    """Модель API: таблицы account, message, feedback в словарях.

    Этап 2: данные в JSON-файле, сервер в тестовом режиме (без расчёта).
    """

    storage_class = FileStorage
    test_mode = True
    accounts = Bundle("accounts")
    messages = Bundle("messages")
    feedbacks = Bundle("feedbacks")

    def __init__(self):
        """Пустая модель и временная папка для базы."""
        super().__init__()
        self.folder = tempfile.mkdtemp()
        self.model = {"account": {}, "message": {}, "feedback": {}}
        self.expected = {}
        self.server = None

    @initialize()
    def start(self):
        """Запустить сервер в фоновом потоке."""
        self.storage = self.storage_class(os.path.join(self.folder, "db"))
        app = make_app(self.storage, USER, PASSWORD, self.test_mode)
        self.server = make_server("127.0.0.1", 0, app,
                                  handler_class=QuietHandler)
        threading.Thread(target=self.server.serve_forever,
                         args=(POLL_SECONDS,), daemon=True).start()
        url = f"http://127.0.0.1:{self.server.server_port}"
        self.client = Client(url, USER, PASSWORD)
        self.intruder = Client(url, USER, "wrong-password")

    def stop(self):
        """Остановить сервер и закрыть хранилище."""
        self.server.shutdown()
        self.server.server_close()
        self.storage.close()

    def teardown(self):
        """Убрать за собой после каждого прогона."""
        if self.server:
            self.stop()
        shutil.rmtree(self.folder, ignore_errors=True)

    def search(self, table, **filters):
        """Поиск по модели - так же, как должен искать сервер."""
        wanted = {k: v for k, v in filters.items() if v is not None}
        return [row for row in self.model[table].values()
                if all(row[k] == v for k, v in wanted.items())]

    def expect_error(self, code, method, *args, **kwargs):
        """Проверить, что запрос закончился ошибкой code с XML-телом."""
        try:
            method(*args, **kwargs)
        except HTTPError as error:
            assert error.code == code
            assert ET.fromstring(error.read()).find("status").text == \
                str(code)
            return error
        raise AssertionError(f"ожидалась ошибка {code}")

    @rule()
    def restart(self):
        """Перезапуск сервера: данные должны сохраниться на диске."""
        self.stop()
        self.start()

    @rule(target=accounts, ip=IPS, age=AGES)
    def account_submit(self, ip, age):
        """1.1 Новый аккаунт появляется с переданными ip и timestamp."""
        stamp = str(int(time.time()) - age * MINUTE)
        record = self.client.post_account_submit(ip=ip, timestamp=stamp)
        assert record == {"uid": record["uid"], "timestamp": stamp,
                          "ip": ip}
        self.model["account"][record["uid"]] = record
        return record["uid"]

    @rule(ip=st.none() | IPS)
    def account_collect(self, ip):
        """1.2 Поиск аккаунтов совпадает с поиском по модели."""
        found = self.client.get_account_collect(ip=ip)
        assert found == self.search("account", ip=ip)

    @rule(uid=accounts)
    def account_inspect(self, uid):
        """1.3 Чтение аккаунта совпадает с моделью."""
        found = self.client.get_account_inspect(uid)
        assert found == self.model["account"][uid]

    @rule(uid=accounts, ip=IPS)
    def account_modify(self, uid, ip):
        """1.4 Изменение ip меняет только ip."""
        record = self.client.patch_account_modify(uid, ip=ip)
        assert record == {**self.model["account"][uid], "ip": ip}
        self.model["account"][uid] = record

    @rule(target=messages, account=accounts, argument=ARGUMENTS)
    def message_submit(self, account, argument):
        """2.1 Новое сообщение сразу выполняется (completed заполнен)."""
        record = self.client.post_message_submit(account=account,
                                                 argument=argument)
        assert (record["account"], record["argument"]) == \
            (account, argument)
        assert int(record["completed"]) >= int(record["timestamp"])
        self.model["message"][record["uid"]] = record
        self.expected[record["uid"]] = expected_feedback(argument,
                                                         self.test_mode)
        return record["uid"]

    @rule(account=accounts, argument=st.none() | ARGUMENTS)
    def message_collect(self, account, argument):
        """2.2 Поиск сообщений аккаунта совпадает с моделью."""
        found = self.client.get_message_collect(account, argument=argument)
        assert found == self.search("message", account=account,
                                    argument=argument)

    @rule(uid=messages)
    def message_inspect(self, uid):
        """2.3 Чтение сообщения совпадает с моделью."""
        found = self.client.get_message_inspect(uid)
        assert found == self.model["message"][uid]

    @rule(uid=messages, argument=ARGUMENTS)
    def message_modify(self, uid, argument):
        """2.4 Изменение текста задачи меняет только argument."""
        record = self.client.patch_message_modify(uid, argument=argument)
        assert record == {**self.model["message"][uid],
                          "argument": argument}
        self.model["message"][uid] = record

    @rule(uid=messages, account=accounts)
    def message_move(self, uid, account):
        """2.4 Перенос сообщения на другой аккаунт меняет только account."""
        record = self.client.patch_message_modify(uid, account=account)
        assert record == {**self.model["message"][uid], "account": account}
        self.model["message"][uid] = record

    @rule(target=feedbacks, message=messages)
    def feedback_collect(self, message):
        """3.1 У сообщения ровно один результат, и он правильный."""
        [record] = self.client.get_feedback_collect(message)
        assert record["message"] == message
        status_and_result = (record["status"], record["result"])
        assert status_and_result == self.expected[message]
        assert bool(record["failure"]) == (record["status"] == "error")
        self.model["feedback"][record["uid"]] = record
        return record["uid"]

    @rule(uid=feedbacks)
    def feedback_inspect(self, uid):
        """3.2 Чтение результата совпадает с моделью."""
        found = self.client.get_feedback_inspect(uid)
        assert found == self.model["feedback"][uid]

    @rule()
    def report_collect(self):
        """4.1 Отчёт совпадает с формулой (15), посчитанной по модели."""
        border = int(time.time()) - REPORT_MINUTES * MINUTE
        expected = set()
        for account in self.model["account"].values():
            if int(account["timestamp"]) >= border:
                linked = self.search("message", account=account["uid"])
                arguments = [msg["argument"] for msg in linked] or [""]
                expected |= {(account["ip"], arg) for arg in arguments}
        found = self.client.get_report_collect()
        pairs = [(row["ip"], row["argument"]) for row in found]
        assert len(pairs) == len(set(pairs))
        assert set(pairs) == expected

    @rule()
    def unauthorized(self):
        """Неверный пароль -> 401 и заголовок WWW-Authenticate."""
        error = self.expect_error(401, self.intruder.get_report_collect)
        assert error.headers["WWW-Authenticate"].startswith("Basic")

    @rule(table=TABLE_NAMES)
    def inspect_missing(self, table):
        """Чтение несуществующей записи -> 404."""
        method = getattr(self.client, f"get_{table}_inspect")
        self.expect_error(404, method, MISSING_UID)

    @rule(argument=ARGUMENTS)
    def message_submit_missing_account(self, argument):
        """Сообщение для несуществующего аккаунта -> 404."""
        self.expect_error(404, self.client.post_message_submit,
                          account=MISSING_UID, argument=argument)

    @rule(uid=messages)
    def message_modify_missing_account(self, uid):
        """Перенос сообщения на несуществующий аккаунт -> 404."""
        self.expect_error(404, self.client.patch_message_modify, uid,
                          account=MISSING_UID)

    @rule(uid=accounts, value=BAD_NUMBERS)
    def bad_number(self, uid, value):
        """Не целое число в числовом поле -> 400."""
        self.expect_error(400, self.client.patch_account_modify, uid,
                          timestamp=value)

    @rule(uid=accounts)
    def bad_xml(self, uid):
        """Тело запроса - не XML -> 400."""
        self.expect_error(400, self.client.send, "PATCH",
                          f"account-modify/{uid}", body=b"<oops")


class SqlApiModel(ApiModel):
    """Этап 3: та же модель, данные в SQLite, задачи реально считаются."""

    storage_class = SqlStorage
    test_mode = False


SETTINGS = settings(max_examples=50, stateful_step_count=30, deadline=None)
TestFileStorage = ApiModel.TestCase
TestFileStorage.settings = SETTINGS
TestSqlStorage = SqlApiModel.TestCase
TestSqlStorage.settings = SETTINGS
