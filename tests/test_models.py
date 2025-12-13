import pytest
from pydantic import ValidationError

from scripts.models import LLMConfig, LLMModelsConfig


def _valid_models() -> LLMModelsConfig:
    return LLMModelsConfig(
        generation="gpt-4o",
        adaptation="gpt-4o",
        quality_check="gpt-4o-mini",
    )


@pytest.mark.parametrize(
    "field_name, value",
    [
        ("temperature", 1.1),
        ("quality_temperature", 1.5),
    ],
)
def test_llm_config_enforces_temperature_upper_bound(field_name, value):
    base_kwargs = dict(
        provider="openai",
        models=_valid_models(),
        temperature=0.3,
        quality_temperature=0.1,
        max_tokens=4096,
    )

    base_kwargs[field_name] = value

    with pytest.raises(ValidationError):
        LLMConfig(**base_kwargs)
