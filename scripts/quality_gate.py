"""
Quality Gate Component

Evaluates article quality using LLM judge.
Regenerates articles that fail, with feedback for improvement.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple

from scripts import prompts
from scripts.models import AdaptedArticle, Topic, SourceArticle, QualityResult
from scripts.config import AppConfig


class QualityGate:
    """Quality checking with smart regeneration"""

    def __init__(self, config: AppConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger.getChild('QualityGate')

        self.quality_config = config.quality_gate.model_dump()
        self.min_score = self.quality_config['min_score']
        self.max_attempts = self.quality_config['max_attempts']
        self.llm_config = config.llm.model_dump()

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
            self.logger.info("Initialized Anthropic client for quality checks")

        elif provider == 'openai':
            api_key = self.llm_config.get('openai_api_key')
            if not api_key:
                raise ValueError("Missing OPENAI_API_KEY in config/environment")

            from openai import OpenAI
            self.llm_client = OpenAI(api_key=api_key)
            self.logger.info("Initialized OpenAI client for quality checks")

        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    def check_and_improve(
        self,
        article: AdaptedArticle,
        generator,
        topic: Topic,
        sources: List[SourceArticle]
    ) -> Tuple[Optional[AdaptedArticle], QualityResult]:
        """
        Check quality and regenerate if needed

        Args:
            article: Article to check
            generator: ContentGenerator instance (for regeneration)
            topic: Original topic dict
            sources: Original source content

        Returns:
            (final_article or None, quality_result)
        """
        attempt_history = []
        current_article = article
        level = article.level

        for attempt in range(1, self.max_attempts + 1):
            self.logger.info(f"Quality check attempt {attempt}/{self.max_attempts}")

            # Evaluate current version
            result_dict = self._evaluate(current_article) # _evaluate returns Dict for now

            attempt_history.append({
                'attempt': attempt,
                'score': result_dict['total_score'],
                'issues': result_dict['issues']
            })

            passed = result_dict['total_score'] >= self.min_score

            if passed:
                self.logger.info(f"✅ Passed on attempt {attempt} (score: {result_dict['total_score']:.1f}/{self.min_score})")
                return current_article, QualityResult(
                    passed=True,
                    score=result_dict['total_score'],
                    issues=[],
                    strengths=result_dict.get('strengths', []),
                    attempts=attempt,
                    grammar_score=result_dict.get('grammar_score'),
                    educational_score=result_dict.get('educational_score'),
                    content_score=result_dict.get('content_score'),
                    level_score=result_dict.get('level_score')
                )

            # Failed - should we try again?
            if attempt >= self.max_attempts:
                self.logger.warning(
                    f"❌ Failed after {attempt} attempts (final: {result_dict['total_score']:.1f}/{self.min_score})"
                )
                return None, QualityResult(
                    passed=False,
                    score=result_dict['total_score'],
                    issues=result_dict['issues'],
                    strengths=result_dict.get('strengths', []),
                    attempts=attempt,
                    grammar_score=result_dict.get('grammar_score'),
                    educational_score=result_dict.get('educational_score'),
                    content_score=result_dict.get('content_score'),
                    level_score=result_dict.get('level_score')
                )

            # Regenerate with feedback
            self.logger.info(
                f"🔄 Regenerating (attempt {attempt + 1}) - score was {result_dict['total_score']:.1f}/{self.min_score}"
            )
            self.logger.debug(f"   Issues: {', '.join(result_dict['issues'][:3])}")

            try:
                current_article = generator.regenerate_with_feedback(
                    topic=topic,
                    sources=sources,
                    level=level,
                    previous_attempt=current_article,
                    issues=result_dict['issues']
                )
            except Exception as e:
                self.logger.error(f"Regeneration failed: {e}")
                return None, QualityResult(
                    passed=False,
                    score=result_dict['total_score'],
                    issues=result_dict['issues'] + [f"Regeneration failed: {str(e)}"],
                    strengths=result_dict.get('strengths', []),
                    attempts=attempt,
                    grammar_score=result_dict.get('grammar_score'),
                    educational_score=result_dict.get('educational_score'),
                    content_score=result_dict.get('content_score'),
                    level_score=result_dict.get('level_score')
                )

        # Should not reach here, but just in case
        return None, QualityResult(
            passed=False,
            score=0,
            issues=["Maximum attempts exceeded"],
            strengths=[],
            attempts=self.max_attempts
        )

    def _evaluate(self, article: AdaptedArticle) -> Dict:
        """Evaluate article quality using LLM judge"""

        level = article.level

        # Get prompt from centralized prompts module
        prompt = prompts.get_quality_judge_prompt(article, level)

        try:
            response = self._call_llm(prompt)
            result = self._parse_judge_response(response)

            # Log the evaluation
            self.logger.debug(f"Quality scores: {result}")

            return result

        except Exception as e:
            self.logger.error(f"Quality evaluation failed: {e}")
            # Return failing result
            return {
                'total_score': 0,
                'issues': [f"Evaluation error: {str(e)}"],
                'strengths': [],
                'grammar_score': 0,
                'educational_score': 0,
                'content_score': 0,
                'level_score': 0
            }

    def _call_llm(self, prompt: str) -> str:
        """Call LLM with prompt"""
        # Use quality_check model (typically cheaper/faster like Haiku)
        model = self.llm_config['models']['quality_check']
        max_tokens = self.llm_config.get('max_tokens', 4096)

        provider = self.llm_config['provider']

        try:
            if provider == 'anthropic':
                response = self.llm_client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=0.2,  # Lower temp for consistent judging
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text

            elif provider == 'openai':
                response = self.llm_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content

            else:
                raise ValueError(f"Unknown provider: {provider}")

        except Exception as e:
            self.logger.error(f"LLM API call failed: {e}")
            raise

    def _parse_judge_response(self, response: str) -> Dict:
        """Parse LLM judge JSON response"""

        # Extract JSON from response (handle markdown code blocks)
        json_str = response

        if '```json' in response:
            json_str = response.split('```json')[1].split('```')[0]
        elif '```' in response:
            json_str = response.split('```')[1].split('```')[0]

        try:
            result = json.loads(json_str.strip())

            # Validate required fields
            required = ['total_score', 'issues']
            for field in required:
                if field not in result:
                    self.logger.warning(f"Missing field in judge response: {field}")
                    result[field] = 0 if field == 'total_score' else []

            # Ensure issues and strengths are lists
            if not isinstance(result.get('issues', []), list):
                result['issues'] = []
            if not isinstance(result.get('strengths', []), list):
                result['strengths'] = []

            return result

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse judge response as JSON: {e}")
            self.logger.debug(f"Response was: {response[:500]}")

            # Return failing result
            return {
                'total_score': 0,
                'issues': ["Failed to parse judge response"],
                'strengths': [],
                'grammar_score': 0,
                'educational_score': 0,
                'content_score': 0,
                'level_score': 0
            }
