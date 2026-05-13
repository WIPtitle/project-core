import logging
from urllib.parse import quote

import httpx

logger = logging.getLogger("irrigation-manager")

PAST_HOURS = 48
RECENT_HOURS = 24
OLD_DISCOUNT = 0.5
FORECAST_HOURS = 6
FORECAST_DISCOUNT = 0.5
RAIN_THRESHOLD_MM = 10.0


class RainAdjuster:

    def fetch_precipitation(self, latitude: float, longitude: float, timezone: str) -> tuple[list[float], list[float]]:
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
        if r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}: body={r.text[:200]!r}")
        if not r.text.strip():
            raise RuntimeError(
                f"empty body: status={r.status_code}, headers={dict(r.headers)}"
            )
        data = r.json()
        values = data.get("hourly", {}).get("precipitation", [])
        safe = [v if v is not None else 0.0 for v in values]
        return safe[:PAST_HOURS], safe[PAST_HOURS:]

    def compute_factor(self, past_values: list[float], forecast_values: list[float]) -> dict:
        safe_past = [v if v is not None else 0.0 for v in past_values]
        safe_forecast = [v if v is not None else 0.0 for v in forecast_values]

        old = safe_past[:PAST_HOURS - RECENT_HOURS]
        recent = safe_past[PAST_HOURS - RECENT_HOURS:]

        old_mm = sum(old)
        recent_mm = sum(recent)
        forecast_mm = sum(safe_forecast)
        effective_mm = recent_mm + (old_mm * OLD_DISCOUNT) + (forecast_mm * FORECAST_DISCOUNT)

        if effective_mm >= RAIN_THRESHOLD_MM:
            factor = 0.0
        elif effective_mm <= 0:
            factor = 1.0
        else:
            factor = 1.0 - (effective_mm / RAIN_THRESHOLD_MM)

        return {
            "factor": factor,
            "effective_mm": effective_mm,
            "old_mm": old_mm,
            "recent_mm": recent_mm,
            "forecast_mm": forecast_mm,
        }
