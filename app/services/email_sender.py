"""
SMTP email sending service.
"""
from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
import smtplib
from typing import Any

from app.core.branding import get_business_identity
from app.core.config import settings
from app.core.logging import logger
from app.core.sender_identity import normalize_sender_content


@dataclass
class PreparedEmail:
    """Normalized email payload ready for SMTP."""

    recipient: str
    actual_recipient: str
    subject: str
    text_body: str
    html_body: str
    language: str
    is_test_mode: bool = False


@dataclass
class EmailSendResult:
    """Outcome of one SMTP send attempt."""

    success: bool
    error: str = ""
    actual_recipient: str = ""
    skipped: bool = False
    simulated: bool = False
    test_mode: bool = False


class EmailSender:
    """Handle SMTP email delivery with safe defaults."""

    def is_configured(self) -> bool:
        """Return whether SMTP credentials are configured enough for sending."""
        return bool(settings.SMTP_HOST and settings.SMTP_FROM_EMAIL)

    def prepare_email(self, prospect: Any, test_to: str | None = None) -> PreparedEmail:
        """Build a normalized payload from a prospect model or dict."""
        language = self._get_value(prospect, "email_language", "fr")
        recipient = (self._get_value(prospect, "email", "") or "").strip()
        actual_recipient = (test_to or recipient).strip()
        subject = self._get_value(
            prospect,
            "email_subject_en" if language == "en" else "email_subject_fr",
            "",
        )
        text_body = self._get_value(
            prospect,
            "email_body_en" if language == "en" else "email_body_fr",
            "",
        )
        html_body = self._get_value(
            prospect,
            "email_html_en" if language == "en" else "email_html_fr",
            "",
        )

        return PreparedEmail(
            recipient=recipient,
            actual_recipient=actual_recipient,
            subject=subject,
            text_body=normalize_sender_content(text_body, settings.PROFESSIONAL_EMAIL),
            html_body=normalize_sender_content(html_body, settings.PROFESSIONAL_EMAIL),
            language=language,
            is_test_mode=bool(test_to),
        )

    def send_prepared_email(self, prepared: PreparedEmail, simulate: bool = False) -> EmailSendResult:
        """Send one email payload through SMTP."""
        if prepared.is_test_mode:
            logger.info(f"Using test recipient override: {prepared.actual_recipient}")
        elif prepared.actual_recipient:
            logger.info(f"Using real recipient: {prepared.actual_recipient}")

        if not prepared.actual_recipient:
            logger.info("Skipping email send because no lead email and no test recipient override were provided")
            return EmailSendResult(success=False, error="missing_email", skipped=True)

        if not prepared.subject or not prepared.text_body:
            logger.warning(f"Skipping email send for {prepared.actual_recipient} because content is incomplete")
            return EmailSendResult(success=False, error="missing_email_content", skipped=True)

        if simulate:
            logger.info(
                f"Simulated email send to {prepared.actual_recipient} | subject={prepared.subject[:120]} | test_mode={prepared.is_test_mode}"
            )
            return EmailSendResult(
                success=True,
                actual_recipient=prepared.actual_recipient,
                simulated=True,
                test_mode=prepared.is_test_mode,
            )

        if not self.is_configured():
            logger.error("SMTP sending failed because SMTP configuration is incomplete")
            return EmailSendResult(success=False, error="smtp_not_configured", actual_recipient=prepared.actual_recipient)

        message = self._build_message(prepared)

        try:
            if settings.SMTP_USE_TLS:
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as smtp:
                    smtp.ehlo()
                    smtp.starttls()
                    smtp.ehlo()
                    self._authenticate_if_needed(smtp)
                    smtp.send_message(message)
            elif settings.SMTP_PORT == 465:
                with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as smtp:
                    self._authenticate_if_needed(smtp)
                    smtp.send_message(message)
            else:
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as smtp:
                    self._authenticate_if_needed(smtp)
                    smtp.send_message(message)

            logger.info(
                f"Email sent to {prepared.actual_recipient} | subject={prepared.subject[:120]} | test_mode={prepared.is_test_mode}"
            )
            return EmailSendResult(
                success=True,
                actual_recipient=prepared.actual_recipient,
                test_mode=prepared.is_test_mode,
            )
        except Exception as exc:
            logger.error(
                f"Email send failed for {prepared.actual_recipient} | subject={prepared.subject[:120]} | error={exc}"
            )
            return EmailSendResult(success=False, error=str(exc), actual_recipient=prepared.actual_recipient)

    def _build_message(self, prepared: PreparedEmail) -> EmailMessage:
        """Create an EmailMessage with text + HTML alternatives."""
        identity = get_business_identity()
        message = EmailMessage()
        from_name = settings.SMTP_FROM_NAME or identity.sender_display_name
        from_email = settings.SMTP_FROM_EMAIL or identity.professional_email
        message["From"] = formataddr((from_name, from_email))
        message["To"] = prepared.actual_recipient
        message["Subject"] = prepared.subject
        message.set_content(prepared.text_body)

        if prepared.html_body:
            message.add_alternative(prepared.html_body, subtype="html")

        return message

    def _authenticate_if_needed(self, smtp: smtplib.SMTP) -> None:
        """Authenticate when SMTP credentials are configured."""
        if settings.SMTP_USERNAME:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)

    def _get_value(self, item: Any, field_name: str, default: Any = None) -> Any:
        """Read a field from either a dict or an object."""
        if isinstance(item, dict):
            return item.get(field_name, default)
        return getattr(item, field_name, default)
