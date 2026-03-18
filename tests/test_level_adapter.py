"""
Unit tests for LevelAdapter component
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from scripts.level_adapter import LevelAdapter
from scripts.models import AdaptedArticle, BaseArticle
from scripts.publisher import Publisher


class FakeAdaptationResponse(BaseModel):
    """Simple stand-in for the internal AdaptationResponse used in LevelAdapter."""

    title: str
    content: str
    vocabulary: list = []
    summary: str
    reading_time: int


class TestLevelAdapterInit:
    """Test LevelAdapter initialization."""

    def test_init_uses_llm_and_generation_config(self, base_config, mock_logger):
        adapter = LevelAdapter(base_config, mock_logger)

        assert adapter.config is base_config
        assert adapter.llm_config == base_config.llm.model_dump()
        assert adapter.generation_config == base_config.generation.model_dump()
        mock_logger.getChild.assert_called_with('LevelAdapter')


class TestLevelAdapterA2:
    """Test A2-level adaptation"""

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_adapt_to_a2_success(self, mock_call_llm, base_config, mock_logger,
                                  sample_base_article, sample_a2_article):
        """Test successful A2 adaptation"""
        # Setup mock
        response_article_dict = sample_a2_article.model_dump()
        # Convert vocabulary dict to list of term/gloss pairs to match AdaptationResponse schema
        vocab_dict = response_article_dict.get('vocabulary') or {}
        response_article_dict['vocabulary'] = [
            {'term': term, 'gloss': gloss} for term, gloss in vocab_dict.items()
        ]
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = FakeAdaptationResponse(**response_article_dict)

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
        vocab_dict = response_article_dict.get('vocabulary') or {}
        response_article_dict['vocabulary'] = [
            {'term': term, 'gloss': gloss} for term, gloss in vocab_dict.items()
        ]
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = FakeAdaptationResponse(**response_article_dict)

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
        response = {
            'title': 'Test',
            'content': 'Content ' * 10,
            'summary': 'Summary ' * 2,
            'reading_time': 2
        }

        mock_call_llm.return_value = FakeAdaptationResponse(**response)

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
        vocab_dict = response_article_dict.get('vocabulary') or {}
        response_article_dict['vocabulary'] = [
            {'term': term, 'gloss': gloss} for term, gloss in vocab_dict.items()
        ]
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = FakeAdaptationResponse(**response_article_dict)

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
        vocab_dict = response_article_dict.get('vocabulary') or {}
        response_article_dict['vocabulary'] = [
            {'term': term, 'gloss': gloss} for term, gloss in vocab_dict.items()
        ]
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = FakeAdaptationResponse(**response_article_dict)

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
        vocab_dict = response_article_dict.get('vocabulary') or {}
        response_article_dict['vocabulary'] = [
            {'term': term, 'gloss': gloss} for term, gloss in vocab_dict.items()
        ]
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = FakeAdaptationResponse(**response_article_dict)

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_level(sample_base_article, 'A2')

        assert isinstance(result, AdaptedArticle)
        assert result.level == 'A2'

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_adapt_to_level_b1(self, mock_call_llm, base_config, mock_logger,
                                sample_base_article, sample_b1_article):
        """Test adapt_to_level routes to B1 correctly"""
        response_article_dict = sample_b1_article.model_dump()
        vocab_dict = response_article_dict.get('vocabulary') or {}
        response_article_dict['vocabulary'] = [
            {'term': term, 'gloss': gloss} for term, gloss in vocab_dict.items()
        ]
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = FakeAdaptationResponse(**response_article_dict)

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
    @patch('scripts.level_adapter.LevelAdapter._build_adapted_article')
    def test_build_adapted_article_error_is_propagated(
        self,
        mock_build_adapted,
        mock_call_llm,
        base_config,
        mock_logger,
        sample_base_article,
    ):
        """Test that errors in building AdaptedArticle are surfaced."""
        resp = FakeAdaptationResponse(
            title="Test",
            content="a" * 100,
            vocabulary=[],
            summary="Summary text",
            reading_time=2,
        )
        mock_call_llm.return_value = resp
        mock_build_adapted.side_effect = ValueError(
            "Invalid adapted article structure or Pydantic validation error"
        )

        adapter = LevelAdapter(base_config, mock_logger)

        with pytest.raises(
            ValueError, match="Invalid adapted article structure or Pydantic validation error"
        ):
            adapter.adapt_to_a2(sample_base_article)


class TestLevelAdapterModelSelection:
    """Test model selection for adaptation"""

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_uses_adaptation_model(self, mock_call_llm, base_config, mock_logger,
                                    sample_base_article, sample_a2_article):
        """Test uses adaptation model from config"""
        base_config.llm.models.adaptation = 'gpt-4o-mini'

        response_article_dict = sample_a2_article.model_dump()
        vocab_dict = response_article_dict.get('vocabulary') or {}
        response_article_dict['vocabulary'] = [
            {'term': term, 'gloss': gloss} for term, gloss in vocab_dict.items()
        ]
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = FakeAdaptationResponse(**response_article_dict)

        adapter = LevelAdapter(base_config, mock_logger)
        adapter.adapt_to_a2(sample_base_article)

        # Verify correct model was used
        # The model is not passed to _call_llm, it's used inside it.
        # We can't directly assert the model used in the call.
        # Instead, we can check that the adapter's llm_config was updated.
        assert adapter.llm_config['models']['adaptation'] == 'gpt-4o-mini'

    @patch('scripts.level_adapter.create_chat_model')
    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_fallback_to_generation_model(
        self,
        mock_call_llm,
        mock_create_chat_model,
        base_config,
        mock_logger,
        sample_base_article,
        sample_a2_article,
    ):
        """Test falls back to generation model if adaptation not specified."""
        # Remove adaptation model from config
        base_config.llm.models.adaptation = None

        # Ensure chain init does not try to build a real client
        mock_create_chat_model.return_value = MagicMock()

        response_article_dict = sample_a2_article.model_dump()
        vocab_dict = response_article_dict.get('vocabulary') or {}
        response_article_dict['vocabulary'] = [
            {'term': term, 'gloss': gloss} for term, gloss in vocab_dict.items()
        ]
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = FakeAdaptationResponse(**response_article_dict)

        adapter = LevelAdapter(base_config, mock_logger)
        adapter.adapt_to_a2(sample_base_article)

        # Should have selected the generation model name when adaptation is None
        assert adapter.llm_config['models']['generation'] == base_config.llm.models.generation


class TestLevelAdapterEdgeCases:
    """Test edge cases and missing metadata handling"""

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_adapt_with_missing_topic_metadata(self, mock_call_llm, base_config, mock_logger,
                                                 sample_base_article_minimal, sample_a2_article):
        """Test adaptation handles missing topic metadata gracefully"""
        response_article_dict = sample_a2_article.model_dump()
        vocab_dict = response_article_dict.get('vocabulary') or {}
        response_article_dict['vocabulary'] = [
            {'term': term, 'gloss': gloss} for term, gloss in vocab_dict.items()
        ]
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = FakeAdaptationResponse(**response_article_dict)

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
        vocab_dict = response_article_dict.get('vocabulary') or {}
        response_article_dict['vocabulary'] = [
            {'term': term, 'gloss': gloss} for term, gloss in vocab_dict.items()
        ]
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = FakeAdaptationResponse(**response_article_dict)

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
        vocab_dict = response_article_dict.get('vocabulary') or {}
        response_article_dict['vocabulary'] = [
            {'term': term, 'gloss': gloss} for term, gloss in vocab_dict.items()
        ]
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = FakeAdaptationResponse(**response_article_dict)

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
        vocab_dict = response_article_dict.get('vocabulary') or {}
        response_article_dict['vocabulary'] = [
            {'term': term, 'gloss': gloss} for term, gloss in vocab_dict.items()
        ]
        del response_article_dict['base_article']
        del response_article_dict['topic']
        del response_article_dict['sources']
        del response_article_dict['level']

        mock_call_llm.return_value = FakeAdaptationResponse(**response_article_dict)

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_a2(sample_base_article)

        # Metadata should match base article
        assert isinstance(result, AdaptedArticle)
        assert result.topic == sample_base_article.topic
        assert result.sources == sample_base_article.sources

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_normalizes_vocabulary_terms_and_warns(
        self,
        mock_call_llm,
        base_config,
        mock_logger,
        sample_base_article,
    ):
        response = {
            'title': 'Test',
            'content': 'La **tasa** sube en el país.' * 5,
            'vocabulary': [
                {'term': '  ****tasa****  ', 'gloss': 'rate - valor de referencia'},
            ],
            'summary': 'Resumen simple suficiente',
            'reading_time': 2,
        }

        mock_call_llm.return_value = FakeAdaptationResponse(**response)

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_a2(sample_base_article)

        assert result.vocabulary == {'tasa': 'rate - valor de referencia'}
        mock_logger.warning.assert_any_call(
            "Normalized vocabulary term for article '%s': '%s' -> '%s'",
            sample_base_article.title,
            '  ****tasa****  ',
            'tasa',
        )

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_drops_vocabulary_terms_not_present_in_content_and_warns(
        self,
        mock_call_llm,
        base_config,
        mock_logger,
        sample_base_article,
    ):
        response = {
            'title': 'Test',
            'content': ('España usa **energía eólica**. ' * 10).strip(),
            'vocabulary': [
                {'term': 'energía eólica', 'gloss': 'wind energy - energía del viento'},
                {'term': 'SEPE', 'gloss': 'employment office - oficina de empleo'},
            ],
            'summary': 'Resumen simple suficiente',
            'reading_time': 2,
        }

        mock_call_llm.return_value = FakeAdaptationResponse(**response)

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_a2(sample_base_article)

        assert result.vocabulary == {'energía eólica': 'wind energy - energía del viento'}
        mock_logger.warning.assert_any_call(
            "Dropped vocabulary terms not present in article '%s': %s",
            sample_base_article.title,
            'SEPE',
        )

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_drops_base_form_when_only_inflected_variant_exists(
        self,
        mock_call_llm,
        base_config,
        mock_logger,
        sample_base_article,
    ):
        response = {
            'title': 'Test',
            'content': ('España reconoció al Estado Palestino. ' * 10).strip(),
            'vocabulary': [
                {'term': 'reconocer', 'gloss': 'recognize - aceptar oficialmente'},
            ],
            'summary': 'Resumen simple suficiente',
            'reading_time': 2,
        }

        mock_call_llm.return_value = FakeAdaptationResponse(**response)

        adapter = LevelAdapter(base_config, mock_logger)
        result = adapter.adapt_to_a2(sample_base_article)

        assert result.vocabulary == {}
        mock_logger.warning.assert_any_call(
            "Dropped vocabulary terms not present in article '%s': %s",
            sample_base_article.title,
            'reconocer',
        )

    @patch('scripts.level_adapter.LevelAdapter._call_llm')
    def test_integration_normalized_term_generates_clean_markdown(
        self,
        mock_call_llm,
        base_config,
        mock_logger,
        sample_base_article,
        tmp_path,
    ):
        response = {
            'title': 'Test',
            'content': ('La **tasa** sube en el país. ' * 10).strip(),
            'vocabulary': [
                {'term': '****tasa****', 'gloss': 'rate - valor de referencia'},
            ],
            'summary': 'Resumen simple suficiente',
            'reading_time': 2,
        }

        mock_call_llm.return_value = FakeAdaptationResponse(**response)

        adapter = LevelAdapter(base_config, mock_logger)
        article = adapter.adapt_to_a2(sample_base_article)

        base_config.output['path'] = str(tmp_path)
        publisher = Publisher(base_config, mock_logger, dry_run=True)
        markdown = publisher._generate_markdown(article, datetime(2024, 1, 1, 12, 0, 0))

        assert "- **tasa** - rate - valor de referencia" in markdown
        assert "****tasa****" not in markdown
