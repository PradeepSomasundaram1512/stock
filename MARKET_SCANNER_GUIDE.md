# 🚀 Ultimate Market Scanner - Complete Guide

## What It Does

**Automatically scans 100+ stocks every hour and sends you Discord alerts with:**
- 🟢 TOP 2 BUY opportunities (highest confidence, best potential)
- 🔴 TOP 2 SELL opportunities (highest risk, time to exit)
- 📊 Price targets, confidence levels, key factors
- ⏰ Hourly updates during market hours (9:30 AM - 4:00 PM ET)

---

## 🔧 Setup (One-Time)

### Step 1: Get Your Discord Webhook URL

1. **Open Discord** and go to your server
2. **Right-click your channel** → Settings → Integrations
3. **Click "Webhooks"** → "New Webhook"
4. **Name it** "Stock Alerts" (or whatever you want)
5. **Copy the Webhook URL** (entire URL, don't cut it off!)
6. **Save it**

### Step 2: Update Your .env File

```bash
# Edit .env file
nano .env

# Find this line:
DISCORD_WEBHOOK_URL=...

# Replace with your COMPLETE webhook URL:
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_FULL_WEBHOOK_URL_HERE

# Save: Ctrl+X, then Y, then Enter
```

**IMPORTANT**: Make sure you copy the ENTIRE webhook URL! It should be very long (100+ characters).

### Step 3: Enable Discord Notifications

```bash
# In .env file, make sure this is set:
DISCORD_ENABLED=true
```

---

## 🚀 How to Use

### Option 1: Scan Market Once (Right Now)

```bash
# Activate environment
cd "/Users/pradeepsomasundaram/Documents/AI Stock Market/stock/ai-stock-agent"
source venv/bin/activate

# Scan the market once and get results immediately
python ultimate_market_scanner.py --scan-now
```

**What happens:**
- Scans 100 popular stocks (AAPL, NVDA, TSLA, etc.)
- Analyzes each with full AI (Technical, Fundamental, News)
- Shows TOP 2 BUY and TOP 2 SELL in your terminal
- Sends results to Discord
- Takes ~15-30 minutes

### Option 2: Quick Scan (Faster, Top 20 Stocks Only)

```bash
python ultimate_market_scanner.py --scan-now --quick
```

**What happens:**
- Scans only top 20 stocks
- Much faster (~5 minutes)
- Good for quick market pulse check

### Option 3: Auto-Monitor (Hourly Updates All Day) ⭐ BEST

```bash
python ultimate_market_scanner.py --monitor
```

**What happens:**
- Runs continuously from market open to close
- Scans market every hour (10:00 AM, 11:00 AM, 12:00 PM, etc.)
- Sends Discord alert each hour automatically
- Press Ctrl+C to stop

---

## 📊 What You'll Get on Discord

### Example Alert:

```
📊 Market Scan Complete - 11:00 AM ET

🟢 TOP BUY OPPORTUNITIES

1. $NVDA @ $875.50
   • Confidence: 78%
   • Target: $950.00 (+8.5%)
   • Risk: LOW
   • Key: strong momentum, positive earnings

2. $AAPL @ $248.04
   • Confidence: 65%
   • Target: $287.22 (+15.8%)
   • Risk: MEDIUM
   • Key: oversold RSI, analyst upgrades

🔴 TOP SELL OPPORTUNITIES

1. $TSLA @ $412.30
   • Confidence: 72%
   • Risk: HIGH
   • Key: overbought, weakening fundamentals

2. $META @ $520.15
   • Confidence: 58%
   • Risk: MEDIUM
   • Key: negative news, high volatility

---
*Not financial advice. Always do your own research.*
```

---

## ⚡ Quick Commands Reference

```bash
# Navigate to project
cd "/Users/pradeepsomasundaram/Documents/AI Stock Market/stock/ai-stock-agent"

# Activate environment
source venv/bin/activate

# Test Discord (verify webhook works)
python ultimate_market_scanner.py --test-discord

# Scan market once
python ultimate_market_scanner.py --scan-now

# Quick scan (top 20 stocks)
python ultimate_market_scanner.py --scan-now --quick

# Auto-monitor with hourly updates
python ultimate_market_scanner.py --monitor

# See all options
python ultimate_market_scanner.py --help
```

---

## 🎯 Recommended Usage

### For Day Trading:
```bash
# Run this in the morning and let it run all day
python ultimate_market_scanner.py --monitor
```
You'll get hourly Discord alerts from 9:30 AM to 4:00 PM ET automatically!

### For Quick Check:
```bash
# Quick scan when you want a market pulse
python ultimate_market_scanner.py --scan-now --quick
```

### For Deep Analysis:
```bash
# Full scan of 100+ stocks
python ultimate_market_scanner.py --scan-now
```

---

## 🔍 What Stocks Are Scanned?

### Default List (100 stocks):
- **Mega-cap Tech**: AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, etc.
- **Finance**: JPM, V, MA, BAC, WFC, GS, etc.
- **Healthcare**: UNH, LLY, JNJ, ABBV, etc.
- **Consumer**: COST, WMT, HD, NKE, SBUX, etc.
- **Energy**: XOM, CVX, COP, etc.
- **Popular Growth**: PLTR, SNOW, CRWD, COIN, UBER, etc.

**Want to scan different stocks?** Edit the `SP500_POPULAR` list in the script!

---

## 💡 Pro Tips

1. **Run --monitor in a screen/tmux session** so it keeps running even if you close terminal
2. **Use --quick for hourly updates** (faster, less API costs)
3. **Check Discord on your phone** for instant alerts throughout the day
4. **Set up multiple Discord channels** for different strategies
5. **Combine with ultimate_analysis.py** for deep dive on specific stocks

---

## 🛠 Troubleshooting

### "Discord webhook not configured"
- Your .env file doesn't have DISCORD_WEBHOOK_URL set
- Follow Setup Step 1 & 2 above

### "401 Unauthorized" error
- Your webhook URL is incomplete or wrong
- Get a fresh webhook URL from Discord
- Make sure you copy the ENTIRE URL

### "Market is closed"
- Scanner only runs during market hours (9:30 AM - 4:00 PM ET, Monday-Friday)
- It will wait automatically until market opens

### Scan takes too long
- Use --quick flag for faster scans
- Or reduce the stock list in the script

---

## 📱 Mobile Setup

Want alerts on your phone?
1. Install Discord mobile app
2. Join your server
3. Enable notifications for the alerts channel
4. You'll get push notifications every hour! 🔔

---

## 🎓 How It Works

For each stock, the scanner:
1. ✅ Fetches real-time price data
2. ✅ Calculates 50+ technical indicators
3. ✅ Analyzes fundamentals (P/E, growth, margins)
4. ✅ Checks news sentiment from 3 APIs
5. ✅ Evaluates market context
6. ✅ Runs AI decision model
7. ✅ Ranks by confidence × potential

Then it picks the TOP 2 of each category and alerts you!

---

## 📈 Example Workflow

**Morning (9:00 AM):**
```bash
python ultimate_market_scanner.py --monitor
```

**You get alerts at:**
- 10:00 AM - First scan after market open
- 11:00 AM - Mid-morning update
- 12:00 PM - Lunch update
- 1:00 PM - Early afternoon
- 2:00 PM - Late afternoon
- 3:00 PM - Pre-close update

**Evening:**
- Review all Discord alerts
- Deep-dive interesting stocks with `ultimate_analysis.py`
- Plan your trades for tomorrow

---

## ⚠️ Important Notes

1. **Not Financial Advice** - This is an educational tool
2. **API Costs** - Each scan uses OpenAI API (costs ~$0.50-2.00 per full scan)
3. **Rate Limits** - Respect Yahoo Finance and News API rate limits
4. **Market Hours** - Only scans during US market hours automatically
5. **Confidence ≠ Certainty** - AI can be wrong, always do your own research

---

## 🚀 Ready to Go!

**Test it now:**
```bash
cd "/Users/pradeepsomasundaram/Documents/AI Stock Market/stock/ai-stock-agent"
source venv/bin/activate
python ultimate_market_scanner.py --test-discord
```

If you see a Discord notification, you're all set! 🎉

**Start monitoring:**
```bash
python ultimate_market_scanner.py --monitor
```

Happy trading! 📈
