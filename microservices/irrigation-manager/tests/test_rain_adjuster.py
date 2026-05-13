import pytest
from unittest.mock import patch, MagicMock

from app.services.rain_adjuster import RainAdjuster


COORDS = (45.0, 11.0)
TZ = "Europe/Rome"


class TestRainAdjuster:

    def _make_adjuster(self):
        return RainAdjuster()

    def _mock_response(self, old_values: list[float], recent_values: list[float],
                       forecast_values: list[float]):
        """Build a mock httpx response matching Open-Meteo hourly format.
        old_values: 24 hourly values (24-48h ago),
        recent_values: 24 hourly values (0-24h ago),
        forecast_values: 6 hourly values (future)."""
        all_values = old_values + recent_values + forecast_values
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
        old = [0.0] * 24
        recent = [0.0] * 24
        forecast = [0.0] * 6
        mock_get.return_value = self._mock_response(old, recent, forecast)

        factor = self._make_adjuster().get_irrigation_factor(*COORDS, TZ)

        assert factor == 1.0

    @patch("app.services.rain_adjuster.httpx.get")
    def test_10mm_recent_returns_factor_0(self, mock_get):
        old = [0.0] * 24
        recent = [0.0] * 23 + [10.0]
        forecast = [0.0] * 6
        mock_get.return_value = self._mock_response(old, recent, forecast)

        factor = self._make_adjuster().get_irrigation_factor(*COORDS, TZ)

        assert factor == 0.0

    @patch("app.services.rain_adjuster.httpx.get")
    def test_above_threshold_clamps_to_0(self, mock_get):
        old = [0.0] * 24
        recent = [1.0] * 24  # 24mm recent
        forecast = [0.0] * 6
        mock_get.return_value = self._mock_response(old, recent, forecast)

        factor = self._make_adjuster().get_irrigation_factor(*COORDS, TZ)

        assert factor == 0.0

    @patch("app.services.rain_adjuster.httpx.get")
    def test_5mm_recent_returns_factor_05(self, mock_get):
        old = [0.0] * 24
        recent = [0.0] * 19 + [1.0] * 5  # 5mm recent
        forecast = [0.0] * 6
        mock_get.return_value = self._mock_response(old, recent, forecast)

        factor = self._make_adjuster().get_irrigation_factor(*COORDS, TZ)

        assert factor == pytest.approx(0.5)

    @patch("app.services.rain_adjuster.httpx.get")
    def test_forecast_discounted_at_05(self, mock_get):
        old = [0.0] * 24
        recent = [0.0] * 24
        forecast = [0.0] * 5 + [10.0]  # 10mm forecast → effective 5mm
        mock_get.return_value = self._mock_response(old, recent, forecast)

        factor = self._make_adjuster().get_irrigation_factor(*COORDS, TZ)

        assert factor == pytest.approx(0.5)

    @patch("app.services.rain_adjuster.httpx.get")
    def test_recent_plus_forecast_combined(self, mock_get):
        old = [0.0] * 24
        recent = [0.0] * 21 + [1.0] * 3  # 3mm recent
        forecast = [2.0] * 6  # 12mm forecast → 6mm effective
        mock_get.return_value = self._mock_response(old, recent, forecast)

        factor = self._make_adjuster().get_irrigation_factor(*COORDS, TZ)

        # effective = 3 + (12 * 0.5) = 9mm → factor = 1 - 9/10 = 0.1
        assert factor == pytest.approx(0.1)

    @patch("app.services.rain_adjuster.httpx.get")
    def test_old_rain_discounted_at_05(self, mock_get):
        old = [0.0] * 14 + [1.0] * 10  # 10mm old → effective 5mm
        recent = [0.0] * 24
        forecast = [0.0] * 6
        mock_get.return_value = self._mock_response(old, recent, forecast)

        factor = self._make_adjuster().get_irrigation_factor(*COORDS, TZ)

        # effective = 0 + (10 * 0.5) + 0 = 5mm → factor = 0.5
        assert factor == pytest.approx(0.5)

    @patch("app.services.rain_adjuster.httpx.get")
    def test_heavy_old_storm_skips_irrigation(self, mock_get):
        old = [0.0] * 18 + [5.0, 11.0, 7.0, 10.0, 2.0, 1.0]  # 36mm old
        recent = [1.0, 0.5, 0.0] + [0.0] * 21  # 1.5mm recent
        forecast = [0.0] * 6
        mock_get.return_value = self._mock_response(old, recent, forecast)

        factor = self._make_adjuster().get_irrigation_factor(*COORDS, TZ)

        # effective = 1.5 + (36 * 0.5) + 0 = 19.5mm → clamped to 0
        assert factor == 0.0

    @patch("app.services.rain_adjuster.httpx.get")
    def test_api_failure_returns_factor_1(self, mock_get):
        mock_get.side_effect = Exception("network error")

        factor = self._make_adjuster().get_irrigation_factor(*COORDS, TZ)

        assert factor == 1.0

    @patch("app.services.rain_adjuster.httpx.get")
    def test_none_values_in_precipitation_treated_as_zero(self, mock_get):
        old = [None] * 24
        recent = [None] * 20 + [5.0, None, None, None]
        forecast = [None] * 6
        mock_get.return_value = self._mock_response(old, recent, forecast)

        factor = self._make_adjuster().get_irrigation_factor(*COORDS, TZ)

        assert factor == pytest.approx(0.5)

    @patch("app.services.rain_adjuster.httpx.get")
    def test_api_called_with_correct_params(self, mock_get):
        mock_get.return_value = self._mock_response([0.0] * 24, [0.0] * 24, [0.0] * 6)

        self._make_adjuster().get_irrigation_factor(45.123, 11.456, "Europe/Rome")

        mock_get.assert_called_once()
        url = mock_get.call_args[0][0]
        assert "latitude=45.123" in url
        assert "longitude=11.456" in url
        assert "past_hours=48" in url
        assert "forecast_hours=6" in url
        assert "timezone=Europe%2FRome" in url or "timezone=Europe/Rome" in url
