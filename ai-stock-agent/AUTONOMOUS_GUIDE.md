# Autonomous AI Stock Analyzer - User Guide

## 🎯 For Users With No Stock Market Expertise

This system analyzes **ALL available data** from the internet and makes clear, autonomous recommendations. You don't need to understand stocks, technical analysis, or financial metrics.

---

## 🚀 Quick Start

### Analyze a Single Stock

```powershell
# Simple analysis
python autonomous_analysis.py AAPL

# With 1-year data
python autonomous_analysis.py MSFT --period 1y

# Initialize knowledge base first (recommended on first run)
python autonomous_analysis.py GOOGL --init-kb
```

### Scan Multiple Stocks

```powershell
# Scan 50 popular stocks (default)
python autonomous_scanner.py

# Scan specific stocks
python autonomous_scanner.py --tickers AAPL MSFT GOOGL NVDA TSLA

# Scan top 100 S&P 500
python autonomous_scanner.py --sp500

# Scan your watchlist
python autonomous_scanner.py --watchlist
```

---

## 📊 What Gets Analyzed

The system looks at **EVERYTHING**:

### 1. **Technical Analysis** (Price Patterns)
- Current price and trends
- Moving averages
- RSI, MACD indicators
- Support/resistance levels
- Volume analysis
- Volatility measurements

### 2. **Fundamental Analysis** (Company Health)
- **Valuation**: P/E ratio, Price/Book, Price/Sales
- **Profitability**: Profit margins, ROE, ROA
- **Financial Health**: Debt levels, current ratio, cash flow
- **Growth**: Revenue growth, earnings growth
- **Analyst Ratings**: Professional recommendations

### 3. **News & Sentiment**
- Recent news headlines
- Sentiment analysis (bullish/neutral/bearish)
- Key topics and concerns
- Company announcements

### 4. **Market Context**
- Overall market trend (S&P 500, NASDAQ, Dow)
- Market volatility (VIX index)
- Sector performance
- Economic conditions

---

## 🎯 Understanding the Recommendations

### BUY 🟢

**What it means:** Strong signals suggest the stock price will go UP.

**Confidence Levels:**
- **75-100%**: Very strong signals across all data sources
- **60-74%**: Good signals, some uncertainty
- **Below 60%**: Weak signals (likely shows as HOLD instead)

**What to do:**
- High confidence (>75%): Consider buying
- Medium confidence (60-75%): Research more or buy smaller position
- Look at the "Price Target" and "Stop Loss" suggestions

### SELL 🔴

**What it means:** Strong signals suggest the stock price will go DOWN.

**What to do:**
- If you own it: Consider selling
- If you don't own it: Don't buy it
- High confidence = stronger signal to sell

### HOLD 🟡

**What it means:** Mixed signals, unclear direction, or high risk.

**What to do:**
- If you own it: Keep holding, don't sell yet
- If you don't own it: Wait for clearer signals before buying
- Monitor for changes

---

## 📋 Reading the Analysis Report

### Example Output

```
🎯 RECOMMENDATION
══════════════════════════════════════

🟢 STRONG BUY
   Confidence: 82.5%
   Risk Level: MEDIUM
   Time Horizon: medium-term (weeks-months)

📝 Why This Decision?
   Strong bullish technical signals combined with solid fundamentals.
   Company shows healthy growth with positive analyst sentiment.

🔑 Key Factors:
   • Bullish trend with RSI at 65 (healthy momentum)
   • Strong revenue growth of 15% year-over-year
   • Positive news sentiment from recent product launch
   • Overall market is bullish

🎯 Price Target: $450.00
   Potential: +8.5%

🛑 Suggested Stop Loss: $380.00
   Risk: -8.0%

🔄 If This Doesn't Work Out:
   Exit if price falls below $380 or if negative earnings surprise
```

### What Each Part Means

1. **Confidence**: How sure the AI is (higher = more certain)

2. **Risk Level**:
   - **Low**: Stable stock, less volatile
   - **Medium**: Normal market risk
   - **High**: Volatile, could swing wildly

3. **Time Horizon**:
   - **Short-term**: Days to weeks
   - **Medium-term**: Weeks to months
   - **Long-term**: Months and beyond

4. **Price Target**: Where AI thinks price could go

