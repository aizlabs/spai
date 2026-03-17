"""
Level Adapter - Step 2 of Two-Step Generation

Adapts base (native-level) articles to specific CEFR levels.
Uses different strategies per level:
- A2: Glossing strategy with strict simplification
- B1: Light adaptation with vocabulary support
"""

import logging
from typing import Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from scripts.models import BaseArticle, AdaptedArticle, Topic
from scripts.config import AppConfig
from scripts.text_utils import ensure_vocabulary_bolded
from scripts.llm_factory import create_chat_model, with_structured_output


class LevelAdapter:
    """Adapts articles to specific CEFR levels"""

    def __init__(self, config: AppConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger.getChild('LevelAdapter')
        self.llm_config = config.llm.model_dump()
        self.generation_config = config.generation.model_dump()

        self.temperature = self.llm_config.get('temperature', 0.3)
        self._init_chains()

    def adapt_to_level(
        self,
        base_article: BaseArticle,
        level: str,
        feedback: Optional[List[str]] = None
    ) -> AdaptedArticle:
        """
        Adapt base article to target CEFR level

        Args:
            base_article: Article from ArticleSynthesizer with native-level Spanish
            level: 'A2' or 'B1'
            feedback: Optional list of issues from quality gate (for regeneration)

        Returns:
            Adapted article dict with:
            - title (level-appropriate)
            - content (adapted to level)
            - vocabulary (glossary)
            - summary (level-appropriate)
            - reading_time (int)
            - level (metadata)
            - topic (metadata)
            - sources (metadata)
            - base_article (stored for regeneration)
        """
        if level == 'A2':
            return self.adapt_to_a2(base_article, feedback)
        elif level == 'B1':
            return self.adapt_to_b1(base_article, feedback)
        else:
            raise ValueError(f"Unsupported level: {level}. Supported: A2, B1")

    def adapt_to_a2(
        self,
        base_article: BaseArticle,
        feedback: Optional[List[str]] = None
    ) -> AdaptedArticle:
        """
        Adapt to A2 using glossing strategy

        Uses existing A2_NEWS_PROCESSING_INSTRUCTIONS from prompts module
        """
        from scripts import prompts

        prompt = prompts.get_a2_adaptation_prompt(base_article, feedback)

        self.logger.info(f"Adapting to A2: {base_article.title}")
        if feedback:
            self.logger.debug(f"A2 adaptation with feedback: {len(feedback)} issues")

        response = self._call_llm(prompt, level='A2')
        article = self._build_adapted_article(response, base_article, 'A2')

        word_count = len(article.content.split())
        vocab_count = len(article.vocabulary)
        self.logger.info(f"A2 article adapted: {word_count} words, {vocab_count} vocabulary items")

        return article

    def adapt_to_b1(
        self,
        base_article: BaseArticle,
        feedback: Optional[List[str]] = None
    ) -> AdaptedArticle:
        """
        Adapt to B1 with light modifications

        Similar structure to A2 but less restrictive.
        Uses B1 adaptation prompt (similar to A2, will be refined externally).
        """
        from scripts import prompts

        prompt = prompts.get_b1_adaptation_prompt(base_article, feedback)

        self.logger.info(f"Adapting to B1: {base_article.title}")
        if feedback:
            self.logger.debug(f"B1 adaptation with feedback: {len(feedback)} issues")

        response = self._call_llm(prompt, level='B1')
        article = self._build_adapted_article(response, base_article, 'B1')

        word_count = len(article.content.split())
        vocab_count = len(article.vocabulary)
        self.logger.info(f"B1 article adapted: {word_count} words, {vocab_count} vocabulary items")

        return article

    def _init_chains(self) -> None:
        """Initialize LangChain structured-output chains for A2 and B1 adaptation."""
        # Use adaptation model (can be cheaper than generation model)
        model_name = self.llm_config['models'].get(
            'adaptation',
            self.llm_config['models']['generation'],
        )
        chat_model = create_chat_model(self.llm_config, model_name, self.temperature)

        class AdaptationResponse(BaseModel):
            title: str = Field(..., description="Level-appropriate title")
            content: str = Field(..., description="Level-adapted content")
            vocabulary: Dict[str, str] = Field(
                default_factory=dict,
                description="Vocabulary glossary mapping term -> translation/explanation",
            )
            summary: str = Field(..., description="Level-appropriate summary")
            reading_time: int = Field(..., description="Estimated reading time in minutes")

        self._adaptation_model = AdaptationResponse
        structured_llm = with_structured_output(chat_model, AdaptationResponse)

        # Prompt template is shared; we inject the full prompt string from prompts.py
        self.prompt_template = ChatPromptTemplate.from_messages(
            [("user", "{prompt}")]
        )
        self.chain = self.prompt_template | structured_llm

    def _call_llm(self, prompt: str, level: str) -> BaseModel:
        """Call LLM for level adaptation and return structured response."""
        try:
            return self.chain.invoke({"prompt": prompt})
        except Exception as e:
            self.logger.error(f"LLM API call failed during {level} adaptation: {e}")
            raise

    def _build_adapted_article(
        self,
        response: BaseModel,
        base_article: BaseArticle,
        level: str
    ) -> AdaptedArticle:
        """Convert structured adaptation response into AdaptedArticle with metadata."""
        try:
            parsed = response.model_dump()

            parsed["content"] = ensure_vocabulary_bolded(
                parsed.get("content", ""),
                parsed.get("vocabulary") or {},
            )

            parsed['level'] = level
            parsed['topic'] = base_article.topic.model_dump() if base_article.topic else None
            parsed['sources'] = [s.model_dump() for s in base_article.sources]
            parsed['base_article'] = base_article.model_dump()

            return AdaptedArticle(**parsed)
        except Exception as e:
            self.logger.error(f"Invalid adapted article structure or Pydantic validation error: {e}")
            raise ValueError(f"Invalid adapted article structure or Pydantic validation error: {e}")

