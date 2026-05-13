import threading
import time
import logging
from datetime import datetime

import pytz

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
            now = time.time()
            next_minute = (now // 60 + 1) * 60 + 2
            time.sleep(max(1, next_minute - time.time()))

    def _tick(self):
        tz = self._get_timezone()
        if tz is None:
            return

        from datetime import date
        now_local = datetime.now(tz)
        canonical_today = date(2000, now_local.month, now_local.day)
        day_of_week = now_local.weekday()
        current_hour = now_local.hour
        current_minute = now_local.minute

        active_setup = self._repo.find_setup_for_date(canonical_today)
        if active_setup is None:
            return

        schedules = self._repo.get_schedules_for_setup_day(active_setup.id, day_of_week)
        matching = [s for s in schedules
                    if s.start_time.hour == current_hour and s.start_time.minute == current_minute]
        if not matching:
            return

        factor = 1.0
        rain_data = self._repo.get_rain_factor(now_local.date())
        if rain_data is not None:
            factor = rain_data.factor
            logger.info(
                f"Scheduler: using rain factor={factor:.2f} "
                f"(effective={rain_data.effective_mm:.1f}mm)"
            )

        for sched in matching:
            base_duration = (
                (sched.end_time.hour * 60 + sched.end_time.minute) -
                (sched.start_time.hour * 60 + sched.start_time.minute)
            ) * 60

            adjusted_duration = base_duration * factor

            if adjusted_duration < 60:
                logger.info(
                    f"Scheduler: skipping zone (adjusted duration {adjusted_duration:.0f}s < 60s, "
                    f"factor={factor:.2f})"
                )
                continue

            zone = self._repo.get_zone_by_id(sched.zone_id)
            if zone is None:
                continue
            logger.info(
                f"Scheduler: opening zone {zone.zone_number} for {adjusted_duration:.0f}s "
                f"(base={base_duration}s, factor={factor:.2f}, "
                f"setup={active_setup.name}, day={day_of_week})"
            )
            threading.Thread(
                target=self._open_valve_sync,
                args=(zone.zone_number, adjusted_duration),
                daemon=True
            ).start()

    def _open_valve_sync(self, zone_number: str, duration_seconds: float):
        vs = self._repo.get_valve_server()
        if not vs:
            return

        import httpx
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
