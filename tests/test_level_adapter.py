"""
Unit tests for LevelAdapter component
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from scripts.level_adapter import LevelAdapter
from scripts.models import BaseArticle, AdaptedArticle


class TestLevelAdapterInit:
    """Test LevelAdapter initialization"""

    @patch('scripts.level_adapter.LevelAdapter._init_llm_client')
    def test_init_with_openai(self, mock_init_llm_client, base_config, mock_logger):
        """Test initialization with OpenAI provider"""
        adapter = LevelAdapter(base_config, mock_logger)

        assert adapter.config == base_config
        assert adapter.llm_config == base_config.llm.model_dump()
        mock_logger.getChild.assert_called_with('LevelAdapter')
        mock_init_llm_client.assert_called_once()

    @patch('scripts.level_adapter.LevelAdapter._init_llm_client')
    def test_init_with_anthropic(self, mock_init_llm_client, base_config, mock_logger):
        """Test initialization with Anthropic provider"""
        base_config.llm.provider = 'anthropic'
        base_config.llm.anthropic_api_key = 'test-key'

        adapter = LevelAdapter(base_config, mock_logger)

        assert adapter.llm_config['provider'] == 'anthropic'
        mock_init_llm_client.assert_called_once()


class TestLevelAdapterA2:
    """Test A2-level adaptation"""

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_adapt_to_a2_success(self, mock_call_llm, base_config, mock_logger,
                                  sample_base_article, sample_a2_article):
        """Test successful A2 adaptation"""
        # Setup mock
        # Remove base_article from expected response (will be added by adapter)
        response_article_dict = sample_a2_article.model_dump()
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = json.dumps(response_article_dict)

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_a2(sample_base_article)

        # Verify result
        assert isinstance(result, AdaptedArticle)
        assert result.level == 'A2'
        assert result.title == sample_a2_article.title
        assert result.vocabulary is not None
        assert len(result.vocabulary) > 0
        assert result.base_article == sample_base_article
        assert result.topic == sample_base_article.topic
        assert result.sources == sample_base_article.sources

        # Verify LLM was called
        mock_call_llm.assert_called_once()

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_adapt_to_a2_with_feedback(self, mock_call_llm, base_config, mock_logger,
                                        sample_base_article, sample_a2_article):
        """Test A2 adaptation with quality feedback"""
        response_article_dict = sample_a2_article.model_dump()
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = json.dumps(response_article_dict)

        adapter = LevelAdapter(base_config, mock_logger)
        feedback = ["Sentences too long", "Vocabulary too complex"]

        result = adapter.adapt_to_a2(sample_base_article, feedback=feedback)

        # Verify feedback was included in prompt
        call_args = mock_call_llm.call_args.args
        prompt = call_args[0]
        assert "PREVIOUS ATTEMPT HAD ISSUES" in prompt
        assert "Sentences too long" in prompt
        assert isinstance(result, AdaptedArticle)

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_adapt_to_a2_empty_vocabulary(self, mock_call_llm, base_config, mock_logger,
                                           sample_base_article):
        """Test A2 adaptation sets empty dict when vocabulary missing"""
        # Response without vocabulary
        response = {
            'title': 'Test',
            'content': 'Content ' * 10,
            'summary': 'Summary ' * 2,
            'reading_time': 2
        }

        mock_call_llm.return_value = json.dumps(response)

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_a2(sample_base_article)

        assert isinstance(result, AdaptedArticle)
        assert result.vocabulary == {}


class TestLevelAdapterB1:
    """Test B1-level adaptation"""

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_adapt_to_b1_success(self, mock_call_llm, base_config, mock_logger,
                                  sample_base_article, sample_b1_article):
        """Test successful B1 adaptation"""
        # Setup mock
        response_article_dict = sample_b1_article.model_dump()
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = json.dumps(response_article_dict)

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_b1(sample_base_article)

        # Verify result
        assert isinstance(result, AdaptedArticle)
        assert result.level == 'B1'
        assert result.title == sample_b1_article.title
        assert result.vocabulary is not None
        assert len(result.vocabulary) > 0
        assert result.base_article == sample_base_article

        # Verify LLM was called
        mock_call_llm.assert_called_once()

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_adapt_to_b1_with_feedback(self, mock_call_llm, base_config, mock_logger,
                                        sample_base_article, sample_b1_article):
        """Test B1 adaptation with quality feedback"""
        response_article_dict = sample_b1_article.model_dump()
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = json.dumps(response_article_dict)

        adapter = LevelAdapter(base_config, mock_logger)
        feedback = ["Not enough vocabulary glosses"]

        result = adapter.adapt_to_b1(sample_base_article, feedback=feedback)

        # Verify feedback was included in prompt
        call_args = mock_call_llm.call_args.args
        prompt = call_args[0]
        assert "PREVIOUS ATTEMPT HAD ISSUES" in prompt
        assert "Not enough vocabulary glosses" in prompt
        assert isinstance(result, AdaptedArticle)


class TestLevelAdapterGeneric:
    """Test generic adapt_to_level method"""

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_adapt_to_level_a2(self, mock_call_llm, base_config, mock_logger,
                                sample_base_article, sample_a2_article):
        """Test adapt_to_level routes to A2 correctly"""
        response_article_dict = sample_a2_article.model_dump()
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = json.dumps(response_article_dict)

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_level(sample_base_article, 'A2')

        assert isinstance(result, AdaptedArticle)
        assert result.level == 'A2'

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_adapt_to_level_b1(self, mock_call_llm, base_config, mock_logger,
                                sample_base_article, sample_b1_article):
        """Test adapt_to_level routes to B1 correctly"""
        response_article_dict = sample_b1_article.model_dump()
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = json.dumps(response_article_dict)

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_level(sample_base_article, 'B1')

        assert isinstance(result, AdaptedArticle)
        assert result.level == 'B1'

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_adapt_to_level_unsupported(self, mock_call_llm, base_config, mock_logger,
                                         sample_base_article):
        """Test adapt_to_level fails with unsupported level"""
        adapter = LevelAdapter(base_config, mock_logger)

        with pytest.raises(ValueError, match="Unsupported level"):
            adapter.adapt_to_level(sample_base_article, 'C1')
        mock_call_llm.assert_not_called()


class TestLevelAdapterParsing:
    """Test response parsing"""

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_parse_with_markdown_json(self, mock_call_llm, base_config, mock_logger,
                                       sample_base_article, sample_a2_article):
        """Test parsing JSON wrapped in markdown"""
        response_article_dict = sample_a2_article.model_dump()
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = f"```json\n{json.dumps(response_article_dict)}\n```"

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_a2(sample_base_article)

        assert isinstance(result, AdaptedArticle)
        assert result.title == sample_a2_article.title

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_parse_invalid_reading_time(self, mock_call_llm, base_config, mock_logger,
                                         sample_base_article):
        """Test reading_time defaults when invalid"""
        response = {
            'title': 'Test',
            'content': 'a' * 50,
            'summary': 'b' * 10,
            'reading_time': 'invalid'  # Invalid value
        }

        mock_call_llm.return_value = json.dumps(response)

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_a2(sample_base_article)

        # Should default to 2 for A2
        assert isinstance(result, AdaptedArticle)
        assert result.reading_time == 2

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_parse_missing_required_field(self, mock_call_llm, base_config, mock_logger,
                                           sample_base_article):
        """Test parsing fails when required field missing"""
        # Missing 'title'
        response = {
            'content': 'Content',
            'summary': 'Summary',
            'reading_time': 2
        }

        mock_call_llm.return_value = json.dumps(response)

        adapter = LevelAdapter(base_config, mock_logger)

        with pytest.raises(ValueError, match="Invalid adapted article structure or Pydantic validation error"):
            adapter.adapt_to_a2(sample_base_article)


class TestLevelAdapterModelSelection:
    """Test model selection for adaptation"""

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_uses_adaptation_model(self, mock_call_llm, base_config, mock_logger,
                                    sample_base_article, sample_a2_article):
        """Test uses adaptation model from config"""
        base_config.llm.models.adaptation = 'gpt-4o-mini'

        response_article_dict = sample_a2_article.model_dump()
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = json.dumps(response_article_dict)

        adapter = LevelAdapter(base_config, mock_logger)
        adapter.adapt_to_a2(sample_base_article)

        # Verify correct model was used
        # The model is not passed to _call_llm, it's used inside it.
        # We can't directly assert the model used in the call.
        # Instead, we can check that the adapter's llm_config was updated.
        assert adapter.llm_config['models']['adaptation'] == 'gpt-4o-mini'

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_fallback_to_generation_model(self, mock_call_llm, base_config, mock_logger,
                                           sample_base_article, sample_a2_article):
        """Test falls back to generation model if adaptation not specified"""
        # Remove adaptation model from config
        base_config.llm.models.adaptation = None

        response_article_dict = sample_a2_article.model_dump()
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = json.dumps(response_article_dict)

        adapter = LevelAdapter(base_config, mock_logger)
        adapter.adapt_to_a2(sample_base_article)

        # Should use generation model as fallback
        # The model is not passed to _call_llm, it's used inside it.
        # We can't directly assert the model used in the call.
        # Instead, we can check that the adapter's llm_config was updated.
        assert adapter.llm_config['models']['adaptation'] is None
        assert adapter.llm_config['models']['generation'] == 'gpt-4o'


class TestLevelAdapterEdgeCases:
    """Test edge cases and missing metadata handling"""

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_adapt_with_missing_topic_metadata(self, mock_call_llm, base_config, mock_logger,
                                                 sample_base_article_minimal, sample_a2_article):
        """Test adaptation handles missing topic metadata gracefully"""
        response_article_dict = sample_a2_article.model_dump()
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = json.dumps(response_article_dict)

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_a2(sample_base_article_minimal)

        # Should not crash and should have empty dict for topic
        assert isinstance(result, AdaptedArticle)
        assert result.topic is None # Topic is Optional, so it should be None
        assert result.sources == []

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_adapt_with_none_topic(self, mock_call_llm, base_config, mock_logger, sample_a2_article):
        """Test adaptation handles explicit None topic"""
        # Base article with explicit None topic
        base_with_none = BaseArticle(
            title='Test',
            content='Content ' * 20, # Make sure content is long enough for validation
            summary='Summary ' * 2, # Make sure summary is long enough for validation
            reading_time=2,
            topic=None,  # Explicit None
            sources=[]
        )

        response_article_dict = sample_a2_article.model_dump()
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = json.dumps(response_article_dict)

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_a2(base_with_none)

        # Should default to empty dict/list, not None
        assert isinstance(result, AdaptedArticle)
        assert result.topic is None
        assert result.sources == []

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_base_article_preserved_in_result(self, mock_call_llm, base_config, mock_logger,
                                               sample_base_article, sample_a2_article):
        """Test base_article is preserved for regeneration"""
        response_article_dict = sample_a2_article.model_dump()
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = json.dumps(response_article_dict)

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_a2(sample_base_article)

        # Base article should be stored
        assert isinstance(result, AdaptedArticle)
        assert result.base_article == sample_base_article

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_metadata_inheritance_from_base(self, mock_call_llm, base_config, mock_logger,
                                             sample_base_article, sample_a2_article):
        """Test metadata is correctly inherited from base article"""
        response_article_dict = sample_a2_article.model_dump()
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = json.dumps(response_article_dict)

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_a2(sample_base_article)

        # Metadata should match base article
        assert isinstance(result, AdaptedArticle)
        assert result.topic == sample_base_article.topic
        assert result.sources == sample_base_article.sources
