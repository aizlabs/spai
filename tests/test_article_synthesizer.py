"""
Unit tests for ArticleSynthesizer component
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from scripts.article_synthesizer import ArticleSynthesizer
from scripts.models import BaseArticle


class TestArticleSynthesizerInit:
    """Test ArticleSynthesizer initialization"""

    @patch('scripts.article_synthesizer.OpenAI')
    def test_init_with_openai(self, mock_openai, base_config, mock_logger):
        """Test initialization with OpenAI provider"""
        synthesizer = ArticleSynthesizer(base_config, mock_logger)

        assert synthesizer.config == base_config
        assert synthesizer.llm_config == base_config.llm.model_dump()
        mock_logger.getChild.assert_called_with('ArticleSynthesizer')
        mock_openai.assert_called_once_with(api_key=base_config.llm.openai_api_key)

    @patch('scripts.article_synthesizer.Anthropic')
    def test_init_with_anthropic(self, mock_anthropic, base_config, mock_logger):
        """Test initialization with Anthropic provider"""
        base_config.llm.provider = 'anthropic'
        base_config.llm.anthropic_api_key = 'test-key'

        synthesizer = ArticleSynthesizer(base_config, mock_logger)

        assert synthesizer.llm_config['provider'] == 'anthropic'
        mock_anthropic.assert_called_once_with(api_key='test-key')

    def test_init_missing_api_key_openai(self, base_config, mock_logger):
        """Test initialization fails with missing OpenAI API key"""
        base_config.llm.openai_api_key = None

        with pytest.raises(ValueError, match="OPENAI_API_KEY is required for OpenAI provider"):
            ArticleSynthesizer(base_config, mock_logger)

    def test_init_missing_api_key_anthropic(self, base_config, mock_logger):
        """Test initialization fails with missing Anthropic API key"""
        base_config.llm.provider = 'anthropic'
        base_config.llm.anthropic_api_key = None

        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is required for Anthropic provider"):
            ArticleSynthesizer(base_config, mock_logger)

    def test_init_unknown_provider(self, base_config, mock_logger):
        """Test initialization fails with unknown provider"""
        base_config.llm.provider = 'unknown'

        with pytest.raises(ValueError, match="Unknown LLM provider"):
            ArticleSynthesizer(base_config, mock_logger)


class TestArticleSynthesizerSynthesize:
    """Test synthesis functionality"""

    @patch('scripts.article_synthesizer.ArticleSynthesizer._call_llm')
    def test_synthesize_success(self, mock_call_llm, base_config, mock_logger,
                                 sample_topic, sample_sources, sample_base_article):
        """Test successful article synthesis"""
        # Setup mock
        mock_call_llm.return_value = json.dumps(sample_base_article.model_dump())

        # Create synthesizer and synthesize
        synthesizer = ArticleSynthesizer(base_config, mock_logger)
        result = synthesizer.synthesize(sample_topic, sample_sources)

        # Verify
        assert isinstance(result, BaseArticle)
        assert result.title == sample_base_article.title
        assert result.content == sample_base_article.content
        assert result.summary == sample_base_article.summary
        assert result.reading_time == sample_base_article.reading_time
        assert result.topic == sample_topic
        assert result.sources == [s.source for s in sample_sources]

        # Verify LLM was called
        mock_call_llm.assert_called_once()
        # The prompt is generated internally, so we can't easily check its content here
        # We can check the model and temperature from llm_config
        assert synthesizer.llm_config['models']['generation'] == base_config.llm.models.generation
        assert synthesizer.llm_config['temperature'] == base_config.llm.temperature

    @patch('scripts.article_synthesizer.ArticleSynthesizer._call_llm')
    def test_synthesize_with_markdown_json(self, mock_call_llm, base_config, mock_logger,
                                            sample_topic, sample_sources, sample_base_article):
        """Test synthesis with JSON wrapped in markdown code blocks"""
        # Mock response with markdown wrapper
        mock_call_llm.return_value = f"```json\n{json.dumps(sample_base_article.model_dump())}\n```"

        synthesizer = ArticleSynthesizer(base_config, mock_logger)
        result = synthesizer.synthesize(sample_topic, sample_sources)

        # Should still parse correctly
        assert isinstance(result, BaseArticle)
        assert result.title == sample_base_article.title
        assert result.topic == sample_topic
        assert result.sources == [s.source for s in sample_sources]

    @patch('scripts.article_synthesizer.ArticleSynthesizer._call_llm')
    def test_synthesize_missing_required_field(self, mock_call_llm, base_config, mock_logger,
                                                 sample_topic, sample_sources):
        """Test synthesis fails when required field is missing"""
        # Response missing 'summary'
        incomplete_response = {
            'title': 'Test',
            'content': 'Content',
            'reading_time': 2
        }

        mock_call_llm.return_value = json.dumps(incomplete_response)

        synthesizer = ArticleSynthesizer(base_config, mock_logger)

        with pytest.raises(ValueError, match="Invalid base article structure or Pydantic validation error"):
            synthesizer.synthesize(sample_topic, sample_sources)

    @patch('scripts.article_synthesizer.ArticleSynthesizer._call_llm')
    def test_synthesize_invalid_json(self, mock_call_llm, base_config, mock_logger,
                                      sample_topic, sample_sources):
        """Test synthesis fails with invalid JSON"""
        mock_call_llm.return_value = "Not valid JSON at all"

        synthesizer = ArticleSynthesizer(base_config, mock_logger)

        with pytest.raises(ValueError, match="LLM returned invalid JSON during synthesis"):
            synthesizer.synthesize(sample_topic, sample_sources)

    @patch('scripts.article_synthesizer.ArticleSynthesizer._call_llm')
    def test_synthesize_reading_time_conversion(self, mock_call_llm, base_config, mock_logger,
                                                  sample_topic, sample_sources):
        """Test reading_time is converted to int"""
        # Response with string reading_time
        response = {
            'title': 'Test',
            'content': 'a' * 100,
            'summary': 'b' * 10,
            'reading_time': '3'  # String instead of int
        }

        mock_call_llm.return_value = json.dumps(response)

        synthesizer = ArticleSynthesizer(base_config, mock_logger)
        result = synthesizer.synthesize(sample_topic, sample_sources)

        assert isinstance(result.reading_time, int)
        assert result.reading_time == 3

    @patch('scripts.article_synthesizer.ArticleSynthesizer._call_llm')
    def test_synthesize_llm_api_error(self, mock_call_llm, base_config, mock_logger,
                                       sample_topic, sample_sources):
        """Test synthesis handles LLM API errors"""
        # Simulate API error
        mock_call_llm.side_effect = Exception("API Error")

        synthesizer = ArticleSynthesizer(base_config, mock_logger)

        with pytest.raises(Exception, match="API Error"):
            synthesizer.synthesize(sample_topic, sample_sources)


class TestArticleSynthesizerAnthropic:
    """Test Anthropic-specific functionality"""

    @patch('scripts.article_synthesizer.ArticleSynthesizer._call_llm')
    def test_synthesize_with_anthropic(self, mock_call_llm, base_config, mock_logger,
                                        sample_topic, sample_sources, sample_base_article):
        """Test synthesis with Anthropic provider"""
        base_config.llm.provider = 'anthropic'
        base_config.llm.anthropic_api_key = 'test-key'

        mock_call_llm.return_value = json.dumps(sample_base_article.model_dump())

        synthesizer = ArticleSynthesizer(base_config, mock_logger)
        result = synthesizer.synthesize(sample_topic, sample_sources)

        assert isinstance(result, BaseArticle)
        assert result.title == sample_base_article.title
        mock_call_llm.assert_called_once()
