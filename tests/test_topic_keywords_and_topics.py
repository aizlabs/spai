from datetime import datetime

from scripts.topic_discovery import TopicDiscoverer
from scripts.publisher import Publisher
from scripts.models import Topic, AdaptedArticle


def test_extract_keywords_ignores_html_href(base_config, mock_logger):
    """_extract_keywords should ignore HTML href fragments from summaries."""
    discoverer = TopicDiscoverer(base_config, mock_logger)

    headlines = [
        {
            "text": "Madrid vive un día importante",
            "summary": '&nbsp;<a href="https://www.elmundo.es/madrid/2026/03/17/69b93e48.html">Leer</a>',
            "url": "https://www.example.com",
            "source": "Example",
            "id": "1",
        }
    ]

    keywords = discoverer._extract_keywords(headlines)

    joined = " ".join(k.lower() for k in keywords)
    assert "href" not in joined
    assert "elmundo.es" not in joined


def test_publisher_filters_href_from_topics(base_config, mock_logger, sample_a2_article):
    """_format_topics should drop href/URL-like keywords before YAML serialization."""
    # Construct a Topic with a bad keyword plus a good one
    topic = Topic(
        title="Madrid",
        sources=["El Mundo"],
        mentions=3,
        score=10.0,
        keywords=['madrid', 'href="https://www.elmundo.es'],
        urls=["https://www.elmundo.es/madrid/2026/03/17/69b93e48.html"],
    )

    article_with_topic = sample_a2_article.model_copy(update={"topic": topic})

    publisher = Publisher(base_config, mock_logger, dry_run=True)
    markdown = publisher._generate_markdown(article_with_topic, datetime(2026, 3, 17, 12, 0, 0))

    # Topics line should not contain href/URL fragments
    assert 'href="https://www.elmundo.es' not in markdown
    # But should still include the valid topic keyword
    assert 'topics: ["madrid"]' in markdown

