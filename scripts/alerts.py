"""Alert management utilities for pipeline errors and notifications."""

from __future__ import annotations

import json
import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, Optional

from scripts.config import AppConfig
from scripts.models import AlertsConfig


class AlertManager:
    """Send alerts via email (and optional Telegram) with cooldown support."""

    def __init__(self, config: AppConfig, logger: logging.Logger):
        self.logger = logger
        self.alerts_config: AlertsConfig = config.alerts
        self.enabled = bool(self.alerts_config.enabled)

        log_file = config.logging.get("file") if isinstance(config.logging, dict) else None
        default_cooldown_path = Path("output/logs/alert_cooldown.json")
        self.cooldown_file = Path(log_file).parent / "alert_cooldown.json" if log_file else default_cooldown_path
        self.cooldown_hours = self.alerts_config.cooldown_hours
        self.cooldowns = self._load_cooldowns()

    def _load_cooldowns(self) -> Dict[str, str]:
        if not self.cooldown_file.exists():
            return {}

        try:
            with self.cooldown_file.open("r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return {}

    def _save_cooldowns(self) -> None:
        self.cooldown_file.parent.mkdir(parents=True, exist_ok=True)
        with self.cooldown_file.open("w", encoding="utf-8") as file:
            json.dump(self.cooldowns, file, indent=2)

    def _check_cooldown(self, alert_key: str) -> bool:
        if alert_key not in self.cooldowns:
            return False

        last_sent = datetime.fromisoformat(self.cooldowns[alert_key])
        cooldown_until = last_sent + timedelta(hours=self.cooldown_hours)
        return datetime.utcnow() < cooldown_until

    def _update_cooldown(self, alert_key: str) -> None:
        self.cooldowns[alert_key] = datetime.utcnow().isoformat()
        self._save_cooldowns()

    def send_critical(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Send a critical alert (bypasses cooldown)."""

        self.logger.critical(message, extra=context or {})
        if not self.enabled:
            return

        self._send_email(
            subject=f"🚨 CRITICAL: AutoSpanishBlog - {message}",
            body=self._format_alert_body(message, context, "CRITICAL"),
            priority="high",
        )

    def send_error(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Send an error alert (respects cooldown)."""

        alert_key = f"error:{message[:50]}"
        self.logger.error(message, extra=context or {})

        if not self.enabled or self._check_cooldown(alert_key):
            return

        self._send_email(
            subject=f"❌ ERROR: AutoSpanishBlog - {message}",
            body=self._format_alert_body(message, context, "ERROR"),
        )
        self._update_cooldown(alert_key)

    def send_warning(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Send a warning alert (currently logged only, cooldown respected)."""

        alert_key = f"warning:{message[:50]}"
        self.logger.warning(message, extra=context or {})

        if not self.enabled or self._check_cooldown(alert_key):
            return

        self._update_cooldown(alert_key)

    def _format_alert_body(self, message: str, context: Optional[Dict[str, Any]], severity: str) -> str:
        body = (
            "AutoSpanishBlog Alert\n\n"
            f"Severity: {severity}\n"
            f"Time: {datetime.utcnow().isoformat()}Z\n"
            f"Message: {message}\n\n"
        )

        if context:
            body += "Context:\n"
            for key, value in context.items():
                body += f"  {key}: {value}\n"

        body += "\n---\nAutoSpanishBlog Alert System"
        return body

    def _send_email(self, subject: str, body: str, priority: str = "normal") -> None:
        email_config = self.alerts_config.email_config
        to_email = self.alerts_config.email

        if not to_email or not email_config:
            self.logger.warning("Alert email not configured, skipping email send")
            return

        try:
            message = MIMEMultipart()
            message["From"] = email_config.from_email
            message["To"] = to_email
            message["Subject"] = subject

            if priority == "high":
                message["X-Priority"] = "1"

            message.attach(MIMEText(body, "plain"))

            smtp_config = email_config.smtp
            username = smtp_config.username
            password = smtp_config.password

            with smtplib.SMTP(smtp_config.host, smtp_config.port) as server:
                server.starttls()

                if username and password:
                    server.login(username, password)

                server.send_message(message)

            self.logger.info("Alert email sent", extra={"subject": subject})
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "Failed to send alert email",
                exc_info=(exc.__class__, exc, exc.__traceback__),
            )

    def send_telegram(self, message: str) -> None:
        telegram_config = self.alerts_config.telegram

        if not telegram_config or not telegram_config.enabled:
            return

        bot_token = telegram_config.bot_token
        chat_id = telegram_config.chat_id

        if not bot_token or not chat_id:
            return

        try:
            import requests

            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}

            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()

            self.logger.info("Telegram alert sent")
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "Failed to send Telegram alert",
                exc_info=(exc.__class__, exc, exc.__traceback__),
            )
