# ============================================
# Daily Trading Bot - Quick Setup Script
# ============================================

Write-Host ""
Write-Host "==============================================================="
Write-Host "           DAILY TRADING BOT SETUP                             "
Write-Host "==============================================================="
Write-Host ""

# Step 1: Install dependencies
Write-Host "STEP 1: Installing required packages..." -ForegroundColor Cyan
pip install schedule twilio

Write-Host ""
Write-Host "OK - Packages installed!" -ForegroundColor Green
Write-Host ""

# Step 2: Setup .env file
Write-Host "STEP 2: Setting up configuration..." -ForegroundColor Cyan

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.daily_trading_example") {
        Copy-Item ".env.daily_trading_example" ".env"
        Write-Host "OK - Created .env file from template" -ForegroundColor Green
    } else {
        Write-Host "WARNING - .env.daily_trading_example not found" -ForegroundColor Yellow
    }
} else {
    Write-Host "OK - .env file already exists" -ForegroundColor Green
}

# Step 3: Create watchlist
Write-Host ""
Write-Host "STEP 3: Creating watchlist..." -ForegroundColor Cyan

if (-not (Test-Path "watchlist.txt")) {
    $defaultWatchlist = @"
# Day Trading Watchlist
# Add one ticker per line

# Tech Giants
AAPL
MSFT
GOOGL
NVDA
TSLA
AMD

# ETFs
SPY
QQQ
IWM

# High Volume Stocks
BAC
F
"@
    Set-Content -Path 'watchlist.txt' -Value $defaultWatchlist
    Write-Host 'OK - Created watchlist.txt with default stocks' -ForegroundColor Green
} else {
    Write-Host 'OK - watchlist.txt already exists' -ForegroundColor Green
}

# Step 4: Instructions
Write-Host ""
Write-Host "===============================================================" -ForegroundColor Cyan
Write-Host "                    SETUP COMPLETE!                            " -ForegroundColor Cyan
Write-Host "===============================================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "(1) Configure your .env file:" -ForegroundColor White
Write-Host "   - Add your email and Gmail app password"
Write-Host "   - Add your OpenAI API key"
Write-Host "   - Optionally add Twilio for SMS"

Write-Host ""
Write-Host "(2) Edit watchlist.txt:" -ForegroundColor White
Write-Host "   - Add your favorite stocks (one per line)"

Write-Host ""
Write-Host "(3) Test the system:" -ForegroundColor White
Write-Host "   python daily_trader.py scan" -ForegroundColor Green

Write-Host ""
Write-Host "(4) Run automated bot:" -ForegroundColor White
Write-Host "   python automated_trader.py" -ForegroundColor Green

Write-Host ""
Write-Host "Read DAILY_TRADING_SETUP.md for detailed instructions" -ForegroundColor Cyan
Write-Host ""
Write-Host 'You are ready to go! Happy trading!' -ForegroundColor Green
Write-Host ''
