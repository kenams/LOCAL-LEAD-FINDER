"""
Scheduler service.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.country_config import detect_country, get_country_display_name
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
                schedule.configs_json = self._serialize_rotation_configs(
                    self._load_rotation_configs_from_settings_or_schedule(schedule)
                )
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
                configs_json=self._serialize_rotation_configs(self._load_rotation_configs_from_settings_or_schedule(None)),
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
            schedule.next_run = self._calculate_next_run(cron_expression) if enabled else None
            if not self._load_rotation_configs_from_schedule(schedule):
                schedule.configs_json = self._serialize_rotation_configs(
                    [self._build_rotation_config(locations=locations, categories=categories, language=language, limit=limit)]
                )
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
                "last_used_config_index": schedule.last_used_config_index if schedule else None,
                "last_run_config": self._deserialize_json_object(schedule.last_run_config) if schedule and schedule.last_run_config else None,
                "rotation_config_count": len(self._load_rotation_configs_from_schedule(schedule)) if schedule else 0,
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
            if summary.get("config_used"):
                schedule.last_run_config = json.dumps(summary.get("config_used"), ensure_ascii=False)
                if summary.get("config_used_index") is not None:
                    schedule.last_used_config_index = int(summary["config_used_index"])
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

    def get_rotating_config_for_run(self) -> dict[str, Any]:
        """Return the next rotating configuration for a one-shot run without mutating persistence."""
        db = SessionLocal()
        try:
            schedule = db.query(Schedule).filter(Schedule.name == settings.AUTO_MODE_NAME).first()
            if not schedule:
                self.ensure_auto_schedule()
                schedule = db.query(Schedule).filter(Schedule.name == settings.AUTO_MODE_NAME).first()
            if not schedule:
                return self._build_rotation_config(
                    locations=settings.AUTO_MODE_LOCATIONS,
                    categories=settings.AUTO_MODE_CATEGORIES,
                    language=settings.AUTO_MODE_LANGUAGE,
                    limit=settings.AUTO_MODE_LIMIT,
                )
            config, index, total = self._select_next_rotation_config(schedule)
            return {**config, "index": index, "rotation_size": total}
        finally:
            db.close()

    def list_rotation_configs(self) -> list[dict[str, Any]]:
        """Return the persisted rotation configs for the autonomous schedule."""
        db = SessionLocal()
        try:
            schedule = db.query(Schedule).filter(Schedule.name == settings.AUTO_MODE_NAME).first()
            configs = self._load_rotation_configs_from_settings_or_schedule(schedule)
            return [{**config, "index": index} for index, config in enumerate(configs)]
        finally:
            db.close()

    def append_rotation_config(self, config: dict[str, Any]) -> int:
        """Append one configuration to the persisted rotation list if it is new."""
        db = SessionLocal()
        try:
            schedule = db.query(Schedule).filter(Schedule.name == settings.AUTO_MODE_NAME).first()
            if not schedule:
                self.ensure_auto_schedule()
                schedule = db.query(Schedule).filter(Schedule.name == settings.AUTO_MODE_NAME).first()
            if not schedule:
                return 0
            configs = self._load_rotation_configs_from_settings_or_schedule(schedule)
            normalized = self._normalize_rotation_config(config, len(configs))
            signature = self._rotation_signature(normalized)
            existing_signatures = {self._rotation_signature(item) for item in configs}
            if signature not in existing_signatures:
                configs.append(normalized)
                schedule.configs_json = self._serialize_rotation_configs(configs)
                db.commit()
            return len(configs)
        finally:
            db.close()

    def reset_rotation_to_single_config(self, config: dict[str, Any]) -> None:
        """Replace the rotation list with a single configuration."""
        db = SessionLocal()
        try:
            schedule = db.query(Schedule).filter(Schedule.name == settings.AUTO_MODE_NAME).first()
            if not schedule:
                self.ensure_auto_schedule()
                schedule = db.query(Schedule).filter(Schedule.name == settings.AUTO_MODE_NAME).first()
            if not schedule:
                return
            normalized = self._normalize_rotation_config(config, 0)
            schedule.configs_json = self._serialize_rotation_configs([normalized])
            schedule.last_used_config_index = None
            schedule.last_run_config = None
            db.commit()
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
            next_run_time = getattr(job, "next_run_time", None)
            schedule.next_run = next_run_time.replace(tzinfo=None) if next_run_time else self._calculate_next_run(schedule.cron_expression)
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
                next_run_time = getattr(job, "next_run_time", None)
                schedule.next_run = next_run_time.replace(tzinfo=None) if next_run_time else (schedule.next_run or self._calculate_next_run(schedule.cron_expression))
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

    def _split_csv(self, raw_value: str | None) -> list[str]:
        return [item.strip() for item in str(raw_value or "").split(",") if item.strip()]

    def _build_rotation_config(self, *, locations: str | list[str], categories: str | list[str], language: str, limit: int, name: str | None = None) -> dict[str, Any]:
        location_items = locations if isinstance(locations, list) else self._split_csv(locations)
        category_items = categories if isinstance(categories, list) else self._split_csv(categories)
        primary_location = location_items[0] if location_items else ""
        country_code = detect_country(primary_location)
        country_name = get_country_display_name(country_code) if primary_location else ""
        primary_category = category_items[0] if category_items else ""
        config_name = name or " | ".join(part for part in [country_name or primary_location, primary_category] if part) or "Configuration auto"
        return {
            "name": config_name,
            "locations": location_items,
            "categories": category_items,
            "language": language or settings.AUTO_MODE_LANGUAGE,
            "limit": int(limit or settings.AUTO_MODE_LIMIT),
            "country": country_name,
            "primary_category": primary_category,
        }

    def _normalize_rotation_config(self, raw_config: dict[str, Any], fallback_index: int = 0) -> dict[str, Any]:
        return self._build_rotation_config(
            locations=raw_config.get("locations", settings.AUTO_MODE_LOCATIONS),
            categories=raw_config.get("categories", settings.AUTO_MODE_CATEGORIES),
            language=str(raw_config.get("language", settings.AUTO_MODE_LANGUAGE)),
            limit=int(raw_config.get("limit", settings.AUTO_MODE_LIMIT) or settings.AUTO_MODE_LIMIT),
            name=raw_config.get("name") or raw_config.get("label") or f"Configuration {fallback_index + 1}",
        )

    def _load_rotation_configs_from_settings_or_schedule(self, schedule: Schedule | None) -> list[dict[str, Any]]:
        schedule_configs = self._load_rotation_configs_from_schedule(schedule)
        if schedule_configs:
            return schedule_configs
        if schedule:
            return [
                self._build_rotation_config(
                    locations=schedule.locations,
                    categories=schedule.categories,
                    language=schedule.language,
                    limit=schedule.limit_per_location,
                )
            ]
        raw_settings = (settings.AUTO_MODE_ROTATION_CONFIGS or "").strip()
        if raw_settings:
            try:
                payload = json.loads(raw_settings)
                if isinstance(payload, list):
                    configs = [self._normalize_rotation_config(item, index) for index, item in enumerate(payload) if isinstance(item, dict)]
                    if configs:
                        return configs
            except Exception as exc:
                logger.warning(f"Could not parse AUTO_MODE_ROTATION_CONFIGS: {exc}")
        return [
            self._build_rotation_config(
                locations=settings.AUTO_MODE_LOCATIONS,
                categories=settings.AUTO_MODE_CATEGORIES,
                language=settings.AUTO_MODE_LANGUAGE,
                limit=settings.AUTO_MODE_LIMIT,
            )
        ]

    def _load_rotation_configs_from_schedule(self, schedule: Schedule | None) -> list[dict[str, Any]]:
        if not schedule or not schedule.configs_json:
            return []
        try:
            payload = json.loads(schedule.configs_json)
            if not isinstance(payload, list):
                return []
            return [self._normalize_rotation_config(item, index) for index, item in enumerate(payload) if isinstance(item, dict)]
        except Exception as exc:
            logger.warning(f"Could not parse stored rotation configs: {exc}")
            return []

    def _serialize_rotation_configs(self, configs: list[dict[str, Any]]) -> str:
        return json.dumps(configs, ensure_ascii=False)

    def _rotation_signature(self, config: dict[str, Any]) -> tuple[Any, ...]:
        return (
            tuple(config.get("locations", [])),
            tuple(config.get("categories", [])),
            config.get("language", ""),
            int(config.get("limit", 0) or 0),
        )

    def _deserialize_json_object(self, raw_value: str) -> dict[str, Any] | None:
        try:
            payload = json.loads(raw_value)
            return payload if isinstance(payload, dict) else None
        except Exception:
            return None

    def _select_next_rotation_config(self, schedule: Schedule) -> tuple[dict[str, Any], int, int]:
        configs = self._load_rotation_configs_from_settings_or_schedule(schedule)
        total = len(configs)
        if total == 0:
            config = self._build_rotation_config(
                locations=schedule.locations,
                categories=schedule.categories,
                language=schedule.language,
                limit=schedule.limit_per_location,
            )
            return config, 0, 1
        last_index = schedule.last_used_config_index if schedule.last_used_config_index is not None else -1
        next_index = (int(last_index) + 1) % total
        return configs[next_index], next_index, total

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
            active_config, next_index, rotation_size = self._select_next_rotation_config(schedule)
            locations = list(active_config.get("locations", []))
            categories = list(active_config.get("categories", []))
            language = str(active_config.get("language") or schedule.language or settings.AUTO_MODE_LANGUAGE)
            limit = int(active_config.get("limit") or schedule.limit_per_location or settings.AUTO_MODE_LIMIT)

            logger.info(
                f"Running autonomous outreach: {schedule.name} "
                f"(rotation_index={next_index}, config={active_config.get('name', '')}, locations={locations}, categories={categories})"
            )
            summary = await self.lead_service.auto_outreach(
                locations=locations,
                categories=categories,
                limit=limit,
                language=language,
                simulate=simulate,
            )
            summary["config_used"] = active_config
            summary["config_used_index"] = next_index
            summary["rotation_size"] = rotation_size
            report_paths = self.report_service.save_outreach_report(summary, trigger=trigger, schedule_name=schedule.name)

            schedule.last_run = datetime.utcnow()
            schedule.last_status = "SUCCESS" if not summary.get("error") else "FAILED"
            schedule.last_error = summary.get("error", "")
            schedule.last_report_path = report_paths["json_path"]
            schedule.last_used_config_index = next_index
            schedule.last_run_config = json.dumps(active_config, ensure_ascii=False)
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
