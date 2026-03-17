"""Tests for config loading and environment overrides."""

import pytest

from scripts.config import apply_env_overrides


def _base_alerts_dict():
    """Minimal alerts structure matching base.yaml."""
    return {
        "enabled": False,
        "email": "your@email.com",
        "cooldown_hours": 6,
        "email_config": {
            "from": "bot@autospanish.com",
            "smtp": {
                "host": "smtp.gmail.com",
                "port": 587,
                "username": "",
                "password": "",
            },
        },
    }


def test_alert_email_override(monkeypatch):
    """ALERT_EMAIL sets alerts.email."""
    monkeypatch.setenv("ALERT_EMAIL", "alerts@example.com")
    try:
        config = {"alerts": _base_alerts_dict()}
        apply_env_overrides(config)
        assert config["alerts"]["email"] == "alerts@example.com"
    finally:
        monkeypatch.delenv("ALERT_EMAIL", raising=False)


def test_alerts_enabled_true(monkeypatch):
    """ALERTS_ENABLED=true sets alerts.enabled to True."""
    monkeypatch.setenv("ALERTS_ENABLED", "true")
    try:
        config = {"alerts": _base_alerts_dict()}
        apply_env_overrides(config)
        assert config["alerts"]["enabled"] is True
    finally:
        monkeypatch.delenv("ALERTS_ENABLED", raising=False)


def test_alerts_enabled_true_case_insensitive(monkeypatch):
    """ALERTS_ENABLED=True (capitalized) still enables alerts."""
    monkeypatch.setenv("ALERTS_ENABLED", "True")
    try:
        config = {"alerts": _base_alerts_dict()}
        apply_env_overrides(config)
        assert config["alerts"]["enabled"] is True
    finally:
        monkeypatch.delenv("ALERTS_ENABLED", raising=False)


def test_alerts_enabled_false_overrides_yaml(monkeypatch):
    """ALERTS_ENABLED=false sets alerts.enabled to False, overriding YAML that had enabled: true."""
    monkeypatch.setenv("ALERTS_ENABLED", "false")
    try:
        config = {"alerts": {**_base_alerts_dict(), "enabled": True}}
        apply_env_overrides(config)
        assert config["alerts"]["enabled"] is False
    finally:
        monkeypatch.delenv("ALERTS_ENABLED", raising=False)


def test_alerts_enabled_unset_unchanged(monkeypatch):
    """When ALERTS_ENABLED is unset, alerts.enabled is unchanged."""
    monkeypatch.delenv("ALERTS_ENABLED", raising=False)
    config = {"alerts": _base_alerts_dict()}
    apply_env_overrides(config)
    assert config["alerts"]["enabled"] is False


def test_smtp_env_overrides(monkeypatch):
    """ALERT_SMTP_* and fallbacks set email_config.smtp."""
    monkeypatch.setenv("ALERT_SMTP_HOST", "smtp.sendgrid.net")
    monkeypatch.setenv("ALERT_SMTP_PORT", "2525")
    monkeypatch.setenv("ALERT_SMTP_USERNAME", "apikey")
    monkeypatch.setenv("ALERT_SMTP_PASSWORD", "secret")
    try:
        config = {"alerts": _base_alerts_dict()}
        apply_env_overrides(config)
        smtp = config["alerts"]["email_config"]["smtp"]
        assert smtp["host"] == "smtp.sendgrid.net"
        assert smtp["port"] == 2525
        assert smtp["username"] == "apikey"
        assert smtp["password"] == "secret"
    finally:
        for key in ("ALERT_SMTP_HOST", "ALERT_SMTP_PORT", "ALERT_SMTP_USERNAME", "ALERT_SMTP_PASSWORD"):
            monkeypatch.delenv(key, raising=False)


