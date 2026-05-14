"""APScheduler wiring for nightly ingestor runs.

Schedules:
- SAM.gov     — daily 02:00 ET
- FPDS        — daily 03:00 ET
- USAspending — Sunday  04:00 ET
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog

from govcon_wfi.config import Settings

log = structlog.get_logger("govcon.sched")


class IngestScheduler:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._scheduler: Any = None

    def start(self) -> None:
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler  # noqa: PLC0415
            from apscheduler.triggers.cron import CronTrigger  # noqa: PLC0415
        except Exception as exc:  # noqa: BLE001
            log.warning("apscheduler_unavailable", error=str(exc))
            return

        sched = AsyncIOScheduler(timezone="America/New_York")
        sched.add_job(self._run_sam, CronTrigger(hour=2), name="sam_daily")
        sched.add_job(self._run_fpds, CronTrigger(hour=3), name="fpds_daily")
        sched.add_job(
            self._run_usaspending,
            CronTrigger(day_of_week="sun", hour=4),
            name="usaspending_weekly",
        )
        sched.start()
        self._scheduler = sched
        log.info("ingest_scheduler_started", jobs=[j.name for j in sched.get_jobs()])

    def shutdown(self) -> None:
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None

    async def _run_sam(self) -> None:
        from govcon_wfi.ingestors.sam_gov import build_sam_adapter, run_sam_sync  # noqa: PLC0415

        adapter = build_sam_adapter(self._settings)
        await run_sam_sync(adapter, started=datetime.now())

    async def _run_fpds(self) -> None:
        from govcon_wfi.ingestors.fpds import build_fpds_adapter, run_fpds_sync  # noqa: PLC0415

        adapter = build_fpds_adapter(self._settings)
        await run_fpds_sync(adapter, started=datetime.now())

    async def _run_usaspending(self) -> None:
        from govcon_wfi.ingestors.usaspending import (  # noqa: PLC0415
            build_usaspending_adapter,
            run_usaspending_sync,
        )

        adapter = build_usaspending_adapter(self._settings)
        await run_usaspending_sync(adapter, started=datetime.now())
