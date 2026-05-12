import threading
from datetime import time
from unittest.mock import MagicMock, patch, call

from app.jobs.irrigation_scheduler import IrrigationScheduler
from app.models.irrigation_models import (
    ValveServer, IrrigationZone, IrrigationSetup, SetupZoneSchedule, IrrigationCoordinates
)


def _make_scheduler(repo=None, valve_client=None, rain_adjuster=None):
    repo = repo or MagicMock()
    valve_client = valve_client or MagicMock()
    rain_adjuster = rain_adjuster or MagicMock()
    return IrrigationScheduler(repo, valve_client, rain_adjuster)


def _setup_repo_for_tick(repo, hour, minute, day_of_week, timezone="Europe/Rome",
                         zone_number="1", start_time=None, end_time=None):
    """Configure repo mock so _tick finds an active setup with one schedule."""
    vs = ValveServer(id=1, url="http://valve:8080", timezone=timezone)
    repo.get_valve_server.return_value = vs

    setup = IrrigationSetup(id=1, name="Summer", color="#22c55e")
    repo.find_setup_for_date.return_value = setup

    coords = IrrigationCoordinates(id=1, latitude=45.0, longitude=11.0)
    repo.get_coordinates.return_value = coords

    st = start_time or time(hour, minute)
    et = end_time or time(hour, minute + 20)
    sched = SetupZoneSchedule(id=1, setup_id=1, zone_id=1, day_of_week=day_of_week,
                              start_time=st, end_time=et)
    repo.get_schedules_for_setup_day.return_value = [sched]

    zone = IrrigationZone(id=1, zone_number=zone_number, name="Lawn")
    repo.get_zone_by_id.return_value = zone

    return vs, setup, sched, zone


class TestSchedulerProportional:

    @patch("app.jobs.irrigation_scheduler.datetime")
    @patch("app.jobs.irrigation_scheduler.threading.Thread")
    def test_full_irrigation_when_factor_1(self, mock_thread_cls, mock_dt):
        repo = MagicMock()
        rain_adj = MagicMock()
        rain_adj.get_irrigation_factor.return_value = 1.0
        sched = _make_scheduler(repo=repo, rain_adjuster=rain_adj)

        _setup_repo_for_tick(repo, 6, 0, 0, start_time=time(6, 0), end_time=time(6, 20))

        mock_now = MagicMock()
        mock_now.weekday.return_value = 0
        mock_now.hour = 6
        mock_now.minute = 0
        mock_now.month = 7
        mock_now.day = 15
        mock_dt.now.return_value = mock_now

        sched._tick()

        mock_thread_cls.assert_called_once()
        args = mock_thread_cls.call_args[1]["args"]
        assert args[1] == 1200.0  # 20 min = 1200s, factor=1.0 → 1200s

    @patch("app.jobs.irrigation_scheduler.datetime")
    @patch("app.jobs.irrigation_scheduler.threading.Thread")
    def test_reduced_irrigation_when_factor_05(self, mock_thread_cls, mock_dt):
        repo = MagicMock()
        rain_adj = MagicMock()
        rain_adj.get_irrigation_factor.return_value = 0.5
        sched = _make_scheduler(repo=repo, rain_adjuster=rain_adj)

        _setup_repo_for_tick(repo, 6, 0, 0, start_time=time(6, 0), end_time=time(6, 20))

        mock_now = MagicMock()
        mock_now.weekday.return_value = 0
        mock_now.hour = 6
        mock_now.minute = 0
        mock_now.month = 7
        mock_now.day = 15
        mock_dt.now.return_value = mock_now

        sched._tick()

        mock_thread_cls.assert_called_once()
        args = mock_thread_cls.call_args[1]["args"]
        assert args[1] == 600.0  # 1200 * 0.5 = 600s

    @patch("app.jobs.irrigation_scheduler.datetime")
    @patch("app.jobs.irrigation_scheduler.threading.Thread")
    def test_skip_irrigation_when_factor_0(self, mock_thread_cls, mock_dt):
        repo = MagicMock()
        rain_adj = MagicMock()
        rain_adj.get_irrigation_factor.return_value = 0.0
        sched = _make_scheduler(repo=repo, rain_adjuster=rain_adj)

        _setup_repo_for_tick(repo, 6, 0, 0, start_time=time(6, 0), end_time=time(6, 20))

        mock_now = MagicMock()
        mock_now.weekday.return_value = 0
        mock_now.hour = 6
        mock_now.minute = 0
        mock_now.month = 7
        mock_now.day = 15
        mock_dt.now.return_value = mock_now

        sched._tick()

        mock_thread_cls.assert_not_called()

    @patch("app.jobs.irrigation_scheduler.datetime")
    @patch("app.jobs.irrigation_scheduler.threading.Thread")
    def test_no_coordinates_irrigates_at_100(self, mock_thread_cls, mock_dt):
        repo = MagicMock()
        rain_adj = MagicMock()
        sched = _make_scheduler(repo=repo, rain_adjuster=rain_adj)

        _setup_repo_for_tick(repo, 6, 0, 0, start_time=time(6, 0), end_time=time(6, 20))
        repo.get_coordinates.return_value = None

        mock_now = MagicMock()
        mock_now.weekday.return_value = 0
        mock_now.hour = 6
        mock_now.minute = 0
        mock_now.month = 7
        mock_now.day = 15
        mock_dt.now.return_value = mock_now

        sched._tick()

        rain_adj.get_irrigation_factor.assert_not_called()
        mock_thread_cls.assert_called_once()
        args = mock_thread_cls.call_args[1]["args"]
        assert args[1] == 1200.0  # full duration