5. **Stop Loss**: Price where you should exit to limit losses

---

## ⚙️ Scanner Options

### Stock Selection

```powershell
# 50 most popular stocks (default)
python autonomous_scanner.py --popular

# Top 100 S&P 500 companies
python autonomous_scanner.py --sp500

# Your custom watchlist (data/watchlist.txt)
python autonomous_scanner.py --watchlist

# Specific tickers
python autonomous_scanner.py --tickers AAPL MSFT GOOGL NVDA AMD
```

### Analysis Options

```powershell
# Show top 15 per category instead of 10
python autonomous_scanner.py --top 15

# Use 1-year historical data
python autonomous_scanner.py --period 1y

# Use 3 parallel workers (slower but avoids rate limits)
python autonomous_scanner.py --workers 3

# Export results to CSV
python autonomous_scanner.py --export my_results.csv

# Initialize knowledge base first
python autonomous_scanner.py --init-kb
```

### Combined Examples

```powershell
# Comprehensive S&P 500 scan
python autonomous_scanner.py --sp500 --period 1y --top 20 --export sp500_analysis.csv

# Quick scan of tech stocks
python autonomous_scanner.py --tickers AAPL MSFT GOOGL NVDA AMD --workers 2

# Daily morning routine
python autonomous_scanner.py --watchlist --export daily_scan.csv
```

---

## 📊 Scanner Output

### Console Output

```
╔══════════════════════════════════════════════════════════════╗
║        AUTONOMOUS AI MARKET SCANNER                          ║
╚══════════════════════════════════════════════════════════════╝

🔍 SCANNING 50 STOCKS...
══════════════════════════════════════════════════════════════

[1/50] ✓ AAPL   - SELL (82.5%)
[2/50] ✓ MSFT   - BUY  (78.2%)
[3/50] ✓ GOOGL  - HOLD (65.1%)
...

📊 TOP STOCK RECOMMENDATIONS
══════════════════════════════════════════════════════════════

🟢 TOP BUY OPPORTUNITIES
──────────────────────────────────────────────────────────────
Rank   Ticker   Conf     Price      Risk       Val/Hlth/Grw
──────────────────────────────────────────────────────────────
1      MSFT     78.2%    $425.50    medium     0.65/0.78/0.72
2      NVDA     76.8%    $875.30    medium     0.58/0.82/0.88
3      GOOGL    74.5%    $142.80    low        0.72/0.75/0.65
...
```

### CSV Export

The CSV contains all analyzed stocks with these columns:

- **ticker**: Stock symbol
- **decision**: BUY/HOLD/SELL
- **confidence**: 0.0-1.0
- **price**: Current price
- **change_20d**: 20-day price change %
- **rsi**: RSI indicator
- **trend**: bullish/neutral/bearish
- **risk_level**: low/medium/high
- **valuation_score**: 0-1 (higher = better value)
- **health_score**: 0-1 (higher = healthier)
- **growth_score**: 0-1 (higher = faster growth)
- **reasoning**: Why this decision

---

## 💡 Pro Tips

### 1. Start Small
```powershell
# Analyze just a few stocks first
python autonomous_scanner.py --tickers AAPL MSFT GOOGL
```

### 2. Use Watchlists
Create `data/watchlist.txt` with your favorite stocks:
```
# Tech stocks
AAPL
MSFT
GOOGL

# Finance
JPM
BAC
```

Then run:
```powershell
python autonomous_scanner.py --watchlist
```

### 3. Export and Track
```powershell
# Export daily
python autonomous_scanner.py --export daily_$(date +%Y%m%d).csv

# Compare over time
python autonomous_scanner.py --export monday.csv
python autonomous_scanner.py --export friday.csv
```

### 4. Manage API Costs

The scanner uses AI models which cost money per request:

- **Single stock**: ~$0.05-$0.10
- **10 stocks**: ~$0.50-$1.00
- **50 stocks**: ~$2.50-$5.00
- **100 stocks**: ~$5.00-$10.00

**To save money:**
```powershell
# Use fewer workers (slower but cheaper)
python autonomous_scanner.py --workers 2

# Scan in batches
python autonomous_scanner.py --tickers AAPL MSFT GOOGL
python autonomous_scanner.py --tickers NVDA AMD INTC

# Use watchlist instead of --sp500
python autonomous_scanner.py --watchlist
```

