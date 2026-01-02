"""
Publisher Component

Saves approved articles as Jekyll markdown files with YAML frontmatter.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from scripts.models import AdaptedArticle
from scripts.config import AppConfig


class Publisher:
    """Publishes articles to Jekyll format"""

    def __init__(self, config: AppConfig, logger: logging.Logger, dry_run: bool = False):
        self.config = config
        self.logger = logger.getChild('Publisher')
        self.dry_run = dry_run

        # Output directory
        self.output_dir = Path(config.output['path'])
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.source_url_map = self._build_source_url_map()

        self.logger.info(f"Publisher initialized (dry_run={dry_run}, output={self.output_dir})")

    def save_article(self, article: AdaptedArticle) -> bool:
        """
        Save article as Jekyll markdown file

        Args:
            article: Article dict with all fields

        Returns:
            True if saved successfully
        """
        try:
            # Generate timestamp once for consistency between filename and frontmatter
            timestamp = datetime.now()

            # Generate filename
            filename = self._generate_filename(article, timestamp)
            filepath = self.output_dir / filename

            # Generate markdown content
            markdown = self._generate_markdown(article, timestamp)

            if self.dry_run:
                self.logger.info(f"[DRY RUN] Would save: {filename}")
                self.logger.debug(f"Content preview:\n{markdown[:200]}...")
                return True

            # Write file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown)

            self.logger.info(f"✅ Saved: {filename}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save article: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return False

    def _generate_filename(self, article: AdaptedArticle, timestamp: datetime) -> str:
        """
        Generate Jekyll filename

        Format: YYYY-MM-DD-HHMMSS-title-slug-level.md
        Includes timestamp to prevent collisions when multiple articles
        with similar titles are generated on the same day.

        Args:
            article: Article dict with title and level
            timestamp: datetime object for consistent timestamping
        """
        timestamp_str = timestamp.strftime("%Y-%m-%d-%H%M%S")

        # Create slug from title
        title = article.title
        slug = self._slugify(title)[:50]  # Max 50 chars

        level = article.level.lower()

        return f"{timestamp_str}-{slug}-{level}.md"

    def _slugify(self, text: str) -> str:
        """Convert text to URL-safe slug"""
        # Remove accents and convert to ASCII
        text = text.lower()

        # Spanish character replacements
        replacements = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
            'ñ': 'n', 'ü': 'u',
            '¿': '', '¡': '', '?': '', '!': ''
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # Replace non-alphanumeric with hyphens
        text = re.sub(r'[^a-z0-9]+', '-', text)

        # Remove leading/trailing hyphens
        text = text.strip('-')

        return text

    def _escape_yaml_string(self, text: str) -> str:
        """
        Escape a string for safe use in YAML double-quoted strings

        Args:
            text: String to escape

        Returns:
            Escaped string safe for YAML
        """
        # Escape backslashes first
        text = text.replace('\\', '\\\\')
        # Escape double quotes
        text = text.replace('"', '\\"')
        return text

    def _build_source_url_map(self) -> Dict[str, str]:
        """Create lookup map of normalized source names to URLs from config."""
        source_map: Dict[str, str] = {}

        for source in self.config.sources_list:
            name = source.get('name') if isinstance(source, dict) else None
            url = source.get('url') if isinstance(source, dict) else None

            if not name or not url:
                continue

            normalized_name = self._normalize_source_key(name)
            normalized_url = self._normalize_url(url, include_path=True)

            if normalized_name and normalized_url:
                source_map[normalized_name] = normalized_url
                host_key = self._normalize_host_key(normalized_url)
                if host_key:
                    source_map.setdefault(host_key, normalized_url)

        return source_map

    def _normalize_url(self, url: str, include_path: bool) -> Optional[str]:
        """Normalize URL, inferring scheme when missing."""
        if not url:
            return None

        cleaned_url = url.strip()
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', cleaned_url):
            cleaned_url = f"https://{cleaned_url}"

        parsed = urlparse(cleaned_url)
        if not parsed.scheme:
            return None

        host = parsed.netloc or parsed.path
        if not host:
            return None

        path = parsed.path.rstrip('/') if include_path else ""

        normalized = f"{parsed.scheme}://{host}"
        if include_path and path:
            normalized = f"{normalized}{path}"

        return normalized

    def _normalize_host_key(self, url: str) -> Optional[str]:
        """Normalize a URL string into a host-only lookup key."""
        parsed = urlparse(url)
        host = parsed.netloc or parsed.path
        if not host:
            return None
        return host.casefold()

    def _normalize_source_key(self, source: str) -> str:
        """Normalize source identifier for consistent de-duplication."""
        cleaned = source.strip().rstrip('/')

        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', cleaned):
            parsed = urlparse(cleaned)
            host = parsed.netloc or parsed.path
            path = parsed.path.rstrip('/')
            return f"{host}{path}".casefold()

        return cleaned.casefold()

    def _resolve_source_url(self, source: str) -> Optional[str]:
        """Resolve source to a best-effort URL if available."""
        if not source:
            return None

        cleaned_source = source.strip()

        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', cleaned_source):
            return self._normalize_url(cleaned_source, include_path=True)

        if re.match(r'^[\w.-]+\.[a-zA-Z]{2,}(/.*)?$', cleaned_source):
            return self._normalize_url(f"https://{cleaned_source}", include_path=True)

        normalized_key = self._normalize_source_key(cleaned_source)
        return self.source_url_map.get(normalized_key)

    def _normalize_sources(self, sources: List[str]) -> List[Tuple[str, Optional[str]]]:
        """Return ordered, de-duplicated list of (source, url?) tuples."""
        normalized_sources: List[Tuple[str, Optional[str]]] = []
        seen_keys = set()

        for source in sources:
            if not source:
                continue

            cleaned_source = source.strip()
            if not cleaned_source:
                continue

            key = self._normalize_source_key(cleaned_source)
            if not key:
                continue

            if key in seen_keys:
                continue

            seen_keys.add(key)
            normalized_sources.append((cleaned_source, self._resolve_source_url(cleaned_source)))

        return normalized_sources

    def _render_source(self, source: str, url: Optional[str]) -> str:
        """Render a source as markdown link when URL is available."""
        if url:
            escaped_source = self._escape_markdown_link_text(source)
            return f"[{escaped_source}]({url})"
        return source

    def _escape_markdown_link_text(self, text: str) -> str:
        """Escape markdown link text to prevent malformed links."""
        escaped = text.replace('\\', '\\\\')
        for char in ['[', ']', '(', ')']:
            escaped = escaped.replace(char, f"\\{char}")
        return escaped

    def _generate_markdown(self, article: AdaptedArticle, timestamp: datetime) -> str:
        """
        Generate Jekyll markdown with frontmatter

        Args:
            article: Article dict with all content
            timestamp: datetime object for consistent timestamping
        """

        sources = article.sources or []
        normalized_sources = self._normalize_sources(sources)
        rendered_sources = [self._render_source(source, url) for source, url in normalized_sources]

        # Escape title and sources for YAML
        escaped_title = self._escape_yaml_string(article.title)
        escaped_sources = self._escape_yaml_string(', '.join(rendered_sources))

        # YAML frontmatter
        # Use Jekyll-compatible date format (without microseconds)
        date_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        frontmatter = f"""---
