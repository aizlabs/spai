from datetime import datetime

from scripts.publisher import Publisher


def test_publisher_deduplicates_sources_with_links(base_config, mock_logger, sample_a2_article, tmp_path):
    base_config.output['path'] = str(tmp_path)
    article = sample_a2_article.model_copy(update={'sources': ['elpais.com', 'elpais.com']})

    publisher = Publisher(base_config, mock_logger, dry_run=True)

    markdown = publisher._generate_markdown(article, datetime(2024, 1, 1, 12, 0, 0))

    expected_source = "[elpais.com](https://elpais.com)"

    assert markdown.count(expected_source) == 2
    assert f'sources: "{expected_source}"' in markdown
    assert f"*Fuentes: {expected_source}*" in markdown


def test_publisher_falls_back_to_plain_text_when_url_missing(base_config, mock_logger, sample_a2_article, tmp_path):
    base_config.output['path'] = str(tmp_path)
    article = sample_a2_article.model_copy(update={'sources': ['Unknown Source', 'Unknown Source']})

    publisher = Publisher(base_config, mock_logger, dry_run=True)

    markdown = publisher._generate_markdown(article, datetime(2024, 1, 1, 12, 0, 0))

    assert markdown.count('Unknown Source') == 2
    assert 'Unknown Source](' not in markdown
    assert 'sources: "Unknown Source"' in markdown
    assert '*Fuentes: Unknown Source*' in markdown


def test_publisher_deduplicates_mixed_url_forms(base_config, mock_logger, sample_a2_article, tmp_path):
    base_config.output['path'] = str(tmp_path)
    mixed_sources = ['https://ElPais.com/news/', 'elpais.com/news', ' https://elpais.com/news']
    article = sample_a2_article.model_copy(update={'sources': mixed_sources})

    publisher = Publisher(base_config, mock_logger, dry_run=True)

    markdown = publisher._generate_markdown(article, datetime(2024, 1, 1, 12, 0, 0))

    rendered = "[https://ElPais.com/news/](https://ElPais.com/news)"
    assert markdown.count(rendered) == 2
    assert 'sources: "' + rendered + '"' in markdown
    assert '*Fuentes: ' + rendered + '*\n*Artículo educativo' in markdown


def test_publisher_handles_empty_sources_gracefully(base_config, mock_logger, sample_a2_article, tmp_path):
    base_config.output['path'] = str(tmp_path)
    article = sample_a2_article.model_copy(update={'sources': ['', '  ']})

    publisher = Publisher(base_config, mock_logger, dry_run=True)

    markdown = publisher._generate_markdown(article, datetime(2024, 1, 1, 12, 0, 0))

    assert '\nsources: ""' in markdown
    assert '*Fuentes: *' in markdown


def test_publisher_ignores_blank_sources_but_keeps_valid_entries(
    base_config,
    mock_logger,
    sample_a2_article,
    tmp_path,
):
    base_config.output['path'] = str(tmp_path)
    article = sample_a2_article.model_copy(update={'sources': ['  ', 'ElPais.com']})

    publisher = Publisher(base_config, mock_logger, dry_run=True)

    markdown = publisher._generate_markdown(article, datetime(2024, 1, 1, 12, 0, 0))

    expected_source = "[ElPais.com](https://ElPais.com)"

    assert markdown.count(expected_source) == 2
    assert 'sources: ""' not in markdown


def test_publisher_deduplicates_domain_and_scheme_sources(
    base_config,
    mock_logger,
    sample_a2_article,
    tmp_path,
):
    base_config.output['path'] = str(tmp_path)
    article = sample_a2_article.model_copy(update={'sources': ['ElPais.com', 'https://elpais.com/']})

    publisher = Publisher(base_config, mock_logger, dry_run=True)

    markdown = publisher._generate_markdown(article, datetime(2024, 1, 1, 12, 0, 0))

    expected_source = "[ElPais.com](https://ElPais.com)"

    assert markdown.count(expected_source) == 2


def test_publisher_escapes_markdown_in_source_labels(
    base_config,
    mock_logger,
    sample_a2_article,
    tmp_path,
):
    base_config.output['path'] = str(tmp_path)
    base_config.sources_list = [{'name': 'Example [Site]', 'url': 'https://example.com'}]
    article = sample_a2_article.model_copy(update={'sources': ['Example [Site]']})

    publisher = Publisher(base_config, mock_logger, dry_run=True)

    markdown = publisher._generate_markdown(article, datetime(2024, 1, 1, 12, 0, 0))

    assert "[Example \\[Site\\]](" in markdown
