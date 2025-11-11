"""
Topic Discovery Component

Discovers newsworthy topics from multiple sources using:
- RSS feeds
- Wikipedia trending
- Google Trends
- SpaCy NER for entity extraction
"""

import spacy
import feedparser
import requests
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import re


class TopicDiscoverer:
    """Discovers topics from multiple Spanish sources"""
    
    def __init__(self, config: Dict, logger: logging.Logger):
        self.config = config
        self.logger = logger.getChild('TopicDiscoverer')
        self.sources = config.get('sources_list', [])
        
        # Load SpaCy Spanish model
        try:
            self.nlp = spacy.load("es_core_news_sm")
        except OSError:
            self.logger.error("SpaCy Spanish model not found. Install with: python -m spacy download es_core_news_sm")
            raise
        
        # Learner-friendly topics
        self.friendly_keywords = {
            'cultura', 'arte', 'música', 'deporte', 'fútbol', 'cine', 'festival',
            'comida', 'gastronomía', 'turismo', 'viaje', 'historia', 'tradición',
            'celebración', 'familia', 'educación', 'libro', 'película'
        }
        
        # Topics to avoid
        self.avoid_keywords = {
            'guerra', 'ataque', 'militar', 'bomba', 'terrorismo',
            'blockchain', 'criptomoneda', 'algoritmo'
        }
    
    def discover(self, limit: int = 10) -> List[Dict]:
        """
        Main entry point: discover topics

        Returns: List of ranked topics
        """
        self.logger.info(f"Starting topic discovery from {len(self.sources)} sources")

        # Step 1: Fetch all headlines in parallel
        all_headlines = []

        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all fetch tasks
            future_to_source = {
                executor.submit(self._fetch_source, source): source
                for source in self.sources
            }

            # Collect results as they complete
            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    headlines = future.result()
                    all_headlines.extend(headlines)
                    self.logger.debug(f"Fetched {len(headlines)} headlines from {source['name']}")
                except Exception as e:
                    self.logger.warning(f"Failed to fetch {source.get('name', 'unknown')}: {e}")

        self.logger.info(f"Fetched {len(all_headlines)} total headlines")
        
        if not all_headlines:
            return []
        
        # Step 2: Extract entities
        entities_by_headline = {}
        for headline in all_headlines:
            entities = self._extract_entities(headline['text'])
            entities_by_headline[headline['id']] = {
                'headline': headline,
                'entities': entities
            }
        
        # Step 3: Cluster topics
        topics = self._cluster_topics(entities_by_headline)
        self.logger.info(f"Found {len(topics)} candidate topics")
        
        # Step 4: Rank topics
        ranked = self._rank_topics(topics)
        
        return ranked[:limit]
    
    def _fetch_source(self, source: Dict) -> List[Dict]:
        """Fetch headlines from one source"""
        source_type = source['type']
        
        if source_type == 'rss':
            return self._fetch_rss(source)
        elif source_type == 'wikipedia_trending':
            return self._fetch_wikipedia_trending(source)
        elif source_type == 'google_trends':
            return self._fetch_google_trends(source)
        else:
            self.logger.warning(f"Unknown source type: {source_type}")
            return []
    
    def _fetch_rss(self, source: Dict) -> List[Dict]:
        """Fetch from RSS feed"""
        try:
            feed = feedparser.parse(source['url'])
            headlines = []
            
            for entry in feed.entries[:20]:
                headlines.append({
                    'id': entry.get('id', entry.link),
                    'text': entry.title,
                    'url': entry.link,
                    'source': source['name'],
                    'published': entry.get('published_parsed', None),
                    'summary': entry.get('summary', '')[:200]
                })
            
            return headlines
        except Exception as e:
            self.logger.warning(f"RSS fetch error for {source['name']}: {e}")
            return []
    
    def _fetch_wikipedia_trending(self, source: Dict) -> List[Dict]:
        """Fetch trending Wikipedia articles"""
        lang = source.get('lang', 'es')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y/%m/%d')
        url = f"https://{lang}.wikipedia.org/api/rest_v1/feed/featured/{yesterday}"

        try:
            # Wikipedia API requires a User-Agent header
            headers = {
                'User-Agent': 'AutoSpanishBot/1.0 (https://github.com/autospanishblog; Educational content bot)'
            }
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            headlines = []
            if 'mostread' in data and 'articles' in data['mostread']:
                for article in data['mostread']['articles'][:10]:
                    headlines.append({
                        'id': article['title'],
                        'text': article['title'],
                        'url': f"https://{lang}.wikipedia.org/wiki/{article['title']}",
                        'source': 'Wikipedia ES',
                        'published': None,
                        'summary': article.get('extract', '')[:200]
                    })
            
            return headlines
        except Exception as e:
            self.logger.warning(f"Wikipedia trending error: {e}")
            return []
    
    def _fetch_google_trends(self, source: Dict) -> List[Dict]:
        """Fetch Google Trends RSS"""
        geo = source.get('geo', 'ES')
        url = f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={geo}"
        
        try:
            feed = feedparser.parse(url)
            headlines = []
            
            for entry in feed.entries[:15]:
                headlines.append({
                    'id': entry.title,
                    'text': entry.title,
                    'url': entry.link,
                    'source': f'Google Trends {geo}',
                    'published': None,
                    'summary': entry.get('description', '')[:200]
                })
            
            return headlines
        except Exception as e:
            self.logger.warning(f"Google Trends error: {e}")
            return []
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extract named entities using SpaCy"""
        doc = self.nlp(text)
        
        entities = []
        for ent in doc.ents:
            # Only relevant entity types
            if ent.label_ in ['PER', 'LOC', 'ORG', 'MISC']:
                if len(ent.text) > 2:  # Filter very short
                    entities.append(ent.text)
        
        return entities
    
    def _cluster_topics(self, entities_by_headline: Dict) -> List[Dict]:
        """Find topics appearing in multiple sources"""
        entity_to_headlines = defaultdict(list)
        entity_to_sources = defaultdict(set)
        
        for headline_id, data in entities_by_headline.items():
            headline = data['headline']
            entities = data['entities']
            
            for entity in entities:
                normalized = entity.lower()
                entity_to_headlines[normalized].append(headline)
                entity_to_sources[normalized].add(headline['source'])
        
        # Find entities in 3+ sources
        topics = []
        for entity, headlines in entity_to_headlines.items():
            sources = entity_to_sources[entity]
            
            if len(sources) >= 3:  # Cross-source validation
                topics.append({
                    'title': entity.title(),
                    'mentions': len(headlines),
                    'sources': list(sources),
                    'headlines': headlines,
                    'keywords': self._extract_keywords(headlines)
                })
        
        return topics
    
    def _extract_keywords(self, headlines: List[Dict]) -> List[str]:
        """Extract common keywords from headlines"""
        all_text = ' '.join([h['text'] + ' ' + h.get('summary', '') for h in headlines])
        doc = self.nlp(all_text)
        
        # Get entities
        entities = [ent.text for ent in doc.ents if len(ent.text) > 2]
        
        # Count and return top 10
        counter = Counter(entities)
        return [word for word, count in counter.most_common(10)]
    
    def _rank_topics(self, topics: List[Dict]) -> List[Dict]:
        """Rank topics by learnability"""
        for topic in topics:
            score = 0
            
            # Base: more sources = more important
            score += len(topic['sources']) * 3
            
            # Mentions matter (capped)
            score += min(topic['mentions'], 10) * 2
            
            # Check keywords
            keywords_lower = [k.lower() for k in topic['keywords']]
            keywords_text = ' '.join(keywords_lower)
            
            # Learner-friendly bonus
            if any(kw in keywords_text for kw in self.friendly_keywords):
                score += 5
            
            # Avoid penalty
            if any(kw in keywords_text for kw in self.avoid_keywords):
                score -= 10
            
            topic['score'] = score
        
        # Sort by score
        return sorted(topics, key=lambda t: t['score'], reverse=True)
