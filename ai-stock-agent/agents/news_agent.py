"""
News Sentiment Agent - Analyzes news and market sentiment for stocks.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import os

logger = logging.getLogger(__name__)


class NewsAgent:
    """Fetches and analyzes news sentiment for stocks."""

    def __init__(self):
        """Initialize the News Agent."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch_news(self, ticker: str, company_name: str = None) -> List[Dict[str, Any]]:
        """
        Fetch recent news for a stock.

        Args:
            ticker: Stock ticker symbol
            company_name: Company name for better search

        Returns:
            List of news articles with title, source, date, url
        """
        news_items = []

        try:
            # Try Google Finance first
            news_items.extend(self._fetch_google_finance_news(ticker))

            # Try Yahoo Finance
            news_items.extend(self._fetch_yahoo_finance_news(ticker))

            logger.info(f"Fetched {len(news_items)} news items for {ticker}")

        except Exception as e:
            logger.error(f"Error fetching news for {ticker}: {str(e)}")

        return news_items[:10]  # Return top 10 most recent

    def _fetch_google_finance_news(self, ticker: str) -> List[Dict[str, Any]]:
        """Fetch news from Google Finance."""
        news_items = []

        try:
            url = f"https://www.google.com/finance/quote/{ticker}:NASDAQ"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Find news articles (structure may vary)
                articles = soup.find_all('div', class_='yY3Lee')

                for article in articles[:5]:
                    try:
                        title_elem = article.find('div', class_='Yfwt5')
                        source_elem = article.find('div', class_='sfyJob')

                        if title_elem:
                            news_items.append({
                                'title': title_elem.get_text(strip=True),
                                'source': source_elem.get_text(strip=True) if source_elem else 'Google Finance',
                                'date': datetime.now().isoformat(),
                                'url': url
                            })
                    except Exception as e:
                        logger.debug(f"Error parsing article: {e}")
                        continue

        except Exception as e:
            logger.debug(f"Google Finance fetch failed: {e}")

        return news_items

    def _fetch_yahoo_finance_news(self, ticker: str) -> List[Dict[str, Any]]:
        """Fetch news from Yahoo Finance RSS."""
        news_items = []

        try:
            # Yahoo Finance news search
            url = f"https://finance.yahoo.com/quote/{ticker}"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Find news articles
                articles = soup.find_all('h3', class_='Mb(5px)')

                for article in articles[:5]:
                    try:
                        link = article.find('a')
                        if link:
                            news_items.append({
                                'title': link.get_text(strip=True),
                                'source': 'Yahoo Finance',
                                'date': datetime.now().isoformat(),
                                'url': f"https://finance.yahoo.com{link.get('href', '')}"
                            })
                    except Exception as e:
                        logger.debug(f"Error parsing Yahoo article: {e}")
                        continue

        except Exception as e:
            logger.debug(f"Yahoo Finance fetch failed: {e}")

        return news_items

    def analyze_sentiment(self, news_items: List[Dict[str, Any]], llm_analyze: callable) -> Dict[str, Any]:
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
                'sentiment_score': 0.5,  # Neutral
                'sentiment': 'neutral',
                'summary': 'No recent news available',
                'key_topics': []
            }

        # Prepare news summary for LLM
        news_text = "\n\n".join([
            f"- {item['title']} ({item['source']})"
            for item in news_items
        ])

        prompt = f"""Analyze the sentiment of these recent news headlines about a stock:

{news_text}

Provide:
1. Overall sentiment (bullish/neutral/bearish)
2. Sentiment score (0.0 = very bearish, 0.5 = neutral, 1.0 = very bullish)
3. Key topics or concerns mentioned
4. Brief summary (2-3 sentences)

Return as JSON:
{{
    "sentiment": "bullish/neutral/bearish",
    "sentiment_score": 0.0-1.0,
    "key_topics": ["topic1", "topic2"],
    "summary": "brief summary"
}}"""

        try:
            result = llm_analyze(prompt)

            # Ensure score is in valid range
            result['sentiment_score'] = max(0.0, min(1.0, result.get('sentiment_score', 0.5)))

            return result

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {
                'sentiment_score': 0.5,
                'sentiment': 'neutral',
                'summary': f'Error analyzing {len(news_items)} news items',
                'key_topics': []
            }

    def get_news_analysis(self, ticker: str, company_name: str, llm_analyze: callable) -> Dict[str, Any]:
        """
        Get complete news analysis for a stock.

        Args:
            ticker: Stock ticker
            company_name: Company name
            llm_analyze: LLM analysis function

        Returns:
            Complete news analysis
        """
        news_items = self.fetch_news(ticker, company_name)
        sentiment = self.analyze_sentiment(news_items, llm_analyze)

        return {
            'news_count': len(news_items),
            'news_items': news_items,
            'sentiment': sentiment['sentiment'],
            'sentiment_score': sentiment['sentiment_score'],
            'key_topics': sentiment.get('key_topics', []),
            'summary': sentiment.get('summary', '')
        }


# Singleton instance
_news_agent_instance = None


def get_news_agent() -> NewsAgent:
    """Get or create the NewsAgent singleton."""
    global _news_agent_instance
    if _news_agent_instance is None:
        _news_agent_instance = NewsAgent()
    return _news_agent_instance
