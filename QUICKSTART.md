# AI Stock Agent - Quick Start Guide

## 🚀 Installation

### Option 1: Automatic Installation (Recommended)

#### macOS/Linux:
```bash
cd ai-stock-agent
chmod +x install.sh
./install.sh
```

#### Windows:
```cmd
cd ai-stock-agent
install.bat
```

### Option 2: Manual Installation

```bash
# Create and activate virtual environment (recommended)
python3 -m venv venv

# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or for Windows:
pip install -r requirements-windows.txt

# Setup environment
cp .env.example .env
```

---

## 🔑 Configuration

Edit the `.env` file and add your API keys:

### Required (choose one):
```bash
# OpenAI (recommended)
OPENAI_API_KEY=sk-...
LLM_PROVIDER=openai

# OR Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...
LLM_PROVIDER=anthropic
```

### Optional Features:

#### Free Notifications:
```bash
# Discord (100% FREE - Recommended!)
DISCORD_ENABLED=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Desktop Voice Alerts (FREE)
VOICE_ENABLED=true

# Email Alerts (FREE)
EMAIL_ENABLED=true
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
SMTP_SERVER=smtp.gmail.com
```

#### News APIs (Optional but Recommended):
```bash
NEWSAPI_KEY=your-key-here          # newsapi.org (free tier)
FINNHUB_KEY=your-key-here          # finnhub.io (free tier)
ALPHAVANTAGE_KEY=your-key-here     # alphavantage.co (free tier)
```

---

## 🎯 Usage

### 1. Analyze a Single Stock

```bash
# Basic analysis
python app/main.py --ticker AAPL

# Extended analysis
python app/main.py --ticker NVDA --period 1y

# Autonomous analysis with ML
python autonomous_analysis.py --ticker TSLA
```

### 2. Scan Multiple Stocks

```bash
# Quick market scan
python scan_market.py

# Full market scanner
python full_market_scanner.py

# Autonomous scanner
python autonomous_scanner.py
```

### 3. View Dashboard

```bash
# Daily dashboard
python daily_dashboard.py

# Full dashboard with analysis
python daily_dashboard_full.py

# Auto-updating dashboard
python auto_dashboard.py
```

### 4. Backtesting

```bash
# Run backtest
python backtest_cli.py --ticker AAPL --start 2023-01-01 --end 2023-12-31

# View backtest performance
python -c "from backtesting.database import get_backtest_db; db = get_backtest_db(); print(db.get_all_backtests())"
```

### 5. Automated Trading

```bash
# Daily trader (scheduled)
python daily_trader.py

# Automated trading with notifications
python automated_trader.py

# Market-wide automated trading
python automated_market_trader.py
```

### 6. Portfolio Management

```bash
# Manage portfolio
python portfolio_manager.py
```

---

## 📊 Features Overview

### Core Features (Always Available):
- ✅ Real-time stock data from Yahoo Finance
- ✅ Multi-agent AI analysis (technical, fundamental, news, market context)
- ✅ LangGraph workflow orchestration
- ✅ RAG-powered knowledge base
- ✅ Backtesting engine with performance tracking
- ✅ Portfolio management

### Optional Features (Install as Needed):
- 📈 **Machine Learning**: LSTM & XGBoost price prediction (requires TensorFlow, XGBoost)
- 🔔 **Notifications**: Discord, Email, SMS, WhatsApp, Voice alerts
- 📰 **News APIs**: Enhanced news sentiment from NewsAPI, Finnhub, Alpha Vantage
- 📊 **Visualization**: Interactive charts with Matplotlib and Plotly

---

## 🧪 Testing Your Installation

### Run Diagnostics:
```bash
python diagnose.py
```

### Test Basic Functionality:
```bash
# Test data fetching
python -c "from agents.data_agent import DataAgent; agent = DataAgent(); data = agent.fetch_stock_data('AAPL'); print('✓ Data fetching works!' if data is not None else '✗ Error')"

# Test LLM connection
python app/main.py --ticker AAPL --help
```

### Test Notifications:
```bash
# Test Discord (if configured)
python test_discord_simple.py

# Test other notifications through the app
python app/main.py --ticker AAPL  # Will use configured notifications
```

---

## 📁 Project Structure

