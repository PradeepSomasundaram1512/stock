# Windows Setup Guide for AI Stock Agent

## Prerequisites

**IMPORTANT:** This project requires **Python 3.10, 3.11, or 3.12** (NOT 3.14)

### Check Your Python Version

```powershell
python --version
```

If you see Python 3.14, you need to install Python 3.12 or 3.11.

## Installation Steps

### Option 1: If You Have Python 3.10-3.12

```powershell
# Navigate to project directory
cd ai-stock-agent

# Create virtual environment
python -m venv venv

# Activate virtual environment (PowerShell)
venv\Scripts\activate

# Or if using Command Prompt (cmd):
# venv\Scripts\activate.bat

# Install dependencies (use Windows-specific requirements)
pip install -r requirements-windows.txt

# If that fails, try installing one at a time:
pip install python-dotenv pydantic yfinance pandas numpy scipy
pip install langchain langchain-openai langchain-community langgraph
pip install faiss-cpu chromadb tiktoken
pip install APScheduler plyer pyttsx3 sqlalchemy
pip install matplotlib plotly pytest
```

### Option 2: If You Have Python 3.14

You need to install Python 3.12 alongside 3.14:

1. **Download Python 3.12**: https://www.python.org/downloads/
2. **Install it** (check "Add to PATH")
3. **Use py launcher** to select version:

```powershell
# Create venv with Python 3.12
py -3.12 -m venv venv

# Activate
venv\Scripts\activate

# Install dependencies
pip install -r requirements-windows.txt
```

## Configuration

### 1. Create .env file

```powershell
# Copy example
copy .env.example .env

# Edit with notepad
notepad .env
```

Add your API key:
```
OPENAI_API_KEY=sk-your-actual-key-here
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview
```

### 2. Initialize Knowledge Base

```powershell
python app\main.py --init-kb AAPL
```

### 3. Test the System

```powershell
# Analyze a stock
python app\main.py AAPL

# Try different stocks
python app\main.py MSFT --period 1y
python app\main.py TSLA
```

## Running the Scheduler

```powershell
# Run with immediate scan
python scheduler\job_runner.py --now

# Run in background
python scheduler\job_runner.py
```

## Troubleshooting

### Issue: "pandas compilation error"

**Cause:** Python 3.14 is too new for pandas 2.1.3

**Solution:** Use Python 3.10-3.12

### Issue: "source command not found"

**Cause:** You're using Windows

**Solution:** Use `venv\Scripts\activate` instead of `source venv/bin/activate`

### Issue: "OPENAI_API_KEY must be set"

**Cause:** .env file not configured

**Solution:**
1. Make sure .env exists (copy from .env.example)
2. Add your actual API key
3. No extra spaces or quotes

### Issue: "Import errors after installation"

**Solution:**
```powershell
# Make sure venv is activated (you should see (venv) in prompt)
venv\Scripts\activate

# Reinstall in order
pip install --upgrade pip
pip install -r requirements-windows.txt
```

### Issue: "plyer notifications don't work"

**Solution:** On Windows, desktop notifications work via win10toast. If issues occur:
```powershell
pip install win10toast
```

### Issue: "pyttsx3 voice doesn't work"

**Solution:** pyttsx3 uses Windows SAPI, should work by default. Test:
```powershell
python -c "import pyttsx3; engine = pyttsx3.init(); engine.say('Test'); engine.runAndWait()"
```

## Minimal Installation (Skip Optional Packages)

If you have issues with some packages, here's the minimal set:

```powershell
# Core only
pip install python-dotenv pydantic
pip install yfinance pandas numpy
pip install langchain langchain-openai langgraph
pip install faiss-cpu tiktoken
pip install APScheduler sqlalchemy

# Skip: chromadb, matplotlib, plotly, plyer, pyttsx3, scipy
```

Then set in .env:
```
VECTOR_DB_TYPE=faiss
ENABLE_DESKTOP_NOTIFICATIONS=false
```

## Verification

After successful installation:

```powershell
# Check imports work
python -c "from graph.decision_graph import get_decision_graph; print('✓ Imports OK')"

# Check config
python -c "from app.config import validate_config; validate_config(); print('✓ Config OK')"
```

## Running on Windows Long-Term

### Option 1: PowerShell Script

Create `run_analyzer.ps1`:
```powershell
# Activate venv
.\venv\Scripts\Activate.ps1

# Run analyzer
python app\main.py $args
```

Usage:
```powershell
.\run_analyzer.ps1 AAPL
.\run_analyzer.ps1 MSFT --period 1y
```

### Option 2: Batch File

Create `run_analyzer.bat`:
```batch
@echo off
call venv\Scripts\activate.bat
python app\main.py %*
```

Usage:
```cmd
run_analyzer.bat AAPL
run_analyzer.bat MSFT --period 1y
```

### Option 3: Windows Task Scheduler

To run daily automatically:

1. Open **Task Scheduler**
2. Create Basic Task
3. Set trigger (daily at 9:30 AM)
4. Action: Start a program
   - Program: `C:\Python312\python.exe` (your Python path)
   - Arguments: `scheduler\job_runner.py --now`
   - Start in: `C:\Pradeep\ai-stock-agent`

## Quick Commands Reference

```powershell
# Activate environment
venv\Scripts\activate

# Deactivate environment
deactivate

# Analyze stock
python app\main.py TICKER

# Run scheduler once
python scheduler\job_runner.py --now

# Run continuous scheduler
python scheduler\job_runner.py

# Run tests
pytest tests\test_decisions.py -v

# Check logs
type stock_agent_scheduler.log

# View database
sqlite3 data\portfolio.db
# Then: SELECT * FROM positions;
```

## Python Version Check Script

Save as `check_python.py`:
```python
import sys
print(f"Python version: {sys.version}")
print(f"Version info: {sys.version_info}")

if sys.version_info >= (3, 10) and sys.version_info < (3, 13):
    print("✓ Compatible Python version")
else:
    print("✗ Incompatible Python version")
    print("Please use Python 3.10, 3.11, or 3.12")
```

Run:
```powershell
python check_python.py
```

## Still Having Issues?

### Manual Installation of Problematic Packages

If pandas fails, try pre-built wheel:
```powershell
pip install --only-binary :all: pandas
```

If faiss-cpu fails:
```powershell
# Alternative: use chroma only
pip install chromadb
# Set VECTOR_DB_TYPE=chroma in .env
```

### Alternative: Use Conda

If pip continues to fail:

```powershell
# Install Miniconda: https://docs.conda.io/en/latest/miniconda.html

# Create environment
conda create -n stock-agent python=3.12
conda activate stock-agent

# Install packages
conda install pandas numpy scipy matplotlib
pip install -r requirements-windows.txt
```

## Success Verification

If everything works, you should see:

```powershell
python app\main.py AAPL

# Output:
╔══════════════════════════════════════════════╗
║      AI STOCK DECISION AGENT                 ║
╚══════════════════════════════════════════════╝

🔄 Analyzing AAPL...

======================================================================
STOCK ANALYSIS REPORT: AAPL
======================================================================
...
```

---

**Next Steps After Successful Installation:**

1. Customize `data\watchlist.txt` with your stocks
2. Run `python scheduler\job_runner.py --now` to test scanner
3. Set up Windows Task Scheduler for daily runs
4. Monitor `stock_agent_scheduler.log` for activity

**Need Help?** Check the main README.md and COMPLETE_SYSTEM_GUIDE.md for detailed documentation.
