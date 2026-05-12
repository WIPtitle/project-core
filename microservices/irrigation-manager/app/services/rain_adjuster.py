import logging
from urllib.parse import quote

import httpx

logger = logging.getLogger("irrigation-manager")

PAST_HOURS = 24
FORECAST_HOURS = 6
FORECAST_DISCOUNT = 0.5
RAIN_THRESHOLD_MM = 10.0


class RainAdjuster:

    def get_irrigation_factor(self, latitude: float, longitude: float, timezone: str) -> float:
        try:
            precipitation = self._fetch_precipitation(latitude, longitude, timezone)
            return self._compute_factor(precipitation)
        except Exception as e:
            logger.warning(f"Rain adjustment failed, irrigating at 100%: {e}")
            return 1.0

    def _fetch_precipitation(self, latitude: float, longitude: float, timezone: str) -> dict:
        tz_encoded = quote(timezone, safe="")
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={latitude}&longitude={longitude}"
            f"&hourly=precipitation"
            f"&past_hours={PAST_HOURS}"
            f"&forecast_hours={FORECAST_HOURS}"
            f"&timezone={tz_encoded}"
        )
        r = httpx.get(url, timeout=30.0)
        return r.json()

    def _compute_factor(self, data: dict) -> float:
        values = data.get("hourly", {}).get("precipitation", [])
        safe = [v if v is not None else 0.0 for v in values]

        past = safe[:PAST_HOURS]
        forecast = safe[PAST_HOURS:]

        past_mm = sum(past)
        forecast_mm = sum(forecast)
        effective_mm = past_mm + (forecast_mm * FORECAST_DISCOUNT)

        if effective_mm >= RAIN_THRESHOLD_MM:
            factor = 0.0
        elif effective_mm <= 0:
            factor = 1.0
        else:
            factor = 1.0 - (effective_mm / RAIN_THRESHOLD_MM)

        logger.info(
            f"Rain adjustment: past_24h={past_mm:.1f}mm, "
            f"forecast_6h={forecast_mm:.1f}mm, "
            f"effective={effective_mm:.1f}mm, factor={factor:.2f}"
        )
        return factor
