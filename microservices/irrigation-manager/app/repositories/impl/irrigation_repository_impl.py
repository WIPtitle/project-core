from datetime import date
from typing import Optional

from sqlmodel import select

from app.database.database_connector import DatabaseConnector
from app.models.irrigation_models import (
    ValveServer, IrrigationZone, IrrigationSetup, SetupZoneSchedule, SetupDateRange
)
from app.repositories.irrigation_repository import IrrigationRepository


class IrrigationRepositoryImpl(IrrigationRepository):
    def __init__(self, db: DatabaseConnector):
        self._db = db

    # -------------------------------------------------------------------------
    # ValveServer
    # -------------------------------------------------------------------------

    def get_valve_server(self) -> Optional[ValveServer]:
        with self._db.get_new_session() as s:
            result = s.exec(select(ValveServer)).first()
            return result

    def save_valve_server(self, vs: ValveServer) -> ValveServer:
        with self._db.get_new_session() as s:
            existing = s.exec(select(ValveServer)).first()
            if existing is not None:
                existing.url = vs.url
                existing.timezone = vs.timezone
                s.add(existing)
                s.commit()
                s.refresh(existing)
                return existing
            else:
                s.add(vs)
                s.commit()
                s.refresh(vs)
                return vs

    def delete_valve_server(self) -> None:
        with self._db.get_new_session() as s:
            existing = s.exec(select(ValveServer)).first()
            if existing is not None:
                s.delete(existing)
                s.commit()

    # -------------------------------------------------------------------------
    # IrrigationZone
    # -------------------------------------------------------------------------

    def get_all_zones(self) -> list[IrrigationZone]:
        with self._db.get_new_session() as s:
            return list(s.exec(select(IrrigationZone)).all())

    def get_zone_by_id(self, zone_id: int) -> Optional[IrrigationZone]:
        with self._db.get_new_session() as s:
            return s.get(IrrigationZone, zone_id)

    def get_zone_by_number(self, zone_number: str) -> Optional[IrrigationZone]:
        with self._db.get_new_session() as s:
            return s.exec(
                select(IrrigationZone).where(IrrigationZone.zone_number == zone_number)
            ).first()

    def save_zone(self, zone: IrrigationZone) -> IrrigationZone:
        with self._db.get_new_session() as s:
            if zone.id is not None:
                existing = s.get(IrrigationZone, zone.id)
                if existing is not None:
                    existing.zone_number = zone.zone_number
                    existing.name = zone.name
                    s.add(existing)
                    s.commit()
                    s.refresh(existing)
                    return existing
            s.add(zone)
            s.commit()
            s.refresh(zone)
            return zone

    def delete_all_zones(self) -> None:
        with self._db.get_new_session() as s:
            zones = s.exec(select(IrrigationZone)).all()
            for zone in zones:
                s.delete(zone)
            s.commit()

    # -------------------------------------------------------------------------
    # IrrigationSetup
    # -------------------------------------------------------------------------

    def get_all_setups(self) -> list[IrrigationSetup]:
        with self._db.get_new_session() as s:
            return list(s.exec(select(IrrigationSetup)).all())

    def get_setup_by_id(self, setup_id: int) -> Optional[IrrigationSetup]:
        with self._db.get_new_session() as s:
            return s.get(IrrigationSetup, setup_id)

    def save_setup(self, setup: IrrigationSetup) -> IrrigationSetup:
        with self._db.get_new_session() as s:
            if setup.id is not None:
                existing = s.get(IrrigationSetup, setup.id)
                if existing is not None:
                    existing.name = setup.name
                    s.add(existing)
                    s.commit()
                    s.refresh(existing)
                    return existing
            s.add(setup)
            s.commit()
            s.refresh(setup)
            return setup

    def delete_setup(self, setup_id: int) -> None:
        # Cascade manually: delete schedules and date ranges first, then setup
        self.delete_all_schedules_for_setup(setup_id)
        with self._db.get_new_session() as s:
            date_ranges = s.exec(
                select(SetupDateRange).where(SetupDateRange.setup_id == setup_id)
            ).all()
            for dr in date_ranges:
                s.delete(dr)
            s.commit()

        with self._db.get_new_session() as s:
            setup = s.get(IrrigationSetup, setup_id)
            if setup is not None:
                s.delete(setup)
                s.commit()

    # -------------------------------------------------------------------------
    # SetupZoneSchedule
    # -------------------------------------------------------------------------

    def get_schedules_for_setup(self, setup_id: int) -> list[SetupZoneSchedule]:
        with self._db.get_new_session() as s:
            return list(s.exec(
                select(SetupZoneSchedule).where(SetupZoneSchedule.setup_id == setup_id)
            ).all())

    def get_schedules_for_setup_day(self, setup_id: int, day_of_week: int) -> list[SetupZoneSchedule]:
        with self._db.get_new_session() as s:
            return list(s.exec(
                select(SetupZoneSchedule).where(
                    SetupZoneSchedule.setup_id == setup_id,
                    SetupZoneSchedule.day_of_week == day_of_week
                )
            ).all())

    def get_schedule_by_id(self, schedule_id: int) -> Optional[SetupZoneSchedule]:
        with self._db.get_new_session() as s:
            return s.get(SetupZoneSchedule, schedule_id)

    def save_schedule(self, schedule: SetupZoneSchedule) -> SetupZoneSchedule:
        with self._db.get_new_session() as s:
            s.add(schedule)
            s.commit()
            s.refresh(schedule)
            return schedule

    def delete_schedule(self, schedule_id: int) -> None:
        with self._db.get_new_session() as s:
            schedule = s.get(SetupZoneSchedule, schedule_id)
            if schedule is not None:
                s.delete(schedule)
                s.commit()

    def delete_all_schedules_for_setup(self, setup_id: int) -> None:
        with self._db.get_new_session() as s:
            schedules = s.exec(
                select(SetupZoneSchedule).where(SetupZoneSchedule.setup_id == setup_id)
            ).all()
            for schedule in schedules:
                s.delete(schedule)
            s.commit()

    def delete_all_schedules(self) -> None:
        with self._db.get_new_session() as s:
            schedules = s.exec(select(SetupZoneSchedule)).all()
            for schedule in schedules:
                s.delete(schedule)
            s.commit()

    # -------------------------------------------------------------------------
    # SetupDateRange
    # -------------------------------------------------------------------------

    def get_date_ranges_for_setup(self, setup_id: int) -> list[SetupDateRange]:
        with self._db.get_new_session() as s:
            return list(s.exec(
                select(SetupDateRange).where(SetupDateRange.setup_id == setup_id)
            ).all())

    def get_date_range_by_id(self, range_id: int) -> Optional[SetupDateRange]:
        with self._db.get_new_session() as s:
            return s.get(SetupDateRange, range_id)

    def save_date_range(self, dr: SetupDateRange) -> SetupDateRange:
        with self._db.get_new_session() as s:
            s.add(dr)
            s.commit()
            s.refresh(dr)
            return dr

    def delete_date_range(self, range_id: int) -> None:
        with self._db.get_new_session() as s:
            dr = s.get(SetupDateRange, range_id)
            if dr is not None:
                s.delete(dr)
                s.commit()

    def delete_all_date_ranges(self) -> None:
        with self._db.get_new_session() as s:
            ranges = s.exec(select(SetupDateRange)).all()
            for dr in ranges:
                s.delete(dr)
            s.commit()

    def find_setup_for_date(self, canonical_date: date) -> Optional[IrrigationSetup]:
        with self._db.get_new_session() as s:
            dr = s.exec(
                select(SetupDateRange).where(
                    SetupDateRange.start_date <= canonical_date,
                    SetupDateRange.end_date >= canonical_date
                )
            ).first()
            if dr is None:
                return None
            return s.get(IrrigationSetup, dr.setup_id)
