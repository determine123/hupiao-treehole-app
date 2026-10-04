import pytest
from app.config import Settings


@pytest.mark.parametrize(
    "prefix", ["postgres://", "postgresql://", "postgresql+psycopg://"]
)
def test_managed_database_driver(prefix):
    settings = Settings(
        _env_file=None, database_url=prefix + "user:password@host/database"
    )
    assert settings.database_url == "postgresql+psycopg://user:password@host/database"


def test_render_public_url(monkeypatch):
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://hupiao-test.onrender.com")
    monkeypatch.delenv("PUBLIC_API_URL", raising=False)
    assert Settings(_env_file=None).public_api_url == "https://hupiao-test.onrender.com"
