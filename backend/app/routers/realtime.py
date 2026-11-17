import asyncio
import json

from fastapi import APIRouter, Query, Response, WebSocket

from ..database import SessionLocal
from ..security import user_from_token
from ..services.placeholder import render
from ..services.realtime import Client, manager

router = APIRouter(tags=["realtime"])

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
def placeholder(seed: str, label: str = "fashionpick", color: str = "블랙", cat: str | None = None):
    """데모 상품용 스튜디오 컷 스타일 SVG."""
    return Response(render(seed, label, color, cat), media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=86400"})
