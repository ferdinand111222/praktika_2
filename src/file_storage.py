"""Этап 2. Файловая СУБД: все таблицы лежат в одном JSON-файле."""
import json
import os

from src.schema import TABLES


class FileStorage:
    """Хранилище записей в JSON-файле.

    Содержимое файла: {"account": [...], "message": [...],
    "feedback": [...]}, каждая запись - словарь с полем uid.
    """

    def __init__(self, path):
        """Открыть файл базы или начать с пустых таблиц."""
        self.path = path
        self.tables = {name: [] for name in TABLES}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as file:
                self.tables = json.load(file)

    def save(self):
        """Записать все таблицы на диск."""
        with open(self.path, "w", encoding="utf-8") as file:
            json.dump(self.tables, file, ensure_ascii=False, indent=2)

    def add(self, table, data):
        """Добавить запись с новым uid и вернуть её."""
        rows = self.tables[table]
        record = {"uid": len(rows) + 1, **data}
        rows.append(record)
        self.save()
        return dict(record)

    def find(self, table, filters):
        """Вернуть записи, у которых поля равны значениям из filters."""
        return [dict(row) for row in self.tables[table]
                if all(row[key] == value for key, value in filters.items())]

    def get(self, table, uid):
        """Вернуть запись по uid или None, если её нет."""
        found = self.find(table, {"uid": uid})
        return found[0] if found else None

    def change(self, table, uid, data):
        """Изменить поля существующей записи и вернуть её."""
        row = next(row for row in self.tables[table] if row["uid"] == uid)
        row.update(data)
        self.save()
        return dict(row)

    def close(self):
        """Закрыть хранилище: файл и так закрывается после каждой записи."""
