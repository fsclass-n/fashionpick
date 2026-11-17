from backend.app.services.catalog import margin_rate, suggest_sale_price


def test_pricing():
    assert suggest_sale_price(39500, 2.2) == 86900
    assert suggest_sale_price(1000, 1.0) >= 2000
    assert margin_rate(10000, 25000) == 0.6


def test_trends_seeded(client, user_headers):
    top = client.get("/api/trends/public-top").json()
    assert len(top) == 10 and top[0]["rank"] == 1
    hist = client.get("/api/trends/history", headers=user_headers).json()
    assert len(hist["series"]) == 5 and len(hist["series"][0]["points"]) > 1
    cats = client.get("/api/trends/categories", headers=user_headers).json()
    assert abs(sum(c["share"] for c in cats) - 1) < 0.01


def test_register_product_and_order_creates_po(client, user_headers):
    sourced = client.get("/api/products?status=sourced&size=1", headers=user_headers).json()["items"][0]
    reg = client.post(f"/api/products/{sourced['id']}/register", json={}, headers=user_headers).json()
    assert reg["status"] == "registered" and reg["registered_name"].startswith("[")
    order = client.post("/api/orders", headers=user_headers, json={
        "customer_name": "테스트", "items": [{"product_id": reg["id"], "option": "블랙/M", "quantity": 2}]}).json()
    assert order["total_amount"] == reg["sale_price"] * 2
    po_id = order["items"][0]["purchase_order_id"]
    assert po_id
    po = client.get(f"/api/purchase-orders/{po_id}", headers=user_headers).json()
    assert po["status"] == "pending" and po["supplier_name"] == reg["supplier_name"]
    assert any(i["id"] == order["items"][0]["id"] for i in po["items"])

    xlsx = client.get(f"/api/purchase-orders/{po_id}/excel", headers=user_headers)
    assert xlsx.status_code == 200 and xlsx.content[:2] == b"PK"
    pdf = client.get(f"/api/purchase-orders/{po_id}/pdf", headers=user_headers)
    assert pdf.content[:4] == b"%PDF"

    sent = client.post(f"/api/purchase-orders/{po_id}/send", headers=user_headers).json()
    assert sent["status"] == "sent" and sent["send_channel"] == "simulation"
    recv = client.patch(f"/api/purchase-orders/{po_id}/status", json={"status": "received"}, headers=user_headers).json()
    assert recv["status"] == "received"
    assert client.get(f"/api/orders/{order['id']}", headers=user_headers).json()["status"] in {"stocked", "ordered", "ordering"}


def test_order_webhook_auth(client):
    body = {"customer_name": "외부", "items": [{"product_id": 1, "quantity": 1}]}
    assert client.post("/api/orders/webhook", json=body).status_code == 401
    assert client.post("/api/orders/webhook", json=body, headers={"X-Webhook-Secret": "hook-secret"}).status_code == 201


def test_rpa_job_run_sync(client, admin_headers):
    from backend.app.services.rpa_jobs import run_job
    entry = run_job("trend_collect", "manual")
    assert entry.status == "success", entry.message
    entry = run_job("product_sourcing", "manual")
    assert entry.status == "success", entry.message
    logs = client.get("/api/admin/rpa/logs", headers=admin_headers).json()
    assert {l["job_name"] for l in logs} >= {"trend_collect", "product_sourcing"}
    stats = client.get("/api/admin/rpa/stats", headers=admin_headers).json()
    assert all(s["success"] >= 1 for s in stats)


def test_websocket_receives_order_event(client, user_headers):
    token = user_headers["Authorization"].split()[1]
    with client.websocket_connect(f"/ws?token={token}") as ws:
        assert ws.receive_json()["event"] == "hello"
        res = client.post("/api/orders/simulate", headers=user_headers)
        assert res.status_code == 201
        events = [ws.receive_json()["event"] for _ in range(2)]
        assert "order.created" in events


def test_placeholder_svg(client):
    res = client.get("/media/placeholder/abcdef123456.svg?label=숏패딩&color=블랙")
    assert res.headers["content-type"].startswith("image/svg+xml") and "숏패딩" in res.text
