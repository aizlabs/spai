"""
Content Fetcher Component

Fetches and extracts clean article text from source URLs using Trafilatura.
Optimized with parallel fetching for better performance.
"""

import requests
import trafilatura
from typing import List, Dict, Optional
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging


class ContentFetcher:
    """Fetches and cleans article content from URLs"""

    def __init__(self, config: Dict, logger: logging.Logger):
        self.config = config
        self.logger = logger.getChild('ContentFetcher')
        self.timeout = config['sources'].get('fetch_timeout', 10)
        self.max_words_per_source = config['sources'].get('max_words_per_source', 300)
        self.min_words_per_source = config['sources'].get('min_words_per_source', 100)
        self.max_sources = config['sources'].get('max_sources_per_topic', 5)

    def fetch_topic_sources(self, topic: Dict) -> List[Dict]:
        """
        Fetch clean article text for a topic with parallel fetching

        Args:
            topic: Topic dict with headlines

        Returns:
            List of source content dicts (3-5 sources)
        """
        sources = []
        urls = [h['url'] for h in topic['headlines'][:8]]  # Try up to 8 sources

        self.logger.info(f"Fetching sources for: {topic['title']}")

        # Parallel fetching with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as executor:
            # Submit all fetch tasks
            future_to_url = {
                executor.submit(self._fetch_article, url): url
                for url in urls
            }

            # Collect results as they complete
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    content = future.result()

                    if content and len(content['text'].split()) >= self.min_words_per_source:
                        sources.append(content)
                        self.logger.debug(f"✓ Fetched: {urlparse(url).netloc}")

                        # Stop after getting enough sources
                        if len(sources) >= self.max_sources:
                            break
                    elif content:
                        self.logger.debug(f"✗ Too short: {urlparse(url).netloc} ({content.get('word_count', 0)} words)")

                except Exception as e:
                    self.logger.debug(f"✗ Failed: {urlparse(url).netloc} - {e}")
                    continue

        # Log summary
        if len(sources) < 3:
            self.logger.warning(f"Insufficient sources for {topic['title']}: {len(sources)}/3 minimum")
        else:
            self.logger.info(f"Successfully fetched {len(sources)} sources")

        return sources

    def _fetch_article(self, url: str) -> Optional[Dict]:
        """
        Fetch and extract clean article text

        Uses Trafilatura for robust extraction
        """
        # Special handling for Wikipedia
        if 'wikipedia.org' in url:
            return self._fetch_wikipedia(url)

        # Regular article fetch
        try:
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; AutoSpanishBot/1.0; Educational content bot)'
                }
            )
            response.raise_for_status()

            # Extract main content using Trafilatura
            extracted = trafilatura.extract(
                response.content,
                include_comments=False,
                include_tables=False,
                no_fallback=False
            )

            if not extracted:
                return None

            # Get metadata
            metadata = trafilatura.extract_metadata(response.content)

            # Truncate to first N words
            words = extracted.split()[:self.max_words_per_source]
            truncated_text = ' '.join(words)

            return {
                'url': url,
                'text': truncated_text,
                'title': metadata.title if metadata else '',
                'author': metadata.author if metadata else '',
                'date': metadata.date if metadata else '',
                'source': urlparse(url).netloc,
                'word_count': len(words)
            }

        except requests.exceptions.Timeout:
            self.logger.debug(f"Timeout fetching {urlparse(url).netloc}")
            return None
        except requests.exceptions.HTTPError as e:
            self.logger.debug(f"HTTP error {e.response.status_code} for {urlparse(url).netloc}")
            return None
        except requests.exceptions.ConnectionError:
            self.logger.debug(f"Connection error for {urlparse(url).netloc}")
            return None
        except Exception as e:
            self.logger.debug(f"Fetch error for {urlparse(url).netloc}: {type(e).__name__}")
            return None

    def _fetch_wikipedia(self, url: str) -> Optional[Dict]:
        """
        Fetch Wikipedia content via API

        Wikipedia has a clean API we can use directly
        """
        try:
            # Extract article title from URL
            # Example: https://es.wikipedia.org/wiki/Lionel_Messi
            parts = url.rstrip('/').split('/')
            title = parts[-1]

            # Determine language
            if 'es.wikipedia.org' in url:
                lang = 'es'
            else:
                lang = 'en'

            # Use Wikipedia API with User-Agent
            api_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"

            response = requests.get(
                api_url,
                timeout=self.timeout,
                headers={
                    'User-Agent': 'AutoSpanishBot/1.0 (https://github.com/autospanishblog; Educational content bot)'
                }
            )
            response.raise_for_status()
            data = response.json()

            # Truncate to first N words
            words = data['extract'].split()[:self.max_words_per_source]
            truncated_text = ' '.join(words)

            return {
                'url': data['content_urls']['desktop']['page'],
                'text': truncated_text,
                'title': data['title'],
                'author': '',
                'date': '',
                'source': 'Wikipedia',
                'word_count': len(words)
            }

        except Exception as e:
            self.logger.debug(f"Wikipedia fetch error for {urlparse(url).netloc}: {type(e).__name__}")
            return None
