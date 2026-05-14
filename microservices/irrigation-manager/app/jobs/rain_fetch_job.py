import logging
import random
import threading
import time
from datetime import datetime, date, timedelta

import pytz

from app.models.irrigation_models import DailyRainFactor
from app.services.rain_adjuster import RainAdjuster

logger = logging.getLogger("irrigation-manager")

MAX_RETRIES = 10
MAX_BACKOFF_SECONDS = 900  # 15 minutes


class RainFetchJob:
    def __init__(self, repo, rain_adjuster: RainAdjuster):
        self._repo = repo
        self._rain_adjuster = rain_adjuster
        self._running = False

    def start(self):
        self._running = True
        self.fetch_and_persist_today()
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()
        logger.info("Rain fetch job started")

    def _get_timezone(self):
        vs = self._repo.get_valve_server()
        if vs is None:
            return None
        try:
            return pytz.timezone(vs.timezone)
        except Exception:
            return pytz.UTC

    def _loop(self):
        while self._running:
            try:
                tz = self._get_timezone()
                if tz is None:
                    time.sleep(60)
                    continue
                now = datetime.now(tz)
                tomorrow_midnight = tz.localize(
                    datetime(now.year, now.month, now.day) + timedelta(days=1)
                )
                seconds_until_midnight = (tomorrow_midnight - now).total_seconds()
                logger.info(
                    f"Rain fetch job: next run at midnight ({tz}), "
                    f"sleeping {seconds_until_midnight:.0f}s"
                )
                time.sleep(max(1, seconds_until_midnight))
                self.fetch_and_persist_today()
            except Exception as e:
                logger.error(f"Rain fetch job loop error: {e}")
                time.sleep(300)

    def fetch_and_persist_today(self):
        vs = self._repo.get_valve_server()
        if vs is None:
            logger.info("Rain fetch: no valve server configured, skipping")
            return
        coords = self._repo.get_coordinates()
        if coords is None:
            logger.info("Rain fetch: no coordinates configured, skipping")
            return

        tz = self._get_timezone()
        today = datetime.now(tz).date() if tz else date.today()

        existing = self._repo.get_rain_factor(today)
        if existing is not None:
            logger.info(
                f"Rain fetch: data for {today} already exists "
                f"(factor={existing.factor:.2f}), skipping"
            )
            return

        tz_name = vs.timezone or "UTC"
        for attempt in range(MAX_RETRIES):
            try:
                past, forecast = self._rain_adjuster.fetch_precipitation(
                    coords.latitude, coords.longitude, tz_name
                )
                result = self._rain_adjuster.compute_factor(past, forecast)

                rf = DailyRainFactor(
                    target_date=today,
                    factor=result["factor"],
                    effective_mm=result["effective_mm"],
                    past_mm=result["past_mm"],
                    forecast_mm=result["forecast_mm"],
                    fetched_at=datetime.now(pytz.UTC),
                )
                self._repo.save_rain_factor(rf)
                logger.info(
                    f"Rain fetch: saved factor={result['factor']:.2f} for {today} "
                    f"(effective={result['effective_mm']:.1f}mm, "
                    f"past_72h={result['past_mm']:.1f}mm, "
                    f"forecast={result['forecast_mm']:.1f}mm)"
                )
                return
            except Exception as e:
                backoff = min(MAX_BACKOFF_SECONDS, (2 ** attempt) + random.uniform(0, 3))
                logger.warning(
                    f"Rain fetch attempt {attempt + 1}/{MAX_RETRIES} failed: {e}. "
                    f"Retrying in {backoff:.0f}s"
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(backoff)

        logger.error(
            f"Rain fetch: gave up after {MAX_RETRIES} attempts for {today}. "
            f"Irrigation will run at 100%."
        )
