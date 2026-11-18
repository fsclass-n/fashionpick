"""모의 결제: 토스페이먼츠 승인(서버 대조) · 무통장입금 입금 확인."""
import httpx

from backend.app.routers import shop


class FakeRes:
    def __init__(self, code, body):
        self.status_code, self._body, self.headers, self.text = code, body, {"content-type": "application/json"}, str(body)

    def json(self):
        return self._body


def _order(client, headers, method):
    pid = client.get("/api/shop/products?size=1").json()["items"][0]["id"]
    return client.post("/api/shop/orders", headers=headers, json={
        "payment_method": method, "customer_phone": "010-1234-5678", "address": "서울특별시 중구",
        "items": [{"product_id": pid, "quantity": 1}]}).json()


def test_payment_config_public(client):
    cfg = client.get("/api/shop/payments/config").json()
    assert cfg["toss_client_key"].startswith("test_") and cfg["bank"]["account"] and "secret" not in str(cfg).lower()


def test_toss_confirm_success_creates_po(client, user_headers, monkeypatch):
    order = _order(client, user_headers, "card")
    pay = order["payment"]
    assert pay["provider"] == "toss" and pay["order_id"] == order["order_no"] and pay["amount"] == order["total_amount"]
    calls = []
    monkeypatch.setattr(shop.httpx, "post", lambda url, **kw: calls.append(kw) or FakeRes(200, {"status": "DONE"}))
    res = client.post("/api/shop/payments/toss/confirm", headers=user_headers,
                      json={"paymentKey": "tgen_test", "orderId": pay["order_id"], "amount": pay["amount"]})
    assert res.status_code == 200 and res.json()["payment_status"] == "paid"
    assert res.json()["items"][0]["purchase_order_id"]
    assert calls and calls[0]["headers"]["Authorization"].startswith("Basic ")


def test_toss_confirm_rejects_tampered_amount(client, user_headers, monkeypatch):
    order = _order(client, user_headers, "easypay")
    monkeypatch.setattr(shop.httpx, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not call toss")))
    res = client.post("/api/shop/payments/toss/confirm", headers=user_headers,
                      json={"paymentKey": "tgen_test", "orderId": order["order_no"], "amount": 100})
    assert res.status_code == 400


def test_toss_confirm_failure_marks_failed(client, user_headers, monkeypatch):
    order = _order(client, user_headers, "card")
    monkeypatch.setattr(shop.httpx, "post", lambda url, **kw: FakeRes(400, {"message": "카드 승인 거절"}))
    res = client.post("/api/shop/payments/toss/confirm", headers=user_headers,
                      json={"paymentKey": "tgen_x", "orderId": order["order_no"], "amount": order["total_amount"]})
    assert res.status_code == 400 and "거절" in res.json()["detail"]


def test_bank_deposit_only_real_admin(client, user_headers, test_admin_headers, admin_headers):
    order = _order(client, user_headers, "bank")
    assert order["payment"]["provider"] == "bank" and order["deposit_due_at"]
    assert client.post(f"/api/orders/{order['id']}/confirm-deposit", headers=user_headers).status_code == 403
    assert client.post(f"/api/orders/{order['id']}/confirm-deposit", headers=test_admin_headers).status_code == 403
    ok = client.post(f"/api/orders/{order['id']}/confirm-deposit", headers=admin_headers).json()
    assert ok["payment_status"] == "paid" and ok["paid_at"]
    assert client.post(f"/api/orders/{order['id']}/confirm-deposit", headers=admin_headers).status_code == 400
