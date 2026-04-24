from fastapi import Request
from fastapi.responses import JSONResponse

from app.config.bindings import inject
from app.clients.auth_client import AuthClient
from app.exceptions.authorization_exception import AuthorizationException
from app.routers.router_wrapper import RouterWrapper
from app.services.irrigation_service import IrrigationService


@inject
class CoordinatesRouter(RouterWrapper):
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
        @self.router.get("/coordinates")
        async def get_coordinates():
            coords = await self._service.get_coordinates()
            if coords is None:
                return {"configured": False}
            return {
                "configured": True,
                "id": coords.id,
                "latitude": coords.latitude,
                "longitude": coords.longitude,
            }

        @self.router.post("/coordinates")
        async def set_coordinates(body: dict, request: Request):
            await self._require_modify(request)
            latitude = body.get("latitude")
            longitude = body.get("longitude")
            if latitude is None or longitude is None:
                return JSONResponse(status_code=400, content={"detail": "latitude and longitude are required"})
            try:
                coords = await self._service.set_coordinates(latitude=float(latitude), longitude=float(longitude))
            except (ValueError, TypeError) as e:
                return JSONResponse(status_code=400, content={"detail": str(e)})
            return {
                "configured": True,
                "id": coords.id,
                "latitude": coords.latitude,
                "longitude": coords.longitude,
            }

        @self.router.put("/coordinates")
        async def update_coordinates(body: dict, request: Request):
            await self._require_modify(request)
            latitude = body.get("latitude")
            longitude = body.get("longitude")
            if latitude is None or longitude is None:
                return JSONResponse(status_code=400, content={"detail": "latitude and longitude are required"})
            try:
                coords = await self._service.set_coordinates(latitude=float(latitude), longitude=float(longitude))
            except (ValueError, TypeError) as e:
                return JSONResponse(status_code=400, content={"detail": str(e)})
            return {
                "configured": True,
                "id": coords.id,
                "latitude": coords.latitude,
                "longitude": coords.longitude,
            }

        @self.router.delete("/coordinates")
        async def delete_coordinates(request: Request):
            await self._require_modify(request)
            await self._service.delete_coordinates()
            return JSONResponse(status_code=204, content=None)
