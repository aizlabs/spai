"""
Level Adapter - Step 2 of Two-Step Generation

Adapts base (native-level) articles to specific CEFR levels.
Uses different strategies per level:
- A2: Glossing strategy with strict simplification
- B1: Light adaptation with vocabulary support
"""

import json
import logging
from typing import Dict, List, Optional

from scripts.models import BaseArticle, AdaptedArticle
from scripts.config import AppConfig


class LevelAdapter:
    """Adapts articles to specific CEFR levels"""

    def __init__(self, config: AppConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger.getChild('LevelAdapter')
        self.llm_config = config.llm.model_dump()
        self.generation_config = config.generation.model_dump()

        # Initialize LLM client
        self._init_llm_client()

    def _init_llm_client(self):
        """Initialize LLM client (Anthropic or OpenAI) based on config"""
        provider = self.llm_config['provider']

        if provider == 'anthropic':
            api_key = self.llm_config.get('anthropic_api_key')
            if not api_key:
                raise ValueError("Missing ANTHROPIC_API_KEY in config/environment")

            from anthropic import Anthropic
            self.llm_client = Anthropic(api_key=api_key)
            self.logger.info("Initialized Anthropic client for level adaptation")

        elif provider == 'openai':
            api_key = self.llm_config.get('openai_api_key')
            if not api_key:
                raise ValueError("Missing OPENAI_API_KEY in config/environment")

            from openai import OpenAI
            self.llm_client = OpenAI(api_key=api_key)
            self.logger.info("Initialized OpenAI client for level adaptation")

        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

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

        response = self._call_llm(prompt)
        article = self._parse_adaptation_response(
            response, base_article, 'A2'
        )

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

        response = self._call_llm(prompt)
        article = self._parse_adaptation_response(
            response, base_article, 'B1'
        )

        word_count = len(article.content.split())
        vocab_count = len(article.vocabulary)
        self.logger.info(f"B1 article adapted: {word_count} words, {vocab_count} vocabulary items")

        return article

    def _call_llm(self, prompt: str, temperature: float = 0.3) -> str:
        """Call LLM for level adaptation"""
        # Use adaptation model (can be cheaper than generation model)
        model = self.llm_config['models'].get(
            'adaptation',
            self.llm_config['models']['generation']
        )
        max_tokens = self.llm_config.get('max_tokens', 4096)
        provider = self.llm_config['provider']

        try:
            if provider == 'anthropic':
                response = self.llm_client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text

            elif provider == 'openai':
                response = self.llm_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content

            else:
                raise ValueError(f"Unknown provider: {provider}")

        except Exception as e:
            self.logger.error(f"LLM API call failed during level adaptation: {e}")
            raise

    def _parse_adaptation_response(
        self,
        response: str,
        base_article: BaseArticle,
        level: str
    ) -> AdaptedArticle:
        """Parse adapted article response and merge with base metadata"""

        # Extract JSON from response (handle markdown code blocks)
        json_str = response

        if '```json' in response:
            json_str = response.split('```json')[1].split('```')[0]
        elif '```' in response:
            json_str = response.split('```')[1].split('```')[0]

        try:
            parsed = json.loads(json_str.strip())

            # Add level metadata
            parsed['level'] = level

            # Inherit metadata from base article
            parsed['topic'] = base_article.topic.model_dump() if base_article.topic else None
            parsed['sources'] = base_article.sources

            # Store base article for regeneration
            parsed['base_article'] = base_article.model_dump()

            # Create AdaptedArticle instance, Pydantic handles validation and type coercion
            return AdaptedArticle(**parsed)

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse adaptation response as JSON: {e}")
            self.logger.debug(f"Response was: {response[:500]}")
            raise ValueError(f"LLM returned invalid JSON during {level} adaptation: {e}")
        except Exception as e:
            self.logger.error(f"Invalid adapted article structure or Pydantic validation error: {e}")
            raise ValueError(f"Invalid adapted article structure or Pydantic validation error: {e}")
