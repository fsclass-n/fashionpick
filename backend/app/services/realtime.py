"""WebSocket 연결 관리 및 이벤트 브로드캐스트 (RPA 스레드에서도 안전하게 호출 가능)."""
import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fastapi import WebSocket

log = logging.getLogger("fashionpick.ws")


@dataclass(eq=False)
class Client:
    ws: WebSocket
    user_id: int
    role: str
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)


class ConnectionManager:
    def __init__(self) -> None:
        self.clients: set[Client] = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self) -> None:
        self.loop = asyncio.get_running_loop()

    def add(self, client: Client) -> None:
        self.clients.add(client)

    def remove(self, client: Client) -> None:
        self.clients.discard(client)

    def update_role(self, user_id: int, role: str) -> None:
        for c in self.clients:
            if c.user_id == user_id:
                c.role = role

    def _dispatch(self, message: str, admin_only: bool, user_id: int | None) -> None:
        for c in list(self.clients):
            if (admin_only and c.role != "admin") or (user_id is not None and c.user_id != user_id):
                continue
            c.queue.put_nowait(message)

    def publish(self, event: str, data: dict, *, admin_only: bool = False, user_id: int | None = None) -> None:
        message = json.dumps({"event": event, "data": data, "at": datetime.now(timezone.utc).isoformat()},
                             ensure_ascii=False, default=str)
        if self.loop is None:
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is self.loop:
            self._dispatch(message, admin_only, user_id)
        elif not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self._dispatch, message, admin_only, user_id)

    @property
    def online(self) -> int:
        return len(self.clients)


manager = ConnectionManager()
