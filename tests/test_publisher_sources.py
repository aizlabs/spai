from datetime import datetime

from scripts.publisher import Publisher
from scripts.models import SourceMetadata


def test_publisher_formats_sources_with_links(base_config, mock_logger, sample_a2_article, tmp_path):
    """Test that sources with URLs are formatted as markdown links in attribution"""
    base_config.output['path'] = str(tmp_path)
    sources = [
        SourceMetadata(name='elpais.com', url='https://elpais.com'),
        SourceMetadata(name='elpais.com', url='https://elpais.com'),  # Duplicate
    ]
    article = sample_a2_article.model_copy(update={'sources': sources})

    publisher = Publisher(base_config, mock_logger, dry_run=True)

    markdown = publisher._generate_markdown(article, datetime(2024, 1, 1, 12, 0, 0))

    # Check YAML frontmatter has structured sources
    assert 'sources:' in markdown
    assert '- name: "elpais.com"' in markdown
    assert 'url: "https://elpais.com"' in markdown
    
    # Check attribution has markdown links
    assert "[elpais.com](https://elpais.com)" in markdown
    assert "*Fuentes:" in markdown


def test_publisher_falls_back_to_plain_text_when_url_missing(base_config, mock_logger, sample_a2_article, tmp_path):
    """Test that sources without URLs are shown as plain text"""
    base_config.output['path'] = str(tmp_path)
    sources = [
        SourceMetadata(name='Unknown Source'),
        SourceMetadata(name='Unknown Source'),  # Duplicate
    ]
    article = sample_a2_article.model_copy(update={'sources': sources})

    publisher = Publisher(base_config, mock_logger, dry_run=True)

    markdown = publisher._generate_markdown(article, datetime(2024, 1, 1, 12, 0, 0))

    # Check YAML frontmatter
    assert '- name: "Unknown Source"' in markdown
    assert 'url:' not in markdown.split('name: "Unknown Source"', 1)[1].split('\n', 1)[0]
    
    # Check attribution has plain text (no markdown links)
    assert '*Fuentes: Unknown Source, Unknown Source*' in markdown
    assert 'Unknown Source](' not in markdown


def test_publisher_handles_mixed_sources_with_and_without_urls(
    base_config,
    mock_logger,
    sample_a2_article,
    tmp_path,
):
    """Test formatting when some sources have URLs and others don't"""
    base_config.output['path'] = str(tmp_path)
    sources = [
        SourceMetadata(name='El País', url='https://elpais.com'),
        SourceMetadata(name='Unknown Source'),  # No URL
    ]
    article = sample_a2_article.model_copy(update={'sources': sources})

    publisher = Publisher(base_config, mock_logger, dry_run=True)

    markdown = publisher._generate_markdown(article, datetime(2024, 1, 1, 12, 0, 0))

    # Check both appear in frontmatter
    assert '- name: "El País"' in markdown
    assert 'url: "https://elpais.com"' in markdown
    assert '- name: "Unknown Source"' in markdown
    
    # Check attribution has link for first, plain text for second
    assert "[El País](https://elpais.com)" in markdown
    assert "*Fuentes:" in markdown
    # Unknown Source should appear as plain text (not as a link)
    assert "Unknown Source" in markdown
    assert "Unknown Source](" not in markdown


def test_publisher_handles_empty_sources_gracefully(base_config, mock_logger, sample_a2_article, tmp_path):
    """Test that empty source lists are handled gracefully"""
    base_config.output['path'] = str(tmp_path)
    article = sample_a2_article.model_copy(update={'sources': []})

    publisher = Publisher(base_config, mock_logger, dry_run=True)

    markdown = publisher._generate_markdown(article, datetime(2024, 1, 1, 12, 0, 0))

    assert 'sources: []' in markdown
    assert '*Fuentes: *' in markdown


def test_publisher_handles_legacy_string_sources(
    base_config,
    mock_logger,
    sample_a2_article,
    tmp_path,
):
    """Test that legacy string sources are converted to SourceMetadata"""
    base_config.output['path'] = str(tmp_path)
    # Pass strings - should be converted via coerce_sources validator
    article = sample_a2_article.model_copy(update={'sources': ['El País', 'BBC Mundo']})

    publisher = Publisher(base_config, mock_logger, dry_run=True)

    markdown = publisher._generate_markdown(article, datetime(2024, 1, 1, 12, 0, 0))

    # Should appear in frontmatter as structured sources (without URLs)
    assert '- name: "El País"' in markdown
    assert '- name: "BBC Mundo"' in markdown
    
    # Should appear as plain text in attribution (no URLs)
    assert '*Fuentes: El País, BBC Mundo*' in markdown
    assert 'El País](' not in markdown


def test_publisher_escapes_markdown_in_source_labels(
    base_config,
    mock_logger,
    sample_a2_article,
    tmp_path,
):
    """Test that special characters in source names are escaped in markdown links"""
    base_config.output['path'] = str(tmp_path)
    sources = [
        SourceMetadata(name='Example [Site]', url='https://example.com'),
    ]
    article = sample_a2_article.model_copy(update={'sources': sources})

    publisher = Publisher(base_config, mock_logger, dry_run=True)

    markdown = publisher._generate_markdown(article, datetime(2024, 1, 1, 12, 0, 0))

    # Verify special characters are escaped in attribution links
    assert "[Example \\[Site\\]](" in markdown
    assert "https://example.com" in markdown


def test_publisher_escapes_special_chars_in_structured_sources(
    base_config,
    mock_logger,
    sample_a2_article,
    tmp_path,
):
    """Test that _format_attribution escapes special characters in SourceMetadata names"""
    base_config.output['path'] = str(tmp_path)
    
    # Test all special markdown characters: [, ], (, )
    sources_with_special_chars = [
        SourceMetadata(name='News [Site]', url='https://example.com'),
        SourceMetadata(name='Article (2024)', url='https://example.org'),
        SourceMetadata(name='Source [with] (parens)', url='https://example.net'),
    ]
    article = sample_a2_article.model_copy(update={'sources': sources_with_special_chars})

    publisher = Publisher(base_config, mock_logger, dry_run=True)

    markdown = publisher._generate_markdown(article, datetime(2024, 1, 1, 12, 0, 0))

    # Verify all special characters are escaped in attribution section
    assert "[News \\[Site\\]](" in markdown
    assert "[Article \\(2024\\)](" in markdown
    assert "[Source \\[with\\] \\(parens\\)](" in markdown
    
    # Verify the links are properly formed (not malformed)
    assert "*Fuentes:" in markdown
    assert "https://example.com" in markdown
    assert "https://example.org" in markdown
    assert "https://example.net" in markdown
