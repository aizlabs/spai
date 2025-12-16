import logging
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
