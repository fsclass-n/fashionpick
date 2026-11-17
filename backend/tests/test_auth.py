import pytest

from backend.app.security import validate_password


@pytest.mark.parametrize("pw", ["short1!", "alllowercase1!", "ALLUPPER1!", "NoDigits!!", "NoSpecial11", ""])
def test_password_rule_rejects_weak(pw):
    with pytest.raises(ValueError):
        validate_password(pw)


def test_password_rule_accepts_strong():
    validate_password("Fashion!2026")


def test_register_login_me(client):
    res = client.post("/api/auth/register", json={"email": "new@fp.dev", "name": "신규", "password": "weakpass"})
    assert res.status_code == 422
    res = client.post("/api/auth/register", json={"email": "new@fp.dev", "name": "신규", "password": "Strong!Pass1"})
    assert res.status_code == 201
    assert res.json()["user"]["role"] == "user"
    assert client.post("/api/auth/register", json={"email": "new@fp.dev", "name": "x", "password": "Strong!Pass1"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "new@fp.dev", "password": "Wrong!Pass1"}).status_code == 401
    token = client.post("/api/auth/login", json={"email": "new@fp.dev", "password": "Strong!Pass1"}).json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == "new@fp.dev"


def test_protected_requires_token(client):
    assert client.get("/api/products").status_code == 401


def test_admin_guard(client, user_headers, admin_headers):
    assert client.get("/api/admin/users", headers=user_headers).status_code == 403
    users = client.get("/api/admin/users", headers=admin_headers).json()
    target = next(u for u in users if u["email"] == "new@fp.dev")
    res = client.patch(f"/api/admin/users/{target['id']}/role", json={"role": "admin"}, headers=admin_headers)
    assert res.json()["role"] == "admin"
    me = next(u for u in users if u["role"] == "admin" and u["email"].startswith("admin"))
    assert client.patch(f"/api/admin/users/{me['id']}/role", json={"role": "user"}, headers=admin_headers).status_code == 400


def test_oauth_not_configured(client):
    assert client.get("/api/auth/oauth/google/login", follow_redirects=False).status_code == 503
    assert client.get("/api/auth/providers").json()["test_login"] is True
