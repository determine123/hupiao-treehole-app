import gzip
import json
import uuid

import pytest
from sqlalchemy import create_engine, event, select, text
from app.db import Base, engine
from app.models import User, Post, Feedback
from backup import export_snapshot, restore_snapshot
from conftest import user, post


@pytest.fixture
def destination(tmp_path):
    schema = "backup_" + uuid.uuid4().hex
    if engine.dialect.name == "postgresql":
        with engine.begin() as connection:
            connection.execute(text('CREATE SCHEMA "' + schema + '"'))
        target = create_engine(
            engine.url, connect_args={"options": "-csearch_path=" + schema}
        )
    else:
        target = create_engine(
            "sqlite:///" + str(tmp_path / "restore.db").replace("\\", "/")
        )

        @event.listens_for(target, "connect")
        def foreign_keys(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(target)
    try:
        yield target
    finally:
        target.dispose()
        if engine.dialect.name == "postgresql":
            with engine.begin() as connection:
                connection.execute(text('DROP SCHEMA "' + schema + '" CASCADE'))


def seeded_snapshot(client, tmp_path):
    author = user(client)
    post(client, author)
    response = client.post(
        "/feedback",
        headers=author,
        json={
            "kind": "idea",
            "body": "需要恢复的私有反馈",
            "device": "test",
            "app_version": "1.0.2",
        },
    )
    assert response.status_code == 201
    snapshot = tmp_path / "snapshot.jsonl.gz"
    counts = export_snapshot(engine, snapshot)
    return snapshot, counts


def test_snapshot_restores_identity_and_private_content(client, destination, tmp_path):
    snapshot, counts = seeded_snapshot(client, tmp_path)
    assert counts["users"] == counts["posts"] == counts["feedback"] == 1
    assert restore_snapshot(destination, snapshot) == counts
    for table in [User.__table__, Post.__table__, Feedback.__table__]:
        with engine.connect() as original, destination.connect() as restored:
            assert list(original.execute(select(table))) == list(
                restored.execute(select(table))
            )
    with pytest.raises(ValueError, match="must be empty"):
        restore_snapshot(destination, snapshot)
    with destination.connect() as connection:
        assert len(connection.execute(select(User.__table__)).all()) == 1


def test_invalid_snapshot_rolls_back_inserted_rows(client, destination, tmp_path):
    snapshot, counts = seeded_snapshot(client, tmp_path)
    with gzip.open(snapshot, "rt", encoding="utf-8") as source:
        records = [json.loads(line) for line in source]
    records[-1]["counts"]["posts"] = 999
    corrupt = tmp_path / "bad-counts.gz"
    with gzip.open(corrupt, "wt", encoding="utf-8") as output:
        output.write("\n".join(json.dumps(row) for row in records) + "\n")
    with pytest.raises(ValueError, match="count mismatch"):
        restore_snapshot(destination, corrupt)
    with destination.connect() as connection:
        assert connection.execute(select(User.__table__)).first() is None
        assert connection.execute(select(Post.__table__)).first() is None
    assert restore_snapshot(destination, snapshot) == counts


def test_export_failure_preserves_previous_file_and_cleans_partial(
    client, tmp_path, monkeypatch
):
    snapshot, counts = seeded_snapshot(client, tmp_path)
    previous = snapshot.read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        export_snapshot(engine, snapshot)
    assert snapshot.read_bytes() == previous
    files_before = set(tmp_path.iterdir())

    def fail(*args, **kwargs):
        raise OSError("simulated disk write failure")

    monkeypatch.setattr(gzip, "open", fail)
    with pytest.raises(OSError):
        export_snapshot(engine, tmp_path / "new-snapshot.gz")
    assert set(tmp_path.iterdir()) == files_before