### 5. Avoid Rate Limits

If you see "Too many requests" errors:

```powershell
# Reduce workers to 2 or 3
python autonomous_scanner.py --workers 2

# Wait a few seconds between batches
python autonomous_scanner.py --tickers AAPL MSFT
# Wait 10 seconds
python autonomous_scanner.py --tickers GOOGL NVDA
```

---

## ⚠️ Important Disclaimers

### This is NOT Financial Advice

- This tool is for **educational and research purposes only**
- Always do your own research
- Consult a licensed financial advisor before investing
- Past performance does not guarantee future results

### Understand the Risks

- **Stocks can lose value**: You can lose money
- **AI is not perfect**: The system can be wrong
- **Markets are unpredictable**: Unexpected events happen
- **High volatility = high risk**: Some stocks swing wildly

### Best Practices

1. **Never invest money you can't afford to lose**
2. **Diversify**: Don't put all money in one stock
3. **Start small**: Test with small amounts first
4. **Set stop losses**: Know when to exit
5. **Have a plan**: Know why you're buying/selling
6. **Monitor regularly**: Check your positions
7. **Ignore emotions**: Stick to your plan

---

## 🔧 Troubleshooting

### "Configuration Error"

**Problem**: Missing API keys

**Solution**:
```powershell
# Create .env file with:
OPENAI_API_KEY=your-key-here
```

### "Too Many Requests"

**Problem**: OpenAI rate limit

**Solution**:
```powershell
# Use fewer workers
python autonomous_scanner.py --workers 2

# Wait between batches
```

### "Out of Credits"

**Problem**: OpenAI API credits depleted

**Solution**: Add credits at https://platform.openai.com/account/billing

### "No Data for Ticker"

**Problem**: Invalid ticker or delisted stock

**Solution**: Double-check ticker symbol on Yahoo Finance

---

## 📞 Support

### Common Questions

**Q: How often should I run the scanner?**
A: Daily before market opens, or weekly for long-term investing.

**Q: What if two signals conflict?**
A: Look at confidence level. Higher confidence = more reliable.

**Q: Should I always follow the recommendation?**
A: No. This is a tool to help you decide, not a guarantee.

**Q: What time horizon should I use?**
A: Short-term = day trading, Medium-term = swing trading, Long-term = investing

**Q: How accurate is this?**
A: No system is perfect. Use it as one input among many.

---

## 🎓 Learning More

### Understanding Scores

**Valuation Score (0-1)**:
- High = Stock is cheap relative to earnings/assets
- Low = Stock might be expensive

**Health Score (0-1)**:
- High = Strong financials, profitable, low debt
- Low = Weak financials, unprofitable, high debt

**Growth Score (0-1)**:
- High = Fast revenue/earnings growth
- Low = Slow or negative growth

### Reading Technical Indicators

**RSI (0-100)**:
- 0-30: Oversold (might bounce up)
- 30-70: Normal range
- 70-100: Overbought (might drop)

**Trend**:
- Bullish: Price going up
- Bearish: Price going down
- Neutral: Sideways movement

**Volatility**:
- Low: Stable, small movements
- Medium: Normal fluctuations
- High: Large swings, risky

---

## 📝 Example Workflow

### Daily Trading Routine

```powershell
# 1. Morning: Scan watchlist
python autonomous_scanner.py --watchlist --export daily_scan.csv

# 2. Review top BUY/SELL opportunities

# 3. Deep dive on interesting stocks
python autonomous_analysis.py AAPL
python autonomous_analysis.py MSFT

# 4. Make informed decisions based on multiple signals
```

### Weekly Investment Routine

```powershell
# 1. Weekend: Comprehensive scan
python autonomous_scanner.py --sp500 --period 1y --top 20 --export weekly_analysis.csv

# 2. Review and compare with last week

# 3. Analyze top picks in detail
python autonomous_analysis.py NVDA --period 1y
python autonomous_analysis.py GOOGL --period 1y

# 4. Update portfolio based on findings
```

---

**Happy Investing! 📊🚀**

*Remember: Smart investors use tools like this to inform their decisions, not to make decisions for them.*
