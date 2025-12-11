"""Alerting utilities for pipeline failures."""

import os
import smtplib
import traceback
from email.message import EmailMessage
from typing import Optional

from config import AppConfig


class AlertManager:
    """Send operational alerts when the pipeline fails."""

    def __init__(self, config: AppConfig, logger) -> None:
        alerts_config = config.alerts or {}
        env_defaults = {
            "email": os.getenv("ALERT_EMAIL"),
            "sender": os.getenv("ALERT_SENDER"),
            "smtp_host": os.getenv("ALERT_SMTP_HOST"),
            "smtp_port": os.getenv("ALERT_SMTP_PORT"),
            "use_tls": os.getenv("ALERT_SMTP_TLS"),
            "username": os.getenv("ALERT_SMTP_USERNAME"),
            "password": os.getenv("ALERT_SMTP_PASSWORD"),
        }

        recipient_value = env_defaults["email"] if env_defaults["email"] is not None else alerts_config.get("email")
        self.recipient: Optional[str] = recipient_value

        sender_value = env_defaults["sender"] if env_defaults["sender"] is not None else alerts_config.get("sender")
        self.sender: str = sender_value or self.recipient or "alerts@autospanishblog"

        host_value = env_defaults["smtp_host"] if env_defaults["smtp_host"] is not None else alerts_config.get("smtp_host")
        self.smtp_host: str = host_value or "localhost"

        port_value = env_defaults["smtp_port"] if env_defaults["smtp_port"] is not None else alerts_config.get("smtp_port")
        self.smtp_port: int = int(port_value) if port_value else 25
        username_value = env_defaults["username"] if env_defaults["username"] is not None else alerts_config.get("username")
        self.username: Optional[str] = username_value

        password_value = env_defaults["password"] if env_defaults["password"] is not None else alerts_config.get("password")
        self.password: Optional[str] = password_value
        env_tls = env_defaults["use_tls"]
        if env_tls is not None:
            tls_value = str(env_tls).lower() in {"1", "true", "yes", "on"}
        else:
            tls_value = alerts_config.get("use_tls")
        self.use_tls: bool = bool(tls_value)

        # Default to sending alerts in CI when a recipient is provided, even if config isn't explicitly set.
        default_enabled = os.getenv("GITHUB_ACTIONS") == "true" and bool(self.recipient)
        env_enabled = os.getenv("ALERTS_ENABLED")
        if env_enabled is not None:
            enabled_value = str(env_enabled).lower() in {"1", "true", "yes", "on"}
        elif alerts_config.get("enabled") is not None:
            enabled_value = bool(alerts_config.get("enabled"))
        else:
            enabled_value = default_enabled

        self.enabled: bool = enabled_value
        self.logger = logger

    def send_failure_alert(self, *, run_id: str, environment: str, stage: str, exception: Exception) -> None:
        """Send a structured failure notification to operators."""
        if not self.enabled or not self.recipient:
            return

        subject = f"[AutoSpanishBlog] Pipeline failure ({environment}) - {run_id}"
        traceback_text = "".join(traceback.format_exception(exception)).strip()
        body = (
            "Pipeline execution failed.\n\n"
            f"Run ID: {run_id}\n"
            f"Environment: {environment}\n"
            f"Stage: {stage or 'unknown'}\n"
            f"Exception: {exception}\n\n"
            "Traceback:\n"
            f"{traceback_text}\n"
        )

        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = self.recipient
        message["Subject"] = subject
        message.set_content(body)

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as smtp:
                if self.use_tls:
                    smtp.starttls()
                if self.username and self.password:
                    smtp.login(self.username, self.password)
                smtp.send_message(message)
            self.logger.info("Failure alert email sent", extra={"run_id": run_id, "stage": stage})
        except Exception as alert_error:  # noqa: BLE001
            self.logger.error(
                "Failed to send failure alert",
                extra={
                    "run_id": run_id,
                    "stage": stage,
                    "error": str(alert_error),
                },
            )
