"""
Publisher Component

Saves approved articles as Jekyll markdown files with YAML frontmatter.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict
import re


class Publisher:
    """Publishes articles to Jekyll format"""

    def __init__(self, config: Dict, logger: logging.Logger, dry_run: bool = False):
        self.config = config
        self.logger = logger.getChild('Publisher')
        self.dry_run = dry_run

        # Output directory
        self.output_dir = Path(config.get('output', {}).get('path', 'output/_posts'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Publisher initialized (dry_run={dry_run}, output={self.output_dir})")

    def save_article(self, article: Dict) -> bool:
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

    def _generate_filename(self, article: Dict, timestamp: datetime) -> str:
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
        title = article['title']
        slug = self._slugify(title)[:50]  # Max 50 chars

        level = article['level'].lower()

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

    def _generate_markdown(self, article: Dict, timestamp: datetime) -> str:
        """
        Generate Jekyll markdown with frontmatter

        Args:
            article: Article dict with all content
            timestamp: datetime object for consistent timestamping
        """

        # Escape title and sources for YAML
        escaped_title = self._escape_yaml_string(article['title'])
        escaped_sources = self._escape_yaml_string(', '.join(article.get('sources', [])))

        # YAML frontmatter
        frontmatter = f"""---
title: "{escaped_title}"
date: {timestamp.isoformat()}
level: {article['level']}
topics: {self._format_topics(article)}
sources: "{escaped_sources}"
reading_time: {article.get('reading_time', 3)}
---

"""

        # Article content
        content = article['content']

        # Vocabulary section
        vocabulary = self._format_vocabulary(article.get('vocabulary', {}))

        # Attribution
        sources_list = article.get('sources', [])
        attribution = f"""

---
*Fuentes: {', '.join(sources_list)}*
*Artículo educativo generado con fines de aprendizaje de idiomas.*
"""

        # Combine all parts
        markdown = frontmatter + content + vocabulary + attribution

        return markdown

    def _format_topics(self, article: Dict) -> str:
        """Extract and format topics from article as valid YAML"""
        import json

        # Try to infer topics from article topic data
        topic_data = article.get('topic', {})
        keywords = topic_data.get('keywords', [])

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
