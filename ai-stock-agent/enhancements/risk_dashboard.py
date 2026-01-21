"""
Risk Management Dashboard
Real-time portfolio risk analysis and monitoring
"""

import logging
from typing import Dict, List, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


class RiskDashboard:
    """Portfolio risk analysis and monitoring"""

    def analyze_portfolio(self, positions: List[Dict[str, Any]],
                         account_value: float) -> Dict[str, Any]:
        """
        Comprehensive portfolio risk analysis

        Args:
            positions: List of position dictionaries
            account_value: Total account value

        Returns:
            Risk analysis dictionary
        """
        if not positions:
            return {'error': 'No positions to analyze'}

        analysis = {
            'total_value': account_value,
            'position_count': len(positions),
            'max_loss': 0,
            'max_gain': 0,
            'risk_reward_ratio': 0,
            'concentration_risk': {},
            'stop_loss_exposure': 0,
            'target_exposure': 0,
            'risk_level': 'UNKNOWN',
            'warnings': [],
            'recommendations': []
        }

        # Calculate position-level risk
        total_stop_loss = 0
        total_target_gain = 0
        sector_exposure = defaultdict(float)

        for pos in positions:
            market_value = pos.get('market_value', 0)
            entry_price = pos.get('entry_price') or pos.get('avg_price', 0)
            current_price = pos.get('current_price', entry_price)
            stop_loss = pos.get('stop_loss')
            price_target = pos.get('price_target')
            ticker = pos.get('ticker', 'UNKNOWN')

            # Calculate potential loss if stop hit
            if stop_loss and entry_price:
                loss_per_share = entry_price - stop_loss
                shares = pos.get('shares', market_value / current_price)
                total_loss = loss_per_share * shares
                total_stop_loss += total_loss

            # Calculate potential gain if target hit
            if price_target and entry_price:
                gain_per_share = price_target - entry_price
                shares = pos.get('shares', market_value / current_price)
                total_gain = gain_per_share * shares
                total_target_gain += total_gain

            # Track sector exposure (simplified - you can enhance with real sector data)
            sector = self._guess_sector(ticker)
            sector_exposure[sector] += market_value

        # Calculate metrics
        analysis['max_loss'] = total_stop_loss
        analysis['max_loss_pct'] = (total_stop_loss / account_value) * 100 if account_value > 0 else 0
        analysis['max_gain'] = total_target_gain
        analysis['max_gain_pct'] = (total_target_gain / account_value) * 100 if account_value > 0 else 0
        analysis['risk_reward_ratio'] = abs(total_target_gain / total_stop_loss) if total_stop_loss != 0 else 0

        # Concentration analysis
        concentration = {}
        for ticker_data in positions:
            ticker = ticker_data.get('ticker')
            value = ticker_data.get('market_value', 0)
            pct = (value / account_value) * 100 if account_value > 0 else 0
            concentration[ticker] = pct

            # Warn if over-concentrated
            if pct > 30:
                analysis['warnings'].append(f"HIGH CONCENTRATION: {ticker} is {pct:.1f}% of portfolio")

        analysis['concentration'] = concentration

        # Sector concentration
        sector_pct = {}
        for sector, value in sector_exposure.items():
            pct = (value / account_value) * 100 if account_value > 0 else 0
            sector_pct[sector] = pct

            if pct > 50:
                analysis['warnings'].append(f"SECTOR RISK: {pct:.1f}% in {sector}")

        analysis['sector_exposure'] = sector_pct

        # Determine overall risk level
        analysis['risk_level'] = self._calculate_risk_level(analysis)

        # Generate recommendations
        analysis['recommendations'] = self._generate_recommendations(analysis)

        return analysis

    def _guess_sector(self, ticker: str) -> str:
        """Simple sector classification (can be enhanced with real data)"""
        tech_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'AMD', 'TSLA', 'NFLX']
        finance_stocks = ['JPM', 'BAC', 'GS', 'MS', 'WFC', 'C']
        healthcare_stocks = ['JNJ', 'PFE', 'UNH', 'ABBV', 'TMO']
        energy_stocks = ['XOM', 'CVX', 'COP', 'SLB']

        if ticker in tech_stocks:
            return 'Technology'
        elif ticker in finance_stocks:
            return 'Financial'
        elif ticker in healthcare_stocks:
            return 'Healthcare'
        elif ticker in energy_stocks:
            return 'Energy'
        elif ticker in ['SPY', 'QQQ', 'IWM', 'DIA']:
            return 'ETF'
        else:
            return 'Other'

    def _calculate_risk_level(self, analysis: Dict) -> str:
        """Determine overall portfolio risk level"""
        max_loss_pct = analysis.get('max_loss_pct', 0)
        risk_reward = analysis.get('risk_reward_ratio', 0)
        warnings = len(analysis.get('warnings', []))

        if max_loss_pct > 20 or warnings >= 3:
            return 'HIGH'
        elif max_loss_pct > 10 or warnings >= 2:
            return 'MODERATE'
        elif max_loss_pct > 5 or warnings >= 1:
            return 'LOW'
        else:
            return 'MINIMAL'

    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """Generate actionable recommendations"""
        recs = []

        # Risk/Reward ratio
        rr_ratio = analysis.get('risk_reward_ratio', 0)
        if rr_ratio < 1.5:
            recs.append(f"Poor risk/reward ({rr_ratio:.2f}x). Consider tighter stops or better targets.")
        elif rr_ratio > 3:
            recs.append(f"Excellent risk/reward ({rr_ratio:.2f}x). Consider increasing position sizes.")

        # Max loss
        max_loss_pct = analysis.get('max_loss_pct', 0)
        if max_loss_pct > 15:
            recs.append(f"High max loss exposure ({max_loss_pct:.1f}%). Consider tighter stops.")

        # Concentration
        concentration = analysis.get('concentration', {})
        max_position = max(concentration.values()) if concentration else 0
        if max_position > 40:
            recs.append("Reduce concentration - no single position should exceed 30-40%")

        # Sector exposure
        sector_exp = analysis.get('sector_exposure', {})
        if sector_exp:
            max_sector = max(sector_exp.items(), key=lambda x: x[1])
            if max_sector[1] > 60:
                recs.append(f"Diversify sectors - {max_sector[0]} is {max_sector[1]:.1f}% of portfolio")

        if not recs:
            recs.append("Portfolio risk is well-managed. Good job!")

        return recs

    def print_dashboard(self, analysis: Dict):
        """Print formatted risk dashboard"""
        print("\n" + "="*70)
        print("📊 RISK MANAGEMENT DASHBOARD")
        print("="*70)

        print(f"\nPORTFOLIO OVERVIEW:")
        print(f"  Total Value: ${analysis['total_value']:,.2f}")
        print(f"  Positions: {analysis['position_count']}")
        print(f"  Risk Level: {analysis['risk_level']}")

        print(f"\nRISK EXPOSURE:")
        print(f"  Max Loss (if all stops hit): ${analysis['max_loss']:,.2f} ({analysis['max_loss_pct']:.2f}%)")
        print(f"  Max Gain (if all targets hit): ${analysis['max_gain']:,.2f} ({analysis['max_gain_pct']:.2f}%)")
        print(f"  Risk/Reward Ratio: {analysis['risk_reward_ratio']:.2f}x")

        if analysis.get('concentration'):
            print(f"\nPOSITION CONCENTRATION:")
            for ticker, pct in sorted(analysis['concentration'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {ticker}: {pct:.1f}%")

        if analysis.get('sector_exposure'):
            print(f"\nSECTOR EXPOSURE:")
            for sector, pct in sorted(analysis['sector_exposure'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {sector}: {pct:.1f}%")

        if analysis.get('warnings'):
            print(f"\n⚠️  WARNINGS:")
            for warning in analysis['warnings']:
                print(f"  • {warning}")

        if analysis.get('recommendations'):
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in analysis['recommendations']:
                print(f"  • {rec}")

        print("\n" + "="*70)


# Singleton instance
_risk_dashboard = None


def get_risk_dashboard() -> RiskDashboard:
    """Get or create risk dashboard"""
    global _risk_dashboard
    if _risk_dashboard is None:
        _risk_dashboard = RiskDashboard()
    return _risk_dashboard
