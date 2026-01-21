# 🤖 Autonomous AI Stock Analyzer

## Two Systems in One

This project now includes **TWO** analysis systems:

### 1. **Original System** - Technical Analysis (Fast)
- Uses: Price data + Technical indicators + LLM
- Speed: ~3-4 seconds per stock
- Use case: Quick technical scans

### 2. **Autonomous System** - Comprehensive Analysis (Thorough) ⭐ NEW
- Uses: Technical + Fundamentals + News + Market Context + LLM
- Speed: ~10-15 seconds per stock
- Use case: Deep analysis for users with no expertise

---

## 🚀 Quick Start

### Install

```powershell
# Clone/download the repository
cd ai-stock-agent

# Install dependencies
pip install -r requirements.txt

# Create .env file
# Add: OPENAI_API_KEY=your-key-here
```

### Run Autonomous Analysis (Recommended)

```powershell
# Single stock comprehensive analysis
python autonomous_analysis.py AAPL

# Scan multiple stocks
python autonomous_scanner.py --tickers AAPL MSFT GOOGL
```

### Run Original Technical-Only Analysis

```powershell
# Single stock
python main.py AAPL

# Scan multiple stocks
python scan_market.py --popular
```

---

## 📚 Documentation

### For the Autonomous System (Comprehensive)

- **[AUTONOMOUS_GUIDE.md](AUTONOMOUS_GUIDE.md)** - Complete user guide for non-experts
- **[AUTONOMOUS_SETUP.md](AUTONOMOUS_SETUP.md)** - Setup and migration guide

### For the Original System (Technical Only)

- **[README.md](README.md)** - Original technical analysis system
- **[QUICKSTART.md](QUICKSTART.md)** - Quick setup guide
- **[MARKET_SCANNER_GUIDE.md](MARKET_SCANNER_GUIDE.md)** - Scanner usage

### General Documentation

- **[COMPLETE_SYSTEM_GUIDE.md](COMPLETE_SYSTEM_GUIDE.md)** - Full system documentation
- **[WINDOWS_SETUP.md](WINDOWS_SETUP.md)** - Windows installation
- **[IMPROVEMENTS_MADE.md](IMPROVEMENTS_MADE.md)** - Logic improvements

---

## 🆚 Which System Should I Use?

### Use **Autonomous System** if:
- ✅ You know nothing about stocks
- ✅ You want comprehensive analysis
- ✅ You need fundamental data (P/E, financials, etc.)
- ✅ You want news sentiment analysis
- ✅ You want market context (indices, VIX, etc.)
- ✅ You don't mind slower analysis (~10-15 sec/stock)
- ✅ You want price targets and stop loss suggestions

**Use this for:** Investment decisions, thorough research

### Use **Original System** if:
- ✅ You only want technical analysis
- ✅ You need fast results (~3-4 sec/stock)
- ✅ You want to scan many stocks quickly
- ✅ You understand technical indicators
- ✅ You want lower API costs

**Use this for:** Quick technical scans, day trading signals

---

## 📊 Feature Comparison

| Feature | Original | Autonomous |
|---------|----------|------------|
| **Data Sources** | | |
| Price data | ✅ | ✅ |
| Technical indicators | ✅ | ✅ |
| Company fundamentals | ❌ | ✅ |
| News & sentiment | ❌ | ✅ |
| Market context | ❌ | ✅ |
| Sector performance | ❌ | ✅ |
| Analyst ratings | ❌ | ✅ |
| **Output** | | |
| BUY/SELL/HOLD | ✅ | ✅ |
| Confidence score | ✅ | ✅ |
| Risk level | Basic | ✅ Detailed |
| Time horizon | ❌ | ✅ |
| Price target | ❌ | ✅ |
| Stop loss | ❌ | ✅ |
| Valuation scores | ❌ | ✅ |
| **Performance** | | |
| Speed per stock | ~3-4 sec | ~10-15 sec |
| API cost per stock | ~$0.02 | ~$0.06-$0.10 |
| Suitable for beginners | Moderate | ✅ Yes |
| Suitable for experts | ✅ Yes | ✅ Yes |

---

## 🎯 Example Outputs

### Original System (Technical Only)

```
══════════════════════════════════════
STOCK ANALYSIS: AAPL
══════════════════════════════════════

📊 Price: $262.87
   20-day change: -5.71%

🎯 DECISION: SELL
   Confidence: 59.5%
   Sentiment: Bearish

📝 Reasoning:
   Technical indicators show bearish momentum.
   RSI at 24.8 suggests oversold but trend is down.
```

