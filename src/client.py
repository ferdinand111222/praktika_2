"""Клиент к HTTP API варианта 15.

Имена методов имеют вид метод_таблица_действие, например
post_account_submit. Одна запись возвращается словарём, несколько -
списком словарей. Все значения - строки (так они лежат в XML).
При ошибке (400, 401, 404) выбрасывается urllib.error.HTTPError.
"""
import base64
from xml.etree.ElementTree import Element, SubElement, fromstring, tostring
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def to_dict(node):
    """<account><uid>1</uid>...</account> -> {"uid": "1", ...}"""
    return {item.tag: item.text or "" for item in node}


def to_list(node):
    """<accounts><account>...</account>...</accounts> -> [{...}, ...]"""
    return [to_dict(item) for item in node]


def to_body(tag, fields):
    """{"ip": "1.2.3.4"} -> b"<tag><ip>1.2.3.4</ip></tag>" """
    node = Element(tag)
    for key, value in fields.items():
        SubElement(node, key).text = str(value)
    return tostring(node)


class Client:
    """Клиент HTTP API с Basic-авторизацией."""

    def __init__(self, url, username, password):
        """url - адрес сервера, например http://127.0.0.1:8000"""
        self.url = url.rstrip("/") + "/core/api/"
        pair = f"{username}:{password}".encode()
        token = base64.b64encode(pair).decode()
        self.headers = {"Authorization": f"Basic {token}",
                        "Content-Type": "application/xml"}

    def send(self, method, path, params=None, body=None):
        """Отправить запрос и вернуть корневой XML-элемент ответа."""
        params = {k: v for k, v in (params or {}).items() if v is not None}
        url = self.url + path + "?" + urlencode(params)
        request = Request(url, data=body, headers=self.headers,
                          method=method)
        with urlopen(request) as answer:
            return fromstring(answer.read())

    def post_account_submit(self, **fields):
        """1.1 Создать аккаунт: post_account_submit(ip="10.0.0.1")."""
        return to_dict(self.send("POST", "account-submit", fields))

    def get_account_collect(self, **filters):
        """1.2 Найти аккаунты: get_account_collect(ip="10.0.0.1")."""
        return to_list(self.send("GET", "account-collect", filters))

    def get_account_inspect(self, uid):
        """1.3 Прочитать аккаунт по uid."""
        return to_dict(self.send("GET", "account-inspect", {"uid": uid}))

    def patch_account_modify(self, uid, **fields):
        """1.4 Изменить аккаунт: patch_account_modify(1, ip="...")."""
        body = to_body("account", fields)
        return to_dict(self.send("PATCH", f"account-modify/{uid}",
                                 body=body))

    def post_message_submit(self, **fields):
        """2.1 Отправить задачу: post_message_submit(account=1, ...)."""
        return to_dict(self.send("POST", "message-submit", fields))

    def get_message_collect(self, account, **filters):
        """2.2 Найти сообщения аккаунта."""
        return to_list(self.send("GET", f"message-collect/{account}",
                                 filters))

    def get_message_inspect(self, uid):
        """2.3 Прочитать сообщение по uid."""
        return to_dict(self.send("GET", "message-inspect", {"uid": uid}))

    def patch_message_modify(self, uid, **fields):
        """2.4 Изменить сообщение: patch_message_modify(1, argument=..)."""
        body = to_body("message", fields)
        return to_dict(self.send("PATCH", f"message-modify/{uid}",
                                 body=body))

    def get_feedback_collect(self, message, **filters):
        """3.1 Найти результаты выполнения сообщения."""
        return to_list(self.send("GET", f"feedback-collect/{message}",
                                 filters))

    def get_feedback_inspect(self, uid):
        """3.2 Прочитать результат по uid."""
        return to_dict(self.send("GET", "feedback-inspect", {"uid": uid}))

    def get_report_collect(self):
        """4.1 Получить отчёт по формуле (15)."""
        return to_list(self.send("GET", "report-collect"))
