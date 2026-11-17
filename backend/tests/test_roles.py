"""권한 체계: 실제 관리자(ADMIN_TOKEN, 전체 CRUD) / 테스트 관리자(읽기 전용) / 일반 회원."""


def test_roles_issued(client, user_headers, test_admin_headers, admin_headers):
    assert client.get("/api/auth/me", headers=user_headers).json()["role"] == "user"
    assert client.get("/api/auth/me", headers=test_admin_headers).json()["role"] == "test_admin"
    me = client.get("/api/auth/me", headers=admin_headers).json()
    assert me["role"] == "admin" and me["email"] == "owner@test.dev"


def test_admin_login_rejects_wrong_token(client):
    assert client.post("/api/auth/admin-login", json={"token": "wrong"}).status_code == 401
    assert client.get("/api/auth/providers").json()["admin_login"] is True


def test_test_admin_can_read_admin_views(client, test_admin_headers):
    for path in ("/api/admin/users", "/api/admin/rpa/jobs", "/api/admin/rpa/logs", "/api/admin/system",
                 "/api/products", "/api/suppliers", "/api/orders", "/api/purchase-orders", "/api/dashboard/summary"):
        assert client.get(path, headers=test_admin_headers).status_code == 200, path


def test_test_admin_writes_blocked(client, test_admin_headers):
    product_id = client.get("/api/shop/products?size=1").json()["items"][0]["id"]
    writes = [
        ("post", "/api/admin/rpa/jobs/trend_collect/run", None),
        ("patch", "/api/admin/rpa/jobs/trend_collect", {"enabled": False}),
        ("patch", "/api/admin/users/1/role", {"role": "admin"}),
        ("post", "/api/suppliers", {"name": "차단되어야 함"}),
        ("delete", "/api/suppliers/1", None),
        ("post", "/api/orders/simulate", None),
        ("post", "/api/purchase-orders/generate", None),
        ("post", f"/api/products/{product_id}/unregister", None),
        ("post", "/api/shop/orders", {"customer_phone": "010-1234-5678", "address": "서울특별시 중구",
                                      "items": [{"product_id": product_id, "quantity": 1}]}),
    ]
    for method, path, body in writes:
        res = getattr(client, method)(path, headers=test_admin_headers, **({"json": body} if body else {}))
        assert res.status_code == 403, (path, res.text)
        assert "읽기 전용" in res.json()["detail"]


def test_user_cannot_access_admin(client, user_headers):
    assert client.get("/api/admin/users", headers=user_headers).status_code == 403
    assert client.get("/api/products", headers=user_headers).status_code == 403
    assert client.post("/api/orders/simulate", headers=user_headers).status_code == 403


def test_real_admin_full_crud(client, admin_headers):
    created = client.post("/api/suppliers", headers=admin_headers, json={"name": "CRUD 테스트 공급처", "order_method": "manual"})
    assert created.status_code == 201
    sid = created.json()["id"]
    updated = client.put(f"/api/suppliers/{sid}", headers=admin_headers,
                         json={"name": "CRUD 테스트 공급처", "order_method": "email", "email": "po@test.dev"})
    assert updated.json()["order_method"] == "email"
    assert client.delete(f"/api/suppliers/{sid}", headers=admin_headers).status_code == 204
    assert client.patch("/api/admin/rpa/jobs/po_dispatch", headers=admin_headers, json={"interval_minutes": 60}).json()["interval_minutes"] == 60


def test_test_admin_role_is_protected(client, admin_headers, test_admin_headers):
    tid = client.get("/api/auth/me", headers=test_admin_headers).json()["id"]
    res = client.patch(f"/api/admin/users/{tid}/role", headers=admin_headers, json={"role": "admin"})
    assert res.status_code == 400


def test_cors_header_on_read_only_403(client, test_admin_headers):
    res = client.post("/api/orders/simulate", headers={**test_admin_headers, "Origin": "http://localhost:5173"})
    assert res.status_code == 403 and res.headers.get("access-control-allow-origin") == "http://localhost:5173"