### Autonomous System (Comprehensive)

```
══════════════════════════════════════
🎯 RECOMMENDATION
══════════════════════════════════════

🔴 STRONG SELL
   Confidence: 82.5%
   Risk Level: MEDIUM
   Time Horizon: medium-term (weeks-months)

📝 Why This Decision?
   Stock is overvalued with deteriorating fundamentals.
   Negative news sentiment combined with bearish technicals.
   Market showing weakness overall.

🔑 Key Factors:
   • P/E ratio of 35 suggests overvaluation
   • Declining revenue growth (5% YoY)
   • Negative news about supply chain issues
   • Market VIX elevated at 22 (uncertainty)
   • Technical breakdown below 200-day MA

🎯 Price Target: $240.00
   Potential: -8.7%

🛑 Suggested Stop Loss: $275.00
   Risk: +4.6%

📊 QUICK STATS
══════════════════════════════════════

Fundamental Analysis:
   Valuation Score: 0.42/1.0 (expensive)
   Health Score: 0.78/1.0 (strong)
   Growth Score: 0.55/1.0 (moderate)
   P/E Ratio: 35.2
   Analyst Consensus: HOLD

News & Sentiment:
   Articles Found: 8
   Sentiment: BEARISH
   Summary: Supply chain concerns...

Market Context:
   Overall Market: NEUTRAL
   Market Volatility (VIX): 22.1 (MODERATE)
```

---

## 🛠️ Installation

### Prerequisites

- Python 3.12 (3.10+ works, but 3.12 recommended)
- OpenAI API key

### Step-by-Step

1. **Clone repository**
   ```powershell
   git clone https://github.com/yourusername/ai-stock-agent.git
   cd ai-stock-agent
   ```

2. **Create virtual environment**
   ```powershell
   python -m venv venv312
   .\venv312\Scripts\activate
   ```

3. **Install dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Configure API key**
   Create `.env` file:
   ```env
   OPENAI_API_KEY=your-openai-api-key-here
   OPENAI_MODEL=gpt-4o
   LLM_PROVIDER=openai
   ```

5. **Test installation**
   ```powershell
   python autonomous_analysis.py AAPL --init-kb
   ```

---

## 📖 Usage Examples

### Autonomous System

```powershell
# Single stock analysis
python autonomous_analysis.py AAPL

# With 1-year data
python autonomous_analysis.py MSFT --period 1y

# Scan 50 popular stocks
python autonomous_scanner.py --popular

# Scan specific stocks
python autonomous_scanner.py --tickers AAPL MSFT GOOGL NVDA

# Scan with export
python autonomous_scanner.py --sp500 --top 20 --export results.csv
```

### Original System

```powershell
# Single stock analysis
python main.py AAPL

# Scan 50 popular stocks
python scan_market.py --popular

# Scan with export
python scan_market.py --sp500 --export results.csv
```

---

## 🏗️ Architecture

### Autonomous System Architecture

```
┌─────────────────────────────────────────────────────────┐
│          AUTONOMOUS DECISION GRAPH (7 steps)            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Fetch Data (Yahoo Finance)                          │
│      ↓                                                  │
│  2. Extract Technical Features                          │
│      ↓                                                  │
│  3. Get Fundamentals (P/E, margins, growth)             │
│      ↓                                                  │
│  4. Analyze News (scrape + sentiment analysis)          │
│      ↓                                                  │
│  5. Get Market Context (indices, VIX, sector)           │
│      ↓                                                  │
│  6. Retrieve RAG Context (historical patterns)          │
│      ↓                                                  │
│  7. Autonomous Decision (comprehensive LLM)             │
│                                                         │
└─────────────────────────────────────────────────────────┘

Data Sources:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Yahoo Finance API (price, fundamentals, analyst ratings)
• Google Finance (news headlines)
• Major Indices (SPY, QQQ, DIA, IWM)
• VIX (volatility index)
• Sector ETFs (XLK, XLV, XLF, etc.)
• Local Knowledge Base (market patterns)
```

### Agents

| Agent | Purpose | Output |
|-------|---------|--------|
| **DataAgent** | Fetch price data | OHLCV dataframe |
| **FeatureAgent** | Calculate indicators | RSI, MACD, trends |
| **FundamentalAgent** | Get financials | Valuation/health/growth scores |
| **NewsAgent** | Scrape & analyze news | Sentiment score |
| **MarketContextAgent** | Track market | Indices, VIX, trends |
| **RAGAgent** | Retrieve patterns | Historical context |
| **AutonomousReasoningAgent** | Make decision | BUY/SELL/HOLD + details |