```
ai-stock-agent/
├── app/                    # Main application
│   ├── main.py            # CLI entry point
│   └── config.py          # Configuration
├── agents/                # AI agents
│   ├── data_agent.py      # Data fetching
│   ├── reasoning_agent.py # LLM reasoning
│   ├── fundamental_agent.py
│   ├── news_agent.py
│   └── ...
├── graph/                 # LangGraph workflows
│   ├── decision_graph.py
│   └── autonomous_decision_graph.py
├── rag/                   # RAG knowledge base
│   ├── ingest.py
│   └── vector_store.py
├── notifications/         # Notification systems
├── backtesting/          # Backtesting engine
├── portfolio/            # Portfolio management
├── ml/                   # Machine learning models
├── scheduler/            # Job scheduling
├── data/                 # Data storage
│   ├── knowledge_base/   # RAG documents
│   └── vector_store/     # Vector embeddings
├── requirements.txt      # Dependencies
├── .env                  # Configuration (create from .env.example)
└── README.md            # Documentation
```

---

## 🎓 Example Workflows

### Workflow 1: Morning Market Analysis

```bash
# 1. Scan the market for opportunities
python autonomous_scanner.py

# 2. View dashboard
python daily_dashboard_full.py

# 3. Analyze specific stocks
python autonomous_analysis.py --ticker AAPL
python autonomous_analysis.py --ticker NVDA
python autonomous_analysis.py --ticker TSLA
```

### Workflow 2: Set Up Automated Daily Trading

```bash
# 1. Configure notifications in .env
# Enable Discord and/or Email

# 2. Set up your watchlist
echo "AAPL
NVDA
TSLA
MSFT" > data/watchlist.txt

# 3. Run automated trader
python daily_trader.py
# This will run continuously and trade at market open/close
```

### Workflow 3: Backtest a Strategy

```bash
# 1. Run historical backtest
python backtest_cli.py --ticker AAPL --start 2023-01-01 --end 2024-01-01

# 2. View performance
python backtest_cli.py --list

# 3. Compare with current analysis
python app/main.py --ticker AAPL
```

---

## 🔧 Troubleshooting

### Common Issues:

1. **"No module named 'X'"**
   ```bash
   pip install -r requirements.txt
   ```

2. **"API key not found"**
   - Check your `.env` file
   - Ensure OPENAI_API_KEY or ANTHROPIC_API_KEY is set

3. **"FAISS installation failed"**
   ```bash
   pip install faiss-cpu --no-cache-dir
   ```

4. **TensorFlow errors (Windows)**
   - Use `requirements-windows.txt`
   - TensorFlow is optional - the app works without it

5. **Virtual environment issues**
   ```bash
   deactivate  # Exit current env
   rm -rf venv  # Remove old env
   python3 -m venv venv  # Create new env
   source venv/bin/activate  # Activate
   pip install -r requirements.txt  # Reinstall
   ```

---

## 💡 Tips

1. **Start Simple**: Begin with basic analysis before enabling all features
2. **Use Notifications**: Discord webhooks are free and instant
3. **Leverage RAG**: Add your own trading strategies to `data/knowledge_base/`
4. **Test First**: Use backtesting before live trading
5. **Monitor API Costs**: Track your OpenAI/Anthropic usage
6. **Free APIs**: NewsAPI, Finnhub, Alpha Vantage have free tiers

---

## 📚 Next Steps

- Read [DEPENDENCIES.md](DEPENDENCIES.md) for detailed dependency info
- Review `.env.example` for all configuration options
- Check individual agent files for customization
- Explore the `data/knowledge_base/` for RAG customization
- Set up scheduled jobs with `scheduler/`

---

## 🚨 Important Notes

### Disclaimer
This is an educational project. Not financial advice. Always do your own research before making investment decisions.

### API Costs
- **OpenAI**: ~$0.01-0.10 per analysis (GPT-4)
- **Anthropic**: Similar pricing for Claude
- **News APIs**: Free tiers available
- **Notifications**: Discord, Email, Voice are FREE

### Rate Limits
- Be mindful of API rate limits
- Yahoo Finance: No official rate limit, but be reasonable
- News APIs: Check your tier limits

---

## 📞 Support

- **Issues**: Check `diagnose.py` output
- **Documentation**: See README.md and code comments
- **Logs**: Check console output for detailed error messages

---

**Happy Trading! 📈🤖**

For more details, see:
- [README.md](README.md) - Full documentation
- [DEPENDENCIES.md](DEPENDENCIES.md) - Dependency guide
- [.env.example](.env.example) - Configuration options
