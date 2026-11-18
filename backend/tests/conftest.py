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
    "SOURCING_MODE": "demo", "TOSS_SECRET_KEY": "test_sk_dummy", "ADMIN_TOKEN": "real-admin-token-for-tests", "ADMIN_EMAIL": "owner@test.dev",
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
def test_admin_headers(client):
    """테스트 관리자(읽기 전용)"""
    return _login(client, "admin")


@pytest.fixture(scope="session")
def admin_headers(client):
    """실제 관리자 (.env ADMIN_TOKEN)"""
    res = client.post("/api/auth/admin-login", json={"token": "real-admin-token-for-tests"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}