---

## 💰 Cost Considerations

### API Costs (OpenAI GPT-4o)

| Task | Tokens | Cost |
|------|--------|------|
| Single stock (original) | ~1,000 | ~$0.02 |
| Single stock (autonomous) | ~3,000 | ~$0.06-$0.10 |
| 10 stocks (autonomous) | ~30,000 | ~$0.60-$1.00 |
| 50 stocks (autonomous) | ~150,000 | ~$3.00-$5.00 |

**Tips to reduce costs:**
- Use fewer workers: `--workers 2`
- Scan fewer stocks at once
- Use watchlist instead of `--sp500`
- Export results to CSV and review without re-scanning

---

## 🔒 Privacy & Security

- ✅ All analysis runs locally
- ✅ Only API calls are to OpenAI and Yahoo Finance
- ✅ No data is stored externally
- ✅ Your API key stays on your machine
- ✅ No telemetry or tracking

---

## ⚠️ Important Disclaimers

### Not Financial Advice

This system is for **educational and research purposes only**. It is NOT:
- Financial advice
- Investment recommendations
- A guarantee of future performance
- A substitute for professional financial advisors

### Understand the Risks

- Stocks can lose value
- AI predictions can be wrong
- Markets are unpredictable
- Past performance ≠ future results

### Best Practices

1. Never invest money you can't afford to lose
2. Diversify your portfolio
3. Do your own research
4. Consult licensed financial advisors
5. Start small and test
6. Set stop losses
7. Have an investment plan

---

## 🐛 Troubleshooting

### "Module not found" errors

```powershell
pip install -r requirements.txt
```

### "API key not found"

Create `.env` file with:
```env
OPENAI_API_KEY=your-key-here
```

### "Too many requests"

Reduce workers:
```powershell
python autonomous_scanner.py --workers 2
```

### Slow performance

Normal for comprehensive analysis. To speed up:
```powershell
# Use more workers (if no rate limits)
python autonomous_scanner.py --workers 5

# Or use original system for speed
python scan_market.py --popular
```

---

## 📞 Support

### Documentation

- [AUTONOMOUS_GUIDE.md](AUTONOMOUS_GUIDE.md) - Full user guide
- [AUTONOMOUS_SETUP.md](AUTONOMOUS_SETUP.md) - Setup guide
- [README.md](README.md) - Original system docs

### Common Questions

**Q: Which system should I use?**
A: Autonomous for thorough analysis, Original for quick scans.

**Q: How accurate is this?**
A: No system is perfect. Use as one input among many.

**Q: How much does it cost?**
A: ~$0.02-$0.10 per stock depending on system.

**Q: Can I use this for day trading?**
A: Original system is better for quick signals.

**Q: Is this safe?**
A: Yes, runs locally. But never invest more than you can lose.

---

## 🎯 Roadmap

### Completed ✅
- Technical analysis system
- Market scanner
- Portfolio management
- Notifications
- Fundamental analysis
- News sentiment
- Market context
- Autonomous decision making

### Planned 🚧
- Backtesting framework
- Paper trading integration
- Mobile app
- Real-time alerts
- Custom indicators
- Social sentiment (Twitter, Reddit)
- Earnings calendar integration

---

## 📄 License

MIT License - See LICENSE file

---

## 🙏 Acknowledgments

- **LangChain** - LLM framework
- **LangGraph** - Workflow orchestration
- **Yahoo Finance** - Market data
- **OpenAI** - GPT models
- **FAISS** - Vector database

---

## 🚀 Getting Started Now

### For Beginners (No Stock Knowledge)

```powershell
# 1. Install
pip install -r requirements.txt

# 2. Add API key to .env
# OPENAI_API_KEY=your-key

# 3. Test one stock
python autonomous_analysis.py AAPL --init-kb

# 4. Scan a few stocks
python autonomous_scanner.py --tickers AAPL MSFT GOOGL
```

### For Experienced Traders

```powershell
# Quick technical scan
python scan_market.py --popular --export quick_scan.csv

# Deep fundamental analysis
python autonomous_analysis.py NVDA --period 1y

# Comprehensive market scan
python autonomous_scanner.py --sp500 --top 20 --export deep_analysis.csv
```

---

**Choose your path:**
- 📘 [Read the Autonomous Guide](AUTONOMOUS_GUIDE.md) - For beginners
- 📗 [Read the Original Guide](README.md) - For technical users
- 🚀 [Quick Setup](AUTONOMOUS_SETUP.md) - Get started now

**Happy Analyzing! 📊🤖**
