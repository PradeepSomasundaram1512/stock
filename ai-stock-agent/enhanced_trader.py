"""
Enhanced Trading System
Includes: Trailing Stops, Paper Trading, Risk Dashboard
"""

import sys
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from enhancements.trailing_stops import get_trailing_stop_manager
from enhancements.paper_trading import get_paper_account
from enhancements.risk_dashboard import get_risk_dashboard
from backtesting.performance import get_performance_tracker

def main():
    parser = argparse.ArgumentParser(description="Enhanced Trading System")
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Paper trading commands
    paper = subparsers.add_parser('paper', help='Paper trading operations')
    paper.add_argument('action', choices=['buy', 'sell', 'status', 'reset'],
                      help='Paper trading action')
    paper.add_argument('--ticker', help='Stock ticker')
    paper.add_argument('--shares', type=int, help='Number of shares')
    paper.add_argument('--price', type=float, help='Price per share')

    # Risk dashboard
    subparsers.add_parser('risk', help='Show risk dashboard')

    # Trailing stops
    trailing = subparsers.add_parser('trailing', help='Trailing stop operations')
    trailing.add_argument('action', choices=['add', 'update', 'status'],
                         help='Trailing stop action')
    trailing.add_argument('--ticker', help='Stock ticker')
    trailing.add_argument('--entry', type=float, help='Entry price')
    trailing.add_argument('--stop', type=float, help='Stop loss')
    trailing.add_argument('--current', type=float, help='Current price')

    args = parser.parse_args()

    if args.command == 'paper':
        handle_paper_trading(args)
    elif args.command == 'risk':
        handle_risk_dashboard()
    elif args.command == 'trailing':
        handle_trailing_stops(args)
    else:
        parser.print_help()


def handle_paper_trading(args):
    """Handle paper trading commands"""
    account = get_paper_account()

    if args.action == 'buy':
        if not all([args.ticker, args.shares, args.price]):
            print("Error: --ticker, --shares, and --price required for buy")
            return

        result = account.buy(args.ticker, args.shares, args.price)
        if result['success']:
            print(f"\n✅ BUY ORDER EXECUTED")
            print(f"   {args.shares} shares of {args.ticker} @ ${args.price:.2f}")
            print(f"   Total Cost: ${args.shares * args.price:.2f}")
            print(f"   Cash Remaining: ${result['trade']['cash_remaining']:.2f}")
        else:
            print(f"\n❌ BUY ORDER FAILED: {result['error']}")

    elif args.action == 'sell':
        if not all([args.ticker, args.shares, args.price]):
            print("Error: --ticker, --shares, and --price required for sell")
            return

        result = account.sell(args.ticker, args.shares, args.price)
        if result['success']:
            trade = result['trade']
            symbol = "📈" if trade['profit_loss'] > 0 else "📉"
            print(f"\n✅ SELL ORDER EXECUTED")
            print(f"   {args.shares} shares of {args.ticker} @ ${args.price:.2f}")
            print(f"   Proceeds: ${trade['proceeds']:.2f}")
            print(f"   {symbol} P/L: ${trade['profit_loss']:.2f} ({trade['profit_loss_pct']:+.2f}%)")
            print(f"   Cash Now: ${trade['cash_remaining']:.2f}")
        else:
            print(f"\n❌ SELL ORDER FAILED: {result['error']}")

    elif args.action == 'status':
        # Get current prices (simplified - you'd fetch real prices)
        current_prices = {}
        for ticker in account.positions.keys():
            current_prices[ticker] = account.positions[ticker]['avg_price'] * 1.02  # Mock 2% gain

        portfolio = account.get_portfolio_value(current_prices)

        print("\n" + "="*70)
        print("📊 PAPER TRADING ACCOUNT STATUS")
        print("="*70)
        print(f"\nCash: ${portfolio['cash']:,.2f}")
        print(f"Positions Value: ${portfolio['positions_value']:,.2f}")
        print(f"Total Value: ${portfolio['total_value']:,.2f}")

        symbol = "📈" if portfolio['total_return'] > 0 else "📉"
        print(f"{symbol} Total Return: ${portfolio['total_return']:,.2f} ({portfolio['total_return_pct']:+.2f}%)")

        if portfolio['positions']:
            print(f"\nPOSITIONS:")
            for pos in portfolio['positions']:
                pl_symbol = "📈" if pos['unrealized_pl'] > 0 else "📉"
                print(f"  {pos['ticker']}: {pos['shares']} shares @ ${pos['current_price']:.2f}")
                print(f"    Value: ${pos['market_value']:.2f} {pl_symbol} P/L: ${pos['unrealized_pl']:.2f} ({pos['unrealized_pl_pct']:+.2f}%)")

        print("\n" + "="*70)

    elif args.action == 'reset':
        account.reset_account()
        print("✅ Paper trading account reset")


def handle_risk_dashboard():
    """Show risk management dashboard"""
    tracker = get_performance_tracker()
    positions = tracker.get_open_positions()

    if not positions:
        print("\n⚠️  No open positions to analyze")
        return

    # Calculate total account value (simplified)
    account_value = sum(pos.get('market_value', pos['entry_price'] * 10) for pos in positions)

    dashboard = get_risk_dashboard()
    analysis = dashboard.analyze_portfolio(positions, account_value)
    dashboard.print_dashboard(analysis)


def handle_trailing_stops(args):
    """Handle trailing stop operations"""
    manager = get_trailing_stop_manager()

    if args.action == 'add':
        if not all([args.ticker, args.entry, args.stop]):
            print("Error: --ticker, --entry, and --stop required")
            return

        manager.add_position(args.ticker, args.entry, args.stop)
        print(f"✅ Added trailing stop for {args.ticker}")

    elif args.action == 'update':
        if not all([args.ticker, args.current]):
            print("Error: --ticker and --current required")
            return

        result = manager.update_position(args.ticker, args.current)

        if 'error' in result:
            print(f"❌ {result['error']}")
            return

        print(f"\n📊 {args.ticker} @ ${result['current_price']:.2f}")
        print(f"   Entry: ${result['entry_price']:.2f}")
        print(f"   Stop: ${result['stop_loss']:.2f}")
        print(f"   Highest: ${result['highest_price']:.2f}")
        print(f"   Profit: {result['profit_pct']:+.2f}%")

        if result.get('trailing_activated'):
            print(f"   🎯 TRAILING ACTIVATED!")

        if result.get('stop_updated'):
            print(f"   ⬆️  STOP RAISED: ${result['old_stop']:.2f} → ${result['new_stop']:.2f}")

        if result['stop_triggered']:
            print(f"   ⛔ STOP LOSS TRIGGERED - SELL NOW!")

    elif args.action == 'status':
        positions = manager.get_all_positions()

        if not positions:
            print("\n⚠️  No positions with trailing stops")
            return

        print("\n" + "="*70)
        print("📊 TRAILING STOP STATUS")
        print("="*70)

        for ticker, pos in positions.items():
            active = "✓" if pos['trailing_active'] else "○"
            print(f"\n{ticker} [{active} Trailing]")
            print(f"  Entry: ${pos['entry_price']:.2f}")
            print(f"  Stop: ${pos['stop_loss']:.2f}")
            print(f"  Highest: ${pos['highest_price']:.2f}")


if __name__ == '__main__':
    main()
