"""
Configuration Management

Hierarchical configuration loading:
1. Load base.yaml
2. Merge with environment-specific (local.yaml or production.yaml)
3. Override with environment variables
"""

import os
import yaml
from typing import Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

from scripts.models import AlertsConfig, LLMConfig, TwoStepSynthesisConfig, LLMModelsConfig


# Load .env file at module import time
load_dotenv()


class GenerationConfig(BaseModel):
    articles_per_run: int = Field(..., ge=1)
    levels: List[str] = Field(..., min_length=1)
    target_word_count: Dict[str, int]
    two_step_synthesis: TwoStepSynthesisConfig


class QualityGateConfig(BaseModel):
    min_score: float = Field(..., ge=0, le=10)
    max_attempts: int = Field(..., ge=1)


class SourceConfig(BaseModel):
    max_words_per_source: int = Field(..., ge=50)
    min_words_per_source: int = Field(..., ge=10)
    max_sources_per_topic: int = Field(..., ge=1)
    fetch_timeout: int = Field(default=10, ge=1)


class AppConfig(BaseModel):
    environment: str = "local"
    sources_list: List[Dict[str, str]] = Field(default_factory=list)
    generation: GenerationConfig
    llm: LLMConfig
    quality_gate: QualityGateConfig
    sources: SourceConfig
    output: Dict[str, str] = Field(default_factory=dict)
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)
    logging: Dict[str, Any] = Field(default_factory=dict)
    discovery: Dict[str, Any] = Field(default_factory=dict)
    ranking: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode='after')
    def validate_llm_keys(self) -> 'AppConfig':
        if self.llm.provider == 'openai' and not self.llm.openai_api_key:
            if self.llm.anthropic_api_key:
                self.llm.provider = 'anthropic'
                print("⚠️  Switched provider to 'anthropic' (OPENAI_API_KEY not found but ANTHROPIC_API_KEY is set)")
            else:
                raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
        elif self.llm.provider == 'anthropic' and not self.llm.anthropic_api_key:
            if self.llm.openai_api_key:
                self.llm.provider = 'openai'
                print("⚠️  Switched provider to 'openai' (ANTHROPIC_API_KEY not found but OPENAI_API_KEY is set)")
            else:
                raise ValueError("ANTHROPIC_API_KEY is required for Anthropic provider")
        return self


def load_yaml(filepath: Path) -> Dict[str, Any]:
    """Load YAML file"""
    if not filepath.exists():
        return {}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def deep_merge(base: Dict, override: Dict) -> Dict:
    """Deep merge two dictionaries"""
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def load_config(environment: str = 'local') -> AppConfig:
    """
    Load configuration with hierarchical merging and Pydantic validation

    Args:
        environment: 'local' or 'production'

    Returns:
        AppConfig instance
    """
    config_dir = Path(__file__).parent.parent / 'config'

    # Load base config
    base_config_dict = load_yaml(config_dir / 'base.yaml')

    # Load sources configuration
    sources_config_dict = load_yaml(config_dir / 'sources.yaml')
    if sources_config_dict:
        base_config_dict['sources_list'] = sources_config_dict.get('sources', [])

    # Load environment-specific config
    env_config_dict = load_yaml(config_dir / f'{environment}.yaml')

    # Merge configs
    merged_config_dict = deep_merge(base_config_dict, env_config_dict)

    # Override with environment variables
    final_config_dict = apply_env_overrides(merged_config_dict)

    # Instantiate Pydantic model for validation and type-safe access
    return AppConfig(**final_config_dict)


