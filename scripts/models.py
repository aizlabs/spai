"""
Pydantic models for type-safe data structures

These models ensure data integrity throughout the pipeline and provide
automatic validation, serialization, and clear type hints.
"""

from typing import Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


# =============================================================================
# Topic Discovery Models
# =============================================================================


class Topic(BaseModel):
    """Topic from discovery phase"""
    title: str = Field(..., min_length=1, description="Topic title")
    sources: List[str] = Field(..., min_length=1, description="Source names")
    mentions: int = Field(..., ge=1, description="Number of mentions across sources")
    score: float = Field(..., ge=0, description="Ranking score")
    keywords: Optional[List[str]] = Field(default=None, description="Optional keywords")
    urls: List[str] = Field(default_factory=list, description="URLs for fetching article content")

    model_config = ConfigDict(frozen=False)  # Allow mutation during pipeline


class SourceArticle(BaseModel):
    """Fetched source article"""
    source: str = Field(..., min_length=1, description="Source name (e.g., 'El País')")
    text: str = Field(..., min_length=50, description="Article text content")
    word_count: int = Field(..., ge=0, description="Word count")
    url: Optional[str] = Field(default=None, description="Optional source URL")

    model_config = ConfigDict(frozen=False)


class SourceMetadata(BaseModel):
    """Structured source metadata for articles"""

    name: str = Field(..., min_length=1, description="Source name")
    url: Optional[str] = Field(default=None, description="Optional source URL")

    model_config = ConfigDict(frozen=False)


# =============================================================================
# Article Models
# =============================================================================


class BaseArticle(BaseModel):
    """Native-level Spanish article from ArticleSynthesizer (Step 1)"""
    title: str = Field(..., min_length=1, max_length=200, description="Article title")
    content: str = Field(..., min_length=100, description="Full article content")
    summary: str = Field(..., min_length=10, max_length=500, description="One-sentence summary")
    reading_time: int = Field(..., ge=1, le=30, description="Estimated reading time in minutes")

    # Metadata from synthesis
    topic: Optional[Topic] = Field(default=None, description="Source topic")
    sources: List[SourceMetadata] = Field(default_factory=list, description="Source metadata used")

    @field_validator('reading_time', mode='before')
    @classmethod
    def coerce_reading_time(cls, v):
        """Convert string to int if needed"""
        if isinstance(v, str):
            try:
                return int(v)
            except ValueError:
                return 3  # Default fallback
        return v

    @field_validator('sources', mode='before')
    @classmethod
    def coerce_sources(cls, v):
        """Normalize legacy or mixed source inputs into structured metadata.

        Accepts older payloads (e.g., list of strings) and mixed dicts from
        serialized `SourceArticle` data, and coerces them into `{name, url}`
        mappings so Pydantic can build `SourceMetadata` consistently.
        """
        if v is None:
            return []

        def to_metadata(item: Union[str, Dict, 'SourceMetadata']):
            if isinstance(item, str):
                return {'name': item}
            if isinstance(item, dict) and 'source' in item and 'text' in item:
                # Handle accidental SourceArticle dicts
                name = item.get('source') or item.get('name')
                url = item.get('url')
                return {'name': name, 'url': url}
            if isinstance(item, dict):
                return item
            return item

        if isinstance(v, list):
            return [to_metadata(item) for item in v]

        return v

    model_config = ConfigDict(frozen=False)


class VocabularyItem(BaseModel):
    """Single vocabulary glossary item"""
    spanish: str = Field(..., description="Spanish term")
    english: str = Field(..., description="English translation")
    explanation: Optional[str] = Field(default=None, description="Spanish A2/B1 explanation")


