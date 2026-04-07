import logging
from datetime import date, time
from typing import Optional

from app.clients.valve_controller_client import ValveControllerClient
from app.exceptions.not_found_exception import NotFoundException
from app.exceptions.valve_locked_exception import ValveLockedException
from app.models.irrigation_models import (
    ValveServer, IrrigationZone, IrrigationSetup, SetupZoneSchedule, SetupDateRange
)
from app.repositories.irrigation_repository import IrrigationRepository
from app.services.irrigation_service import IrrigationService

logger = logging.getLogger("irrigation-manager")


def _to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


class IrrigationServiceImpl(IrrigationService):
    def __init__(self, repo: IrrigationRepository, valve_client: ValveControllerClient):
        self._repo = repo
        self._valve_client = valve_client

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    async def _require_no_active_valve(self) -> None:
        """Raise ValveLockedException if a valve is currently open.
        If the valve controller is unreachable, allow the operation through."""
        try:
            status = await self._valve_client.get_status()
            if status.get("active_zone") is not None:
                raise ValveLockedException(
                    "A valve is currently open. Close it before making changes."
                )
        except ValveLockedException:
            raise
        except Exception:
            # Valve controller unreachable — allow changes
            logger.warning("Valve controller unreachable during lock check; proceeding without lock.")

    # -------------------------------------------------------------------------
    # Config
    # -------------------------------------------------------------------------

    async def get_valve_server(self) -> Optional[ValveServer]:
        return self._repo.get_valve_server()

    async def set_valve_server(self, url: str, timezone: str) -> ValveServer:
        # Health check before saving
        reachable = await self._valve_client.health_check(url)
        if not reachable:
            raise ValueError(f"Cannot reach valve controller at {url}")

        existing = self._repo.get_valve_server()
        timezone_changed = existing is not None and existing.timezone != timezone

        vs = ValveServer(url=url, timezone=timezone)
        saved = self._repo.save_valve_server(vs)

        # If timezone changed, wipe all schedules, date ranges, and zones
        # (they depend on timezone for correct interpretation)
        if timezone_changed:
            logger.info("Timezone changed — clearing all schedules, date ranges, and zones.")
            self._repo.delete_all_schedules()
            self._repo.delete_all_date_ranges()
            self._repo.delete_all_zones()

        self._valve_client.set_url(url)
        return saved

    async def delete_valve_server(self) -> None:
        self._repo.delete_valve_server()
        self._valve_client.clear_url()

    # -------------------------------------------------------------------------
    # Zones
    # -------------------------------------------------------------------------

    async def sync_zones(self) -> list[IrrigationZone]:
        status = await self._valve_client.get_status()
        zone_numbers: list[str] = status.get("zones", [])

        result: list[IrrigationZone] = []
        for zone_number in zone_numbers:
            existing = self._repo.get_zone_by_number(zone_number)
            if existing is not None:
                result.append(existing)
            else:
                new_zone = IrrigationZone(
                    zone_number=zone_number,
                    name=f"Zone {zone_number}"
                )
                saved = self._repo.save_zone(new_zone)
                result.append(saved)

        return result

    async def get_all_zones(self) -> list[IrrigationZone]:
        return self._repo.get_all_zones()

    async def update_zone_name(self, zone_id: int, name: str) -> IrrigationZone:
        await self._require_no_active_valve()
        zone = self._repo.get_zone_by_id(zone_id)
        if zone is None:
            raise ValueError(f"Zone {zone_id} not found")
        zone.name = name
        return self._repo.save_zone(zone)

    # -------------------------------------------------------------------------
    # Setups
    # -------------------------------------------------------------------------

    async def get_all_setups(self) -> list[IrrigationSetup]:
        return self._repo.get_all_setups()

    async def create_setup(self, name: str, color: str = "#22c55e") -> IrrigationSetup:
        await self._require_no_active_valve()
        setup = IrrigationSetup(name=name, color=color)
        return self._repo.save_setup(setup)

    async def update_setup(self, setup_id: int, name: str, color: str) -> IrrigationSetup:
        await self._require_no_active_valve()
        setup = self._repo.get_setup_by_id(setup_id)
        if setup is None:
            raise NotFoundException(f"Setup {setup_id} not found")
        setup.name = name
        setup.color = color
        return self._repo.save_setup(setup)

    async def delete_setup(self, setup_id: int) -> None:
        await self._require_no_active_valve()
        setup = self._repo.get_setup_by_id(setup_id)
        if setup is None:
            raise ValueError(f"Setup {setup_id} not found")
        self._repo.delete_setup(setup_id)

    # -------------------------------------------------------------------------
    # Schedules
    # -------------------------------------------------------------------------

    async def get_schedules_for_setup(self, setup_id: int) -> list[SetupZoneSchedule]:
        return self._repo.get_schedules_for_setup(setup_id)

    async def add_schedule(
        self,
        setup_id: int,
        zone_id: int,
        days_of_week: list[int],
        start_time: time,
        end_time: time
    ) -> list[SetupZoneSchedule]:
        await self._require_no_active_valve()

        if start_time >= end_time:
            raise ValueError("start_time must be before end_time")

        new_start_min = _to_minutes(start_time)
        new_end_min = _to_minutes(end_time)

        # Validate all days before creating any schedule
        for day in days_of_week:
            existing_schedules = self._repo.get_schedules_for_setup_day(setup_id, day)
            conflicts: list[str] = []
            for sched in existing_schedules:
                ex_start_min = _to_minutes(sched.start_time)
                ex_end_min = _to_minutes(sched.end_time)
                overlaps = not (new_end_min + 1 <= ex_start_min or ex_end_min + 1 <= new_start_min)
                if overlaps:
                    zone = self._repo.get_zone_by_id(sched.zone_id)
                    zone_label = zone.name if zone else f"Zone {sched.zone_id}"
                    start_str = sched.start_time.strftime("%H:%M")
                    end_str = sched.end_time.strftime("%H:%M")
                    conflicts.append(f"{zone_label} ({start_str}\u2013{end_str})")
            if conflicts:
                day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                conflict_list = ", ".join(conflicts)
                raise ValueError(
                    f"Time slot overlaps on {day_names[day]}: {conflict_list}. "
                    f"A 1-minute gap is required between ANY zones on the same day, "
                    f"because only one valve can be open at a time due to water pressure."
                )

        # All days validated — create schedules
        created = []
        for day in days_of_week:
            schedule = SetupZoneSchedule(
                setup_id=setup_id,
                zone_id=zone_id,
                day_of_week=day,
                start_time=start_time,
                end_time=end_time
            )
            created.append(self._repo.save_schedule(schedule))
        return created

    async def delete_schedule(self, schedule_id: int) -> None:
        await self._require_no_active_valve()
        schedule = self._repo.get_schedule_by_id(schedule_id)
        if schedule is None:
            raise ValueError(f"Schedule {schedule_id} not found")
        self._repo.delete_schedule(schedule_id)

    # -------------------------------------------------------------------------
    # Date ranges
    # -------------------------------------------------------------------------

    async def get_date_ranges_for_setup(self, setup_id: int) -> list[SetupDateRange]:
        return self._repo.get_date_ranges_for_setup(setup_id)

    async def add_date_range(
        self,
        setup_id: int,
        start_date: date,
        end_date: date
    ) -> SetupDateRange:
        await self._require_no_active_valve()

        # Canonicalize to year 2000 for year-agnostic storage
        canonical_start = start_date.replace(year=2000)
        canonical_end = end_date.replace(year=2000)

        if canonical_start > canonical_end:
            raise ValueError("start_date must be on or before end_date")

        # Check overlap across ALL setups — each calendar day must map to at most one setup
        all_setups = self._repo.get_all_setups()
        for setup in all_setups:
            existing_ranges = self._repo.get_date_ranges_for_setup(setup.id)
            for dr in existing_ranges:
                ex_start = dr.start_date
                ex_end = dr.end_date
                # Simple overlap: NOT (new_end < ex_start OR ex_end < new_start)
                overlaps = not (canonical_end < ex_start or ex_end < canonical_start)
                if overlaps:
                    raise ValueError(
                        f"Date range overlaps with setup '{setup.name}' "
                        f"({dr.start_date.strftime('%m-%d')}\u2013{dr.end_date.strftime('%m-%d')})"
                    )

        dr = SetupDateRange(
            setup_id=setup_id,
            start_date=canonical_start,
            end_date=canonical_end
        )
        return self._repo.save_date_range(dr)

    async def delete_date_range(self, range_id: int) -> None:
        await self._require_no_active_valve()
        dr = self._repo.get_date_range_by_id(range_id)
        if dr is None:
            raise ValueError(f"Date range {range_id} not found")
        self._repo.delete_date_range(range_id)

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------

    async def get_zone_status(self) -> dict:
        try:
            return await self._valve_client.get_status()
        except Exception as e:
            logger.warning(f"Failed to get zone status: {e}")
            return {"error": "Valve controller unreachable", "active_zone": None}

    async def open_valve_manual(self, zone_number: str) -> dict:
        return await self._valve_client.open_valve(zone_number, 3600.0)

    async def close_valve_manual(self) -> dict:
        return await self._valve_client.close_all()
