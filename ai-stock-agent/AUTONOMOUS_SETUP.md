# Autonomous System - Quick Setup Guide

## 🚀 5-Minute Setup

### 1. Install Dependencies

```powershell
# Install new dependencies
pip install beautifulsoup4 requests lxml
```

Or reinstall everything:

```powershell
pip install -r requirements.txt
```

### 2. Verify .env Configuration

Your `.env` should have:

```env
# Required
OPENAI_API_KEY=your-openai-api-key-here

# Optional (for alternative LLM)
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Model selection
OPENAI_MODEL=gpt-4o
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
LLM_PROVIDER=openai
```

### 3. Test Single Stock Analysis

```powershell
# Test with Apple
python autonomous_analysis.py AAPL --init-kb
```

### 4. Test Market Scanner

```powershell
# Scan 3 stocks (quick test)
python autonomous_scanner.py --tickers AAPL MSFT GOOGL --workers 1
```

---

## 📊 What's New

### New Agents

1. **News Agent** ([agents/news_agent.py](agents/news_agent.py))
   - Fetches recent news from Google Finance & Yahoo Finance
   - Analyzes sentiment using LLM
   - Returns bullish/neutral/bearish signals

2. **Fundamental Agent** ([agents/fundamental_agent.py](agents/fundamental_agent.py))
   - Gets company financials from Yahoo Finance
   - Calculates valuation, health, and growth scores
   - Includes analyst recommendations

3. **Market Context Agent** ([agents/market_context_agent.py](agents/market_context_agent.py))
   - Tracks major indices (S&P 500, NASDAQ, Dow)
   - Monitors VIX (volatility index)
   - Analyzes sector performance

4. **Autonomous Reasoning Agent** ([agents/autonomous_reasoning_agent.py](agents/autonomous_reasoning_agent.py))
   - Combines ALL data sources
   - Makes decisions without user input
   - Provides comprehensive reasoning

### New Workflows

1. **Autonomous Decision Graph** ([graph/autonomous_decision_graph.py](graph/autonomous_decision_graph.py))
   - 7-step workflow
   - Integrates all new agents
   - Fully autonomous analysis

### New Tools

1. **autonomous_analysis.py** - Single stock comprehensive analysis
2. **autonomous_scanner.py** - Multi-stock scanner with all features

---

## 🔄 Migration from Old System

### Old Way (Technical Only)

```powershell
# Only technical analysis
python main.py AAPL
```

### New Way (Comprehensive)

```powershell
# Technical + Fundamental + News + Market
python autonomous_analysis.py AAPL
```

### Old Scanner

```powershell
# Only technical + basic LLM
python scan_market.py --popular
```

### New Scanner

```powershell
# Comprehensive multi-source analysis
python autonomous_scanner.py --popular
```

---

## 🆚 Comparison

### Original System

**Analyzed:**
- ✅ Price data
- ✅ Technical indicators
- ✅ LLM reasoning
- ✅ RAG knowledge base

**Output:**
- BUY/SELL/HOLD
- Confidence score
- Brief explanation

### New Autonomous System

**Analyzed:**
- ✅ Price data
- ✅ Technical indicators
- ✅ **Company fundamentals** (NEW)
- ✅ **News & sentiment** (NEW)
- ✅ **Market context** (NEW)
- ✅ **Sector performance** (NEW)
- ✅ Enhanced LLM reasoning
- ✅ RAG knowledge base

**Output:**
- BUY/SELL/HOLD
- Confidence score (0-100%)
- **Risk level** (low/medium/high) (NEW)
- **Time horizon** (short/medium/long) (NEW)
- **Price target** (NEW)
- **Stop loss suggestion** (NEW)
- **Detailed reasoning** (NEW)
- **Key factors** (NEW)
- **Alternative action** (NEW)
- **Valuation/Health/Growth scores** (NEW)

---

## 💰 Cost Considerations

### API Costs (OpenAI GPT-4o)

**Single Stock Analysis:**
- Technical: ~$0.01
- News sentiment: ~$0.02
- Autonomous decision: ~$0.03
- **Total per stock: ~$0.06-$0.10**

**Market Scanner:**
- 10 stocks: ~$0.60-$1.00
- 50 stocks: ~$3.00-$5.00
- 100 stocks: ~$6.00-$10.00

### Tips to Reduce Costs

1. **Use fewer workers** (slower but cheaper)
   ```powershell
   python autonomous_scanner.py --workers 2
   ```

2. **Scan in smaller batches**
   ```powershell
   python autonomous_scanner.py --tickers AAPL MSFT GOOGL
   ```

3. **Use watchlist instead of --sp500**
   ```powershell
   python autonomous_scanner.py --watchlist
   ```

4. **Cache results** (save CSV and review without re-scanning)
   ```powershell
   python autonomous_scanner.py --export results.csv
   # Review results.csv multiple times without cost
   ```

---

## ⚡ Performance

### Speed Comparison

