import asyncio
import json

from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.config.bindings import inject
from app.clients.auth_client import AuthClient
from app.exceptions.authorization_exception import AuthorizationException
from app.routers.router_wrapper import RouterWrapper
from app.services.irrigation_service import IrrigationService
from app.utils.valve_status_manager import ValveStatusManager


@inject
class ZoneRouter(RouterWrapper):
    def __init__(self, service: IrrigationService, auth_client: AuthClient, status_manager: ValveStatusManager):
        self._service = service
        self._auth_client = auth_client
        self._status_manager = status_manager
        super().__init__(prefix="/zones")

    async def _require_modify(self, request: Request):
        token = request.headers.get("Authorization")
        user = await self._auth_client.get_authenticated_user(token)
        if user is None or "MODIFY_DEVICES" not in user.permissions:
            raise AuthorizationException("Insufficient permissions")

    def _define_routes(self):
        @self.router.get("/")
        async def get_all_zones():
            zones = await self._service.get_all_zones()
            return [z.model_dump() for z in zones]

        @self.router.post("/sync")
        async def sync_zones(request: Request):
            await self._require_modify(request)
            zones = await self._service.sync_zones()
            return [z.model_dump() for z in zones]

        @self.router.put("/{zone_id}/name")
        async def update_zone_name(zone_id: int, body: dict, request: Request):
            await self._require_modify(request)
            name = body.get("name")
            if not name:
                return JSONResponse(status_code=400, content={"detail": "name is required"})
            zone = await self._service.update_zone_name(zone_id=zone_id, name=name)
            return zone.model_dump()

        @self.router.get("/status")
        async def get_status():
            return await self._service.get_zone_status()

        @self.router.get("/status/stream")
        async def stream_status(auth_token: str = None):
            status_manager = self._status_manager

            async def generate():
                q = status_manager.subscribe()
                last = status_manager.get_last_status()
                if last:
                    yield f"data: {json.dumps(last)}\n\n"
                try:
                    while True:
                        try:
                            status = await asyncio.wait_for(q.get(), timeout=30)
                            yield f"data: {json.dumps(status)}\n\n"
                        except asyncio.TimeoutError:
                            yield ": keepalive\n\n"
                except asyncio.CancelledError:
                    pass
                finally:
                    status_manager.unsubscribe(q)

            return StreamingResponse(generate(), media_type="text/event-stream")
