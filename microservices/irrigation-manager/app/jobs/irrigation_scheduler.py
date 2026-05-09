import threading
import time
import logging
from datetime import datetime, date
from typing import Optional
import pytz
import httpx

logger = logging.getLogger("irrigation-manager")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(_handler)


class IrrigationScheduler:
    def __init__(self, repo, valve_client):
        self._repo = repo
        self._valve_client = valve_client
        self._running = False
        self._rain_checked_today: Optional[bool] = None
        self._rain_check_date: Optional[str] = None

    def start(self):
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()
        logger.info("Irrigation scheduler started")

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
                self._tick()
            except Exception as e:
                logger.error(f"Scheduler tick error: {e}")
            # Sleep until next minute boundary + 2s buffer
            now = time.time()
            next_minute = (now // 60 + 1) * 60 + 2
            time.sleep(max(1, next_minute - time.time()))

    def _has_rained_today(self, latitude: float, longitude: float) -> bool:
        today_str = datetime.now().strftime("%Y-%m-%d")
        if self._rain_check_date == today_str and self._rain_checked_today is not None:
            return self._rain_checked_today

        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={latitude}&longitude={longitude}"
                f"&hourly=precipitation&forecast_days=1"
            )
            r = httpx.get(url, timeout=30.0)
            data = r.json()
            precipitation_values = data.get("hourly", {}).get("precipitation", [])
            rained = any(v > 0 for v in precipitation_values if v is not None)
            logger.info(
                f"Rain check: lat={latitude}, lon={longitude}, "
                f"precipitation={precipitation_values}, rained={rained}"
            )
            self._rain_checked_today = rained
            self._rain_check_date = today_str
            return rained
        except Exception as e:
            logger.warning(f"Rain check failed (irrigation will proceed): {e}")
            return False

    def _tick(self):
        tz = self._get_timezone()
        if tz is None:
            return

        now_local = datetime.now(tz)
        canonical_today = date(2000, now_local.month, now_local.day)
        day_of_week = now_local.weekday()  # 0=Monday
        current_hour = now_local.hour
        current_minute = now_local.minute

        active_setup = self._repo.find_setup_for_date(canonical_today)
        if active_setup is None:
            return

        coords = self._repo.get_coordinates()
        if coords is not None:
            if self._has_rained_today(coords.latitude, coords.longitude):
                logger.info("Scheduler: rain detected today, skipping all scheduled irrigations")
                return

        schedules = self._repo.get_schedules_for_setup_day(active_setup.id, day_of_week)
        for sched in schedules:
            if sched.start_time.hour == current_hour and sched.start_time.minute == current_minute:
                duration_seconds = (
                    (sched.end_time.hour * 60 + sched.end_time.minute) -
                    (sched.start_time.hour * 60 + sched.start_time.minute)
                ) * 60
                zone = self._repo.get_zone_by_id(sched.zone_id)
                if zone is None:
                    continue
                logger.info(
                    f"Scheduler: opening zone {zone.zone_number} for {duration_seconds}s "
                    f"(setup={active_setup.name}, day={day_of_week})"
                )
                threading.Thread(
                    target=self._open_valve_sync,
                    args=(zone.zone_number, duration_seconds),
                    daemon=True
                ).start()

    def _open_valve_sync(self, zone_number: str, duration_seconds: float):
        vs = self._repo.get_valve_server()
        if not vs:
            return

        status_before = None
        try:
            sr = httpx.get(f"{vs.url.rstrip('/')}/api/status", timeout=5.0)
            status_before = sr.json()
        except Exception:
            pass

        url = f"{vs.url.rstrip('/')}/api/valve/{zone_number}/open?duration={duration_seconds}"
        try:
            r = httpx.post(url, timeout=10.0)
            if r.status_code == 200:
                logger.warning(
                    f"Scheduler: zone {zone_number} OPENED for {duration_seconds}s | "
                    f"status_before={status_before} | response={r.text}"
                )
            elif r.status_code == 409:
                logger.warning(
                    f"Scheduler: zone {zone_number} CONFLICT | "
                    f"wanted_duration={duration_seconds}s | "
                    f"status_before={status_before} | response={r.text}"
                )
            else:
                logger.error(
                    f"Scheduler: zone {zone_number} FAILED ({r.status_code}) | "
                    f"url={url} | response={r.text}"
                )
        except Exception as e:
            logger.error(f"Scheduler: failed to open zone {zone_number}: {e}")
