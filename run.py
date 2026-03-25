#!/usr/bin/env python3
"""
Local Lead Finder - Main entry point
"""
import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.core.logging import setup_logging
from app.services.lead_service import LeadService
from app.services.scheduler_service import SchedulerService
from app.services.export_service import ExportService
from app.db.session import init_db


def print_smtp_diagnostics() -> None:
    """Print a safe SMTP configuration snapshot."""
    diagnostics = settings.get_smtp_diagnostics()
    print(f"SMTP host: {diagnostics['host']}")
    print(f"SMTP port: {diagnostics['port']}")
    print(f"SMTP username: {diagnostics['username']}")
    print(f"From email: {diagnostics['from_email']}")
    print(f"Password present: {diagnostics['password_present']}")
    print(f"Password length: {diagnostics['password_length']}")
    for warning in diagnostics["warnings"]:
        print(f"WARNING: {warning}")


def main():
    # Setup logging
    setup_logging()

    parser = argparse.ArgumentParser(description="Local Lead Finder")
    parser.add_argument("--collect", action="store_true", help="Run lead collection")
    parser.add_argument("--locations", type=str, help="Comma-separated locations")
    parser.add_argument("--categories", type=str, help="Comma-separated categories")
    parser.add_argument("--limit", type=int, default=settings.DEFAULT_PROSPECTS_PER_LOCATION, help="Prospects per location")
    parser.add_argument("--lang", type=str, default=settings.DEFAULT_LANGUAGE, choices=["fr", "en"], help="Email language")
    parser.add_argument("--generate-emails", action="store_true", help="Generate emails for existing leads")
    parser.add_argument("--send-emails", action="store_true", help="Send generated outreach emails")
    parser.add_argument("--only-not-sent", action="store_true", help="Only target leads that have never been sent")
    parser.add_argument("--test-to", type=str, help="Override all recipients with a test email address")
    parser.add_argument("--simulate-send", action="store_true", help="Simulate sending without SMTP delivery")
    parser.add_argument("--send-country", type=str, help="Filter sending by country code")
    parser.add_argument("--send-category", type=str, help="Filter sending by category")
    parser.add_argument("--min-priority", type=float, help="Filter sending by minimum priority score")
    parser.add_argument("--export", type=str, choices=["csv", "xlsx"], help="Export leads to format")
    parser.add_argument("--ui", action="store_true", help="Run Streamlit UI")
    parser.add_argument("--init-db", action="store_true", help="Initialize database")
    parser.add_argument("--reset-leads", action="store_true", help="Clear existing leads and search history")
    parser.add_argument("--check-smtp", action="store_true", help="Show safe SMTP diagnostics without revealing the password")

    args = parser.parse_args()

    # Initialize database
    if args.init_db:
        init_db()
        print("Database initialized.")
        return

    if args.check_smtp:
        print_smtp_diagnostics()
        return

    if args.ui:
        import subprocess
        import os
        env = os.environ.copy()
        env["PYTHONPATH"] = str(PROJECT_ROOT)
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "app/ui/streamlit_app.py"],
            env=env,
            check=True
        )
        return

    init_db()

    # Initialize services
    lead_service = LeadService()
    export_service = ExportService()

    if args.reset_leads:
        deleted = lead_service.reset_leads(clear_search_history=True)
        print(f"Reset completed. {deleted} leads deleted.")
        if not any([args.collect, args.generate_emails, args.export]):
            return

    if args.collect:
        locations = args.locations.split(",") if args.locations else ["Toulouse"]
        categories = args.categories.split(",") if args.categories else ["coiffeur"]
        saved_count = asyncio.run(lead_service.collect_leads(locations, categories, args.limit, args.lang))
        print(f"Lead collection completed. {saved_count} leads saved.")

    if args.generate_emails:
        asyncio.run(lead_service.generate_emails())
        print("Emails generated.")

    if args.send_emails:
        for warning in settings.get_smtp_identity_warnings():
            print(f"WARNING: {warning}")
        if args.test_to:
            print(f"Using test recipient override: {args.test_to}")
        send_summary = lead_service.send_emails(
            limit=args.limit,
            only_not_sent=args.only_not_sent,
            test_to=args.test_to,
            simulate=args.simulate_send,
            country=args.send_country,
            category=args.send_category,
            min_priority=args.min_priority,
            allow_resend=settings.SEND_ALLOW_RESEND,
        )
        print(
            "Email sending completed. "
            f"selected={send_summary.get('selected', 0)} "
            f"sent={send_summary.get('sent', 0)} "
            f"failed={send_summary.get('failed', 0)} "
            f"skipped={send_summary.get('skipped', 0)} "
            f"simulated={send_summary.get('simulated', 0)}"
        )

    if args.export:
        export_service.export_leads(args.export)
        print(f"Leads exported to {args.export}.")

    if not any([
        args.collect,
        args.generate_emails,
        args.send_emails,
        args.export,
        args.ui,
        args.init_db,
        args.reset_leads,
        args.check_smtp,
    ]):
        # Default: run scheduler
        scheduler = SchedulerService()
        scheduler.start()
        print("Scheduler started. Press Ctrl+C to stop.")
        try:
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            scheduler.stop()
            print("Scheduler stopped.")


if __name__ == "__main__":
    main()
