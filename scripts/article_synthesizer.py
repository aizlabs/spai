"""
Article Synthesizer - Step 1 of Two-Step Generation

Synthesizes multiple source articles into one coherent native-level
Spanish article. No level adjustment - focuses on factual accuracy
and natural Spanish expression.
"""

import json
import logging
from typing import Dict, List, Union, cast

from openai import OpenAI
from anthropic import Anthropic

from scripts.models import Topic, SourceArticle, BaseArticle
from scripts.config import AppConfig


class ArticleSynthesizer:
    """Synthesizes native-level Spanish articles from multiple sources"""

    def __init__(self, config: AppConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger.getChild('ArticleSynthesizer')

        # Initialize LLM client
        provider = config.llm.provider

        if provider == 'anthropic':
            if not config.llm.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY is required for Anthropic provider")

            self.llm_client: Union[Anthropic, OpenAI] = Anthropic(api_key=config.llm.anthropic_api_key)
            self.logger.info("Initialized Anthropic client for synthesis")

        elif provider == 'openai':
            if not config.llm.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required for OpenAI provider")

            self.llm_client = OpenAI(api_key=config.llm.openai_api_key)
            self.logger.info("Initialized OpenAI client for synthesis")

        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    def synthesize(self, topic: Topic, sources: List[SourceArticle]) -> BaseArticle:
        """
        Synthesize native-level article from multiple sources

        Args:
            topic: Topic dict from discovery with 'title' key
            sources: List of source content dicts with 'source' and 'text' keys

        Returns:
            Base article dict with:
            - title (Spanish)
            - content (native-level Spanish, 300-400 words)
            - summary (Spanish, one sentence)
            - reading_time (int, estimated minutes)
            - topic (metadata)
            - sources (metadata, list of source names)
        """
        from scripts import prompts

        prompt = prompts.get_synthesis_prompt(topic, sources)

        self.logger.info(f"Synthesizing base article for topic: {topic.title}")

        response = self._call_llm(prompt)
        article = self._parse_response(response, topic, sources)

        self.logger.info(f"Synthesized base article: {article.title}")
        self.logger.debug(f"Base article word count: {len(article.content.split())}")

        return article

    def _call_llm(self, prompt: str, temperature: float = 0.3) -> str:
        """Call LLM with prompt for synthesis"""
        model = self.config.llm.models.generation
        max_tokens = self.config.llm.max_tokens
        provider = self.config.llm.provider

        try:
            if provider == 'anthropic':
                client = cast(Anthropic, self.llm_client)
                response = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}]
                )
                # Extract text from first content block (should be TextBlock)
                if response.content and len(response.content) > 0:
                    first_block = response.content[0]
                    if hasattr(first_block, 'text'):
                        return first_block.text
                    else:
                        raise ValueError(f"Unexpected content block type: {type(first_block)}")
                else:
                    raise ValueError("Empty response from Anthropic API")

            elif provider == 'openai':
                client = cast(OpenAI, self.llm_client)  # type: ignore[assignment]
                response = client.chat.completions.create(  # type: ignore[attr-defined]
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                content = response.choices[0].message.content
                if content is None:
                    raise ValueError("Empty response from OpenAI API")
                return content  # type: ignore[no-any-return]

            else:
                raise ValueError(f"Unknown provider: {provider}")

        except Exception as e:
            self.logger.error(f"LLM API call failed during synthesis: {e}")
            raise

    def _parse_response(
        self,
        response: str,
        topic: Topic,
        sources: List[SourceArticle]
    ) -> BaseArticle:
        """Parse LLM JSON response into base article dict"""

        # Extract JSON from response (handle markdown code blocks)
        json_str = response

        if '```json' in response:
            json_str = response.split('```json')[1].split('```')[0]
        elif '```' in response:
            json_str = response.split('```')[1].split('```')[0]

        try:
            parsed = json.loads(json_str.strip())

            # Add metadata
            parsed['topic'] = topic.model_dump()  # Convert Pydantic model to dict for BaseArticle constructor
            parsed['sources'] = [
                {'name': s.source, 'url': s.url} if s.url else {'name': s.source}
                for s in sources
            ]

            # Create BaseArticle instance, Pydantic handles validation and type coercion
            return BaseArticle(**parsed)

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse synthesis response as JSON: {e}")
            self.logger.debug(f"Response was: {response[:500]}")
            raise ValueError(f"LLM returned invalid JSON during synthesis: {e}")
        except Exception as e:
            self.logger.error(f"Invalid base article structure or Pydantic validation error: {e}")
            raise ValueError(f"Invalid base article structure or Pydantic validation error: {e}")