class AdaptedArticle(BaseModel):
    """Level-adapted article from LevelAdapter (Step 2)"""
    title: str = Field(..., min_length=1, max_length=150, description="Adapted title")
    content: str = Field(..., min_length=50, description="Level-adapted content")
    summary: str = Field(..., min_length=10, max_length=500, description="Level-adapted summary")
    reading_time: int = Field(..., ge=1, le=30, description="Reading time in minutes")

    # Vocabulary glossary (key: spanish term, value: translation + explanation)
    vocabulary: Dict[str, str] = Field(default_factory=dict, description="Vocabulary glossary")

    # Level and metadata
    level: str = Field(..., pattern="^(A2|B1)$", description="CEFR level")
    topic: Optional[Topic] = Field(default=None, description="Source topic")
    sources: List[SourceMetadata] = Field(default_factory=list, description="Source metadata")

    # Base article stored for regeneration
    base_article: Optional[BaseArticle] = Field(default=None, description="Base article for regeneration")

    @field_validator('reading_time', mode='before')
    @classmethod
    def coerce_reading_time(cls, v):
        """Convert string to int if needed"""
        if isinstance(v, str):
            try:
                return int(v)
            except ValueError:
                # Default based on level if available
                return 2  # Fallback
        return v

    @field_validator('sources', mode='before')
    @classmethod
    def coerce_sources(cls, v):
        """Normalize legacy or mixed source inputs into structured metadata.

        Accepts older payloads (e.g., list of strings) and mixed dicts from
        serialized `SourceArticle` data, and coerces them into `{name, url}`
        mappings so Pydantic can build `SourceMetadata` consistently.
        """
        if v is None:
            return []

        def to_metadata(item: Union[str, Dict, 'SourceMetadata']):
            if isinstance(item, str):
                return {'name': item}
            if isinstance(item, dict) and 'source' in item and 'text' in item:
                name = item.get('source') or item.get('name')
                url = item.get('url')
                return {'name': name, 'url': url}
            if isinstance(item, dict):
                return item
            return item

        if isinstance(v, list):
            return [to_metadata(item) for item in v]

        return v

    model_config = ConfigDict(frozen=False)


# =============================================================================
# Quality Gate Models
# =============================================================================


class QualityResult(BaseModel):
    """Result from quality evaluation"""
    passed: bool = Field(..., description="Whether article passed quality gate")
    score: float = Field(..., ge=0, le=10, description="Overall quality score (0-10)")
    issues: List[str] = Field(default_factory=list, description="Issues found")
    strengths: List[str] = Field(default_factory=list, description="Article strengths")
    attempts: int = Field(..., ge=1, description="Number of generation attempts")

    # Detailed scores (optional)
    grammar_score: Optional[float] = Field(default=None, ge=0, le=4)
    educational_score: Optional[float] = Field(default=None, ge=0, le=3)
    content_score: Optional[float] = Field(default=None, ge=0, le=2)
    level_score: Optional[float] = Field(default=None, ge=0, le=1)

    model_config = ConfigDict(frozen=False)


# =============================================================================
# Configuration Models
# =============================================================================


class TwoStepSynthesisConfig(BaseModel):
    """Configuration for two-step synthesis"""
    enabled: bool = Field(default=True, description="Enable two-step synthesis")
    save_base_article: bool = Field(default=False, description="Save base articles to disk")
    base_article_path: str = Field(default="./output/base_articles/", description="Path for base articles")
    regeneration_strategy: str = Field(
        default="adaptation_only",
        pattern="^(adaptation_only|full_pipeline)$",
        description="Regeneration strategy"
    )


class LLMModelsConfig(BaseModel):
    """LLM model configuration"""
    generation: str = Field(..., description="Model for synthesis (Step 1)")
    adaptation: str = Field(..., description="Model for adaptation (Step 2)")
    quality_check: str = Field(..., description="Model for quality evaluation")


class LLMConfig(BaseModel):
    """LLM configuration"""
    provider: str = Field(..., pattern="^(openai|anthropic)$", description="LLM provider")
    models: LLMModelsConfig
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    temperature: float = Field(default=0.3, ge=0, le=2, description="Temperature for generation")
    max_tokens: int = Field(default=4096, ge=100, le=100000, description="Max tokens")


# =============================================================================
# Helper Functions
# =============================================================================


def dict_to_topic(data: Dict) -> Topic:
    """Convert dict to Topic model with validation"""
    return Topic(**data)


def dict_to_base_article(data: Dict) -> BaseArticle:
    """Convert dict to BaseArticle model with validation"""
    # Convert nested topic if present
    if 'topic' in data and isinstance(data['topic'], dict):
        data['topic'] = Topic(**data['topic'])
    return BaseArticle(**data)


def dict_to_adapted_article(data: Dict) -> AdaptedArticle:
    """Convert dict to AdaptedArticle model with validation"""
    # Convert nested structures
    if 'topic' in data and data['topic'] and isinstance(data['topic'], dict):
        data['topic'] = Topic(**data['topic'])
    if 'base_article' in data and data['base_article'] and isinstance(data['base_article'], dict):
        data['base_article'] = BaseArticle(**data['base_article'])
    return AdaptedArticle(**data)
