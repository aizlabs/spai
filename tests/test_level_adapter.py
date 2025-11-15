"""
Unit tests for LevelAdapter component
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from scripts.level_adapter import LevelAdapter


class TestLevelAdapterInit:
    """Test LevelAdapter initialization"""

    def test_init_with_openai(self, base_config, mock_logger):
        """Test initialization with OpenAI provider"""
        with patch('scripts.level_adapter.OpenAI'):
            adapter = LevelAdapter(base_config, mock_logger)

            assert adapter.config == base_config
            assert adapter.llm_config == base_config['llm']
            mock_logger.getChild.assert_called_with('LevelAdapter')

    def test_init_with_anthropic(self, base_config, mock_logger):
        """Test initialization with Anthropic provider"""
        base_config['llm']['provider'] = 'anthropic'
        base_config['llm']['anthropic_api_key'] = 'test-key'

        with patch('scripts.level_adapter.Anthropic'):
            adapter = LevelAdapter(base_config, mock_logger)

            assert adapter.llm_config['provider'] == 'anthropic'


class TestLevelAdapterA2:
    """Test A2-level adaptation"""

    @patch('scripts.level_adapter.OpenAI')
    def test_adapt_to_a2_success(self, mock_openai, base_config, mock_logger,
                                  sample_base_article, sample_a2_article):
        """Test successful A2 adaptation"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Remove base_article from expected response (will be added by adapter)
        response_article = sample_a2_article.copy()
        del response_article['base_article']

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(response_article)
        mock_client.chat.completions.create.return_value = mock_response

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_a2(sample_base_article)

        # Verify result
        assert result['level'] == 'A2'
        assert result['title'] == sample_a2_article['title']
        assert 'vocabulary' in result
        assert len(result['vocabulary']) > 0
        assert result['base_article']['title'] == sample_base_article['title']
        assert result['base_article']['content'] == sample_base_article['content']

        # Verify LLM was called
        mock_client.chat.completions.create.assert_called_once()

    @patch('scripts.level_adapter.OpenAI')
    def test_adapt_to_a2_with_feedback(self, mock_openai, base_config, mock_logger,
                                        sample_base_article, sample_a2_article):
        """Test A2 adaptation with quality feedback"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        response_article = sample_a2_article.copy()
        del response_article['base_article']

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(response_article)
        mock_client.chat.completions.create.return_value = mock_response

        adapter = LevelAdapter(base_config, mock_logger)
        feedback = ["Sentences too long", "Vocabulary too complex"]

        result = adapter.adapt_to_a2(sample_base_article, feedback=feedback)

        # Verify feedback was included in prompt
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        prompt = call_kwargs['messages'][0]['content']
        assert "PREVIOUS ATTEMPT HAD ISSUES" in prompt
        assert "Sentences too long" in prompt

    @patch('scripts.level_adapter.OpenAI')
    def test_adapt_to_a2_empty_vocabulary(self, mock_openai, base_config, mock_logger,
                                           sample_base_article):
        """Test A2 adaptation sets empty dict when vocabulary missing"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Response without vocabulary
        response = {
            'title': 'Test',
            'content': 'Content',
            'summary': 'Summary',
            'reading_time': 2
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(response)
        mock_client.chat.completions.create.return_value = mock_response

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_a2(sample_base_article)

        assert result['vocabulary'] == {}


class TestLevelAdapterB1:
    """Test B1-level adaptation"""

    @patch('scripts.level_adapter.OpenAI')
    def test_adapt_to_b1_success(self, mock_openai, base_config, mock_logger,
                                  sample_base_article, sample_b1_article):
        """Test successful B1 adaptation"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        response_article = sample_b1_article.copy()
        del response_article['base_article']

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(response_article)
        mock_client.chat.completions.create.return_value = mock_response

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_b1(sample_base_article)

        # Verify result
        assert result['level'] == 'B1'
        assert result['title'] == sample_b1_article['title']
        assert 'vocabulary' in result
        assert len(result['vocabulary']) > 0
        assert result['base_article']['title'] == sample_base_article['title']

    @patch('scripts.level_adapter.OpenAI')
    def test_adapt_to_b1_with_feedback(self, mock_openai, base_config, mock_logger,
                                        sample_base_article, sample_b1_article):
        """Test B1 adaptation with quality feedback"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        response_article = sample_b1_article.copy()
        del response_article['base_article']

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(response_article)
        mock_client.chat.completions.create.return_value = mock_response

        adapter = LevelAdapter(base_config, mock_logger)
        feedback = ["Not enough vocabulary glosses"]

        result = adapter.adapt_to_b1(sample_base_article, feedback=feedback)

        # Verify feedback was included
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        prompt = call_kwargs['messages'][0]['content']
        assert "PREVIOUS ATTEMPT HAD ISSUES" in prompt
        assert "Not enough vocabulary glosses" in prompt


class TestLevelAdapterGeneric:
    """Test generic adapt_to_level method"""

    @patch('scripts.level_adapter.OpenAI')
    def test_adapt_to_level_a2(self, mock_openai, base_config, mock_logger,
                                sample_base_article, sample_a2_article):
        """Test adapt_to_level routes to A2 correctly"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        response_article = sample_a2_article.copy()
        del response_article['base_article']

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(response_article)
        mock_client.chat.completions.create.return_value = mock_response

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_level(sample_base_article, 'A2')

        assert result['level'] == 'A2'

    @patch('scripts.level_adapter.OpenAI')
    def test_adapt_to_level_b1(self, mock_openai, base_config, mock_logger,
                                sample_base_article, sample_b1_article):
        """Test adapt_to_level routes to B1 correctly"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        response_article = sample_b1_article.copy()
        del response_article['base_article']

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(response_article)
        mock_client.chat.completions.create.return_value = mock_response

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_level(sample_base_article, 'B1')

        assert result['level'] == 'B1'

    @patch('scripts.level_adapter.OpenAI')
    def test_adapt_to_level_unsupported(self, mock_openai, base_config, mock_logger,
                                         sample_base_article):
        """Test adapt_to_level fails with unsupported level"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        adapter = LevelAdapter(base_config, mock_logger)

        with pytest.raises(ValueError, match="Unsupported level"):
            adapter.adapt_to_level(sample_base_article, 'C1')


class TestLevelAdapterParsing:
    """Test response parsing"""

    @patch('scripts.level_adapter.OpenAI')
    def test_parse_with_markdown_json(self, mock_openai, base_config, mock_logger,
                                       sample_base_article, sample_a2_article):
        """Test parsing JSON wrapped in markdown"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        response_article = sample_a2_article.copy()
        del response_article['base_article']

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = f"```json\n{json.dumps(response_article)}\n```"
        mock_client.chat.completions.create.return_value = mock_response

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_a2(sample_base_article)

        assert result['title'] == sample_a2_article['title']

    @patch('scripts.level_adapter.OpenAI')
    def test_parse_invalid_reading_time(self, mock_openai, base_config, mock_logger,
                                         sample_base_article):
        """Test reading_time defaults when invalid"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        response = {
            'title': 'Test',
            'content': 'Content',
            'summary': 'Summary',
            'reading_time': 'invalid'  # Invalid value
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(response)
        mock_client.chat.completions.create.return_value = mock_response

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_a2(sample_base_article)

        # Should default to 2 for A2
        assert result['reading_time'] == 2

    @patch('scripts.level_adapter.OpenAI')
    def test_parse_missing_required_field(self, mock_openai, base_config, mock_logger,
                                           sample_base_article):
        """Test parsing fails when required field missing"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Missing 'title'
        response = {
            'content': 'Content',
            'summary': 'Summary',
            'reading_time': 2
        }

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(response)
        mock_client.chat.completions.create.return_value = mock_response

        adapter = LevelAdapter(base_config, mock_logger)

        with pytest.raises(ValueError, match="Missing required field"):
            adapter.adapt_to_a2(sample_base_article)


class TestLevelAdapterModelSelection:
    """Test model selection for adaptation"""

    @patch('scripts.level_adapter.OpenAI')
    def test_uses_adaptation_model(self, mock_openai, base_config, mock_logger,
                                    sample_base_article, sample_a2_article):
        """Test uses adaptation model from config"""
        base_config['llm']['models']['adaptation'] = 'gpt-4o-mini'

        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        response_article = sample_a2_article.copy()
        del response_article['base_article']

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(response_article)
        mock_client.chat.completions.create.return_value = mock_response

        adapter = LevelAdapter(base_config, mock_logger)
        adapter.adapt_to_a2(sample_base_article)

        # Verify correct model was used
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs['model'] == 'gpt-4o-mini'

    @patch('scripts.level_adapter.OpenAI')
    def test_fallback_to_generation_model(self, mock_openai, base_config, mock_logger,
                                           sample_base_article, sample_a2_article):
        """Test falls back to generation model if adaptation not specified"""
        # Remove adaptation model from config
        del base_config['llm']['models']['adaptation']

        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        response_article = sample_a2_article.copy()
        del response_article['base_article']

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(response_article)
        mock_client.chat.completions.create.return_value = mock_response

        adapter = LevelAdapter(base_config, mock_logger)
        adapter.adapt_to_a2(sample_base_article)

        # Should use generation model as fallback
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs['model'] == 'gpt-4o'


class TestLevelAdapterEdgeCases:
    """Test edge cases and missing metadata handling"""

    @patch('scripts.level_adapter.OpenAI')
    def test_adapt_with_missing_topic_metadata(self, mock_openai, base_config, mock_logger,
                                                 sample_base_article_minimal, sample_a2_article):
        """Test adaptation handles missing topic metadata gracefully"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        response_article = sample_a2_article.copy()
        del response_article['base_article']

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(response_article)
        mock_client.chat.completions.create.return_value = mock_response

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_a2(sample_base_article_minimal)

        # Should not crash and should have empty dict for topic
        assert result['topic'] == {}
        assert result['sources'] == []

    @patch('scripts.level_adapter.OpenAI')
    def test_adapt_with_none_topic(self, mock_openai, base_config, mock_logger, sample_a2_article):
        """Test adaptation handles explicit None topic"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Base article with explicit None topic
        base_with_none = {
            'title': 'Test',
            'content': 'Content',
            'summary': 'Summary',
            'reading_time': 2,
            'topic': None,  # Explicit None
            'sources': None
        }

        response_article = sample_a2_article.copy()
        del response_article['base_article']

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(response_article)
        mock_client.chat.completions.create.return_value = mock_response

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_a2(base_with_none)

        # Should default to empty dict/list, not None
        assert result['topic'] == {}
        assert result['sources'] == []

    @patch('scripts.level_adapter.OpenAI')
    def test_base_article_preserved_in_result(self, mock_openai, base_config, mock_logger,
                                               sample_base_article, sample_a2_article):
        """Test base_article is preserved for regeneration"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        response_article = sample_a2_article.copy()
        del response_article['base_article']

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(response_article)
        mock_client.chat.completions.create.return_value = mock_response

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_a2(sample_base_article)

        # Base article should be stored
        assert 'base_article' in result
        assert result['base_article']['title'] == sample_base_article['title']
        assert result['base_article']['content'] == sample_base_article['content']
        assert result['base_article']['summary'] == sample_base_article['summary']
        assert result['base_article']['reading_time'] == sample_base_article['reading_time']

    @patch('scripts.level_adapter.OpenAI')
    def test_metadata_inheritance_from_base(self, mock_openai, base_config, mock_logger,
                                             sample_base_article, sample_a2_article):
        """Test metadata is correctly inherited from base article"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        response_article = sample_a2_article.copy()
        del response_article['base_article']

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(response_article)
        mock_client.chat.completions.create.return_value = mock_response

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_a2(sample_base_article)

        # Metadata should match base article
        assert result['topic'] == sample_base_article['topic']
        assert result['sources'] == sample_base_article['sources']
