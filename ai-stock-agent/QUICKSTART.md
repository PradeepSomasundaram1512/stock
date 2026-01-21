# Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies
```bash
cd ai-stock-agent
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API Key
```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI key:
```bash
OPENAI_API_KEY=sk-your-actual-key-here
```

### 3. Initialize Knowledge Base
```bash
python app/main.py --init-kb AAPL
```

### 4. Run Analysis
```bash
python app/main.py AAPL
```

## Sample Commands

```bash
# Analyze Apple
python app/main.py AAPL

# Analyze Microsoft with 1-year data
python app/main.py MSFT --period 1y

# Analyze Tesla with weekly interval
python app/main.py TSLA --interval 1wk

# Analyze NVIDIA with debug output
python app/main.py NVDA --debug
```

## Expected Output

You should see:
1. Banner with system info
2. Analysis progress messages
3. Detailed stock report with:
   - Current price and changes
   - Technical indicators (RSI, MACD, etc.)
   - AI decision (Buy/Hold/Sell)
   - Confidence score
   - Detailed explanation
   - Risk factors
   - Disclaimer

## Troubleshooting

### "OPENAI_API_KEY must be set"
- Check that `.env` file exists
- Verify API key is correct
- Ensure no extra spaces in `.env`

### "No data returned for ticker"
- Ticker symbol may be invalid
- Try a common ticker like AAPL, MSFT, GOOGL
- Check internet connection

### "Vector store not found"
- Run with `--init-kb` flag first time
- This creates the knowledge base

### Import Errors
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt` again
- Check Python version is 3.10+

## What Each Component Does

- **main.py**: Entry point, orchestrates everything
- **data_agent.py**: Fetches stock data from Yahoo Finance
- **graph_feature_agent.py**: Computes technical indicators
- **rag_agent.py**: Retrieves relevant market knowledge
- **reasoning_agent.py**: LLM analyzes and decides
- **decision_graph.py**: LangGraph workflow coordinator

## Next Steps

1. Try different tickers (MSFT, GOOGL, TSLA, NVDA)
2. Experiment with different time periods (1mo, 3mo, 1y)
3. Read the full README.md for architecture details
4. Explore the knowledge base files in `data/knowledge_base/`
5. Modify technical indicator parameters in `app/config.py`

## Remember

**THIS IS NOT FINANCIAL ADVICE**

This system is for educational purposes only. Always:
- Do your own research
- Consult qualified financial advisors
- Never invest money you can't afford to lose
- Understand that past performance doesn't guarantee future results