def apply_env_overrides(config_dict: Dict) -> Dict:
    """Override config dictionary with environment variables before Pydantic validation"""

    # LLM API keys
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')

    if anthropic_key:
        config_dict.setdefault('llm', {})
        config_dict['llm']['anthropic_api_key'] = anthropic_key

    if openai_key:
        config_dict.setdefault('llm', {})
        config_dict['llm']['openai_api_key'] = openai_key

    # Override articles per run
    articles_per_run = os.getenv('ARTICLES_PER_RUN')
    if articles_per_run:
        config_dict.setdefault('generation', {})
        config_dict['generation']['articles_per_run'] = int(articles_per_run)

    # Override alert email
    alert_email = os.getenv('ALERT_EMAIL')
    if alert_email:
        config_dict.setdefault('alerts', {})
        config_dict['alerts']['email'] = alert_email

    # Override alerts.enabled from ALERTS_ENABLED (CI)
    alerts_enabled = os.getenv('ALERTS_ENABLED')
    if alerts_enabled is not None and alerts_enabled != '':
        normalized = str(alerts_enabled).strip().lower()
        if normalized == 'true':
            config_dict.setdefault('alerts', {})
            config_dict['alerts']['enabled'] = True
        elif normalized == 'false':
            config_dict.setdefault('alerts', {})
            config_dict['alerts']['enabled'] = False

    # Override alerts.email_config from env only when at least one SMTP-related var is set.
    # Otherwise we would inject a non-None email_config and bypass the "no email configured" guard in alerts.py.
    _sender = os.getenv('ALERT_SENDER')
    _smtp_host = os.getenv('ALERT_SMTP_HOST')
    _smtp_port = os.getenv('ALERT_SMTP_PORT')
    _smtp_user = os.getenv('ALERT_SMTP_USERNAME') or os.getenv('EMAIL_USERNAME')
    _smtp_pass = os.getenv('ALERT_SMTP_PASSWORD') or os.getenv('EMAIL_PASSWORD')
    if _sender or _smtp_host or _smtp_port or _smtp_user or _smtp_pass:
        config_dict.setdefault('alerts', {})
        alerts = config_dict['alerts']
        if alerts.get('email_config') is None:
            alerts['email_config'] = {}
        email_config = alerts['email_config']
        if email_config.get('smtp') is None:
            email_config['smtp'] = {}
        email_config.setdefault('smtp', {})

        if _sender:
            email_config['from'] = _sender
        if _smtp_host:
            email_config['smtp']['host'] = _smtp_host
        if _smtp_port:
            try:
                email_config['smtp']['port'] = int(_smtp_port.strip())
            except ValueError:
                pass
        if _smtp_user:
            email_config['smtp']['username'] = _smtp_user
        if _smtp_pass:
            email_config['smtp']['password'] = _smtp_pass

    # Override Telegram alert config from env.
    # If both required values are present, enable Telegram alerts automatically.
    _telegram_bot_token = os.getenv('ALERT_TELEGRAM_BOT_TOKEN')
    _telegram_chat_id = os.getenv('ALERT_TELEGRAM_CHAT_ID')
    if _telegram_bot_token or _telegram_chat_id:
        config_dict.setdefault('alerts', {})
        alerts = config_dict['alerts']
        if alerts.get('telegram') is None:
            alerts['telegram'] = {}
        telegram_config = alerts['telegram']

        if _telegram_bot_token:
            telegram_config['bot_token'] = _telegram_bot_token
        if _telegram_chat_id:
            telegram_config['chat_id'] = _telegram_chat_id

        has_complete_telegram_config = bool(_telegram_bot_token and _telegram_chat_id)
        if has_complete_telegram_config:
            telegram_config['enabled'] = True

            # Auto-enable alert delivery for CI secret-only Telegram setup unless explicitly disabled.
            if not (alerts_enabled is not None and str(alerts_enabled).strip().lower() == 'false'):
                alerts['enabled'] = True

    return config_dict





def get_config_value(config: AppConfig, path: str, default: Any = None) -> Any:
    """
    Get nested config value using dot notation
    
    Example:
        get_config_value(config, 'llm.models.generation')
    """
    keys = path.split('.')
    value = config
    
    for key in keys:
        if hasattr(value, key):
            value = getattr(value, key)
        else:
            return default
    
    return value