def test_smtp_fallback_username_password(monkeypatch):
    """EMAIL_USERNAME and EMAIL_PASSWORD used when ALERT_SMTP_* not set."""
    monkeypatch.setenv("EMAIL_USERNAME", "user@gmail.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "app-pass")
    try:
        config = {"alerts": _base_alerts_dict()}
        apply_env_overrides(config)
        smtp = config["alerts"]["email_config"]["smtp"]
        assert smtp["username"] == "user@gmail.com"
        assert smtp["password"] == "app-pass"
    finally:
        monkeypatch.delenv("EMAIL_USERNAME", raising=False)
        monkeypatch.delenv("EMAIL_PASSWORD", raising=False)


def test_alert_sender_override(monkeypatch):
    """ALERT_SENDER sets email_config.from."""
    monkeypatch.setenv("ALERT_SENDER", "Bot <noreply@example.com>")
    try:
        config = {"alerts": _base_alerts_dict()}
        apply_env_overrides(config)
        assert config["alerts"]["email_config"]["from"] == "Bot <noreply@example.com>"
    finally:
        monkeypatch.delenv("ALERT_SENDER", raising=False)


def test_smtp_unset_preserves_yaml(monkeypatch):
    """When SMTP env vars are unset, existing email_config from YAML is unchanged."""
    monkeypatch.delenv("ALERT_SMTP_HOST", raising=False)
    monkeypatch.delenv("ALERT_SMTP_PORT", raising=False)
    monkeypatch.delenv("ALERT_SMTP_USERNAME", raising=False)
    monkeypatch.delenv("ALERT_SMTP_PASSWORD", raising=False)
    monkeypatch.delenv("EMAIL_USERNAME", raising=False)
    monkeypatch.delenv("EMAIL_PASSWORD", raising=False)
    config = {"alerts": _base_alerts_dict()}
    apply_env_overrides(config)
    smtp = config["alerts"]["email_config"]["smtp"]
    assert smtp["host"] == "smtp.gmail.com"
    assert smtp["port"] == 587
    assert smtp["username"] == ""
    assert smtp["password"] == ""


def test_smtp_port_invalid_skipped(monkeypatch):
    """Invalid ALERT_SMTP_PORT does not crash; port override is skipped."""
    monkeypatch.setenv("ALERT_SMTP_PORT", "not_a_number")
    try:
        config = {"alerts": _base_alerts_dict()}
        apply_env_overrides(config)
        # Port remains YAML default
        assert config["alerts"]["email_config"]["smtp"]["port"] == 587
    finally:
        monkeypatch.delenv("ALERT_SMTP_PORT", raising=False)


def test_alerts_section_created_when_missing(monkeypatch):
    """When only ALERT_EMAIL is set, alerts dict is created if missing."""
    monkeypatch.setenv("ALERT_EMAIL", "new@example.com")
    try:
        config = {}
        apply_env_overrides(config)
        assert "alerts" in config
        assert config["alerts"]["email"] == "new@example.com"
    finally:
        monkeypatch.delenv("ALERT_EMAIL", raising=False)


def test_email_config_null_normalized_when_smtp_env_set(monkeypatch):
    """When alerts.email_config is null but an SMTP env var is set, it is normalized to a dict so overrides do not raise."""
    monkeypatch.setenv("ALERT_SMTP_HOST", "smtp.example.com")
    try:
        config = {
            "alerts": {
                "enabled": False,
                "email": "you@example.com",
                "cooldown_hours": 6,
                "email_config": None,
            },
        }
        apply_env_overrides(config)
        assert config["alerts"]["email_config"] is not None
        assert config["alerts"]["email_config"]["smtp"]["host"] == "smtp.example.com"
    finally:
        monkeypatch.delenv("ALERT_SMTP_HOST", raising=False)


def test_email_config_unchanged_when_no_smtp_env(monkeypatch):
    """When no SMTP-related env vars are set, email_config is not created or overwritten (guard in alerts.py preserved)."""
    monkeypatch.delenv("ALERT_SENDER", raising=False)
    monkeypatch.delenv("ALERT_SMTP_HOST", raising=False)
    monkeypatch.delenv("ALERT_SMTP_PORT", raising=False)
    monkeypatch.delenv("ALERT_SMTP_USERNAME", raising=False)
    monkeypatch.delenv("ALERT_SMTP_PASSWORD", raising=False)
    monkeypatch.delenv("EMAIL_USERNAME", raising=False)
    monkeypatch.delenv("EMAIL_PASSWORD", raising=False)
    config = {"alerts": {"enabled": False, "email": "y@example.com", "cooldown_hours": 6}}
    apply_env_overrides(config)
    assert "email_config" not in config["alerts"]
