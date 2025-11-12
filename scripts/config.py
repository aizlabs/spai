"""
Configuration Management

Hierarchical configuration loading:
1. Load base.yaml
2. Merge with environment-specific (local.yaml or production.yaml)
3. Override with environment variables
"""

import os
import yaml
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv

# Load .env file at module import time
load_dotenv()


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


def load_config(environment: str = 'local') -> Dict[str, Any]:
    """
    Load configuration with hierarchical merging
    
    Args:
        environment: 'local' or 'production'
    
    Returns:
        Merged configuration dictionary
    """
    config_dir = Path(__file__).parent.parent / 'config'
    
    # Load base config
    base_config = load_yaml(config_dir / 'base.yaml')

    # Load sources configuration
    sources_config = load_yaml(config_dir / 'sources.yaml')
    if sources_config:
        base_config['sources_list'] = sources_config.get('sources', [])

    # Load environment-specific config
    env_config = load_yaml(config_dir / f'{environment}.yaml')

    # Merge configs
    config = deep_merge(base_config, env_config)
    
    # Override with environment variables
    config = apply_env_overrides(config)
    
    # Validate required fields
    validate_config(config)
    
    return config


def apply_env_overrides(config: Dict) -> Dict:
    """Override config with environment variables"""

    # LLM API keys
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')

    if anthropic_key:
        config.setdefault('llm', {})
        config['llm']['anthropic_api_key'] = anthropic_key

    if openai_key:
        config.setdefault('llm', {})
        config['llm']['openai_api_key'] = openai_key

    # Smart provider detection: auto-switch provider based on available API key
    # if configured provider's key is missing but another provider's key exists
    configured_provider = config.get('llm', {}).get('provider', 'openai')

    if configured_provider == 'openai' and not config.get('llm', {}).get('openai_api_key'):
        if config.get('llm', {}).get('anthropic_api_key'):
            config['llm']['provider'] = 'anthropic'
            print("⚠️  Switched provider to 'anthropic' (OPENAI_API_KEY not found but ANTHROPIC_API_KEY is set)")

    elif configured_provider == 'anthropic' and not config.get('llm', {}).get('anthropic_api_key'):
        if config.get('llm', {}).get('openai_api_key'):
            config['llm']['provider'] = 'openai'
            print("⚠️  Switched provider to 'openai' (ANTHROPIC_API_KEY not found but OPENAI_API_KEY is set)")

    # Alerts
    if os.getenv('ALERT_EMAIL'):
        config.setdefault('alerts', {})
        config['alerts']['email'] = os.getenv('ALERT_EMAIL')

    # Override articles per run
    if os.getenv('ARTICLES_PER_RUN'):
        config.setdefault('generation', {})
        config['generation']['articles_per_run'] = int(os.getenv('ARTICLES_PER_RUN'))

    return config


def validate_config(config: Dict):
    """Validate required configuration fields"""
    required_fields = [
        'sources',  # Base config section
        'generation',
        'quality_gate',
        'llm'
    ]

    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required config field: {field}")

    # Validate sources_list is populated (set by load_config)
    if 'sources_list' not in config or not config['sources_list']:
        raise ValueError("Missing or empty sources_list - check config/sources.yaml")

    # Validate LLM config
    if 'provider' not in config['llm']:
        raise ValueError("Missing llm.provider in config")

    if 'models' not in config['llm']:
        raise ValueError("Missing llm.models in config")


def get_config_value(config: Dict, path: str, default: Any = None) -> Any:
    """
    Get nested config value using dot notation
    
    Example:
        get_config_value(config, 'llm.models.generation')
    """
    keys = path.split('.')
    value = config
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    
    return value
