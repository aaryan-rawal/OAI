"""Periodic, fail-safe self-reported rest compliance monitor."""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.config import settings
from app.db import get_sessionmaker
from app.models import DriverRestEvent, FleetDriver, Shipment

log = logging.getLogger(__name__)

async def check_driver_rest_compliance() -> int:
    """Permanently blacklist drivers with active work and no rest/delivery for policy window."""
    threshold = timedelta(hours=max(1, settings.DRIVER_REST_MISSED_AFTER_HOURS))
    count = 0
    async with get_sessionmaker()() as db:
        drivers = (await db.scalars(select(FleetDriver).where(FleetDriver.blacklisted.is_(False)))).all()
        now = datetime.now(timezone.utc)
        for driver in drivers:
            active = (await db.scalars(select(Shipment).where(Shipment.assigned_driver_id == driver.id,
                Shipment.status.notin_(["cancelled", "delivered"])).order_by(Shipment.created_at.asc()))).all()
            if not active:
                continue
            latest_rest = await db.scalar(select(DriverRestEvent).where(DriverRestEvent.driver_id == driver.id)
                .order_by(DriverRestEvent.ended_at.desc()).limit(1))
            reference = max(latest_rest.ended_at, active[0].created_at) if latest_rest else active[0].created_at
            if reference.tzinfo is None:
                reference = reference.replace(tzinfo=timezone.utc)
            if now - reference >= threshold:
                driver.blacklisted = True
                driver.blacklist_reason = (f"No self-reported rest record or completed final delivery within "
                    f"{settings.DRIVER_REST_MISSED_AFTER_HOURS} hours during active duty. Permanent company blacklist.")
                count += 1
        if count:
            await db.commit()
    return count

async def monitor_loop() -> None:
    while True:
        try:
            if settings.DRIVER_AUTO_BLACKLIST:
                count = await check_driver_rest_compliance()
                if count:
                    log.warning("Automatically blacklisted %s driver(s) for missing rest records.", count)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Keep the API alive if DB/migrations are not ready; never claim compliance on error.
            log.exception("Driver rest monitor could not complete this cycle.")
        await asyncio.sleep(60)
