"""
Content Generator Component

Generates original Spanish articles by synthesizing multiple sources using LLM.
Supports regeneration with feedback for quality improvement.
"""

import json
import logging
from typing import Dict, List, Optional

from scripts import prompts


class ContentGenerator:
    """Generates articles from multiple sources using LLM"""

    def __init__(self, config: Dict, logger: logging.Logger):
        self.config = config
        self.logger = logger.getChild('ContentGenerator')

        self.generation_config = config['generation']
        self.llm_config = config['llm']

        # Initialize LLM client based on provider
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
            self.logger.info("Initialized Anthropic client")

        elif provider == 'openai':
            api_key = self.llm_config.get('openai_api_key')
            if not api_key:
                raise ValueError("Missing OPENAI_API_KEY in config/environment")

            from openai import OpenAI
            self.llm_client = OpenAI(api_key=api_key)
            self.logger.info("Initialized OpenAI client")

        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    def generate_article(
        self,
        topic: Dict,
        sources: List[Dict],
        level: str
    ) -> Dict:
        """
        Generate initial article (no feedback)

        Args:
            topic: Topic dict from discovery
            sources: List of source content dicts
            level: 'A2' or 'B1'

        Returns:
            Article dict with title, content, vocabulary, etc.
        """
        # Get word count with fallback for unknown levels
        word_count = self.generation_config['target_word_count'].get(level, 250)

        # Get prompt from centralized prompts module
        prompt = prompts.get_generation_prompt(topic, sources, level, word_count)

        self.logger.info(f"Generating {level} article for topic: {topic['title']}")

        response = self._call_llm(prompt)

        article = self._parse_response(response, topic, level, sources)

        self.logger.info(f"Generated {level} article: {article['title']}")

        return article

    def regenerate_with_feedback(
        self,
        topic: Dict,
        sources: List[Dict],
        level: str,
        previous_attempt: Dict,
        issues: List[str]
    ) -> Dict:
        """
        Regenerate article with feedback about issues

        Args:
            topic: Topic dict
            sources: Source content
            level: CEFR level
            previous_attempt: Previous article that failed
            issues: List of specific issues to fix

        Returns:
            New improved article
        """
        # Get word count with fallback for unknown levels
        word_count = self.generation_config['target_word_count'].get(level, 250)

        feedback = {
            'previous_title': previous_attempt['title'],
            'previous_content': previous_attempt['content'],
            'issues': issues
        }

        # Get regeneration prompt from centralized prompts module
        prompt = prompts.get_regeneration_prompt(
            topic, sources, level, word_count, feedback
        )

        self.logger.info(f"Regenerating {level} article with feedback")
        self.logger.debug(f"Issues to fix: {', '.join(issues[:3])}")

        response = self._call_llm(prompt, temperature=0.4)  # Slightly higher temp

        article = self._parse_response(response, topic, level, sources)

        self.logger.info(f"Regenerated {level} article: {article['title']}")

        return article

    def _call_llm(self, prompt: str, temperature: float = 0.3) -> str:
        """Call LLM with prompt"""
        model = self.llm_config['models']['generation']
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
            self.logger.error(f"LLM API call failed: {e}")
            raise

    def _parse_response(
        self,
        response: str,
        topic: Dict,
        level: str,
        sources: List[Dict]
    ) -> Dict:
        """Parse LLM JSON response into article dict"""

        # Extract JSON from response (handle markdown code blocks)
        json_str = response

        if '```json' in response:
            json_str = response.split('```json')[1].split('```')[0]
        elif '```' in response:
            json_str = response.split('```')[1].split('```')[0]

        try:
            parsed = json.loads(json_str.strip())

            # Add metadata
            parsed['topic'] = topic
            parsed['level'] = level
            parsed['sources'] = [s['source'] for s in sources]

            # Ensure vocabulary is present
            if 'vocabulary' not in parsed or not parsed['vocabulary']:
                self.logger.warning("No vocabulary in article, setting empty dict")
                parsed['vocabulary'] = {}

            # Validate required fields
            required = ['title', 'content', 'summary', 'reading_time']
            for field in required:
                if field not in parsed:
                    self.logger.error(f"Missing required field: {field}")
                    raise ValueError(f"Missing required field: {field}")

            return parsed

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {e}")
            self.logger.debug(f"Response was: {response[:500]}")

            # Raise exception instead of returning fallback to avoid wasting regeneration attempts
            raise ValueError(f"LLM returned invalid JSON: {e}")

        except ValueError as e:
            self.logger.error(f"Invalid article structure: {e}")

            # Raise exception instead of returning fallback to avoid wasting regeneration attempts
            raise ValueError(f"Invalid article structure: {e}")
