import pytest
from unittest.mock import patch, MagicMock

from app.services.rain_adjuster import RainAdjuster


COORDS = (45.0, 11.0)
TZ = "Europe/Rome"


class TestRainAdjuster:

    def _make_adjuster(self):
        return RainAdjuster()

    def _mock_response(self, past_values: list[float], forecast_values: list[float]):
        """Build a mock httpx response matching Open-Meteo hourly format.
        past_values: 24 hourly values (past), forecast_values: 6 hourly values (future)."""
        all_values = past_values + forecast_values
        all_times = [f"2026-05-12T{i:02d}:00" for i in range(len(all_values))]
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "hourly": {
                "time": all_times,
                "precipitation": all_values,
            }
        }
        mock_resp.status_code = 200
        return mock_resp

    @patch("app.services.rain_adjuster.httpx.get")
    def test_no_rain_returns_factor_1(self, mock_get):
        past = [0.0] * 24
        forecast = [0.0] * 6
        mock_get.return_value = self._mock_response(past, forecast)

        adj = self._make_adjuster()
        factor = adj.get_irrigation_factor(*COORDS, TZ)

        assert factor == 1.0

    @patch("app.services.rain_adjuster.httpx.get")
    def test_threshold_rain_returns_factor_0(self, mock_get):
        past = [0.0] * 23 + [10.0]  # 10mm in last hour
        forecast = [0.0] * 6
        mock_get.return_value = self._mock_response(past, forecast)

        adj = self._make_adjuster()
        factor = adj.get_irrigation_factor(*COORDS, TZ)

        assert factor == 0.0

    @patch("app.services.rain_adjuster.httpx.get")
    def test_above_threshold_clamps_to_0(self, mock_get):
        past = [1.0] * 24  # 24mm total
        forecast = [0.0] * 6
        mock_get.return_value = self._mock_response(past, forecast)

        adj = self._make_adjuster()
        factor = adj.get_irrigation_factor(*COORDS, TZ)

        assert factor == 0.0

    @patch("app.services.rain_adjuster.httpx.get")
    def test_5mm_past_returns_factor_05(self, mock_get):
        past = [0.0] * 19 + [1.0] * 5  # 5mm total
        forecast = [0.0] * 6
        mock_get.return_value = self._mock_response(past, forecast)

        adj = self._make_adjuster()
        factor = adj.get_irrigation_factor(*COORDS, TZ)

        assert factor == pytest.approx(0.5)

    @patch("app.services.rain_adjuster.httpx.get")
    def test_forecast_discounted_at_05(self, mock_get):
        past = [0.0] * 24
        forecast = [0.0] * 5 + [10.0]  # 10mm forecast → effective 5mm
        mock_get.return_value = self._mock_response(past, forecast)

        adj = self._make_adjuster()
        factor = adj.get_irrigation_factor(*COORDS, TZ)

        assert factor == pytest.approx(0.5)

    @patch("app.services.rain_adjuster.httpx.get")
    def test_past_plus_forecast_combined(self, mock_get):
        past = [0.0] * 21 + [1.0] * 3  # 3mm past
        forecast = [2.0] * 6  # 12mm forecast → 6mm effective
        mock_get.return_value = self._mock_response(past, forecast)

        adj = self._make_adjuster()
        factor = adj.get_irrigation_factor(*COORDS, TZ)

        # effective = 3 + (12 * 0.5) = 9mm → factor = 1 - 9/10 = 0.1
        assert factor == pytest.approx(0.1)

    @patch("app.services.rain_adjuster.httpx.get")
    def test_api_failure_returns_factor_1(self, mock_get):
        mock_get.side_effect = Exception("network error")

        adj = self._make_adjuster()
        factor = adj.get_irrigation_factor(*COORDS, TZ)

        assert factor == 1.0

    @patch("app.services.rain_adjuster.httpx.get")
    def test_none_values_in_precipitation_treated_as_zero(self, mock_get):
        past = [None] * 20 + [5.0, None, None, None]
        forecast = [None] * 6
        mock_get.return_value = self._mock_response(past, forecast)

        adj = self._make_adjuster()
        factor = adj.get_irrigation_factor(*COORDS, TZ)

        assert factor == pytest.approx(0.5)

    @patch("app.services.rain_adjuster.httpx.get")
    def test_api_called_with_correct_params(self, mock_get):
        mock_get.return_value = self._mock_response([0.0] * 24, [0.0] * 6)

        adj = self._make_adjuster()
        adj.get_irrigation_factor(45.123, 11.456, "Europe/Rome")

        mock_get.assert_called_once()
        url = mock_get.call_args[0][0]
        assert "latitude=45.123" in url
        assert "longitude=11.456" in url
        assert "past_hours=24" in url
        assert "forecast_hours=6" in url
        assert "timezone=Europe%2FRome" in url or "timezone=Europe/Rome" in url
