from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings


class Base(DeclarativeBase):
    pass


options = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    options["connect_args"] = {"check_same_thread": False, "timeout": 20}
else:
    options.update(
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_recycle=1800,
        pool_timeout=10,
    )
engine = create_engine(settings.database_url, **options)
if engine.dialect.name == "sqlite":

    @event.listens_for(engine, "connect")
    def setup(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")


Session = sessionmaker(engine, expire_on_commit=False)


def database():
    with Session() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
