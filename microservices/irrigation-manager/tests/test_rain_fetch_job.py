import pytest
from datetime import date, datetime
from unittest.mock import MagicMock, patch, call

from app.jobs.rain_fetch_job import RainFetchJob
from app.models.irrigation_models import (
    ValveServer, IrrigationCoordinates, DailyRainFactor
)


class TestRainFetchJob:

    def _make_job(self, repo=None, rain_adjuster=None):
        repo = repo or MagicMock()
        rain_adjuster = rain_adjuster or MagicMock()
        if isinstance(repo.get_valve_server.return_value, MagicMock):
            repo.get_valve_server.return_value = ValveServer(
                id=1, url="http://valve:8080", timezone="Europe/Rome"
            )
        if isinstance(repo.get_coordinates.return_value, MagicMock):
            repo.get_coordinates.return_value = IrrigationCoordinates(
                id=1, latitude=45.53, longitude=12.11
            )
        return RainFetchJob(repo, rain_adjuster)

    def test_fetch_and_persist_saves_to_repo(self):
        repo = MagicMock()
        adj = MagicMock()
        adj.fetch_precipitation.return_value = ([0.0] * 48, [0.0] * 6)
        adj.compute_factor.return_value = {
            "factor": 0.7, "effective_mm": 3.0,
            "old_mm": 2.0, "recent_mm": 1.0, "forecast_mm": 2.0,
        }
        repo.get_rain_factor.return_value = None

        job = self._make_job(repo=repo, rain_adjuster=adj)
        job.fetch_and_persist_today()

        repo.save_rain_factor.assert_called_once()
        saved = repo.save_rain_factor.call_args[0][0]
        assert saved.factor == 0.7
        assert saved.effective_mm == 3.0

    def test_fetch_skips_if_already_exists(self):
        repo = MagicMock()
        adj = MagicMock()
        repo.get_rain_factor.return_value = DailyRainFactor(
            id=1, target_date=date.today(), factor=0.5,
            effective_mm=5.0, old_mm=4.0, recent_mm=1.0,
            forecast_mm=0.0, fetched_at=datetime.now()
        )

        job = self._make_job(repo=repo, rain_adjuster=adj)
        job.fetch_and_persist_today()

        adj.fetch_precipitation.assert_not_called()
        repo.save_rain_factor.assert_not_called()

    @patch("app.jobs.rain_fetch_job.time.sleep")
    def test_retry_on_failure(self, mock_sleep):
        repo = MagicMock()
        adj = MagicMock()
        repo.get_rain_factor.return_value = None
        adj.fetch_precipitation.side_effect = [
            RuntimeError("empty body"),
            RuntimeError("HTTP 429"),
            ([0.0] * 48, [0.0] * 6),
        ]
        adj.compute_factor.return_value = {
            "factor": 1.0, "effective_mm": 0.0,
            "old_mm": 0.0, "recent_mm": 0.0, "forecast_mm": 0.0,
        }

        job = self._make_job(repo=repo, rain_adjuster=adj)
        job.fetch_and_persist_today()

        assert adj.fetch_precipitation.call_count == 3
        repo.save_rain_factor.assert_called_once()

    @patch("app.jobs.rain_fetch_job.time.sleep")
    def test_gives_up_after_max_retries(self, mock_sleep):
        repo = MagicMock()
        adj = MagicMock()
        repo.get_rain_factor.return_value = None
        adj.fetch_precipitation.side_effect = RuntimeError("always fails")

        job = self._make_job(repo=repo, rain_adjuster=adj)
        job.fetch_and_persist_today()

        assert adj.fetch_precipitation.call_count == 10
        repo.save_rain_factor.assert_not_called()

    def test_no_coordinates_skips(self):
        repo = MagicMock()
        adj = MagicMock()
        repo.get_coordinates.return_value = None

        job = self._make_job(repo=repo, rain_adjuster=adj)
        job.fetch_and_persist_today()

        adj.fetch_precipitation.assert_not_called()

    def test_no_valve_server_skips(self):
        repo = MagicMock()
        adj = MagicMock()
        repo.get_valve_server.return_value = None

        job = RainFetchJob(repo, adj)
        job.fetch_and_persist_today()

        adj.fetch_precipitation.assert_not_called()
