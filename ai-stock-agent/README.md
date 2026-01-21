# AI Stock Decision Agent

An intelligent stock analysis system built with LangChain, LangGraph, and RAG (Retrieval-Augmented Generation) that provides reasoned Buy/Hold/Sell recommendations based on technical analysis.

## ⚠️ CRITICAL DISCLAIMER

**THIS IS NOT FINANCIAL ADVICE. THIS SYSTEM IS FOR EDUCATIONAL AND INFORMATIONAL PURPOSES ONLY.**

- This AI system analyzes technical patterns, NOT fundamentals
- It provides directional analysis, NOT price predictions
- Past performance does not guarantee future results
- All investments carry risk of loss
- Always consult qualified financial advisors before making investment decisions
- Never invest money you cannot afford to lose

## 🎯 Project Overview

This system demonstrates how to build a production-quality agentic AI application that:

1. Fetches real-time stock data from Yahoo Finance
2. Computes technical indicators (RSI, MACD, Moving Averages, etc.)
3. Retrieves relevant historical market patterns using RAG
4. Uses LLM reasoning to analyze signals
5. Outputs Buy/Hold/Sell decisions with confidence scores and explanations
6. Includes comprehensive risk warnings

**This is NOT a price prediction system** - it performs technical analysis to assess momentum and trend direction.

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    LANGGRAPH WORKFLOW                       │
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│  │  Fetch   │───▶│ Extract  │───▶│ Retrieve │             │
│  │  Data    │    │ Features │    │ Context  │             │
│  └──────────┘    └──────────┘    └──────────┘             │
│                                        │                    │
│                                        ▼                    │
│                                   ┌──────────┐             │
│                                   │   Risk   │             │
│                                   │  Check   │             │
│                                   └──────────┘             │
│                                        │                    │
│                      ┌─────────────────┴────────┐          │
│                      ▼                          ▼           │
│              ┌──────────────┐          ┌──────────────┐    │
│              │ Add Warning  │          │     LLM      │    │
│              │  (if risky)  │──────────▶  Reasoning   │    │
│              └──────────────┘          └──────────────┘    │
│                                               │             │
│                                               ▼             │
│                                        ┌──────────┐         │
│                                        │ Finalize │         │
│                                        │ Decision │         │
│                                        └──────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### Agent Breakdown

1. **Data Agent** (`agents/data_agent.py`)
   - Fetches OHLCV data from Yahoo Finance
   - Handles caching and data validation
   - Provides clean pandas DataFrames

2. **Graph Feature Agent** (`agents/graph_feature_agent.py`)
   - Computes 20+ technical indicators
   - Detects patterns (crossovers, divergence, etc.)
   - Provides high-level interpretations (trend, momentum, volatility)

3. **RAG Agent** (`agents/rag_agent.py`)
   - Retrieves relevant historical patterns from vector database
   - Generates contextual queries based on technical features
   - Provides educational context to LLM

4. **Reasoning Agent** (`agents/reasoning_agent.py`)
   - Uses LLM (GPT-4 or Claude) for analysis
   - Combines technical signals + RAG context
   - Outputs structured decisions with explanations

### LangGraph Decision Flow

The system uses LangGraph to orchestrate a deterministic workflow:

1. **Fetch Data** - Pull stock data from Yahoo Finance
2. **Extract Features** - Compute technical indicators
3. **Retrieve Context** - Get relevant historical patterns via RAG
4. **Risk Check** - Identify high-risk conditions (high volatility, extreme RSI)
5. **Add Warning** (conditional) - Append risk warnings if needed
6. **LLM Reasoning** - Analyze all signals and context
7. **Finalize Decision** - Validate and adjust confidence based on risk

### How RAG Improves Decisions

Traditional technical analysis systems are "black boxes" that apply rules mechanically. This system uses RAG to:

1. **Provide Context**: Retrieves descriptions of similar historical patterns
2. **Educational Layer**: LLM learns from stored market knowledge
3. **Reasoning**: LLM explains WHY it made a decision, citing patterns
4. **Adaptability**: Can update knowledge base without retraining

The vector database contains:
- Technical pattern descriptions (double bottom, golden cross, etc.)
- Historical behavior of indicators
- Risk management guidelines
- Market context considerations

## 📁 Project Structure

