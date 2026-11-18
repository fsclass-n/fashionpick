from backend.app.services.catalog import margin_rate, suggest_sale_price


def test_pricing():
    assert suggest_sale_price(39500, 2.2) == 86900
    assert suggest_sale_price(1000, 1.0) >= 2000
    assert margin_rate(10000, 25000) == 0.6


def test_trends_public(client):
    top = client.get("/api/trends/public-top").json()
    assert len(top) == 10 and top[0]["rank"] == 1
    hist = client.get("/api/trends/history").json()
    assert len(hist["series"]) == 5 and len(hist["series"][0]["points"]) > 1
    cats = client.get("/api/trends/categories").json()
    assert abs(sum(c["share"] for c in cats) - 1) < 0.01


def test_shop_public_hides_wholesale_info(client):
    home = client.get("/api/shop/home").json()
    assert home["new_arrivals"] and home["trend_keywords"] and home["lookbook"]
    item = client.get("/api/shop/products?size=1").json()["items"][0]
    detail = client.get(f"/api/shop/products/{item['id']}").json()
    for secret in ("wholesale_price", "supplier_id", "supplier_name", "margin_rate", "source_url"):
        assert secret not in item and secret not in detail
    assert detail["price"] > 0 and isinstance(detail["related"], list)


def test_admin_register_then_user_order_creates_po(client, user_headers, admin_headers):
    sourced = client.get("/api/products?status=sourced&size=1", headers=admin_headers).json()["items"][0]
    reg = client.post(f"/api/products/{sourced['id']}/register", json={}, headers=admin_headers).json()
    assert reg["status"] == "registered" and reg["registered_name"].startswith("[")
    assert client.get(f"/api/shop/products/{reg['id']}").status_code == 200

    order = client.post("/api/shop/orders", headers=user_headers, json={
        "payment_method": "bank", "depositor_name": "테스트", "customer_phone": "010-1234-5678", "address": "서울특별시 성동구 성수동",
        "items": [{"product_id": reg["id"], "option": "블랙/M", "quantity": 2}]}).json()
    assert order["total_amount"] == reg["sale_price"] * 2 and order["user_id"]
    assert order["status"] == "pending_payment" and order["payment"]["provider"] == "bank"
    assert order["items"][0]["purchase_order_id"] is None  # 입금 전에는 발주하지 않음
    order = client.post(f"/api/orders/{order['id']}/confirm-deposit", headers=admin_headers).json()
    assert order["payment_status"] == "paid" and order["status"] in {"ordering", "received"}
    mine = client.get("/api/me/orders", headers=user_headers).json()
    assert any(o["id"] == order["id"] for o in mine)

    po_id = order["items"][0]["purchase_order_id"]
    po = client.get(f"/api/purchase-orders/{po_id}", headers=admin_headers).json()
    assert po["status"] == "pending" and po["supplier_name"] == reg["supplier_name"]
    xlsx = client.get(f"/api/purchase-orders/{po_id}/excel", headers=admin_headers)
    assert xlsx.status_code == 200 and xlsx.content[:2] == b"PK"
    assert client.get(f"/api/purchase-orders/{po_id}/pdf", headers=admin_headers).content[:4] == b"%PDF"

    sent = client.post(f"/api/purchase-orders/{po_id}/send", headers=admin_headers).json()
    assert sent["status"] == "sent" and sent["send_channel"] == "simulation"
    recv = client.patch(f"/api/purchase-orders/{po_id}/status", json={"status": "received"}, headers=admin_headers).json()
    assert recv["status"] == "received"


def test_order_webhook_auth(client):
    body = {"customer_name": "외부", "items": [{"product_id": 1, "quantity": 1}]}
    assert client.post("/api/orders/webhook", json=body).status_code == 401
    assert client.post("/api/orders/webhook", json=body, headers={"X-Webhook-Secret": "hook-secret"}).status_code == 201


def test_rpa_job_run_sync(client, admin_headers):
    from backend.app.services.rpa_jobs import run_job
    assert run_job("trend_collect", "manual").status == "success"
    assert run_job("product_sourcing", "manual").status == "success"
    logs = client.get("/api/admin/rpa/logs", headers=admin_headers).json()
    assert {l["job_name"] for l in logs} >= {"trend_collect", "product_sourcing"}
    assert all(s["success"] >= 1 for s in client.get("/api/admin/rpa/stats", headers=admin_headers).json())


def _token(headers):
    return headers["Authorization"].split()[1]


def test_websocket_events_are_scoped(client, user_headers, test_admin_headers, admin_headers):
    """주문 알림(order.created)은 관리자에게만, 주문자 본인에게는 order.placed 가 간다."""
    product_id = client.get("/api/shop/products?size=1").json()["items"][0]["id"]
    with client.websocket_connect(f"/ws?token={_token(test_admin_headers)}") as admin_ws, \
            client.websocket_connect(f"/ws?token={_token(user_headers)}") as user_ws:
        assert admin_ws.receive_json()["event"] == "hello" and user_ws.receive_json()["event"] == "hello"
        res = client.post("/api/shop/orders", headers=user_headers, json={
            "customer_phone": "010-1234-5678", "address": "서울특별시 중구", "items": [{"product_id": product_id, "quantity": 1}]})
        assert res.status_code == 201
        assert user_ws.receive_json()["event"] == "order.placed"
        assert admin_ws.receive_json()["event"] == "order.created"  # 결제 전이라 발주 이벤트는 아직 없음


def test_placeholder_svg(client):
    res = client.get("/media/placeholder/abcdef123456.svg?label=숏패딩&color=블랙")
    assert res.headers["content-type"].startswith("image/svg+xml") and "<svg" in res.text
