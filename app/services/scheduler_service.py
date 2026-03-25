"""
Scheduler service
"""
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.schedule import Schedule
from app.services.lead_service import LeadService
from app.core.logging import logger

class SchedulerService:
    """Handle scheduled lead collection"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.lead_service = LeadService()

    def start(self):
        """Start the scheduler"""
        self._load_schedules()
        self.scheduler.start()
        logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")

    def add_schedule(self, name: str, cron_expression: str, locations: str, categories: str, limit: int, language: str):
        """Add a new scheduled job"""
        db = SessionLocal()
        try:
            schedule = Schedule(
                name=name,
                cron_expression=cron_expression,
                locations=locations,
                categories=categories,
                limit_per_location=limit,
                language=language
            )
            db.add(schedule)
            db.commit()
            db.refresh(schedule)

            # Add to scheduler
            self._schedule_job(schedule)

            logger.info(f"Added schedule: {name}")
            return schedule.id

        finally:
            db.close()

    def _load_schedules(self):
        """Load existing schedules from database"""
        db = SessionLocal()
        try:
            schedules = db.query(Schedule).filter(Schedule.enabled == True).all()

            for schedule in schedules:
                self._schedule_job(schedule)

        finally:
            db.close()

    def _schedule_job(self, schedule: Schedule):
        """Schedule a job"""
        try:
            trigger = CronTrigger.from_crontab(schedule.cron_expression)

            self.scheduler.add_job(
                func=self._run_scheduled_collection,
                trigger=trigger,
                args=[schedule.id],
                id=f"schedule_{schedule.id}",
                name=schedule.name,
                replace_existing=True
            )

            logger.info(f"Scheduled job: {schedule.name} ({schedule.cron_expression})")

        except Exception as e:
            logger.error(f"Failed to schedule job {schedule.name}: {e}")

    async def _run_scheduled_collection(self, schedule_id: int):
        """Run scheduled lead collection"""
        db = SessionLocal()
        try:
            schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
            if not schedule or not schedule.enabled:
                return

            locations = schedule.locations.split(",")
            categories = schedule.categories.split(",")

            logger.info(f"Running scheduled collection: {schedule.name}")

            await self.lead_service.collect_leads(
                locations=locations,
                categories=categories,
                limit=schedule.limit_per_location,
                language=schedule.language
            )

            # Update last run
            schedule.last_run = datetime.utcnow()
            db.commit()

        except Exception as e:
            logger.error(f"Scheduled collection failed: {e}")
        finally:
            db.close()