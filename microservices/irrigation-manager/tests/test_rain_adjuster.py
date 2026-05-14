import pytest
from unittest.mock import patch, MagicMock

from app.services.rain_adjuster import RainAdjuster, RAIN_HALF_MM


COORDS = (45.0, 11.0)
TZ = "Europe/Rome"


class TestRainAdjusterCompute:

    def _make_adjuster(self):
        return RainAdjuster()

    def test_no_rain_returns_factor_1(self):
        adj = self._make_adjuster()
        result = adj.compute_factor([0.0] * 72, [0.0] * 6)
        assert result["factor"] == 1.0

    def test_at_half_point_returns_factor_05(self):
        adj = self._make_adjuster()
        past = [0.0] * 71 + [RAIN_HALF_MM]
        result = adj.compute_factor(past, [0.0] * 6)
        assert result["factor"] == pytest.approx(0.5)

    def test_light_rain_barely_reduces(self):
        adj = self._make_adjuster()
        past = [0.0] * 70 + [1.0, 1.0]  # 2mm
        result = adj.compute_factor(past, [0.0] * 6)
        assert result["factor"] == pytest.approx(1.0 / (1.0 + (2.0 / 14.0) ** 2))
        assert result["factor"] > 0.97

    def test_moderate_rain_10mm(self):
        adj = self._make_adjuster()
        past = [0.0] * 62 + [1.0] * 10
        result = adj.compute_factor(past, [0.0] * 6)
        assert result["factor"] == pytest.approx(1.0 / (1.0 + (10.0 / 14.0) ** 2))
        assert 0.6 < result["factor"] < 0.7

    def test_heavy_rain_never_reaches_zero(self):
        adj = self._make_adjuster()
        past = [1.0] * 72  # 72mm
        result = adj.compute_factor(past, [0.0] * 6)
        assert result["factor"] > 0
        assert result["factor"] < 0.05

    def test_today_scenario_44mm(self):
        adj = self._make_adjuster()
        past = [0.0] * 30 + [5.0, 11.0, 2.5, 7.7, 1.0, 1.9, 10.2, 0.9] + [0.9, 0.8, 1.1] + [0.0] * 29
        past_mm = sum(past)  # ~42.0 + 2.8 = 44.8
        result = adj.compute_factor(past, [1.0] * 6)
        assert result["factor"] < 0.1

    def test_forecast_discounted_at_05(self):
        adj = self._make_adjuster()
        result = adj.compute_factor([0.0] * 72, [RAIN_HALF_MM * 2] + [0.0] * 5)
        # effective = 0 + 28*0.5 = 14 = RAIN_HALF_MM → factor = 0.5
        assert result["factor"] == pytest.approx(0.5)

    def test_none_values_treated_as_zero(self):
        adj = self._make_adjuster()
        past = [None] * 58 + [RAIN_HALF_MM] + [None] * 13
        result = adj.compute_factor(past, [None] * 6)
        assert result["factor"] == pytest.approx(0.5)

    def test_result_contains_all_fields(self):
        adj = self._make_adjuster()
        past = [0.0] * 62 + [1.0] * 10  # 10mm
        result = adj.compute_factor(past, [2.0] * 6)
        assert "factor" in result
        assert "effective_mm" in result
        assert "past_mm" in result
        assert "forecast_mm" in result
        assert result["past_mm"] == pytest.approx(10.0)
        assert result["forecast_mm"] == pytest.approx(12.0)
        assert result["effective_mm"] == pytest.approx(10.0 + 12.0 * 0.5)


class TestRainAdjusterFetch:

    def _mock_response(self, values):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"hourly":{"precipitation":[]}}'
        mock_resp.json.return_value = {
            "hourly": {"precipitation": values}
        }
        return mock_resp

    @patch("app.services.rain_adjuster.httpx.get")
    def test_fetch_returns_past_and_forecast(self, mock_get):
        all_vals = [0.0] * 72 + [0.0] * 6
        mock_get.return_value = self._mock_response(all_vals)

        adj = RainAdjuster()
        past, forecast = adj.fetch_precipitation(45.0, 11.0, "Europe/Rome")

        assert len(past) == 72
        assert len(forecast) == 6

    @patch("app.services.rain_adjuster.httpx.get")
    def test_fetch_raises_on_empty_body(self, mock_get):
        resp = MagicMock()
        resp.status_code = 200
        resp.text = ""
        resp.headers = {}
        mock_get.return_value = resp

        adj = RainAdjuster()
        with pytest.raises(RuntimeError, match="empty body"):
            adj.fetch_precipitation(45.0, 11.0, "Europe/Rome")

    @patch("app.services.rain_adjuster.httpx.get")
    def test_fetch_raises_on_non_200(self, mock_get):
        resp = MagicMock()
        resp.status_code = 429
        resp.text = '{"error": true}'
        mock_get.return_value = resp

        adj = RainAdjuster()
        with pytest.raises(RuntimeError, match="HTTP 429"):
            adj.fetch_precipitation(45.0, 11.0, "Europe/Rome")

    @patch("app.services.rain_adjuster.httpx.get")
    def test_fetch_url_params(self, mock_get):
        mock_get.return_value = self._mock_response([0.0] * 78)

        adj = RainAdjuster()
        adj.fetch_precipitation(45.123, 11.456, "Europe/Rome")

        url = mock_get.call_args[0][0]
        assert "latitude=45.123" in url
        assert "longitude=11.456" in url
        assert "past_hours=72" in url
        assert "forecast_hours=6" in url
