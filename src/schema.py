"""Схема данных с рис. 15: таблицы и типы их полей.

Поле uid (первичный ключ) здесь не указано: его выдаёт хранилище.
"""

TABLES = {
    "account": {
        "timestamp": int,
        "ip": str,
    },
    "message": {
        "timestamp": int,
        "argument": str,
        "account": int,
        "completed": int,
    },
    "feedback": {
        "timestamp": int,
        "result": str,
        "status": str,
        "failure": str,
        "message": int,
    },
}
