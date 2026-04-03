from abc import ABC, abstractmethod
from datetime import date, time
from typing import Optional

from app.models.irrigation_models import (
    ValveServer, IrrigationZone, IrrigationSetup, SetupZoneSchedule, SetupDateRange
)


class IrrigationService(ABC):
    # -------------------------------------------------------------------------
    # Config
    # -------------------------------------------------------------------------

    @abstractmethod
    async def get_valve_server(self) -> Optional[ValveServer]: pass

    @abstractmethod
    async def set_valve_server(self, url: str, timezone: str) -> ValveServer: pass

    @abstractmethod
    async def delete_valve_server(self) -> None: pass

    # -------------------------------------------------------------------------
    # Zones
    # -------------------------------------------------------------------------

    @abstractmethod
    async def sync_zones(self) -> list[IrrigationZone]: pass

    @abstractmethod
    async def get_all_zones(self) -> list[IrrigationZone]: pass

    @abstractmethod
    async def update_zone_name(self, zone_id: int, name: str) -> IrrigationZone: pass

    # -------------------------------------------------------------------------
    # Setups
    # -------------------------------------------------------------------------

    @abstractmethod
    async def get_all_setups(self) -> list[IrrigationSetup]: pass

    @abstractmethod
    async def create_setup(self, name: str) -> IrrigationSetup: pass

    @abstractmethod
    async def rename_setup(self, setup_id: int, name: str) -> IrrigationSetup: pass

    @abstractmethod
    async def delete_setup(self, setup_id: int) -> None: pass

    # -------------------------------------------------------------------------
    # Schedules
    # -------------------------------------------------------------------------

    @abstractmethod
    async def get_schedules_for_setup(self, setup_id: int) -> list[SetupZoneSchedule]: pass

    @abstractmethod
    async def add_schedule(
        self,
        setup_id: int,
        zone_id: int,
        day_of_week: int,
        start_time: time,
        end_time: time
    ) -> SetupZoneSchedule: pass

    @abstractmethod
    async def delete_schedule(self, schedule_id: int) -> None: pass

    # -------------------------------------------------------------------------
    # Date ranges
    # -------------------------------------------------------------------------

    @abstractmethod
    async def get_date_ranges_for_setup(self, setup_id: int) -> list[SetupDateRange]: pass

    @abstractmethod
    async def add_date_range(
        self,
        setup_id: int,
        start_date: date,
        end_date: date
    ) -> SetupDateRange: pass

    @abstractmethod
    async def delete_date_range(self, range_id: int) -> None: pass

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------

    @abstractmethod
    async def get_zone_status(self) -> dict: pass
