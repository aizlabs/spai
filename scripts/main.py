#!/usr/bin/env python3
"""
AutoSpanishBlog - Main Pipeline Entry Point

This script orchestrates the entire content generation pipeline:
1. Topic Discovery
2. Content Fetching
3. Article Generation
4. Quality Gate
5. Publishing

Usage:
    uv run spai-pipeline              # Run full pipeline
    ENVIRONMENT=local uv run spai-pipeline
    DRY_RUN=true uv run spai-pipeline  # Generate but don't publish
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from logger import setup_logger
from topic_discovery import TopicDiscoverer
from content_fetcher import ContentFetcher
from content_generator import ContentGenerator
from quality_gate import QualityGate
from publisher import Publisher


def detect_environment() -> str:
    """Detect execution environment"""
    if os.getenv('GITHUB_ACTIONS') == 'true':
        return 'production'
    return os.getenv('ENVIRONMENT', 'local')


def create_run_id() -> str:
    """Generate unique run identifier"""
    env = detect_environment()
    timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    return f"{env}-{timestamp}"


def main():
    """Main pipeline execution"""

    # Setup
    run_id = create_run_id()
    environment = detect_environment()
    dry_run = os.getenv('DRY_RUN', 'false').lower() == 'true'
    start_time = time.time()

    # Load configuration
    config = load_config(environment)

    # Initialize logging
    logger = setup_logger(config, run_id)

    print("=" * 60)
    print("AutoSpanishBlog - Content Generation Pipeline")
    print("=" * 60)
    print(f"Run ID: {run_id}")
    print(f"Environment: {environment}")
    print(f"Dry Run: {dry_run}")
    print(f"Provider: {config['llm']['provider']}")
    print(f"Articles per run: {config['generation']['articles_per_run']}")
    print(f"Levels: {config['generation']['levels']}")
    print("=" * 60)
    print()

    logger.info(f"Pipeline started - {run_id}")

    # Statistics
    stats = {
        'attempted': 0,
        'published': 0,
        'rejected': 0,
        'regenerations': 0,
        'total_quality_score': 0.0
    }

    try:
        # Initialize pipeline components
        logger.info("Initializing components...")
        discoverer = TopicDiscoverer(config, logger)
        fetcher = ContentFetcher(config, logger)
        generator = ContentGenerator(config, logger)
        quality_gate = QualityGate(config, logger)
        publisher = Publisher(config, logger, dry_run=dry_run)

        print("✓ All components initialized")
        print()

        # Phase 1: Topic Discovery
        print("-" * 60)
        print("Phase 1: Topic Discovery")
        print("-" * 60)

        topics = discoverer.discover(limit=10)
        print(f"✓ Discovered {len(topics)} topics")
        print()

        if not topics:
            raise Exception("No topics discovered")

        # Phase 2-5: Process each topic
        target_articles = config['generation']['articles_per_run']
        levels = config['generation']['levels']

        for topic in topics:
            if stats['published'] >= target_articles:
                print(f"\n✓ Target reached: {target_articles} articles published")
                break

            print("=" * 60)
            print(f"Topic: {topic['title']}")
            print(f"Sources: {len(topic['sources'])} | Mentions: {topic['mentions']}")
            print("=" * 60)
            print()

            # Phase 2: Fetch Sources
            print("Phase 2: Fetching article sources...")
            sources = fetcher.fetch_topic_sources(topic)

            if len(sources) < 3:
                print(f"⚠ Insufficient sources ({len(sources)}/3), skipping topic")
                print()
                continue

            print(f"✓ Fetched {len(sources)} sources")
            for i, s in enumerate(sources, 1):
                print(f"  {i}. {s['source']:25} ({s['word_count']} words)")
            print()

            # Generate articles for each level
            for level in levels:
                stats['attempted'] += 1

                print("-" * 60)
                print(f"Generating {level} article...")
                print("-" * 60)

                # Phase 3: Generate Article
                article = generator.generate_article(topic, sources, level)
                word_count = len(article['content'].split())

                print(f"✓ Generated: {article['title']}")
                print(f"  Word count: {word_count}")
                print(f"  Vocabulary: {len(article.get('vocabulary', {}))} words")
                print()

                # Phase 4: Quality Gate (with regeneration)
                print("Phase 4: Quality check...")
                final_article, quality_result = quality_gate.check_and_improve(
                    article,
                    generator,
                    topic,
                    sources
                )

                if final_article:
                    # Quality passed
                    stats['total_quality_score'] += quality_result.score
                    stats['regenerations'] += (quality_result.attempts - 1)

                    print(f"✅ Quality check passed!")
                    print(f"  Score: {quality_result.score:.1f}/10")
                    print(f"  Attempts: {quality_result.attempts}")
                    if quality_result.strengths:
                        print(f"  Strengths: {', '.join(quality_result.strengths[:2])}")
                    print()

                    # Phase 5: Publish
                    print("Phase 5: Publishing...")
                    published = publisher.save_article(final_article)

                    if published:
                        stats['published'] += 1
                        print(f"✅ Published successfully!")

                        # Check if target reached after each publication
                        if stats['published'] >= target_articles:
                            print(f"\n✓ Target reached: {target_articles} articles published")
                            break
                    else:
                        print(f"❌ Publishing failed")

                else:
                    # Quality failed
                    stats['rejected'] += 1
                    print(f"❌ Quality check failed")
                    print(f"  Score: {quality_result.score:.1f}/10 (min: {config['quality_gate']['min_score']})")
                    print(f"  Attempts: {quality_result.attempts}")
                    if quality_result.issues:
                        print(f"  Issues:")
                        for issue in quality_result.issues[:3]:
                            print(f"    - {issue}")

                print()

        # Pipeline completed successfully
        duration = time.time() - start_time
        avg_quality = stats['total_quality_score'] / stats['published'] if stats['published'] > 0 else 0

        print("=" * 60)
        print("Pipeline Completed Successfully")
        print("=" * 60)
        print()
        print(f"✨ Summary:")
        print(f"   Articles attempted:  {stats['attempted']}")
        print(f"   Articles published:  {stats['published']}")
        print(f"   Articles rejected:   {stats['rejected']}")
        print(f"   Success rate:        {stats['published']/stats['attempted']*100:.0f}%" if stats['attempted'] > 0 else "   Success rate:        N/A")
        print(f"   Regenerations:       {stats['regenerations']}")
        print(f"   Avg quality score:   {avg_quality:.1f}/10" if stats['published'] > 0 else "   Avg quality score:   N/A")
        print(f"   Duration:            {duration:.1f}s")
        print("=" * 60)

        logger.info(f"Pipeline completed - Published: {stats['published']}/{stats['attempted']}")

        return 0

    except Exception as e:
        duration = time.time() - start_time

        print()
        print("=" * 60)
        print("Pipeline Failed")
        print("=" * 60)
        print(f"Error: {str(e)}")
        print(f"Duration: {duration:.1f}s")
        print("=" * 60)

        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)

        return 1


if __name__ == "__main__":
    sys.exit(main())
