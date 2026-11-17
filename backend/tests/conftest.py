import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
_tmp = tempfile.mkdtemp(prefix="fashionpick-test-")
os.environ.update({
    "DATABASE_URL": f"sqlite:///{Path(_tmp, 'test.db').as_posix()}",
    "SCHEDULER_ENABLED": "false", "RPA_MODE": "demo", "ENABLE_TEST_LOGIN": "true",
    "AUTO_PURCHASE_ORDER": "true", "AUTO_SEND_PURCHASE_ORDER": "false", "SMTP_HOST": "",
    "SECRET_KEY": "test-secret-key-for-pytest-only-0123456789", "ORDER_WEBHOOK_SECRET": "hook-secret",
    "TELEGRAM_BOT_TOKEN": "", "DISCORD_WEBHOOK_URL": "",
})

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, role):
    res = client.post("/api/auth/test-login", json={"role": role})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture(scope="session")
def user_headers(client):
    return _login(client, "user")


@pytest.fixture(scope="session")
def admin_headers(client):
    return _login(client, "admin")
