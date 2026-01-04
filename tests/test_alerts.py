import logging
from pathlib import Path
from types import SimpleNamespace

from scripts.alerts import AlertManager
from scripts.models import AlertsConfig, EmailConfig, SMTPConfig


class DummySMTP:
    last_instance = None

    def __init__(self, *args, **kwargs):
        self.closed = False

    def __enter__(self):
        DummySMTP.last_instance = self
        return self

    def __exit__(self, exc_type, exc, tb):
        self.closed = True

    def starttls(self):
        raise RuntimeError("starttls failure")

    def login(self, *args, **kwargs):
        return None

    def send_message(self, *args, **kwargs):
        return None


def test_send_email_closes_connection_on_failure(monkeypatch):
    monkeypatch.setattr("smtplib.SMTP", DummySMTP)

    alerts_config = AlertsConfig(
        enabled=True,
        email="recipient@example.com",
        email_config=EmailConfig(
            from_email="sender@example.com",
            smtp=SMTPConfig(host="smtp.example.com", port=587, username="user", password="pass"),
        ),
    )
    config = SimpleNamespace(alerts=alerts_config, logging={})
    alert_manager = AlertManager(config=config, logger=logging.getLogger("alerts-test"))

    alert_manager._send_email(subject="Test", body="Body", priority="high")

    assert DummySMTP.last_instance is not None
    assert DummySMTP.last_instance.closed is True


def test_send_error_does_not_raise_when_cooldown_save_fails(monkeypatch, tmp_path, caplog):
    def failing_open(self, *args, **kwargs):  # noqa: ANN001, ANN002
        raise OSError("write failure")

    alerts_config = AlertsConfig(
        enabled=True,
        email="recipient@example.com",
        email_config=EmailConfig(
            from_email="sender@example.com",
            smtp=SMTPConfig(host="smtp.example.com", port=587),
        ),
    )
    config = SimpleNamespace(alerts=alerts_config, logging={"file": str(tmp_path / "alerts.log")})
    alert_manager = AlertManager(config=config, logger=logging.getLogger("alerts-test"))

    monkeypatch.setattr(AlertManager, "_send_email", lambda *_, **__: None)
    monkeypatch.setattr(Path, "open", failing_open)

    caplog.set_level(logging.ERROR)

    alert_manager.send_error("Failure sending alert")

    assert any("Failed to persist alert cooldowns" in record.getMessage() for record in caplog.records)


def test_send_failure_alert_sends_email(monkeypatch):
    captured = {}

    def fake_send_email(*, subject, body, priority="normal"):
        captured["subject"] = subject
        captured["body"] = body
        captured["priority"] = priority

    alerts_config = AlertsConfig(
        enabled=True,
        email="recipient@example.com",
        email_config=EmailConfig(
            from_email="sender@example.com",
            smtp=SMTPConfig(host="smtp.example.com", port=587),
        ),
    )
    config = SimpleNamespace(alerts=alerts_config, logging={})
    alert_manager = AlertManager(config=config, logger=logging.getLogger("alerts-test"))

    monkeypatch.setattr(AlertManager, "_send_email", staticmethod(fake_send_email))

    alert_manager.send_failure_alert(
        run_id="run-123",
        environment="production",
        stage="synthesis",
        exception=ValueError("bad json"),
    )

    assert captured["priority"] == "high"
    assert "run-123" in captured["subject"]
    assert "Traceback:" in captured["body"]
