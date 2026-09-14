@echo off
REM Installation script for AI Stock Agent (Windows)
REM This script installs all required dependencies

echo =========================================
echo AI Stock Agent - Installation Script
echo =========================================
echo.

REM Check Python version
echo Checking Python version...
python --version > nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found
    echo Please install Python 3.10 or higher from python.org
    pause
    exit /b 1
)

python --version
echo.

REM Check if we're in a virtual environment
if "%VIRTUAL_ENV%"=="" (
    echo WARNING: You are not in a virtual environment
    echo It's recommended to use a virtual environment
    echo.

    set /p create_venv="Do you want to create a virtual environment? (y/n): "

    if /i "%create_venv%"=="y" (
        echo Creating virtual environment...
        python -m venv venv

        echo Activating virtual environment...
        call venv\Scripts\activate.bat

        echo Virtual environment created and activated
        echo.
    )
)

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
echo pip upgraded
echo.

REM Install dependencies
echo Installing dependencies from requirements-windows.txt...
echo This may take several minutes...
echo.

pip install -r requirements-windows.txt

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed
    echo Try running as administrator or check your internet connection
    pause
    exit /b 1
)

echo.
echo All dependencies installed successfully!
echo.

REM Check for .env file
if not exist ".env" (
    echo Setting up environment configuration...
    if exist ".env.example" (
        copy .env.example .env
        echo Created .env file from .env.example
        echo.
        echo IMPORTANT: Edit the .env file and add your API keys:
        echo   - OPENAI_API_KEY or ANTHROPIC_API_KEY (required^)
        echo   - Optional: Discord, Twilio, News API keys
        echo.
    ) else (
        echo WARNING: .env.example not found
    )
) else (
    echo .env file already exists
    echo.
)

REM Run diagnostics
echo Running system diagnostics...
echo.

if exist "diagnose.py" (
    python diagnose.py
    echo.
) else (
    echo Note: diagnose.py not found, skipping diagnostics
    echo.
)

REM Summary
echo =========================================
echo Installation Complete!
echo =========================================
echo.
echo Next steps:
echo 1. Edit .env file and add your API keys
echo 2. Run the application: python app\main.py --ticker AAPL
echo 3. Or try the dashboard: python daily_dashboard.py
echo.
echo For help: python app\main.py --help
echo Documentation: See README.md and DEPENDENCIES.md
echo.

if not "%VIRTUAL_ENV%"=="" (
    echo Note: To activate the virtual environment in future sessions:
    echo   venv\Scripts\activate.bat
    echo.
)

echo Happy trading! 📈
echo.
pause
