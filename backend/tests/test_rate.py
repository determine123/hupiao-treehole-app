import pytest
from fastapi import HTTPException
from redis import RedisError
from sqlalchemy import select
from app import security
from app.db import Session
from app.models import RateBucket


def test_database_rate_window_reports_remaining_wait_and_cleans_expired(
    client, monkeypatch
):
    clock = [590]
    monkeypatch.setattr(security.time, "time", lambda: clock[0])
    monkeypatch.setattr(security, "redis", None)
    with Session() as session:
        security.rate(session, "test-author", limit=1, seconds=600)
        row = session.scalar(select(RateBucket))
        assert row.expires == 600 and row.count == 1
        assert "test-author" not in row.key
        with pytest.raises(HTTPException) as error:
            security.rate(session, "test-author", limit=1, seconds=600)
        assert error.value.status_code == 429
        assert error.value.headers["Retry-After"] == "10"
        clock[0] = 599
        with pytest.raises(HTTPException) as error:
            security.rate(session, "test-author", limit=1, seconds=600)
        assert error.value.headers["Retry-After"] == "1"
        clock[0] = 600
        security.rate(session, "test-author", limit=1, seconds=600)
        rows = session.scalars(select(RateBucket)).all()
        assert len(rows) == 1 and rows[0].count == 1 and rows[0].expires == 1200


def test_redis_rate_ttl_and_retry_follow_the_same_window(client, monkeypatch):
    clock, calls, counts = [590], [], {}

    class FakeRedis:
        def eval(self, script, nkeys, key, ttl):
            calls.append((nkeys, key, ttl))
            counts[key] = counts.get(key, 0) + 1
            return counts[key]

    monkeypatch.setattr(security.time, "time", lambda: clock[0])
    monkeypatch.setattr(security, "redis", FakeRedis())
    with Session() as session:
        security.rate(session, "redis-author", limit=1, seconds=600)
        assert calls[0][0] == 1 and calls[0][2] == 11
        clock[0] = 599
        with pytest.raises(HTTPException) as error:
            security.rate(session, "redis-author", limit=1, seconds=600)
        assert calls[-1][2] == 2
        assert error.value.headers["Retry-After"] == "1"
        clock[0] = 600
        security.rate(session, "redis-author", limit=1, seconds=600)
        assert calls[-1][1] != calls[0][1] and calls[-1][2] == 601
        assert session.scalar(select(RateBucket)) is None


def test_redis_failure_does_not_bypass_shared_limits(client, monkeypatch):
    class UnavailableRedis:
        def eval(self, *args):
            raise RedisError("temporarily unavailable")

    monkeypatch.setattr(security, "redis", UnavailableRedis())
    with Session() as session:
        with pytest.raises(HTTPException) as error:
            security.rate(session, "author", limit=1, seconds=600)
        assert error.value.status_code == 503
        assert session.scalar(select(RateBucket)) is None
