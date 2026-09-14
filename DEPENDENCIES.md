# AI Stock Agent - Complete Dependency Guide

## Overview
This document provides a comprehensive overview of all dependencies needed for the AI Stock Agent project.

## Project Type
**Python 3.10+** - Advanced AI-powered stock market analysis and trading system

---

## Installation Methods

### Method 1: Using pip (Recommended)
```bash
# Navigate to project directory
cd ai-stock-agent

# Install all dependencies
pip install -r requirements.txt
```

### Method 2: Using setup.py
```bash
# Navigate to project directory
cd ai-stock-agent

# Install in development mode (recommended for development)
pip install -e .

# Or install normally
pip install .
```

### Method 3: Install specific dependency groups

#### Core Dependencies (Required)
```bash
pip install python-dotenv==1.0.0 pydantic==2.5.0
```

#### Data & Finance (Required)
```bash
pip install yfinance>=0.2.32 pandas>=2.2.0 numpy>=1.26.0 scipy>=1.11.0
```

#### LangChain AI Framework (Required)
```bash
pip install langchain>=0.1.0 langchain-openai>=0.0.2 langchain-anthropic>=0.1.0 \
    langchain-community>=0.0.10 langchain-text-splitters>=0.0.1 langgraph>=0.0.20 \
    tiktoken==0.5.2
```

#### Vector Databases (Required)
```bash
pip install faiss-cpu==1.7.4 chromadb==0.4.18
```

#### Scheduler (Required for automated trading)
```bash
pip install APScheduler==3.10.4 schedule>=1.2.0
```

#### Database (Required for backtesting)
```bash
pip install sqlalchemy==2.0.23
```

#### Web Scraping (Required for news)
```bash
pip install beautifulsoup4==4.12.2 requests==2.31.0 lxml==4.9.3
```

#### Visualization (Optional)
```bash
pip install matplotlib>=3.8.0 plotly>=5.18.0
```

#### Machine Learning (Optional - for price prediction)
```bash
pip install tensorflow>=2.16.0 xgboost>=2.0.0 scikit-learn>=1.3.0
```

#### Notifications (Optional)
```bash
# Desktop notifications
pip install plyer==2.1.0

# Voice notifications
pip install pyttsx3==2.90

# SMS & WhatsApp (via Twilio)
pip install twilio>=8.0.0
```

#### News APIs (Optional)
```bash
pip install newsapi-python==0.2.7 finnhub-python==2.4.19 alpha-vantage==2.3.1
```

#### Testing (Optional)
```bash
pip install pytest==7.4.3 pytest-asyncio==0.21.1
```

---

## Complete Dependency List

### Core Application
| Package | Version | Purpose | Required |
|---------|---------|---------|----------|
| python-dotenv | 1.0.0 | Environment variable management | Yes |
| pydantic | 2.5.0 | Data validation | Yes |

### Data & Finance
| Package | Version | Purpose | Required |
|---------|---------|---------|----------|
| yfinance | >=0.2.32 | Stock market data from Yahoo Finance | Yes |
| pandas | >=2.2.0 | Data manipulation and analysis | Yes |
| numpy | >=1.26.0 | Numerical computing | Yes |
| scipy | >=1.11.0 | Scientific computing | Yes |

### AI/ML Framework
| Package | Version | Purpose | Required |
|---------|---------|---------|----------|
| langchain | >=0.1.0 | LLM orchestration framework | Yes |
| langchain-openai | >=0.0.2 | OpenAI integration | Yes* |
| langchain-anthropic | >=0.1.0 | Anthropic Claude integration | Yes* |
| langchain-community | >=0.0.10 | Community integrations | Yes |
| langchain-text-splitters | >=0.0.1 | Text chunking for RAG | Yes |
| langgraph | >=0.0.20 | Agent graph orchestration | Yes |
| tiktoken | 0.5.2 | Token counting for LLMs | Yes |

*At least one LLM provider (OpenAI or Anthropic) is required

### Vector Databases
| Package | Version | Purpose | Required |
|---------|---------|---------|----------|
| faiss-cpu | 1.7.4 | Facebook AI Similarity Search | Yes |
| chromadb | 0.4.18 | Alternative vector store | Yes |

### Task Scheduling
| Package | Version | Purpose | Required |
|---------|---------|---------|----------|
| APScheduler | 3.10.4 | Advanced task scheduling | Yes |
| schedule | >=1.2.0 | Simple job scheduling | Yes |

### Database
| Package | Version | Purpose | Required |
|---------|---------|---------|----------|
| sqlalchemy | 2.0.23 | SQL toolkit and ORM | Yes |

### Web & APIs
| Package | Version | Purpose | Required |
|---------|---------|---------|----------|
| beautifulsoup4 | 4.12.2 | HTML/XML parsing | Yes |
| requests | 2.31.0 | HTTP library | Yes |
| lxml | 4.9.3 | XML/HTML processing | Yes |

