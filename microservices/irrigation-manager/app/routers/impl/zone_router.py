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

        @self.router.get("/mismatch")
        async def get_mismatch():
            db_zones = await self._service.get_all_zones()
            db_zone_numbers = {z.zone_number for z in db_zones}
            try:
                vc_status = await self._service.get_zone_status()
                if "error" in vc_status:
                    return JSONResponse(content={"has_mismatch": False, "unreachable": True})
                vc_zone_numbers = set(vc_status.get("zones", []))
            except Exception:
                return JSONResponse(content={"has_mismatch": False, "unreachable": True})
            missing_in_controller = sorted(db_zone_numbers - vc_zone_numbers)
            missing_in_db = sorted(vc_zone_numbers - db_zone_numbers)
            has_mismatch = bool(missing_in_controller or missing_in_db)
            return JSONResponse(content={
                "has_mismatch": has_mismatch,
                "missing_in_controller": missing_in_controller,
                "missing_in_db": missing_in_db,
            })

        @self.router.get("/status")
        async def get_status():
            return await self._service.get_zone_status()

        @self.router.get("/status/stream")
        async def stream_status(auth_token: str = None):
            if not auth_token:
                raise AuthorizationException("auth_token query parameter is required")
            user = await self._auth_client.get_authenticated_user(f"Bearer {auth_token}")
            if user is None:
                raise AuthorizationException("Invalid or expired auth_token")
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
