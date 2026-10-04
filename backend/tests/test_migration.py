from pathlib import Path
import os
import uuid
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from app import db


def test_upgrade_preserves_legacy_audit_privacy(tmp_path, monkeypatch):
    test_url = os.environ.get("TEST_DATABASE_URL", "")
    schema = "migration_" + uuid.uuid4().hex
    base_engine = db.engine
    if test_url.startswith("postgresql"):
        with base_engine.begin() as c:
            c.execute(text('CREATE SCHEMA "' + schema + '"'))
        engine = create_engine(
            test_url, connect_args={"options": "-csearch_path=" + schema}
        )
    else:
        engine = create_engine(
            "sqlite:///" + str(tmp_path / "migration.db").replace("\\", "/")
        )
    monkeypatch.setattr(db, "engine", engine)
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    try:
        command.upgrade(config, "47350762dcb6")
        with engine.begin() as c:
            c.execute(
                text(
                    "INSERT INTO audit(id,target,action,note,created) VALUES (:id,:target,'hide','internal legacy note',1)"
                ),
                {"id": "a" * 36, "target": "b" * 36},
            )
        command.upgrade(config, "head")
        with engine.connect() as c:
            row = c.execute(
                text("SELECT note,public_reason,target_type FROM audit")
            ).one()
            assert tuple(row) == ("internal legacy note", "", "unknown")
        command.check(config)
    finally:
        engine.dispose()
        if test_url.startswith("postgresql"):
            with base_engine.begin() as c:
                c.execute(text('DROP SCHEMA "' + schema + '" CASCADE'))
