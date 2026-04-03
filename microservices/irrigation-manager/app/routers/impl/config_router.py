from fastapi import Request
from fastapi.responses import JSONResponse

from app.config.bindings import inject
from app.clients.auth_client import AuthClient
from app.exceptions.authorization_exception import AuthorizationException
from app.routers.router_wrapper import RouterWrapper
from app.services.irrigation_service import IrrigationService


@inject
class ConfigRouter(RouterWrapper):
    def __init__(self, service: IrrigationService, auth_client: AuthClient):
        self._service = service
        self._auth_client = auth_client
        super().__init__(prefix="/config")

    async def _require_modify(self, request: Request):
        token = request.headers.get("Authorization")
        user = await self._auth_client.get_authenticated_user(token)
        if user is None or "MODIFY_DEVICES" not in user.permissions:
            raise AuthorizationException("Insufficient permissions")

    def _define_routes(self):
        @self.router.get("/valve-server")
        async def get_valve_server():
            vs = await self._service.get_valve_server()
            if vs is None:
                return {"configured": False}
            return {
                "configured": True,
                "id": vs.id,
                "url": vs.url,
                "timezone": vs.timezone,
            }

        @self.router.post("/valve-server")
        async def set_valve_server(body: dict, request: Request):
            await self._require_modify(request)
            url = body.get("url")
            timezone = body.get("timezone", "UTC")
            if not url:
                return JSONResponse(status_code=400, content={"detail": "url is required"})
            try:
                vs = await self._service.set_valve_server(url=url, timezone=timezone)
            except ValueError as e:
                return JSONResponse(status_code=400, content={"detail": str(e)})
            return {"configured": True, "id": vs.id, "url": vs.url, "timezone": vs.timezone}

        @self.router.delete("/valve-server")
        async def delete_valve_server(request: Request):
            await self._require_modify(request)
            await self._service.delete_valve_server()
            return JSONResponse(status_code=204, content=None)