title: "{escaped_title}"
date: {date_str}
level: {article.level}
topics: {self._format_topics(article)}
sources: "{escaped_sources}"
reading_time: {article.reading_time}
---

"""

        # Article content
        content = article.content

        # Vocabulary section
        vocabulary = self._format_vocabulary(article.vocabulary)

        # Attribution
        sources_list = rendered_sources
        attribution = f"""

---
*Fuentes: {', '.join(sources_list)}*
*Artículo educativo generado con fines de aprendizaje de idiomas.*
"""

        # Combine all parts
        markdown = frontmatter + content + vocabulary + attribution

        return markdown

    def _format_topics(self, article: AdaptedArticle) -> str:
        """Extract and format topics from article as valid YAML"""
        import json

        # Try to infer topics from article topic data
        # Use 'or {}' to handle None case (when topic is explicitly None)
        topic_data = article.topic
        keywords = topic_data.keywords if topic_data else []

        if keywords:
            # Take first 3 keywords, lowercased
            topics = [k.lower() for k in keywords[:3]]
            # Use JSON serialization for proper YAML compatibility
            # This handles apostrophes, quotes, and special characters correctly
            return json.dumps(topics)

        # Fallback: generic topic
        return '["general"]'

    def _format_vocabulary(self, vocabulary: Dict[str, str]) -> str:
        """Format vocabulary section"""
        if not vocabulary:
            return ""

        vocab_lines = ["", "## Vocabulario", ""]

        for spanish, english in vocabulary.items():
            vocab_lines.append(f"- **{spanish}** - {english}")

        return '\n'.join(vocab_lines)
