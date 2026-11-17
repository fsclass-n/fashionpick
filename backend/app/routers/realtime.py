import asyncio
import json
from html import escape

from fastapi import APIRouter, Query, Response, WebSocket

from ..database import SessionLocal
from ..security import user_from_token
from ..services.realtime import Client, manager

router = APIRouter(tags=["realtime"])

PALETTE = {"블랙": "#1f1f1f", "아이보리": "#efe8da", "그레이": "#9a9a9a", "네이비": "#23304a", "베이지": "#d8c3a5",
           "브라운": "#6b4a35", "카키": "#6b6b47", "버건디": "#6d2233", "스카이블루": "#9cc3e0"}


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str = Query(default="")):
    """인증된 사용자 브라우저로 주문·발주·트렌드·RPA 이벤트를 실시간 푸시."""
    db = SessionLocal()
    try:
        user = user_from_token(db, token)
    finally:
        db.close()
    if not user:
        await ws.close(code=4401)
        return
    await ws.accept()
    client = Client(ws=ws, user_id=user.id, role=user.role)
    manager.add(client)
    await ws.send_text(json.dumps({"event": "hello", "data": {"name": user.name, "role": user.role}}, ensure_ascii=False))

    async def sender() -> None:
        while True:
            await ws.send_text(await client.queue.get())

    async def receiver() -> None:
        while True:
            if await ws.receive_text() == "ping":
                await ws.send_text('{"event":"pong","data":{}}')

    tasks = [asyncio.create_task(sender()), asyncio.create_task(receiver())]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        for t in done:
            t.exception()
    finally:
        for t in tasks:
            t.cancel()
        manager.remove(client)


@router.get("/media/placeholder/{seed}.svg")
def placeholder(seed: str, label: str = "fashionpick", color: str = "블랙"):
    """데모 상품용 에디토리얼 스타일 SVG 이미지 (외부 이미지 의존 없음)."""
    bg = PALETTE.get(color, "#cfcfcf")
    h = int(seed[:6], 16) if all(c in "0123456789abcdef" for c in seed[:6]) and len(seed) >= 6 else 0
    light = color in {"아이보리", "베이지", "스카이블루", "그레이"}
    fg = "#111111" if light else "#f5f5f5"
    cx, cy, r = 120 + h % 160, 140 + (h >> 8) % 160, 90 + (h >> 16) % 70
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 500" width="400" height="500">
<rect width="400" height="500" fill="{bg}"/>
<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fg}" opacity="0.08"/>
<rect x="{60 + h % 60}" y="{220 + (h >> 4) % 60}" width="{180 + h % 80}" height="{140 + (h >> 12) % 80}" fill="{fg}" opacity="0.06"/>
<text x="32" y="56" font-family="Georgia, serif" font-size="18" letter-spacing="6" fill="{fg}" opacity="0.7">FASHIONPICK</text>
<text x="32" y="440" font-family="sans-serif" font-size="30" font-weight="700" fill="{fg}">{escape(label[:14])}</text>
<text x="32" y="470" font-family="sans-serif" font-size="14" letter-spacing="3" fill="{fg}" opacity="0.6">{escape(color)} · WHOLESALE SAMPLE</text>
</svg>"""
    return Response(svg, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})
