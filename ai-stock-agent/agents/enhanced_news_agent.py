"""
Enhanced News Agent - Integrates multiple professional news APIs.
Provides reliable, structured news data with sentiment analysis.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import os
import requests

logger = logging.getLogger(__name__)


class EnhancedNewsAgent:
    """
    Fetches news from multiple professional APIs:
    1. NewsAPI (newsapi.org) - General news
    2. Finnhub (finnhub.io) - Financial news
    3. Alpha Vantage - News sentiment

    Falls back to web scraping if APIs unavailable.
    """

    def __init__(self):
        """Initialize the Enhanced News Agent."""
        self.newsapi_key = os.getenv('NEWSAPI_KEY')
        self.finnhub_key = os.getenv('FINNHUB_KEY')
        self.alphavantage_key = os.getenv('ALPHAVANTAGE_KEY')

        # Track which APIs are available
        self.has_newsapi = bool(self.newsapi_key)
        self.has_finnhub = bool(self.finnhub_key)
        self.has_alphavantage = bool(self.alphavantage_key)

        if not any([self.has_newsapi, self.has_finnhub, self.has_alphavantage]):
            logger.warning("No news API keys found. Will use fallback web scraping.")
        else:
            apis = []
            if self.has_newsapi: apis.append("NewsAPI")
            if self.has_finnhub: apis.append("Finnhub")
            if self.has_alphavantage: apis.append("Alpha Vantage")
            logger.info(f"News APIs available: {', '.join(apis)}")

    def fetch_news(self, ticker: str, company_name: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        Fetch news from all available sources.

        Args:
            ticker: Stock ticker symbol
            company_name: Company name for better search
            days: Number of days to look back

        Returns:
            List of news articles with title, source, date, url, description
        """
        all_news = []

        # Try NewsAPI first (best general news coverage)
        if self.has_newsapi:
            try:
                newsapi_articles = self._fetch_from_newsapi(ticker, company_name, days)
                all_news.extend(newsapi_articles)
                logger.info(f"NewsAPI: Found {len(newsapi_articles)} articles")
            except Exception as e:
                logger.error(f"NewsAPI error: {str(e)}")

        # Try Finnhub (best for financial news)
        if self.has_finnhub:
            try:
                finnhub_articles = self._fetch_from_finnhub(ticker, days)
                all_news.extend(finnhub_articles)
                logger.info(f"Finnhub: Found {len(finnhub_articles)} articles")
            except Exception as e:
                logger.error(f"Finnhub error: {str(e)}")

        # Try Alpha Vantage (includes sentiment scores)
        if self.has_alphavantage:
            try:
                av_articles = self._fetch_from_alphavantage(ticker)
                all_news.extend(av_articles)
                logger.info(f"Alpha Vantage: Found {len(av_articles)} articles")
            except Exception as e:
                logger.error(f"Alpha Vantage error: {str(e)}")

        # Fallback to web scraping if no API news found
        if not all_news:
            logger.warning("No news from APIs, falling back to web scraping")
            all_news = self._fallback_web_scraping(ticker, company_name)

        # Remove duplicates based on title similarity
        all_news = self._deduplicate_news(all_news)

        # Sort by date (newest first)
        all_news.sort(key=lambda x: x.get('date', ''), reverse=True)

        logger.info(f"Total unique articles found: {len(all_news)}")
        return all_news[:20]  # Return top 20 most recent

    def _fetch_from_newsapi(self, ticker: str, company_name: str, days: int) -> List[Dict[str, Any]]:
        """Fetch news from NewsAPI."""
        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        # Search for company name and ticker
        query = f'"{company_name}" OR {ticker}'

        url = 'https://newsapi.org/v2/everything'
        params = {
            'q': query,
            'apiKey': self.newsapi_key,
            'language': 'en',
            'sortBy': 'publishedAt',
            'from': from_date,
            'pageSize': 20
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        articles = []
        for article in data.get('articles', []):
            articles.append({
                'title': article.get('title', ''),
                'description': article.get('description', ''),
                'source': article.get('source', {}).get('name', 'NewsAPI'),
                'url': article.get('url', ''),
                'date': article.get('publishedAt', ''),
                'api': 'NewsAPI'
            })

        return articles

    def _fetch_from_finnhub(self, ticker: str, days: int) -> List[Dict[str, Any]]:
        """Fetch company news from Finnhub."""
        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        to_date = datetime.now().strftime('%Y-%m-%d')

        url = 'https://finnhub.io/api/v1/company-news'
        params = {
            'symbol': ticker,
            'from': from_date,
            'to': to_date,
            'token': self.finnhub_key
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        articles = []
        for article in data:
            # Convert timestamp to ISO format
            date_str = datetime.fromtimestamp(article.get('datetime', 0)).isoformat()

            articles.append({
                'title': article.get('headline', ''),
                'description': article.get('summary', ''),
                'source': article.get('source', 'Finnhub'),
                'url': article.get('url', ''),
                'date': date_str,
                'api': 'Finnhub'
            })

        return articles

    def _fetch_from_alphavantage(self, ticker: str) -> List[Dict[str, Any]]:
        """Fetch news with sentiment from Alpha Vantage."""
        url = 'https://www.alphavantage.co/query'
        params = {
            'function': 'NEWS_SENTIMENT',
            'tickers': ticker,
            'apikey': self.alphavantage_key,
            'limit': 50
        }

        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        articles = []
        for article in data.get('feed', []):
            # Extract ticker-specific sentiment if available
            ticker_sentiments = article.get('ticker_sentiment', [])
            ticker_sentiment = next(
                (ts for ts in ticker_sentiments if ts.get('ticker') == ticker),
                {}
            )

            articles.append({
                'title': article.get('title', ''),
                'description': article.get('summary', ''),
                'source': article.get('source', 'Alpha Vantage'),
                'url': article.get('url', ''),
                'date': article.get('time_published', ''),
                'sentiment_score': float(ticker_sentiment.get('ticker_sentiment_score', 0)),
                'sentiment_label': ticker_sentiment.get('ticker_sentiment_label', 'Neutral'),
                'api': 'AlphaVantage'
            })

        return articles

    def _fallback_web_scraping(self, ticker: str, company_name: str) -> List[Dict[str, Any]]:
        """Fallback to original web scraping method."""
        from agents.news_agent import get_news_agent

        # Use original news agent as fallback
        original_agent = get_news_agent()
        return original_agent.fetch_news(ticker, company_name)

    def _deduplicate_news(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate articles based on title similarity."""
        seen_titles = set()
        unique_articles = []

        for article in articles:
            title = article.get('title', '').lower().strip()

            # Skip if empty title
            if not title:
                continue

            # Simple deduplication: check if title already seen
            # (Could be enhanced with fuzzy matching)
            title_key = title[:50]  # First 50 chars as key

            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_articles.append(article)

        return unique_articles

    def analyze_sentiment(
        self,
        news_items: List[Dict[str, Any]],
        llm_analyze: callable
    ) -> Dict[str, Any]:
        """
        Analyze sentiment of news articles using LLM.

        Args:
            news_items: List of news articles
            llm_analyze: Function to call LLM for analysis

        Returns:
            Sentiment analysis results
        """
        if not news_items:
            return {
                'sentiment_score': 0.5,
                'sentiment': 'neutral',
                'summary': 'No recent news available',
                'key_topics': [],
                'confidence': 0.0
            }

        # Check if we have Alpha Vantage sentiment scores
        av_sentiments = [
            article.get('sentiment_score', 0)
            for article in news_items
            if article.get('api') == 'AlphaVantage' and 'sentiment_score' in article
        ]

        # Prepare news summary for LLM
        news_text = "\n\n".join([
            f"[{item.get('source', 'Unknown')}] {item.get('title', '')} - {item.get('description', '')[:200]}"
            for item in news_items[:15]  # Use top 15 for analysis
        ])

        prompt = f"""Analyze the sentiment of these recent news articles about a stock:

{news_text}

Provide:
1. Overall sentiment (bullish/neutral/bearish)
2. Sentiment score (0.0 = very bearish, 0.5 = neutral, 1.0 = very bullish)
3. Key topics or themes mentioned (3-5 topics)
4. Brief summary (2-3 sentences)
5. Confidence in sentiment assessment (0.0-1.0)

{"Note: Some articles have pre-calculated sentiment scores from Alpha Vantage that you should consider." if av_sentiments else ""}

Return as JSON:
{{
    "sentiment": "bullish/neutral/bearish",
    "sentiment_score": 0.0-1.0,
    "key_topics": ["topic1", "topic2", "topic3"],
    "summary": "brief summary",
    "confidence": 0.0-1.0
}}"""

        try:
            result = llm_analyze(prompt)

            # If we have Alpha Vantage scores, blend them with LLM analysis
            if av_sentiments:
                av_avg = sum(av_sentiments) / len(av_sentiments)
                # AV scores are -1 to +1, convert to 0-1
                av_normalized = (av_avg + 1) / 2

                # Weighted average: 60% LLM, 40% Alpha Vantage
                llm_score = result.get('sentiment_score', 0.5)
                blended_score = (llm_score * 0.6) + (av_normalized * 0.4)
                result['sentiment_score'] = blended_score

                logger.info(f"Blended sentiment: LLM={llm_score:.2f}, AV={av_normalized:.2f}, Final={blended_score:.2f}")

            # Ensure score is in valid range
            result['sentiment_score'] = max(0.0, min(1.0, result.get('sentiment_score', 0.5)))

            # Ensure confidence exists
            result['confidence'] = max(0.0, min(1.0, result.get('confidence', 0.7)))

            return result

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")

            # Fallback: use Alpha Vantage scores if available
            if av_sentiments:
                av_avg = sum(av_sentiments) / len(av_sentiments)
                av_normalized = (av_avg + 1) / 2

                if av_normalized > 0.6:
                    sentiment = 'bullish'
                elif av_normalized < 0.4:
                    sentiment = 'bearish'
                else:
                    sentiment = 'neutral'

                return {
                    'sentiment_score': av_normalized,
                    'sentiment': sentiment,
                    'summary': f'Sentiment based on {len(av_sentiments)} Alpha Vantage scores',
                    'key_topics': [],
                    'confidence': 0.6
                }

            return {
                'sentiment_score': 0.5,
                'sentiment': 'neutral',
                'summary': f'Error analyzing {len(news_items)} news items: {str(e)}',
                'key_topics': [],
                'confidence': 0.0
            }

    def get_news_analysis(
        self,
        ticker: str,
        company_name: str,
        llm_analyze: callable,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get complete news analysis for a stock.

        Args:
            ticker: Stock ticker
            company_name: Company name
            llm_analyze: LLM analysis function
            days: Number of days to look back

        Returns:
            Complete news analysis
        """
        news_items = self.fetch_news(ticker, company_name, days)
        sentiment = self.analyze_sentiment(news_items, llm_analyze)

        return {
            'news_count': len(news_items),
            'news_items': news_items,
            'sentiment': sentiment['sentiment'],
            'sentiment_score': sentiment['sentiment_score'],
            'key_topics': sentiment.get('key_topics', []),
            'summary': sentiment.get('summary', ''),
            'confidence': sentiment.get('confidence', 0.7),
            'data_sources': self._get_active_sources()
        }

    def _get_active_sources(self) -> List[str]:
        """Get list of active data sources."""
        sources = []
        if self.has_newsapi:
            sources.append('NewsAPI')
        if self.has_finnhub:
            sources.append('Finnhub')
        if self.has_alphavantage:
            sources.append('Alpha Vantage')
        if not sources:
            sources.append('Web Scraping')
        return sources


# Singleton instance
_enhanced_news_agent_instance = None


def get_enhanced_news_agent() -> EnhancedNewsAgent:
    """Get or create the EnhancedNewsAgent singleton."""
    global _enhanced_news_agent_instance
    if _enhanced_news_agent_instance is None:
        _enhanced_news_agent_instance = EnhancedNewsAgent()
    return _enhanced_news_agent_instance
