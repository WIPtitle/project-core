from typing import Optional
from datetime import time, date, datetime
from sqlmodel import SQLModel, Field


class ValveServer(SQLModel, table=True):
    __tablename__ = "valve_server"
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(unique=True)
    timezone: str = Field(default="UTC")


class IrrigationZone(SQLModel, table=True):
    __tablename__ = "irrigation_zone"
    id: Optional[int] = Field(default=None, primary_key=True)
    zone_number: str
    name: str = Field(default="")


class IrrigationSetup(SQLModel, table=True):
    __tablename__ = "irrigation_setup"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    color: str = Field(default="#22c55e")  # green-500 default


class SetupZoneSchedule(SQLModel, table=True):
    __tablename__ = "setup_zone_schedule"
    id: Optional[int] = Field(default=None, primary_key=True)
    setup_id: int = Field(foreign_key="irrigation_setup.id")
    zone_id: int = Field(foreign_key="irrigation_zone.id")
    day_of_week: int  # 0=Monday, 6=Sunday
    start_time: time
    end_time: time


class SetupDateRange(SQLModel, table=True):
    __tablename__ = "setup_date_range"
    id: Optional[int] = Field(default=None, primary_key=True)
    setup_id: int = Field(foreign_key="irrigation_setup.id")
    start_date: date  # canonical year 2000
    end_date: date


class IrrigationCoordinates(SQLModel, table=True):
    __tablename__ = "irrigation_coordinates"
    id: Optional[int] = Field(default=None, primary_key=True)
    latitude: float
    longitude: float


class DailyRainFactor(SQLModel, table=True):
    __tablename__ = "daily_rain_factor"
    id: Optional[int] = Field(default=None, primary_key=True)
    target_date: date = Field(unique=True)
    factor: float
    effective_mm: float
    past_mm: float
    forecast_mm: float
    fetched_at: datetime
