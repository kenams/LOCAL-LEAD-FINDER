"""
SMS sending service.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

import requests

from app.core.config import settings
from app.core.logging import logger
from app.core.sender_identity import normalize_sender_content


@dataclass
class PreparedSMS:
    """Normalized SMS payload ready for provider delivery."""

    recipient: str
    actual_recipient: str
    body: str
    provider: str


@dataclass
class SMSSendResult:
    """Outcome of one SMS send attempt."""

    success: bool
    error: str = ""
    actual_recipient: str = ""
    skipped: bool = False
    simulated: bool = False


class SMSSender:
    """Handle provider-based SMS delivery with graceful failure modes."""

    def is_configured(self) -> bool:
        return bool(settings.SMS_PROVIDER and settings.SMS_API_KEY and settings.SMS_API_SECRET and settings.SMS_FROM_NUMBER)

    def prepare_sms(self, prospect: Any) -> PreparedSMS:
        recipient = (self._get_value(prospect, "phone", "") or "").strip()
        message = self._extract_sms_body(prospect)
        return PreparedSMS(
            recipient=recipient,
            actual_recipient=recipient,
            body=normalize_sender_content(message, settings.PROFESSIONAL_EMAIL),
            provider=settings.SMS_PROVIDER,
        )

    def send_prepared_sms(self, prepared: PreparedSMS, simulate: bool = False) -> SMSSendResult:
        if prepared.actual_recipient:
            logger.info(f"Using SMS recipient: {prepared.actual_recipient}")
        if not prepared.actual_recipient:
            logger.info("Skipping SMS send because no phone number was provided")
            return SMSSendResult(success=False, error="missing_phone", skipped=True)
        if not prepared.body:
            logger.warning(f"Skipping SMS send for {prepared.actual_recipient} because SMS content is incomplete")
            return SMSSendResult(success=False, error="missing_sms_content", skipped=True)
        if simulate:
            logger.info(f"Simulated SMS send to {prepared.actual_recipient} | provider={prepared.provider}")
            return SMSSendResult(success=True, actual_recipient=prepared.actual_recipient, simulated=True)
        if not settings.SMS_PROVIDER:
            logger.error("SMS sending failed because SMS provider is not configured")
            return SMSSendResult(success=False, error="sms_provider_not_configured", actual_recipient=prepared.actual_recipient)
        if not self.is_configured():
            logger.error("SMS sending failed because SMS provider credentials are incomplete")
            return SMSSendResult(success=False, error="sms_not_configured", actual_recipient=prepared.actual_recipient)
        if settings.SMS_PROVIDER == "twilio":
            return self._send_twilio(prepared)
        logger.error(f"SMS sending failed because provider {settings.SMS_PROVIDER} is unsupported")
        return SMSSendResult(success=False, error="sms_provider_unsupported", actual_recipient=prepared.actual_recipient)

    def _send_twilio(self, prepared: PreparedSMS) -> SMSSendResult:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.SMS_API_KEY}/Messages.json"
        payload = {"From": settings.SMS_FROM_NUMBER, "To": prepared.actual_recipient, "Body": prepared.body}
        try:
            response = requests.post(
                url,
                data=payload,
                auth=(settings.SMS_API_KEY, settings.SMS_API_SECRET),
                timeout=30,
            )
            if response.ok:
                logger.info(f"SMS sent to {prepared.actual_recipient} | provider=twilio")
                return SMSSendResult(success=True, actual_recipient=prepared.actual_recipient)
            logger.error(f"SMS send failed for {prepared.actual_recipient} | provider=twilio | status={response.status_code}")
            return SMSSendResult(
                success=False,
                error=f"twilio_http_{response.status_code}",
                actual_recipient=prepared.actual_recipient,
            )
        except Exception as exc:
            logger.error(f"SMS send failed for {prepared.actual_recipient} | provider=twilio | error={exc}")
            return SMSSendResult(success=False, error=str(exc), actual_recipient=prepared.actual_recipient)

    def _extract_sms_body(self, prospect: Any) -> str:
        if isinstance(prospect, dict):
            return prospect.get("sms_message") or prospect.get("sms") or ""
        notes = self._get_value(prospect, "notes", "")
        if notes:
            try:
                payload = json.loads(notes)
                if isinstance(payload, dict):
                    return payload.get("sms_message") or payload.get("sms") or ""
            except json.JSONDecodeError:
                return ""
        return self._get_value(prospect, "sms_message", "") or ""

    def _get_value(self, item: Any, field_name: str, default: Any = None) -> Any:
        if isinstance(item, dict):
            return item.get(field_name, default)
        return getattr(item, field_name, default)
