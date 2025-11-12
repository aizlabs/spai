"""
Content Fetcher Test Script

Tests the ContentFetcher component with real topics from Topic Discovery.
"""

from scripts.config import load_config
from scripts.logger import setup_logger
from scripts.topic_discovery import TopicDiscoverer
from scripts.content_fetcher import ContentFetcher


def test_content_fetcher():
    """Test the content fetcher component"""
    print("=" * 60)
    print("Testing Content Fetcher Component")
    print("=" * 60)

    # Load config and setup logger
    config = load_config('local')
    logger = setup_logger(config, 'test-fetcher')

    print("\n✓ Config loaded successfully")
    print("✓ Logger initialized")

    # Initialize components
    discoverer = TopicDiscoverer(config, logger)
    fetcher = ContentFetcher(config, logger)

    print("\n" + "-" * 60)
    print("Step 1: Discovering topics...")
    print("-" * 60)

    # Discover topics
    topics = discoverer.discover(limit=3)  # Test with 3 topics

    if not topics:
        print("✗ No topics found!")
        return

    print(f"\n✓ Discovered {len(topics)} topics")

    # Test fetching for each topic
    print("\n" + "-" * 60)
    print("Step 2: Fetching article sources...")
    print("-" * 60)

    results = []
    for i, topic in enumerate(topics, 1):
        print(f"\nTopic {i}: {topic['title']}")
        print(f"  Headlines available: {len(topic['headlines'])}")

        # Fetch sources
        sources = fetcher.fetch_topic_sources(topic)

        results.append({
            'topic': topic['title'],
            'sources_count': len(sources),
            'sources': sources
        })

        # Validation
        if len(sources) >= 3:
            print(f"  ✓ Fetched {len(sources)} sources (minimum met)")
        elif len(sources) > 0:
            print(f"  ⚠ Fetched {len(sources)} sources (below minimum of 3)")
        else:
            print(f"  ✗ Failed to fetch any sources")

        # Show source details
        for j, source in enumerate(sources, 1):
            print(f"    {j}. {source['source']:25} ({source['word_count']} words)")
            if source['title']:
                print(f"       Title: {source['title'][:50]}...")

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    total_sources = sum(r['sources_count'] for r in results)
    successful_topics = sum(1 for r in results if r['sources_count'] >= 3)

    print(f"\nTopics tested: {len(results)}")
    print(f"Topics with 3+ sources: {successful_topics}/{len(results)}")
    print(f"Total sources fetched: {total_sources}")
    print(f"Average sources per topic: {total_sources / len(results):.1f}")

    # Detailed validation
    print("\n" + "-" * 60)
    print("Validation")
    print("-" * 60)

    all_pass = True

    for i, result in enumerate(results, 1):
        topic_name = result['topic']
        sources = result['sources']

        print(f"\nTopic {i}: {topic_name}")

        # Check minimum sources
        if len(sources) >= 3:
            print(f"  ✓ Minimum sources: {len(sources)}/3")
        else:
            print(f"  ✗ Minimum sources: {len(sources)}/3")
            all_pass = False

        # Check word counts
        for j, source in enumerate(sources, 1):
            wc = source['word_count']
            if 100 <= wc <= 300:
                print(f"  ✓ Source {j} word count: {wc} words")
            else:
                print(f"  ✗ Source {j} word count: {wc} words (expected 100-300)")
                all_pass = False

        # Check required fields
        for j, source in enumerate(sources, 1):
            required_fields = ['url', 'text', 'source', 'word_count']
            missing = [f for f in required_fields if f not in source]
            if not missing:
                print(f"  ✓ Source {j} has all required fields")
            else:
                print(f"  ✗ Source {j} missing fields: {missing}")
                all_pass = False

        # Check text content
        for j, source in enumerate(sources, 1):
            text = source['text']
            if text and len(text) > 50:
                print(f"  ✓ Source {j} has valid text content")
            else:
                print(f"  ✗ Source {j} has insufficient text")
                all_pass = False

    # Sample content display
    print("\n" + "-" * 60)
    print("Sample Content")
    print("-" * 60)

    if results and results[0]['sources']:
        sample = results[0]['sources'][0]
        print(f"\nSource: {sample['source']}")
        print(f"Title: {sample.get('title', 'N/A')}")
        print(f"Word count: {sample['word_count']}")
        print(f"URL: {sample['url'][:60]}...")
        print(f"\nFirst 200 characters of text:")
        print(sample['text'][:200] + "...")

    # Final result
    print("\n" + "=" * 60)
    if all_pass:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 60)


def main():
    """Entry point for CLI"""
    try:
        test_content_fetcher()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