### Visualization (Optional)
| Package | Version | Purpose | Required |
|---------|---------|---------|----------|
| matplotlib | >=3.8.0 | Static plotting | No |
| plotly | >=5.18.0 | Interactive visualization | No |

### Machine Learning (Optional)
| Package | Version | Purpose | Required |
|---------|---------|---------|----------|
| tensorflow | >=2.16.0 | LSTM neural networks | No |
| xgboost | >=2.0.0 | Gradient boosting | No |
| scikit-learn | >=1.3.0 | ML preprocessing & metrics | No |

### Notifications (Optional)
| Package | Version | Purpose | Required |
|---------|---------|---------|----------|
| plyer | 2.1.0 | Cross-platform desktop notifications | No |
| pyttsx3 | 2.90 | Text-to-speech (voice alerts) | No |
| twilio | >=8.0.0 | SMS & WhatsApp notifications | No |

### News APIs (Optional)
| Package | Version | Purpose | Required |
|---------|---------|---------|----------|
| newsapi-python | 0.2.7 | NewsAPI integration | No |
| finnhub-python | 2.4.19 | Finnhub financial news | No |
| alpha-vantage | 2.3.1 | Alpha Vantage news sentiment | No |

### Testing (Optional)
| Package | Version | Purpose | Required |
|---------|---------|---------|----------|
| pytest | 7.4.3 | Testing framework | No |
| pytest-asyncio | 0.21.1 | Async test support | No |

---

## Environment Variables

After installing dependencies, you need to configure environment variables. Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

### Required Environment Variables

```bash
# LLM Provider (choose one)
OPENAI_API_KEY=your_openai_api_key_here
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Set which provider to use
LLM_PROVIDER=openai  # or 'anthropic'
```

### Optional Environment Variables

```bash
# Notification APIs (all optional)
DISCORD_WEBHOOK_URL=your_discord_webhook
NEWSAPI_KEY=your_newsapi_key
FINNHUB_KEY=your_finnhub_key
ALPHAVANTAGE_KEY=your_alphavantage_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
```

See `.env.example` for complete list of configuration options.

---

## System Requirements

- **Python Version**: 3.10, 3.11, or 3.12
- **Operating System**: Windows, macOS, or Linux
- **RAM**: Minimum 4GB (8GB+ recommended for ML features)
- **Disk Space**: ~2GB for all dependencies

---

## Platform-Specific Notes

### Windows
If you're on Windows and encounter issues with `faiss-cpu`, use:
```bash
pip install -r requirements-windows.txt
```

### macOS (Apple Silicon)
TensorFlow installation on M1/M2 Macs:
```bash
pip install tensorflow-macos>=2.16.0
pip install tensorflow-metal  # GPU acceleration
```

### Linux
For better TensorFlow performance:
```bash
pip install tensorflow>=2.16.0
```

---

## Verifying Installation

Run the diagnostic tool to verify all dependencies:

```bash
python diagnose.py
```

Or test the installation:

```bash
python -m app.main --help
```

---

## Troubleshooting

### Common Issues

1. **FAISS installation fails**
   - Try: `pip install faiss-cpu --no-cache-dir`
   - On Windows: Use `requirements-windows.txt`

2. **TensorFlow issues**
   - TensorFlow is optional. If you don't need ML predictions, you can skip it
   - For Apple Silicon: Use `tensorflow-macos` instead

3. **ChromaDB issues**
   - Try upgrading pip: `pip install --upgrade pip`
   - Then: `pip install chromadb==0.4.18`

4. **Import errors**
   - Make sure you're in the correct directory
   - Try: `pip install -e .` to install in development mode

### Getting Help

- Check `diagnose.py` for system diagnostics
- Review `.env.example` for configuration
- Ensure Python 3.10+ is being used: `python --version`

---

## Minimal Installation (For Testing)

If you want to test with minimal dependencies first:

```bash
# Core only (no ML, no optional notifications)
pip install python-dotenv pydantic yfinance pandas numpy scipy \
    langchain langchain-openai langchain-community langchain-text-splitters \
    langgraph tiktoken faiss-cpu chromadb APScheduler schedule \
    sqlalchemy beautifulsoup4 requests lxml
```

Then add optional features as needed.

---

## Updates and Maintenance

To update all dependencies to latest versions:

```bash
pip install --upgrade -r requirements.txt
```

To check for outdated packages:

```bash
pip list --outdated
```

---

## License Notes

All dependencies are open-source with permissive licenses:
- Most use MIT, Apache 2.0, or BSD licenses
- Commercial use is allowed
- Check individual package licenses for specific terms

---

**Last Updated**: 2026-01-23
**Project Version**: 1.0.0