```
ai-stock-agent/
│
├── app/
│   ├── main.py                 # Entry point
│   └── config.py               # Configuration & settings
│
├── agents/
│   ├── data_agent.py           # Yahoo Finance data fetching
│   ├── graph_feature_agent.py  # Technical indicator extraction
│   ├── rag_agent.py            # RAG retrieval logic
│   └── reasoning_agent.py      # LLM-based decision making
│
├── graph/
│   └── decision_graph.py       # LangGraph workflow orchestration
│
├── tools/
│   ├── finance_tools.py        # LangChain tool wrappers
│   └── indicator_utils.py      # Technical indicator functions
│
├── rag/
│   ├── ingest.py               # Document ingestion
│   └── vector_store.py         # FAISS/Chroma vector DB
│
├── data/
│   ├── knowledge_base/         # Educational market content
│   │   ├── market_patterns.txt
│   │   └── risk_guidelines.txt
│   └── vector_store/           # Vector DB storage (created at runtime)
│
├── prompts/
│   └── reasoning_prompt.txt    # LLM system prompt
│
├── tests/
│   └── test_decisions.py       # Unit tests
│
├── requirements.txt
├── .env.example
└── README.md
```

## 🚀 Installation

### Prerequisites

- Python 3.10 or higher
- OpenAI API key OR Anthropic API key
- Internet connection (for Yahoo Finance data)

### Setup Steps

1. **Clone or create the project directory**
```bash
cd ai-stock-agent
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env and add your API key
```

Example `.env`:
```bash
# For OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4-turbo-preview

# OR for Anthropic
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-your-key-here
# LLM_MODEL=claude-3-opus-20240229
```

5. **Initialize knowledge base** (first time only)
```bash
python app/main.py --init-kb AAPL
```

This creates the vector database from the knowledge base files.

## 💻 Usage

### Basic Usage

Analyze a stock:
```bash
python app/main.py AAPL
```

### Advanced Options

```bash
# Analyze with custom period
python app/main.py MSFT --period 1y

# Analyze with different interval
python app/main.py TSLA --period 3mo --interval 1wk

# Reinitialize knowledge base
python app/main.py NVDA --init-kb

# Enable debug logging
python app/main.py GOOGL --debug

# Show help
python app/main.py --help
```

### Example Output

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              AI STOCK DECISION AGENT                         ║
║                                                              ║
║  Agentic AI System for Stock Analysis                       ║
║  Using LangChain, LangGraph, RAG & Technical Analysis        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

======================================================================
STOCK ANALYSIS REPORT: AAPL
======================================================================

📊 STOCK INFORMATION
   Ticker: AAPL
   Current Price: $178.42
   1-Day Change: +1.23%
   5-Day Change: +3.45%
   20-Day Change: +8.92%

📈 TECHNICAL OVERVIEW
   Trend: BULLISH
   Momentum: Increasing
   Pattern: None
   Volatility: MEDIUM

🔍 KEY INDICATORS
   RSI: 62.45 (NEUTRAL)
   MACD Signal: BULLISH
   Volume Confirmation: ✓
   Support Level: $172.30
   Resistance Level: $182.50

🟢 AI DECISION: BUY
   Confidence: 73.5%
   Sentiment: BULLISH

💡 EXPLANATION
   The technical picture shows bullish alignment with price trading
   above both 20-day and 50-day moving averages. Recent golden cross
   confirms strengthening trend. RSI at healthy 62 indicates momentum
   without overbought conditions. MACD recently crossed above signal
   line with expanding histogram. Volume has been confirming the upward
   moves. However, approaching resistance at $182.50 which may cause
   near-term pause.

✅ KEY SUPPORTING SIGNALS
   • Price above all major moving averages
   • MACD bullish crossover with expanding histogram
   • Volume confirming upward moves
   • RSI in healthy range (40-70)
   • Recent golden cross formation

⚠️  RISK FACTORS
   • Approaching resistance level may cause pullback
   • Moderate volatility increases near-term uncertainty
   • Overbought risk if RSI continues rising
   • Market-wide conditions could override individual signals

