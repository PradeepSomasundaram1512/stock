"""
Diagnostic script for AI Stock Agent.
Checks Python version, dependencies, and configuration.
"""

import sys
import platform

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print('='*60)

def check_python_version():
    print_header("Python Version Check")
    print(f"Python Version: {sys.version}")
    print(f"Version Info: {sys.version_info}")
    print(f"Platform: {platform.platform()}")

    if sys.version_info >= (3, 10) and sys.version_info < (3, 13):
        print("✓ Compatible Python version (3.10-3.12)")
        return True
    else:
        print("✗ INCOMPATIBLE Python version")
        print("  Required: Python 3.10, 3.11, or 3.12")
        print("  Your version: Python {}.{}".format(
            sys.version_info.major, sys.version_info.minor
        ))
        return False

def check_dependencies():
    print_header("Dependency Check")

    required = {
        'dotenv': 'python-dotenv',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'yfinance': 'yfinance',
        'langchain': 'langchain',
        'langgraph': 'langgraph',
        'faiss': 'faiss-cpu',
        'apscheduler': 'APScheduler',
        'sqlalchemy': 'sqlalchemy',
    }

    optional = {
        'pyttsx3': 'pyttsx3 (voice notifications)',
        'plyer': 'plyer (desktop notifications)',
        'chromadb': 'chromadb (alternative vector DB)',
        'matplotlib': 'matplotlib (visualization)',
    }

    all_ok = True

    print("\nRequired Packages:")
    for module, package in required.items():
        try:
            __import__(module)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} - NOT INSTALLED")
            all_ok = False

    print("\nOptional Packages:")
    for module, package in optional.items():
        try:
            __import__(module)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ⚠ {package} - not installed (optional)")

    return all_ok

def check_imports():
    print_header("Import Check")

    imports = [
        ('app.config', 'Configuration'),
        ('agents.data_agent', 'Data Agent'),
        ('agents.graph_feature_agent', 'Feature Agent'),
        ('graph.decision_graph', 'Decision Graph'),
        ('portfolio.manager', 'Portfolio Manager'),
        ('notifications.notifier', 'Notifier'),
    ]

    all_ok = True
    for module, name in imports:
        try:
            __import__(module)
            print(f"  ✓ {name}")
        except Exception as e:
            print(f"  ✗ {name} - ERROR: {str(e)[:50]}")
            all_ok = False

    return all_ok

def check_config():
    print_header("Configuration Check")

    try:
        from pathlib import Path
        env_file = Path('.env')

        if env_file.exists():
            print("  ✓ .env file exists")

            # Try to load
            from dotenv import load_dotenv
            import os
            load_dotenv()

            if os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY'):
                print("  ✓ API key configured")
            else:
                print("  ✗ No API key found in .env")
                print("    Add OPENAI_API_KEY=sk-... to .env")
                return False
        else:
            print("  ✗ .env file not found")
            print("    Copy .env.example to .env and add your API key")
            return False

        return True

    except Exception as e:
        print(f"  ✗ Configuration error: {str(e)}")
        return False

def check_data_directories():
    print_header("Directory Check")

    from pathlib import Path

    dirs = [
        'data',
        'data/knowledge_base',
        'data/vector_store',
    ]

    files = [
        'data/knowledge_base/market_patterns.txt',
        'data/knowledge_base/risk_guidelines.txt',
        'data/watchlist.txt',
    ]

    for d in dirs:
        p = Path(d)
        if p.exists():
            print(f"  ✓ {d}/")
        else:
            print(f"  ✗ {d}/ - missing")

    for f in files:
        p = Path(f)
        if p.exists():
            print(f"  ✓ {f}")
        else:
            print(f"  ⚠ {f} - missing")

    return True

def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        AI STOCK AGENT - DIAGNOSTIC TOOL                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    results = []

    results.append(("Python Version", check_python_version()))
    results.append(("Dependencies", check_dependencies()))
    results.append(("Imports", check_imports()))
    results.append(("Configuration", check_config()))
    results.append(("Data Directories", check_data_directories()))

    print_header("Summary")

    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False

    print("\n" + "="*60)

    if all_passed:
        print("\n✓ ALL CHECKS PASSED!")
        print("\nYou're ready to use the system:")
        print("  python app/main.py --init-kb AAPL")
        print("  python app/main.py AAPL")
    else:
        print("\n✗ SOME CHECKS FAILED")
        print("\nRecommended actions:")

        if not results[0][1]:  # Python version
            print("  1. Install Python 3.10, 3.11, or 3.12")
            print("     Download: https://www.python.org/downloads/")

        if not results[1][1]:  # Dependencies
            print("  2. Install missing dependencies:")
            print("     pip install -r requirements-windows.txt")

        if not results[3][1]:  # Config
            print("  3. Configure .env file:")
            print("     copy .env.example .env")
            print("     notepad .env")
            print("     Add: OPENAI_API_KEY=sk-your-key")

    print("\n" + "="*60)
    print()

if __name__ == "__main__":
    main()
