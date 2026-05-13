import asyncio
from fastapi import FastAPI
from app.config.handlers import get_exception_handlers
from app.config.bindings import status_manager, scheduler, rain_fetch_job
from app.routers.impl.config_router import ConfigRouter
from app.routers.impl.zone_router import ZoneRouter
from app.routers.impl.setup_router import SetupRouter
from app.routers.impl.schedule_router import ScheduleRouter
from app.routers.impl.date_range_router import DateRangeRouter
from app.routers.impl.coordinates_router import CoordinatesRouter

exception_handlers = get_exception_handlers()
app = FastAPI()

for exc, handler in exception_handlers:
    app.add_exception_handler(exc, handler)

routers = [
    ConfigRouter(),
    ZoneRouter(),
    SetupRouter(),
    ScheduleRouter(),
    DateRangeRouter(),
    CoordinatesRouter(),
]
for router in routers:
    app.include_router(router.get_fastapi_router())


@app.on_event("startup")
async def _startup():
    status_manager.set_main_loop(asyncio.get_running_loop())
    status_manager.start()
    rain_fetch_job.start()
    scheduler.start()
