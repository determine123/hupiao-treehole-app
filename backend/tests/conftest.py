import os, tempfile

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "sqlite:///" + tempfile.gettempdir().replace("\\", "/") + "/hupiao-mobile-tests.db",
)
os.environ["ENVIRONMENT"] = "development"
os.environ["REDIS_URL"] = ""
os.environ["ADMIN_TOKEN"] = "test-admin-token-with-more-than-32-characters"
os.environ["TOKEN_PEPPER"] = "test-pepper-not-for-production-with-32-characters"
os.environ["MODERATE_BEFORE_PUBLISH"] = "true"
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine
from app.config import settings


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as client:
        yield client


ADMIN = {"X-Admin-Token": settings.admin_token}


def user(client):
    r = client.post("/session", json={"accepted_terms": "2026-10-04"})
    assert r.status_code == 201, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def post(client, headers):
    r = client.post(
        "/posts",
        headers=headers,
        json={
            "title": "在上海生活的一个问题",
            "body": "这是一条本机测试帖子，不会上传生产服务器。",
            "category": "生活求助",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def approve(client, type, id):
    r = client.post(
        "/admin/moderate",
        headers=ADMIN,
        json={
            "target_type": type,
            "target_id": id,
            "decision": "approve",
            "note": "已检查测试内容",
        },
    )
    assert r.status_code == 200, r.text
