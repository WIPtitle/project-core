import httpx
import logging
from typing import Optional

logger = logging.getLogger("irrigation-manager")


class ValveControllerClient:
    def __init__(self):
        self._url: Optional[str] = None

    def set_url(self, url: str):
        self._url = url.rstrip("/")

    def clear_url(self):
        self._url = None

    @property
    def url(self) -> Optional[str]:
        return self._url

    async def get_status(self) -> dict:
        if not self._url:
            raise RuntimeError("Valve controller URL not configured")
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self._url}/api/status", timeout=5.0)
            r.raise_for_status()
            return r.json()

    async def health_check(self, url: str) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{url.rstrip('/')}/api/status", timeout=5.0)
                return r.status_code == 200
        except Exception:
            return False

    async def open_valve(self, zone: str, duration_seconds: float) -> dict:
        if not self._url:
            raise RuntimeError("Valve controller URL not configured")
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self._url}/api/valve/{zone}/open?duration={duration_seconds}",
                timeout=10.0
            )
            return r.json()

    async def close_all(self) -> dict:
        if not self._url:
            raise RuntimeError("Valve controller URL not configured")
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{self._url}/api/close", timeout=5.0)
            return r.json()
