@echo off
echo ========================================
echo Autonomous AI Stock Analyzer
echo Installing new dependencies...
echo ========================================
echo.

REM Activate virtual environment if it exists
if exist venv312\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv312\Scripts\activate.bat
) else if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo No virtual environment found.
    echo Creating new virtual environment...
    python -m venv venv312
    call venv312\Scripts\activate.bat
)

echo.
echo Installing new dependencies...
pip install beautifulsoup4==4.12.2
pip install requests==2.31.0
pip install lxml==4.9.3

echo.
echo ========================================
echo Installation complete!
echo ========================================
echo.
echo Next steps:
echo 1. Make sure your .env file has OPENAI_API_KEY
echo 2. Test the system:
echo    python autonomous_analysis.py AAPL --init-kb
echo.
echo Documentation:
echo - AUTONOMOUS_GUIDE.md - User guide
echo - AUTONOMOUS_SETUP.md - Setup guide
echo - ENHANCEMENTS_SUMMARY.md - What's new
echo.
pause
