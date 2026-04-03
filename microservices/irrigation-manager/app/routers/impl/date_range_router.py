from datetime import date

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
class DateRangeRouter(RouterWrapper):
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
        @self.router.get("/{setup_id}/date-ranges/")
        async def get_date_ranges(setup_id: int):
            ranges = await self._service.get_date_ranges_for_setup(setup_id=setup_id)
            return [r.model_dump() for r in ranges]

        @self.router.post("/{setup_id}/date-ranges/")
        async def add_date_range(setup_id: int, body: dict, request: Request):
            await self._require_modify(request)
            start_date_str = body.get("start_date")
            end_date_str = body.get("end_date")
            if not start_date_str or not end_date_str:
                return JSONResponse(status_code=400, content={"detail": "start_date and end_date are required"})
            try:
                start_date = date.fromisoformat(f"2000-{start_date_str}")
                end_date = date.fromisoformat(f"2000-{end_date_str}")
            except ValueError as e:
                return JSONResponse(status_code=400, content={"detail": f"Invalid date format (expected MM-DD): {e}"})
            dr = await self._service.add_date_range(
                setup_id=setup_id,
                start_date=start_date,
                end_date=end_date,
            )
            return dr.model_dump()

        @self.router.delete("/{setup_id}/date-ranges/{range_id}")
        async def delete_date_range(setup_id: int, range_id: int, request: Request):
            await self._require_modify(request)
            await self._service.delete_date_range(range_id=range_id)
            return JSONResponse(status_code=204, content=None)
