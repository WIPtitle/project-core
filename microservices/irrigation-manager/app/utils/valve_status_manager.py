import asyncio
import threading
import time
import logging
from typing import Optional

logger = logging.getLogger("irrigation-manager")


class ValveStatusManager:
    def __init__(self, valve_client):
        self._client = valve_client
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._subscribers: list[asyncio.Queue] = []
        self._lock = threading.Lock()
        self._last_status: Optional[dict] = None
        self._running = False

    def set_main_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    def start(self):
        self._running = True
        t = threading.Thread(target=self._poll_loop, daemon=True)
        t.start()

    def _poll_loop(self):
        while self._running:
            if self._client.url:
                try:
                    import httpx
                    r = httpx.get(f"{self._client.url}/api/status", timeout=5.0)
                    if r.status_code == 200:
                        status = r.json()
                        prev = self._last_status
                        self._last_status = status
                        if prev is None or status.get("active_zone") != prev.get("active_zone"):
                            self._push(status)
                except Exception as e:
                    logger.debug(f"Valve status poll error: {e}")
            time.sleep(2)

    def _push(self, status: dict):
        if not self._loop:
            return
        with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            asyncio.run_coroutine_threadsafe(q.put(status), self._loop)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        with self._lock:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass

    def get_last_status(self) -> Optional[dict]:
        return self._last_status