======================================================================
⚠️  IMPORTANT DISCLAIMER ⚠️
This analysis is generated by an AI system for educational purposes
only. This is NOT financial advice. Always consult qualified advisors
before making investment decisions. Past performance does not guarantee
future results. All investments carry risk of loss.
======================================================================
```

## 🧪 Testing

Run tests:
```bash
pytest tests/test_decisions.py -v
```

Run specific test:
```bash
pytest tests/test_decisions.py::TestIndicatorUtils::test_rsi_calculation -v
```

## 📊 Technical Indicators Computed

- **Moving Averages**: SMA (20, 50), EMA (12, 26)
- **Momentum**: RSI (14), MACD (12,26,9)
- **Volatility**: ATR (14), Bollinger Bands
- **Volume**: Volume trend, confirmation ratios
- **Support/Resistance**: Dynamic levels based on recent data
- **Pattern Detection**: Crossovers, divergence

## 🔧 Configuration

Key settings in `app/config.py`:

```python
# LLM Configuration
LLM_PROVIDER = "openai"  # or "anthropic"
LLM_MODEL = "gpt-4-turbo-preview"
LLM_TEMPERATURE = 0.3

# Technical Indicator Periods
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
SMA_SHORT = 20
SMA_LONG = 50

# RAG Configuration
RAG_TOP_K = 3  # Number of documents to retrieve
EMBEDDING_MODEL = "text-embedding-3-small"

# Risk Thresholds
HIGH_VOLATILITY_THRESHOLD = 0.03  # 3% daily
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
```

## 🛠️ Extending the System

### Add New Technical Indicators

1. Add calculation function to `tools/indicator_utils.py`
2. Update `GraphFeatureAgent.extract_features()` to compute it
3. Include in features dictionary

### Add New Knowledge

1. Create `.txt` or `.md` file in `data/knowledge_base/`
2. Run with `--init-kb` to rebuild vector database
3. RAG will automatically retrieve new content

### Customize Decision Logic

Edit `graph/decision_graph.py` to:
- Add new nodes to workflow
- Modify risk check conditions
- Add custom conditional edges

### Use Different LLM

Set in `.env`:
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-key
LLM_MODEL=claude-3-opus-20240229
```

## 📝 How It Works: Technical Deep Dive

### 1. Data Acquisition
```python
data_agent.fetch_stock_data(ticker="AAPL", period="6mo")
# Returns pandas DataFrame with OHLCV data
```

### 2. Feature Extraction
```python
features = feature_agent.extract_features(df, ticker)
# Computes 20+ technical indicators
# Returns structured dictionary
```

### 3. RAG Retrieval
```python
query = rag_agent._generate_query_from_features(features)
# Example: "bullish trend increasing momentum RSI neutral MACD bullish"

context = rag_agent.retrieve_context(features)
# Retrieves top-3 most relevant historical patterns
```

### 4. LLM Reasoning
```python
decision = reasoning_agent.analyze(
    ticker=ticker,
    latest_price=price,
    features=features,
    context=context
)
# LLM analyzes all inputs and returns structured decision
```

### 5. Risk-Adjusted Finalization
```python
if high_volatility or extreme_RSI:
    decision['confidence'] *= 0.7  # Reduce confidence
    if decision['confidence'] < 0.5:
        decision['decision'] = 'HOLD'  # Change to HOLD if too risky
```

## 🚫 Limitations

**What This System Does NOT Do:**

- ❌ Predict future prices
- ❌ Guarantee profitable trades
- ❌ Analyze company fundamentals
- ❌ Consider news or earnings
- ❌ Account for macroeconomic factors
- ❌ Replace professional financial advice

**Known Limitations:**

- Technical analysis alone is insufficient for investment decisions
- LLM reasoning can vary between runs (temperature > 0)
- Historical patterns may not repeat
- No backtesting or performance validation included
- Market conditions can invalidate all technical signals

## 🔒 Security & Privacy

- API keys stored in `.env` (never commit to git)
- No data sent to third parties except OpenAI/Anthropic APIs
- All stock data from public Yahoo Finance API
- Vector database stored locally

## 📄 License

This is an educational project. Use at your own risk. No warranty provided.

## 🤝 Contributing

This is a demonstration project. Feel free to fork and extend for your own learning.

## 📚 Further Reading

- [LangChain Documentation](https://python.langchain.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Technical Analysis Basics](https://www.investopedia.com/technical-analysis-4689657)
- [RAG Overview](https://python.langchain.com/docs/use_cases/question_answering/)

## 🙏 Acknowledgments

- **yfinance**: For stock market data access
- **LangChain/LangGraph**: For agent orchestration
- **OpenAI/Anthropic**: For LLM capabilities
- **FAISS/Chroma**: For vector similarity search

---

**Remember: This is NOT financial advice. Always do your own research and consult professionals before investing.**
