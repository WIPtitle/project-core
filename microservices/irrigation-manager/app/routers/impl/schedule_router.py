import time as time_module
from datetime import time

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
class ScheduleRouter(RouterWrapper):
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
        @self.router.get("/{setup_id}/schedules/")
        async def get_schedules(setup_id: int):
            schedules = await self._service.get_schedules_for_setup(setup_id=setup_id)
            return [s.model_dump() for s in schedules]

        @self.router.post("/{setup_id}/schedules/")
        async def add_schedule(setup_id: int, body: dict, request: Request):
            await self._require_modify(request)
            zone_id = body.get("zone_id")
            start_time_str = body.get("start_time")
            end_time_str = body.get("end_time")

            # Accept days_of_week (list) or day_of_week (int) for backward compatibility
            days_of_week = body.get("days_of_week")
            if days_of_week is None:
                day_of_week = body.get("day_of_week")
                if day_of_week is not None:
                    days_of_week = [day_of_week]

            if zone_id is None or days_of_week is None or not start_time_str or not end_time_str:
                return JSONResponse(status_code=400, content={"detail": "zone_id, days_of_week (or day_of_week), start_time and end_time are required"})
            try:
                start_time = time.fromisoformat(start_time_str)
                end_time = time.fromisoformat(end_time_str)
            except ValueError as e:
                return JSONResponse(status_code=400, content={"detail": f"Invalid time format: {e}"})
            try:
                schedules = await self._service.add_schedule(
                    setup_id=setup_id,
                    zone_id=zone_id,
                    days_of_week=days_of_week,
                    start_time=start_time,
                    end_time=end_time,
                )
            except ValueError as e:
                return JSONResponse(status_code=400, content={"detail": str(e)})
            return [s.model_dump() for s in schedules]

        @self.router.delete("/{setup_id}/schedules/{schedule_id}")
        async def delete_schedule(setup_id: int, schedule_id: int, request: Request):
            await self._require_modify(request)
            await self._service.delete_schedule(schedule_id=schedule_id)
            return JSONResponse(status_code=204, content=None)
