"""
Multi-channel notification system for Phase 5E.

Provides:
    NotificationChannel  — enum of supported delivery channels
    NotificationSystem   — facade with send_* convenience methods
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from backend.models.schedules import NotificationLog


class NotificationChannel(str, Enum):
    """Supported notification delivery channels."""

    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    IN_APP = "in_app"


class NotificationSystem:
    """
    Centralised notification dispatcher.

    All methods are static/async for easy use from the scheduling engine and
    job executors.  Actual delivery (email, SMS, webhook) is currently
    stubbed — replace the private ``_send_*`` helpers with real integrations.
    """

    # ------------------------------------------------------------------
    # Core send method
    # ------------------------------------------------------------------

    @staticmethod
    async def send_notification(
        notification_type: str,
        recipient_id: int,
        channel: str,
        subject: str,
        body: str,
        recipient_type: str = "user",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a NotificationLog entry and dispatch via the requested channel.

        Returns a dict with ``success`` and the log document id (if persisted).
        """
        log = NotificationLog(
            notification_type=notification_type,
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            channel=channel,
            subject=subject,
            body=body,
            status="PENDING",
            metadata=metadata or {},
        )

        try:
            await log.insert()
        except Exception:  # noqa: BLE001
            pass  # Best-effort persistence; continue with dispatch

        try:
            channel_value = channel.value if hasattr(channel, "value") else channel
            if channel_value == NotificationChannel.EMAIL:
                await NotificationSystem._send_email(recipient_id, subject, body)
            elif channel_value == NotificationChannel.SMS:
                await NotificationSystem._send_sms(recipient_id, body)
            elif channel_value == NotificationChannel.WEBHOOK:
                url = (metadata or {}).get("webhook_url", "")
                await NotificationSystem._send_webhook(url, {"subject": subject, "body": body, **(metadata or {})})
            elif channel_value == NotificationChannel.IN_APP:
                pass  # In-app notifications are consumed directly from NotificationLog

            log.status = "SENT"
            log.sent_at = datetime.now()
        except Exception as exc:  # noqa: BLE001
            log.status = "FAILED"
            log.error = str(exc)
            try:
                await log.save()
            except Exception:  # noqa: BLE001
                pass
            return {"success": False, "error": str(exc), "log_id": str(getattr(log, "id", None))}

        try:
            await log.save()
        except Exception:  # noqa: BLE001
            pass

        return {"success": True, "log_id": str(getattr(log, "id", None))}

    # ------------------------------------------------------------------
    # Domain-specific convenience methods
    # ------------------------------------------------------------------

    @staticmethod
    async def send_expiry_warning(contract: Any, days_remaining: int) -> List[Dict[str, Any]]:
        """
        Send expiry warning notifications for a contract to its owner and team.
        """
        contract_code = getattr(contract, "contract_code", "N/A")
        contract_id = getattr(contract, "uid", 0)
        recipient_id = getattr(contract, "created_by_admin_id", 0) or 0

        urgency = "URGENT: " if days_remaining <= 7 else ""
        subject = f"{urgency}Contract {contract_code} expires in {days_remaining} days"
        body = (
            f"This is an automated reminder that contract {contract_code} "
            f"(ID: {contract_id}) will expire in {days_remaining} day(s). "
            f"Please take the necessary action to renew or complete the contract."
        )

        results = []
        for channel in (NotificationChannel.EMAIL, NotificationChannel.IN_APP):
            result = await NotificationSystem.send_notification(
                notification_type="expiry_warning",
                recipient_id=recipient_id,
                channel=channel,
                subject=subject,
                body=body,
                metadata={"contract_id": contract_id, "days_remaining": days_remaining},
            )
            results.append(result)

        return results

    @staticmethod
    async def send_renewal_reminder(contract: Any) -> Dict[str, Any]:
        """Send a renewal reminder to the contract owner."""
        contract_code = getattr(contract, "contract_code", "N/A")
        contract_id = getattr(contract, "uid", 0)
        recipient_id = getattr(contract, "created_by_admin_id", 0) or 0

        subject = f"Renewal Required: Contract {contract_code}"
        body = (
            f"Contract {contract_code} (ID: {contract_id}) is approaching its expiry. "
            f"A renewal approval request has been created. "
            f"Please review and approve the renewal to continue the contract."
        )

        return await NotificationSystem.send_notification(
            notification_type="renewal_reminder",
            recipient_id=recipient_id,
            channel=NotificationChannel.EMAIL,
            subject=subject,
            body=body,
            metadata={"contract_id": contract_id},
        )

    @staticmethod
    async def send_payment_reminder(contract: Any) -> Dict[str, Any]:
        """Send a payment due reminder to billing contacts."""
        contract_code = getattr(contract, "contract_code", "N/A")
        contract_id = getattr(contract, "uid", 0)
        contract_value = getattr(contract, "contract_value", 0.0)
        recipient_id = getattr(contract, "created_by_admin_id", 0) or 0

        subject = f"Payment Reminder: Contract {contract_code}"
        body = (
            f"This is your monthly payment reminder for contract {contract_code} "
            f"(ID: {contract_id}). "
            f"Total contract value: {contract_value:.2f} KD. "
            f"Please ensure payment is processed according to the agreed payment terms."
        )

        return await NotificationSystem.send_notification(
            notification_type="payment_reminder",
            recipient_id=recipient_id,
            channel=NotificationChannel.EMAIL,
            subject=subject,
            body=body,
            metadata={"contract_id": contract_id, "contract_value": contract_value},
        )

    @staticmethod
    async def send_completion_notification(contract: Any) -> List[Dict[str, Any]]:
        """Send completion notifications to all stakeholders."""
        contract_code = getattr(contract, "contract_code", "N/A")
        contract_id = getattr(contract, "uid", 0)
        recipient_id = getattr(contract, "created_by_admin_id", 0) or 0

        subject = f"Contract {contract_code} Completed"
        body = (
            f"Contract {contract_code} (ID: {contract_id}) has been automatically "
            f"completed on its end date. "
            f"All module resources have been released. "
            f"Please review the final contract summary."
        )

        results = []
        for channel in (NotificationChannel.EMAIL, NotificationChannel.IN_APP):
            result = await NotificationSystem.send_notification(
                notification_type="contract_completed",
                recipient_id=recipient_id,
                channel=channel,
                subject=subject,
                body=body,
                metadata={"contract_id": contract_id},
            )
            results.append(result)

        return results

    # ------------------------------------------------------------------
    # Channel stubs — replace with real integrations
    # ------------------------------------------------------------------

    @staticmethod
    async def _send_email(recipient_id: int, subject: str, body: str) -> None:
        """Placeholder: dispatch email via SMTP / SendGrid / SES."""
        pass  # TODO: integrate with email provider

    @staticmethod
    async def _send_sms(recipient_id: int, message: str) -> None:
        """Placeholder: dispatch SMS via Twilio / AWS SNS."""
        pass  # TODO: integrate with SMS provider

    @staticmethod
    async def _send_webhook(url: str, payload: Dict[str, Any]) -> None:
        """Placeholder: POST notification payload to a webhook URL."""
        if not url:
            return
        # TODO: use httpx / aiohttp to POST payload to url
        pass
