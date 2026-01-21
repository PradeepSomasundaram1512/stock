# Market Scanner Guide

## 🎯 Overview

The Market Scanner analyzes multiple stocks in parallel and ranks them by Buy/Hold/Sell recommendations with confidence scores.

## 🚀 Quick Start

### Scan Popular Stocks (Default - 50 stocks)

```powershell
python scan_market.py
```

### Scan Specific Stocks

```powershell
# Analyze specific tickers
python scan_market.py --tickers AAPL MSFT GOOGL TSLA NVDA

# Just tech stocks
python scan_market.py --tickers AAPL MSFT GOOGL AMZN META NFLX
```

### Scan Your Watchlist

```powershell
python scan_market.py --watchlist
```

### Scan S&P 500 Top 100

```powershell
python scan_market.py --sp500
```

## 📊 Command Options

### Stock Selection

```powershell
# 50 popular stocks (default)
python scan_market.py --popular

# Top 100 S&P 500 stocks
python scan_market.py --sp500

# Stocks from data/watchlist.txt
python scan_market.py --watchlist

# Custom list
python scan_market.py --tickers AAPL MSFT GOOGL
```

### Analysis Options

```powershell
# Show top 20 per category instead of 10
python scan_market.py --top 20

# Use 1-year data
python scan_market.py --period 1y

# Use 10 parallel workers (faster)
python scan_market.py --workers 10

# Export to CSV
python scan_market.py --export my_rankings.csv

# Initialize knowledge base first
python scan_market.py --init-kb
```

### Combined Examples

```powershell
# Scan S&P 500, show top 15, export to CSV
python scan_market.py --sp500 --top 15 --export sp500_rankings.csv

# Scan watchlist with 1-year data
python scan_market.py --watchlist --period 1y

# Quick scan of tech stocks
python scan_market.py --tickers AAPL MSFT GOOGL NVDA AMD INTC --workers 3
```

## 📋 Output Format

### Console Output

```
╔══════════════════════════════════════════════════════════════╗
║              AI STOCK MARKET SCANNER                         ║
╚══════════════════════════════════════════════════════════════╝

🔍 SCANNING 50 STOCKS...
======================================================================

[1/50] ✓ AAPL   - SELL (59.5%)
[2/50] ✓ MSFT   - BUY  (78.2%)
[3/50] ✓ GOOGL  - HOLD (65.1%)
...

======================================================================
📊 TOP STOCK RECOMMENDATIONS
======================================================================

🟢 TOP BUY OPPORTUNITIES
----------------------------------------------------------------------
Rank   Ticker   Conf     Price      20d Chg    RSI      Trend
----------------------------------------------------------------------
1      MSFT     78.2%    $425.50    +5.20%     62.5     bullish
2      NVDA     76.8%    $875.30    +8.10%     68.2     bullish
3      GOOGL    74.5%    $142.80    +3.50%     58.9     bullish
...

🟡 TOP HOLD POSITIONS
----------------------------------------------------------------------
...

🔴 TOP SELL OPPORTUNITIES
----------------------------------------------------------------------
1      AAPL     59.5%    $262.87    -5.71%     24.8     neutral
...

📊 SUMMARY:
   Total Analyzed: 50
   🟢 BUY signals:  15
   🟡 HOLD signals: 25
   🔴 SELL signals: 10
```

### CSV Export

Columns:
- ticker
- decision (BUY/HOLD/SELL)
- confidence (0-1)
- price
- change_20d
- rsi
- trend
- volatility
- explanation

## ⚡ Performance Tips

### Speed Up Scanning

```powershell
# Use more workers (CPU cores)
python scan_market.py --workers 10

# Scan fewer stocks
python scan_market.py --tickers AAPL MSFT GOOGL NVDA AMD

# Use shorter period
python scan_market.py --period 3mo
```

### Reduce API Costs

```powershell
# Fewer stocks = fewer API calls
python scan_market.py --watchlist

# Use cached knowledge base (don't reinitialize)
python scan_market.py  # without --init-kb
```

## 🎯 Use Cases

### Daily Morning Scan

```powershell
# Quick scan of your watchlist
python scan_market.py --watchlist --export daily_scan.csv
```

### Weekly Deep Dive

```powershell
# Comprehensive S&P 500 scan
python scan_market.py --sp500 --period 1y --top 20 --export weekly_analysis.csv
```

### Sector Analysis

```powershell
# Tech sector
python scan_market.py --tickers AAPL MSFT GOOGL AMZN META NVDA AMD INTC

# Finance sector
python scan_market.py --tickers JPM BAC WFC GS MS C V MA

# Healthcare
python scan_market.py --tickers JNJ UNH PFE ABBV MRK LLY
```

## 📊 Understanding the Rankings

### Confidence Score

- **75-100%**: High confidence (strong signals)
- **60-74%**: Medium confidence (good signals)
- **50-59%**: Low confidence (weak signals)
- **<50%**: Very low (conflicting signals)

### Decision Logic

**BUY** recommendations have:
- Bullish technical indicators
- Positive momentum
- Volume confirmation
- Low-medium volatility

**SELL** recommendations have:
- Bearish technical indicators
- Negative momentum
- Breaking support levels
- May have high volatility

**HOLD** recommendations have:
- Mixed signals
- High volatility
- Consolidation patterns
- Awaiting clarity

## 🔧 Customization

### Create Custom Stock Lists

Edit `data/watchlist.txt`:
```
# My tech picks
AAPL
MSFT
GOOGL

# My value picks
JPM
JNJ
PG
```

Then run:
```powershell
python scan_market.py --watchlist
```

### Adjust Workers for Your CPU

```powershell
# Conservative (4 workers)
python scan_market.py --workers 4

# Aggressive (10 workers)
python scan_market.py --workers 10
```

**Note:** More workers = faster but more memory usage

## ⚠️ Important Notes

### API Costs

- Each stock = 2-3 API calls (embeddings + chat)
- 50 stocks ≈ $0.50-$1.50 (with GPT-4o)
- 100 stocks ≈ $1-$3
- Use `--popular` or `--watchlist` to control costs

### Rate Limits

If you hit OpenAI rate limits:
```powershell
# Reduce workers
python scan_market.py --workers 2

# Scan in batches
python scan_market.py --tickers AAPL MSFT GOOGL
python scan_market.py --tickers NVDA AMD INTC
```

### Time Estimates

- 10 stocks: ~30-60 seconds
- 50 stocks: ~2-5 minutes (5 workers)
- 100 stocks: ~5-10 minutes (5 workers)

## 💡 Pro Tips

1. **Morning Routine**: Scan watchlist every morning before market opens
2. **Weekly Analysis**: Full S&P 500 scan on weekends
3. **Export Everything**: Always use `--export` for records
4. **Compare Periods**: Run same scan with different `--period` values
5. **Track Changes**: Compare CSV exports over time

## 🆘 Troubleshooting

### "Too Many Requests" Error

```powershell
# Reduce workers
python scan_market.py --workers 2
```

### Out of API Credits

Add credits at https://platform.openai.com/account/billing

### Slow Performance

```powershell
# Increase workers if you have CPU
python scan_market.py --workers 8
```

### No Results

Check:
1. Internet connection
2. API key in `.env`
3. Valid ticker symbols

---

**Happy Scanning! 📊🚀**
