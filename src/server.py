"""Запуск веб-сервера с настройками из config.ini.

Запуск из корня проекта:
    python -m src.server
"""
import configparser

from bottle import run

from src.app import make_app
from src.file_storage import FileStorage
from src.sql_storage import SqlStorage

STORAGES = {"file": FileStorage, "sqlite": SqlStorage}


def main(path="config.ini"):
    """Прочитать настройки, открыть хранилище и запустить сервер."""
    config = configparser.ConfigParser()
    config.read(path, encoding="utf-8")
    storage_class = STORAGES[config["storage"]["kind"]]
    storage = storage_class(config["storage"]["path"])
    app = make_app(storage,
                   config["auth"]["username"],
                   config["auth"]["password"],
                   config["app"].getboolean("test_mode"))
    run(app, host=config["app"]["host"], port=config["app"].getint("port"))


if __name__ == "__main__":
    main()
