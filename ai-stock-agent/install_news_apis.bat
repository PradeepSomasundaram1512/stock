@echo off
echo ========================================
echo Enhanced News API Installation
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
    echo No virtual environment found. Please create one first.
    pause
    exit /b 1
)

echo.
echo Installing news API packages...
echo.

pip install newsapi-python==0.2.7
pip install finnhub-python==2.4.19
pip install alpha-vantage==2.3.1

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Next Steps:
echo.
echo 1. Get FREE API keys (5 minutes):
echo    - NewsAPI:       https://newsapi.org/register
echo    - Finnhub:       https://finnhub.io/register
echo    - Alpha Vantage: https://www.alphavantage.co/support/#api-key
echo.
echo 2. Add keys to your .env file:
echo    NEWSAPI_KEY=your-newsapi-key-here
echo    FINNHUB_KEY=your-finnhub-key-here
echo    ALPHAVANTAGE_KEY=your-alphavantage-key-here
echo.
echo 3. Test the system:
echo    python autonomous_analysis.py AAPL
echo.
echo Read NEWS_API_SETUP.md for detailed instructions
echo.
pause
