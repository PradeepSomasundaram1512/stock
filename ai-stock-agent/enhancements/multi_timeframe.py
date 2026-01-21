"""
Multi-Timeframe Analysis
Analyze hourly, daily, and weekly charts for maximum accuracy
"""

import logging
from typing import Dict, Any, List
import yfinance as yf
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)


class MultiTimeframeAnalyzer:
    """Analyze multiple timeframes for higher accuracy signals"""

    def __init__(self):
        """Initialize multi-timeframe analyzer"""
        pass

    def analyze(self, ticker: str) -> Dict[str, Any]:
        """
        Perform multi-timeframe analysis

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with analysis for each timeframe and overall signal
        """
        logger.info(f"Multi-timeframe analysis for {ticker}")

        result = {
            'ticker': ticker,
            'timestamp': datetime.now().isoformat(),
            'timeframes': {},
            'overall_signal': 'NEUTRAL',
            'confidence': 0.5,
            'alignment': 0,  # How many timeframes agree
            'explanation': ''
        }

        # Analyze each timeframe
        try:
            # 1-hour chart (intraday momentum)
            hourly = self._analyze_timeframe(ticker, period='5d', interval='1h', name='Hourly')
            result['timeframes']['hourly'] = hourly

            # Daily chart (short-term trend)
            daily = self._analyze_timeframe(ticker, period='3mo', interval='1d', name='Daily')
            result['timeframes']['daily'] = daily

            # Weekly chart (long-term trend)
            weekly = self._analyze_timeframe(ticker, period='1y', interval='1wk', name='Weekly')
            result['timeframes']['weekly'] = weekly

            # Calculate alignment
            signals = [hourly['signal'], daily['signal'], weekly['signal']]
            buy_count = signals.count('BUY')
            sell_count = signals.count('SELL')

            result['alignment'] = max(buy_count, sell_count)

            # Determine overall signal
            if buy_count >= 2:
                result['overall_signal'] = 'BUY'
                result['confidence'] = 0.70 + (buy_count - 2) * 0.15  # 0.70, 0.85, 1.0
                result['explanation'] = f"{buy_count}/3 timeframes bullish"
            elif sell_count >= 2:
                result['overall_signal'] = 'SELL'
                result['confidence'] = 0.70 + (sell_count - 2) * 0.15
                result['explanation'] = f"{sell_count}/3 timeframes bearish"
            else:
                result['overall_signal'] = 'HOLD'
                result['confidence'] = 0.50
                result['explanation'] = "Mixed signals across timeframes"

            # Perfect alignment bonus
            if buy_count == 3:
                result['confidence'] = 0.95
                result['explanation'] = "🔥 PERFECT ALIGNMENT: All 3 timeframes bullish!"
            elif sell_count == 3:
                result['confidence'] = 0.95
                result['explanation'] = "⚠️ PERFECT ALIGNMENT: All 3 timeframes bearish!"

            logger.info(f"{ticker}: {result['overall_signal']} ({result['confidence']*100:.0f}% confidence)")

        except Exception as e:
            logger.error(f"Error in multi-timeframe analysis: {e}")
            result['error'] = str(e)

        return result

    def _analyze_timeframe(self, ticker: str, period: str, interval: str, name: str) -> Dict[str, Any]:
        """
        Analyze a single timeframe

        Args:
            ticker: Stock ticker
            period: Data period (5d, 3mo, 1y)
            interval: Data interval (1h, 1d, 1wk)
            name: Timeframe name for display

        Returns:
            Timeframe analysis dictionary
        """
        try:
            # Fetch data
            data = yf.download(ticker, period=period, interval=interval, progress=False)

            if data.empty:
                return {
                    'name': name,
                    'signal': 'NEUTRAL',
                    'reason': 'No data available'
                }

            # Calculate key indicators
            close = data['Close']
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]  # Get first column if DataFrame
            current_price = float(close.iloc[-1])

            # Moving averages (adjusted for timeframe)
            if interval == '1h':
                short_window = 20  # ~1 day
                long_window = 50   # ~2.5 days
            elif interval == '1d':
                short_window = 20  # 20 days
                long_window = 50   # 50 days
            else:  # weekly
                short_window = 10  # 10 weeks
                long_window = 20   # 20 weeks

            sma_short = close.rolling(window=short_window).mean()
            sma_long = close.rolling(window=long_window).mean()

            # Current values (convert to float to avoid pandas scalar issues)
            sma_short_val = float(sma_short.iloc[-1])
            sma_long_val = float(sma_long.iloc[-1])

            price_above_short = current_price > sma_short_val
            price_above_long = current_price > sma_long_val
            ma_bullish = sma_short_val > sma_long_val

            # RSI
            rsi = self._calculate_rsi(close, period=14)
            current_rsi = float(rsi.iloc[-1])

            # Trend strength
            trend_pct = float(((current_price / close.iloc[0]) - 1) * 100)

            # Determine signal
            bullish_count = sum([
                price_above_short,
                price_above_long,
                ma_bullish,
                30 < current_rsi < 70,  # Healthy RSI
                trend_pct > 0  # Positive trend
            ])

            if bullish_count >= 4:
                signal = 'BUY'
                reason = f"Strong bullish: {bullish_count}/5 indicators"
            elif bullish_count <= 1:
                signal = 'SELL'
                reason = f"Strong bearish: {5-bullish_count}/5 bearish indicators"
            else:
                signal = 'NEUTRAL'
                reason = f"Mixed: {bullish_count}/5 bullish"

            return {
                'name': name,
                'signal': signal,
                'reason': reason,
                'price': float(current_price),
                'rsi': float(current_rsi),
                'trend_pct': float(trend_pct),
                'above_short_ma': bool(price_above_short),
                'above_long_ma': bool(price_above_long),
                'ma_bullish': bool(ma_bullish)
            }

        except Exception as e:
            logger.error(f"Error analyzing {name} timeframe: {e}")
            return {
                'name': name,
                'signal': 'NEUTRAL',
                'reason': f'Error: {str(e)}'
            }

    def _calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def format_report(self, analysis: Dict[str, Any]) -> str:
        """
        Format multi-timeframe analysis as readable report

        Args:
            analysis: Analysis result from analyze()

        Returns:
            Formatted string report
        """
        report = "\n" + "="*70 + "\n"
        report += f"📊 MULTI-TIMEFRAME ANALYSIS: {analysis['ticker']}\n"
        report += "="*70 + "\n\n"

        # Overall signal
        symbol = "🟢" if analysis['overall_signal'] == 'BUY' else "🔴" if analysis['overall_signal'] == 'SELL' else "🟡"
        report += f"{symbol} OVERALL SIGNAL: {analysis['overall_signal']}\n"
        report += f"   Confidence: {analysis['confidence']*100:.0f}%\n"
        report += f"   Alignment: {analysis['alignment']}/3 timeframes agree\n"
        report += f"   {analysis['explanation']}\n\n"

        # Individual timeframes
        report += "TIMEFRAME BREAKDOWN:\n\n"

        for tf_name, tf_data in analysis['timeframes'].items():
            signal = tf_data['signal']
            symbol = "🟢" if signal == 'BUY' else "🔴" if signal == 'SELL' else "🟡"

            report += f"{symbol} {tf_data['name']}:\n"
            report += f"   Signal: {signal}\n"
            report += f"   Price: ${tf_data.get('price', 0):.2f}\n"
            report += f"   RSI: {tf_data.get('rsi', 50):.1f}\n"
            report += f"   Trend: {tf_data.get('trend_pct', 0):+.2f}%\n"
            report += f"   Reason: {tf_data['reason']}\n\n"

        report += "="*70 + "\n"

        # Trading recommendation
        if analysis['overall_signal'] == 'BUY' and analysis['confidence'] >= 0.85:
            report += "💡 STRONG BUY - High confidence across timeframes\n"
        elif analysis['overall_signal'] == 'BUY':
            report += "💡 Moderate BUY - Some bullish signals\n"
        elif analysis['overall_signal'] == 'SELL' and analysis['confidence'] >= 0.85:
            report += "💡 STRONG SELL - High confidence bearish trend\n"
        elif analysis['overall_signal'] == 'SELL':
            report += "💡 Moderate SELL - Some bearish signals\n"
        else:
            report += "💡 HOLD - Wait for clearer signals\n"

        report += "="*70 + "\n"

        return report


# Singleton instance
_mtf_analyzer = None


def get_mtf_analyzer() -> MultiTimeframeAnalyzer:
    """Get or create multi-timeframe analyzer"""
    global _mtf_analyzer
    if _mtf_analyzer is None:
        _mtf_analyzer = MultiTimeframeAnalyzer()
    return _mtf_analyzer
