import pytest
from unittest.mock import patch, MagicMock

from app.services.rain_adjuster import RainAdjuster


COORDS = (45.0, 11.0)
TZ = "Europe/Rome"


class TestRainAdjusterCompute:

    def _make_adjuster(self):
        return RainAdjuster()

    def test_no_rain_returns_factor_1(self):
        adj = self._make_adjuster()
        result = adj.compute_factor([0.0] * 48, [0.0] * 6)
        assert result["factor"] == 1.0

    def test_10mm_recent_returns_factor_0(self):
        adj = self._make_adjuster()
        past = [0.0] * 47 + [10.0]
        result = adj.compute_factor(past, [0.0] * 6)
        assert result["factor"] == 0.0

    def test_above_threshold_clamps_to_0(self):
        adj = self._make_adjuster()
        past = [0.0] * 24 + [1.0] * 24  # 24mm recent
        result = adj.compute_factor(past, [0.0] * 6)
        assert result["factor"] == 0.0

    def test_5mm_recent_returns_factor_05(self):
        adj = self._make_adjuster()
        past = [0.0] * 43 + [1.0] * 5
        result = adj.compute_factor(past, [0.0] * 6)
        assert result["factor"] == pytest.approx(0.5)

    def test_forecast_discounted_at_05(self):
        adj = self._make_adjuster()
        result = adj.compute_factor([0.0] * 48, [0.0] * 5 + [10.0])
        assert result["factor"] == pytest.approx(0.5)

    def test_old_rain_discounted_at_05(self):
        adj = self._make_adjuster()
        past = [0.0] * 14 + [1.0] * 10 + [0.0] * 24  # 10mm old, 0 recent
        result = adj.compute_factor(past, [0.0] * 6)
        assert result["factor"] == pytest.approx(0.5)

    def test_heavy_old_storm_skips(self):
        adj = self._make_adjuster()
        past = [0.0] * 18 + [5.0, 11.0, 7.0, 10.0, 2.0, 1.0] + [1.0, 0.5] + [0.0] * 22
        result = adj.compute_factor(past, [0.0] * 6)
        # old=36, recent=1.5, effective = 1.5 + 36*0.5 = 19.5
        assert result["factor"] == 0.0

    def test_none_values_treated_as_zero(self):
        adj = self._make_adjuster()
        past = [None] * 24 + [None] * 20 + [5.0, None, None, None]
        result = adj.compute_factor(past, [None] * 6)
        assert result["factor"] == pytest.approx(0.5)

    def test_result_contains_all_fields(self):
        adj = self._make_adjuster()
        past = [0.0] * 14 + [2.0] * 10 + [0.0] * 21 + [3.0, 0.0, 0.0]
        result = adj.compute_factor(past, [1.0] * 6)
        assert "factor" in result
        assert "effective_mm" in result
        assert "old_mm" in result
        assert "recent_mm" in result
        assert "forecast_mm" in result
        assert result["old_mm"] == pytest.approx(20.0)
        assert result["recent_mm"] == pytest.approx(3.0)
        assert result["forecast_mm"] == pytest.approx(6.0)


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
        all_vals = [0.0] * 48 + [0.0] * 6
        mock_get.return_value = self._mock_response(all_vals)

        adj = RainAdjuster()
        past, forecast = adj.fetch_precipitation(45.0, 11.0, "Europe/Rome")

        assert len(past) == 48
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
        mock_get.return_value = self._mock_response([0.0] * 54)

        adj = RainAdjuster()
        adj.fetch_precipitation(45.123, 11.456, "Europe/Rome")

        url = mock_get.call_args[0][0]
        assert "latitude=45.123" in url
        assert "longitude=11.456" in url
        assert "past_hours=48" in url
        assert "forecast_hours=6" in url