**Old Technical-Only Scanner:**
- 50 stocks: ~2-3 minutes (5 workers)
- Per stock: ~3-4 seconds

**New Autonomous Scanner:**
- 50 stocks: ~8-15 minutes (3 workers)
- Per stock: ~10-15 seconds

**Why slower?**
- Fetches fundamentals from Yahoo Finance
- Scrapes news from multiple sources
- Analyzes market indices
- More comprehensive LLM prompts

### Optimization Tips

1. **Use more workers** (if you have API headroom)
   ```powershell
   python autonomous_scanner.py --workers 5
   ```

2. **Shorter analysis period**
   ```powershell
   python autonomous_scanner.py --period 3mo
   ```

3. **Analyze fewer stocks at once**
   ```powershell
   python autonomous_scanner.py --tickers AAPL MSFT GOOGL --workers 3
   ```

---

## 🐛 Troubleshooting

### News Scraping Issues

**Problem**: No news found or timeout errors

**Solutions:**
- News scraping is best-effort (not critical for decision)
- System continues with "No news available" if scraping fails
- Check your internet connection

### Fundamental Data Missing

**Problem**: Some fundamental metrics show "N/A"

**Solutions:**
- Normal for some stocks (especially small caps)
- Yahoo Finance may not have all data
- System uses scores of 0.5 (neutral) when data missing

### Rate Limits

**Problem**: "Too many requests" or "Rate limit exceeded"

**Solutions:**
```powershell
# Reduce workers
python autonomous_scanner.py --workers 2

# Wait between runs (API cooldown)
# Wait 1-2 minutes between scans

# Use shorter period
python autonomous_scanner.py --period 3mo
```

### Slow Performance

**Problem**: Scanner takes too long

**Solutions:**
```powershell
# Increase workers (if no rate limits)
python autonomous_scanner.py --workers 5

# Scan fewer stocks
python autonomous_scanner.py --tickers AAPL MSFT GOOGL

# Use faster model (if using Anthropic)
# Edit .env: ANTHROPIC_MODEL=claude-3-haiku-20240307
```

---

## 📊 Example Workflow

### First Time Setup

```powershell
# 1. Install dependencies
pip install beautifulsoup4 requests lxml

# 2. Test single stock
python autonomous_analysis.py AAPL --init-kb

# 3. Test small batch
python autonomous_scanner.py --tickers AAPL MSFT GOOGL --workers 1

# 4. If all works, run bigger scan
python autonomous_scanner.py --popular --export first_scan.csv
```

### Daily Routine

```powershell
# Morning: Quick watchlist scan
python autonomous_scanner.py --watchlist --export daily_$(date +%Y%m%d).csv

# Review top picks
python autonomous_analysis.py MSFT
python autonomous_analysis.py NVDA
```

### Weekly Deep Dive

```powershell
# Weekend: Comprehensive analysis
python autonomous_scanner.py --sp500 --period 1y --top 20 --export weekly_analysis.csv

# Detailed analysis of top picks
python autonomous_analysis.py AAPL --period 1y
python autonomous_analysis.py GOOGL --period 1y
```

---

## 🔍 What Changed in Code

### New Files Created

```
agents/
  news_agent.py                    # News scraping & sentiment
  fundamental_agent.py              # Company financials
  market_context_agent.py           # Market indices & context
  autonomous_reasoning_agent.py     # Comprehensive decision making

graph/
  autonomous_decision_graph.py      # New workflow integrating all agents

autonomous_analysis.py              # CLI for single stock
autonomous_scanner.py               # CLI for multiple stocks

AUTONOMOUS_GUIDE.md                 # User documentation
AUTONOMOUS_SETUP.md                 # This file
```

### Modified Files

```
requirements.txt                    # Added beautifulsoup4, requests, lxml
```

### Unchanged Files (Still Work)

```
main.py                            # Original technical-only analysis
scan_market.py                     # Original technical-only scanner
graph/decision_graph.py            # Original workflow
```

**You can still use the original system** if you want faster, technical-only analysis!

---

## 🎯 Next Steps

1. **Read the user guide**: [AUTONOMOUS_GUIDE.md](AUTONOMOUS_GUIDE.md)
2. **Test the system**: Run a few test analyses
3. **Create your watchlist**: Edit `data/watchlist.txt`
4. **Start small**: Analyze 3-5 stocks first
5. **Scale up**: Once comfortable, scan larger lists

---

## 📞 Need Help?

### Check These First

1. [AUTONOMOUS_GUIDE.md](AUTONOMOUS_GUIDE.md) - Full user guide
2. [README.md](README.md) - System architecture
3. [QUICKSTART.md](QUICKSTART.md) - Original setup guide

### Common Issues

- **API Key Issues**: Check `.env` file
- **Rate Limits**: Reduce `--workers`
- **Slow Performance**: Normal for comprehensive analysis
- **Missing Data**: Some stocks have incomplete data (normal)

---

**You're all set! Start with a simple test:**

```powershell
python autonomous_analysis.py AAPL
```

**Happy Analyzing! 📊🚀**
