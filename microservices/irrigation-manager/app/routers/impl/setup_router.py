from fastapi import Request
from fastapi.responses import JSONResponse

from app.config.bindings import inject
from app.clients.auth_client import AuthClient
from app.exceptions.authorization_exception import AuthorizationException
from app.exceptions.not_found_exception import NotFoundException
from app.exceptions.valve_locked_exception import ValveLockedException
from app.routers.router_wrapper import RouterWrapper
from app.services.irrigation_service import IrrigationService


@inject
class SetupRouter(RouterWrapper):
    def __init__(self, service: IrrigationService, auth_client: AuthClient):
        self._service = service
        self._auth_client = auth_client
        super().__init__(prefix="/setups")

    async def _require_modify(self, request: Request):
        token = request.headers.get("Authorization")
        user = await self._auth_client.get_authenticated_user(token)
        if user is None or "MODIFY_DEVICES" not in user.permissions:
            raise AuthorizationException("Insufficient permissions")

    def _define_routes(self):
        @self.router.get("/")
        async def get_all_setups():
            setups = await self._service.get_all_setups()
            return [s.model_dump() for s in setups]

        @self.router.post("/")
        async def create_setup(body: dict, request: Request):
            await self._require_modify(request)
            name = body.get("name")
            if not name:
                return JSONResponse(status_code=400, content={"detail": "name is required"})
            setup = await self._service.create_setup(name=name)
            return setup.model_dump()

        @self.router.put("/{setup_id}")
        async def update_setup(setup_id: int, body: dict, request: Request):
            await self._require_modify(request)
            name = body.get("name")
            if not name:
                return JSONResponse(status_code=400, content={"detail": "name is required"})
            color = body.get("color", "#22c55e")
            setup = await self._service.update_setup(setup_id=setup_id, name=name, color=color)
            return setup.model_dump()

        @self.router.delete("/{setup_id}")
        async def delete_setup(setup_id: int, request: Request):
            await self._require_modify(request)
            await self._service.delete_setup(setup_id=setup_id)
            return JSONResponse(status_code=204, content=None)
