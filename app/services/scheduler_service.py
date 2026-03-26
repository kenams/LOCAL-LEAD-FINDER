"""
Scheduler service.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.logging import logger
from app.db.session import SessionLocal
from app.models.schedule import Schedule
from app.services.lead_service import LeadService
from app.services.report_service import ReportService


class SchedulerService:
    """Handle automated outreach scheduling and execution."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.lead_service = LeadService()
        self.report_service = ReportService()

    def start(self):
        """Start the scheduler in autonomous mode."""
        if not settings.ENABLE_SCHEDULER:
            logger.info("Scheduler start skipped because ENABLE_SCHEDULER is false")
            return
        self.ensure_auto_schedule()
        self._load_schedules()
        self.scheduler.start()
        self._refresh_next_run_times()
        logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")

    def ensure_auto_schedule(self) -> int | None:
        """Ensure a single autonomous outreach schedule exists from config defaults."""
        db = SessionLocal()
        try:
            schedule = db.query(Schedule).filter(Schedule.name == settings.AUTO_MODE_NAME).first()
            if schedule:
                schedule.cron_expression = settings.AUTO_MODE_CRON
                schedule.locations = settings.AUTO_MODE_LOCATIONS
                schedule.categories = settings.AUTO_MODE_CATEGORIES
                schedule.limit_per_location = settings.AUTO_MODE_LIMIT
                schedule.language = settings.AUTO_MODE_LANGUAGE
                schedule.enabled = settings.AUTO_MODE_ENABLED
                db.commit()
                db.refresh(schedule)
                return schedule.id

            schedule = Schedule(
                name=settings.AUTO_MODE_NAME,
                cron_expression=settings.AUTO_MODE_CRON,
                locations=settings.AUTO_MODE_LOCATIONS,
                categories=settings.AUTO_MODE_CATEGORIES,
                limit_per_location=settings.AUTO_MODE_LIMIT,
                language=settings.AUTO_MODE_LANGUAGE,
                enabled=settings.AUTO_MODE_ENABLED,
                last_status="IDLE",
            )
            db.add(schedule)
            db.commit()
            db.refresh(schedule)
            return schedule.id
        finally:
            db.close()

    def update_auto_schedule(self, *, cron_expression: str, locations: str, categories: str, limit: int, language: str, enabled: bool) -> int | None:
        """Update the autonomous outreach schedule."""
        db = SessionLocal()
        try:
            schedule = db.query(Schedule).filter(Schedule.name == settings.AUTO_MODE_NAME).first()
            if not schedule:
                schedule = Schedule(name=settings.AUTO_MODE_NAME)
                db.add(schedule)
            schedule.cron_expression = cron_expression
            schedule.locations = locations
            schedule.categories = categories
            schedule.limit_per_location = limit
            schedule.language = language
            schedule.enabled = enabled
            db.commit()
            db.refresh(schedule)
            self._reschedule(schedule)
            return schedule.id
        finally:
            db.close()

    def get_auto_schedule_status(self) -> dict[str, Any]:
        """Return scheduler status and next run information for the autonomous job."""
        self.ensure_auto_schedule()
        db = SessionLocal()
        try:
            schedule = db.query(Schedule).filter(Schedule.name == settings.AUTO_MODE_NAME).first()
            if schedule and not schedule.last_run:
                self._backfill_from_latest_report(schedule, db)
            next_run = None
            if schedule:
                job = self.scheduler.get_job(f"schedule_{schedule.id}") if self.scheduler.running else None
                next_run = job.next_run_time if job else (schedule.next_run or self._calculate_next_run(schedule.cron_expression))
            return {
                "enabled": bool(schedule.enabled) if schedule else False,
                "scheduler_running": self.scheduler.running,
                "name": schedule.name if schedule else settings.AUTO_MODE_NAME,
                "cron_expression": schedule.cron_expression if schedule else settings.AUTO_MODE_CRON,
                "locations": schedule.locations if schedule else settings.AUTO_MODE_LOCATIONS,
                "categories": schedule.categories if schedule else settings.AUTO_MODE_CATEGORIES,
                "limit": schedule.limit_per_location if schedule else settings.AUTO_MODE_LIMIT,
                "language": schedule.language if schedule else settings.AUTO_MODE_LANGUAGE,
                "last_run": schedule.last_run if schedule else None,
                "last_status": schedule.last_status if schedule else "IDLE",
                "last_error": schedule.last_error if schedule else "",
                "last_report_path": schedule.last_report_path if schedule else "",
                "next_run": next_run,
            }
        finally:
            db.close()

    def record_external_run(self, *, trigger: str, summary: dict[str, Any], report_paths: dict[str, str]) -> None:
        """Persist the result of a one-shot external run so the monitor stays accurate."""
        db = SessionLocal()
        try:
            schedule = db.query(Schedule).filter(Schedule.name == settings.AUTO_MODE_NAME).first()
            if not schedule:
                self.ensure_auto_schedule()
                schedule = db.query(Schedule).filter(Schedule.name == settings.AUTO_MODE_NAME).first()
            if not schedule:
                return

            schedule.last_run = datetime.utcnow()
            schedule.last_status = "SUCCESS" if not summary.get("error") else "FAILED"
            schedule.last_error = summary.get("error", "")
            schedule.last_report_path = report_paths.get("json_path", "")
            schedule.next_run = self._calculate_next_run(schedule.cron_expression)
            db.commit()
            logger.info(f"Recorded external autonomous outreach run ({trigger})")
        finally:
            db.close()

    def run_auto_outreach_now(self, simulate: bool = False) -> dict[str, Any]:
        """Run the autonomous outreach flow immediately."""
        db = SessionLocal()
        try:
            schedule = db.query(Schedule).filter(Schedule.name == settings.AUTO_MODE_NAME).first()
            if not schedule:
                self.ensure_auto_schedule()
                schedule = db.query(Schedule).filter(Schedule.name == settings.AUTO_MODE_NAME).first()
            if not schedule:
                return {"failed": 1, "error": "missing_schedule"}
            return asyncio.run(self._execute_schedule(schedule.id, trigger="manual", simulate=simulate))
        finally:
            db.close()

    def _load_schedules(self):
        """Load enabled schedules from the database."""
        db = SessionLocal()
        try:
            schedules = db.query(Schedule).filter(Schedule.enabled == True).all()
            for schedule in schedules:
                self._schedule_job(schedule)
        finally:
            db.close()

    def _reschedule(self, schedule: Schedule):
        """Replace one job after configuration changes."""
        if self.scheduler.get_job(f"schedule_{schedule.id}"):
            self.scheduler.remove_job(f"schedule_{schedule.id}")
        if schedule.enabled:
            self._schedule_job(schedule)
        self._refresh_next_run_times()

    def _schedule_job(self, schedule: Schedule):
        """Schedule one autonomous outreach job."""
        try:
            trigger = CronTrigger.from_crontab(schedule.cron_expression)
            self.scheduler.add_job(
                func=self._run_scheduled_collection,
                trigger=trigger,
                args=[schedule.id],
                id=f"schedule_{schedule.id}",
                name=schedule.name,
                replace_existing=True,
            )
            job = self.scheduler.get_job(f"schedule_{schedule.id}")
            schedule.next_run = job.next_run_time.replace(tzinfo=None) if job and job.next_run_time else None
            db = SessionLocal()
            try:
                db_schedule = db.query(Schedule).filter(Schedule.id == schedule.id).first()
                if db_schedule:
                    db_schedule.next_run = schedule.next_run
                    db.commit()
            finally:
                db.close()
            logger.info(f"Scheduled auto job: {schedule.name} ({schedule.cron_expression})")
        except Exception as exc:
            logger.error(f"Failed to schedule job {schedule.name}: {exc}")

    def _refresh_next_run_times(self):
        """Persist next run times from APScheduler to the database."""
        db = SessionLocal()
        try:
            schedules = db.query(Schedule).all()
            for schedule in schedules:
                job = self.scheduler.get_job(f"schedule_{schedule.id}") if self.scheduler.running else None
                schedule.next_run = job.next_run_time.replace(tzinfo=None) if job and job.next_run_time else schedule.next_run
            db.commit()
        finally:
            db.close()

    def _calculate_next_run(self, cron_expression: str):
        """Calculate the next run from a cron expression even when APScheduler is not running in-process."""
        try:
            trigger = CronTrigger.from_crontab(cron_expression)
            now = datetime.now(trigger.timezone) if trigger.timezone else datetime.now().astimezone()
            next_run = trigger.get_next_fire_time(None, now)
            return next_run.replace(tzinfo=None) if next_run else None
        except Exception:
            return None

    def _backfill_from_latest_report(self, schedule: Schedule, db) -> None:
        """Hydrate schedule status from the latest saved report when runs happened outside the in-process scheduler."""
        latest_report = next(iter(self.report_service.list_reports(limit=1)), None)
        if not latest_report:
            return
        payload = self.report_service.load_report(latest_report.get("path"))
        generated_at = payload.get("generated_at") if payload else latest_report.get("generated_at")
        if generated_at:
            try:
                schedule.last_run = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                pass
        summary = payload.get("summary", {}) if payload else {}
        schedule.last_status = "FAILED" if summary.get("error") else "SUCCESS"
        schedule.last_error = summary.get("error", "")
        schedule.last_report_path = latest_report.get("path")
        if not schedule.next_run:
            schedule.next_run = self._calculate_next_run(schedule.cron_expression)
        db.commit()

    async def _run_scheduled_collection(self, schedule_id: int):
        """Run scheduled autonomous outreach."""
        await self._execute_schedule(schedule_id, trigger="scheduler", simulate=False)

    async def _execute_schedule(self, schedule_id: int, *, trigger: str, simulate: bool) -> dict[str, Any]:
        """Execute one scheduled autonomous outreach run and persist status/reporting."""
        db = SessionLocal()
        try:
            schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
            if not schedule or not schedule.enabled:
                return {"skipped": 1, "error": "schedule_disabled"}

            schedule.last_status = "RUNNING"
            schedule.last_error = ""
            db.commit()

            locations = [item.strip() for item in schedule.locations.split(",") if item.strip()]
            categories = [item.strip() for item in schedule.categories.split(",") if item.strip()]

            logger.info(f"Running autonomous outreach: {schedule.name}")
            summary = await self.lead_service.auto_outreach(
                locations=locations,
                categories=categories,
                limit=schedule.limit_per_location,
                language=schedule.language,
                simulate=simulate,
            )
            report_paths = self.report_service.save_outreach_report(summary, trigger=trigger, schedule_name=schedule.name)

            schedule.last_run = datetime.utcnow()
            schedule.last_status = "SUCCESS" if not summary.get("error") else "FAILED"
            schedule.last_error = summary.get("error", "")
            schedule.last_report_path = report_paths["json_path"]
            db.commit()
            self._refresh_next_run_times()
            return {**summary, **report_paths}
        except Exception as exc:
            if "schedule" in locals() and schedule:
                schedule.last_run = datetime.utcnow()
                schedule.last_status = "FAILED"
                schedule.last_error = str(exc)
                db.commit()
            logger.error(f"Scheduled autonomous outreach failed: {exc}")
            return {"failed": 1, "error": str(exc)}
        finally:
            db.close()
