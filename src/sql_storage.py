"""Этап 3. Слой доступа к данным на SQLite через ORM SQLAlchemy.

Методы те же, что у FileStorage, поэтому API работает с любым из них.
"""
from sqlalchemy import ForeignKey, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""


class Account(Base):
    """Таблица Account."""

    __tablename__ = "account"
    uid: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[int]
    ip: Mapped[str]


class Message(Base):
    """Таблица Message: вычислительная задача пользователя."""

    __tablename__ = "message"
    uid: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[int]
    argument: Mapped[str]
    account: Mapped[int] = mapped_column(ForeignKey("account.uid"))
    completed: Mapped[int]


class Feedback(Base):
    """Таблица Feedback: результат выполнения задачи."""

    __tablename__ = "feedback"
    uid: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[int]
    result: Mapped[str]
    status: Mapped[str]
    failure: Mapped[str]
    message: Mapped[int] = mapped_column(ForeignKey("message.uid"))


MODELS = {"account": Account, "message": Message, "feedback": Feedback}


def to_dict(row):
    """ORM-объект -> обычный словарь {поле: значение}."""
    return {column.name: getattr(row, column.name)
            for column in row.__table__.columns}


class SqlStorage:
    """Хранилище записей в базе SQLite."""

    def __init__(self, path):
        """Подключиться к файлу базы и создать таблицы, если их нет."""
        self.engine = create_engine(f"sqlite:///{path}")
        Base.metadata.create_all(self.engine)

    def add(self, table, data):
        """Добавить запись (uid выдаёт SQLite) и вернуть её."""
        with Session(self.engine) as session:
            row = MODELS[table](**data)
            session.add(row)
            session.commit()
            return to_dict(row)

    def find(self, table, filters):
        """Вернуть записи, у которых поля равны значениям из filters."""
        model = MODELS[table]
        query = select(model).filter_by(**filters).order_by(model.uid)
        with Session(self.engine) as session:
            return [to_dict(row) for row in session.scalars(query)]

    def get(self, table, uid):
        """Вернуть запись по uid или None, если её нет."""
        with Session(self.engine) as session:
            row = session.get(MODELS[table], uid)
            return to_dict(row) if row else None

    def change(self, table, uid, data):
        """Изменить поля существующей записи и вернуть её."""
        with Session(self.engine) as session:
            row = session.get(MODELS[table], uid)
            for key, value in data.items():
                setattr(row, key, value)
            session.commit()
            return to_dict(row)

    def close(self):
        """Закрыть соединения с базой."""
        self.engine.dispose()
