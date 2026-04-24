from abc import ABC, abstractmethod
from datetime import date
from typing import Optional
from app.models.irrigation_models import (
    ValveServer, IrrigationZone, IrrigationSetup, SetupZoneSchedule, SetupDateRange,
    IrrigationCoordinates
)


class IrrigationRepository(ABC):
    # ValveServer
    @abstractmethod
    def get_valve_server(self) -> Optional[ValveServer]: pass

    @abstractmethod
    def save_valve_server(self, vs: ValveServer) -> ValveServer: pass

    @abstractmethod
    def delete_valve_server(self) -> None: pass

    # IrrigationZone
    @abstractmethod
    def get_all_zones(self) -> list[IrrigationZone]: pass

    @abstractmethod
    def get_zone_by_id(self, zone_id: int) -> Optional[IrrigationZone]: pass

    @abstractmethod
    def get_zone_by_number(self, zone_number: str) -> Optional[IrrigationZone]: pass

    @abstractmethod
    def save_zone(self, zone: IrrigationZone) -> IrrigationZone: pass

    @abstractmethod
    def delete_all_zones(self) -> None: pass

    # IrrigationSetup
    @abstractmethod
    def get_all_setups(self) -> list[IrrigationSetup]: pass

    @abstractmethod
    def get_setup_by_id(self, setup_id: int) -> Optional[IrrigationSetup]: pass

    @abstractmethod
    def save_setup(self, setup: IrrigationSetup) -> IrrigationSetup: pass

    @abstractmethod
    def delete_setup(self, setup_id: int) -> None: pass

    # SetupZoneSchedule
    @abstractmethod
    def get_schedules_for_setup(self, setup_id: int) -> list[SetupZoneSchedule]: pass

    @abstractmethod
    def get_schedules_for_setup_day(self, setup_id: int, day_of_week: int) -> list[SetupZoneSchedule]: pass

    @abstractmethod
    def get_schedule_by_id(self, schedule_id: int) -> Optional[SetupZoneSchedule]: pass

    @abstractmethod
    def save_schedule(self, schedule: SetupZoneSchedule) -> SetupZoneSchedule: pass

    @abstractmethod
    def delete_schedule(self, schedule_id: int) -> None: pass

    @abstractmethod
    def delete_all_schedules_for_setup(self, setup_id: int) -> None: pass

    @abstractmethod
    def delete_all_schedules(self) -> None: pass

    # SetupDateRange
    @abstractmethod
    def get_date_ranges_for_setup(self, setup_id: int) -> list[SetupDateRange]: pass

    @abstractmethod
    def get_date_range_by_id(self, range_id: int) -> Optional[SetupDateRange]: pass

    @abstractmethod
    def save_date_range(self, dr: SetupDateRange) -> SetupDateRange: pass

    @abstractmethod
    def delete_date_range(self, range_id: int) -> None: pass

    @abstractmethod
    def delete_all_date_ranges(self) -> None: pass

    @abstractmethod
    def find_setup_for_date(self, canonical_date: date) -> Optional[IrrigationSetup]: pass

    # IrrigationCoordinates
    @abstractmethod
    def get_coordinates(self) -> Optional[IrrigationCoordinates]: pass

    @abstractmethod
    def save_coordinates(self, coords: IrrigationCoordinates) -> IrrigationCoordinates: pass

    @abstractmethod
    def delete_coordinates(self) -> None: pass
