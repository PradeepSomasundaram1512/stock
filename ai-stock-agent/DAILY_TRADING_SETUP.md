# 📱 Daily Trading Bot Setup Guide

Complete setup for automated daily trading with SMS/Email alerts - Perfect for day trading!

## 🎯 What This System Does

1. **Morning (9:35 AM)**: Scans your watchlist and sends top BUY/SELL opportunities
2. **During Market Hours**: Monitors your positions every 30 minutes
3. **Real-Time Alerts**: Sends SMS/Email when targets or stop-losses are hit
4. **End of Day (4:05 PM)**: Sends daily performance summary

---

## ⚡ Quick Start (5 Minutes)

### Step 1: Install Required Packages

```powershell
cd "c:\Pradeep\ai-stock-agent"
pip install schedule twilio
```

**Note**: Twilio is only needed for SMS. Email works without any extra packages!

---

### Step 2: Configure Notifications

Edit your `.env` file:

#### Option A: Email Notifications (Easiest - FREE!)

```env
# Email Notifications
EMAIL_ENABLED=true
EMAIL_ADDRESS=your.email@gmail.com
EMAIL_PASSWORD=your_app_password
RECIPIENT_EMAIL=your.email@gmail.com

# Gmail SMTP (default)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

**How to get Gmail App Password:**
1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and your device
3. Copy the 16-character password
4. Paste it as EMAIL_PASSWORD

#### Option B: SMS Notifications (Paid - Twilio)

```env
# SMS Notifications
SMS_ENABLED=true
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
YOUR_PHONE_NUMBER=+1234567890
```

**How to setup Twilio:**
1. Sign up at https://www.twilio.com (Free trial: $15 credit)
2. Get a phone number ($1/month)
3. Copy Account SID and Auth Token from dashboard

---

### Step 3: Create Your Watchlist

Create a file named `watchlist.txt` in the project folder:

```
# Your day trading watchlist
# Add one ticker per line

# Tech Stocks
AAPL
MSFT
NVDA
TSLA
AMD

# High Volume
SPY
QQQ
IWM

# Add your favorites here
```

**Pro Tip**: Start with 10-20 stocks. More stocks = longer scan time.

---

## 🚀 Running the Bot

### Test It First (Manual Commands)

```powershell
# Test morning scan
python daily_trader.py scan

# Test position monitoring
python daily_trader.py monitor

# Test EOD summary
python daily_trader.py summary
```

---

### Run Automated Bot (Runs All Day)

```powershell
python automated_trader.py
```

**What happens:**
- ✅ Runs morning scan at 9:35 AM
- ✅ Monitors positions every 30 minutes
- ✅ Sends alerts when targets/stops hit
- ✅ Sends EOD summary at 4:05 PM
- ✅ Skips weekends automatically

**Keep it running**: The bot will run until you press `Ctrl+C`

---

## 📅 Schedule Configuration

Edit `automated_trader.py` to customize:

```python
CONFIG = {
    'morning_scan_time': "09:35",  # When to scan
    'monitor_interval_minutes': 30,  # How often to check positions
    'eod_summary_time': "16:05",  # When to send summary
    'watchlist': 'watchlist.txt',  # Your watchlist file
    'scan_period': '1mo'  # Data period (1mo perfect for day trading)
}
```

---

## 📱 What Alerts You'll Get

### Morning Alert (9:35 AM)
```
🌅 MARKET OPEN ALERT - Jan 09, 2026

🟢 TOP BUYS:
1. AAPL @ $180.50 (85%)
2. NVDA @ $520.30 (82%)
3. AMD @ $142.10 (78%)

🔴 TOP SELLS:
1. TSLA @ $245.20 (88%)

View full report in your dashboard.
```

### Target Hit Alert (Real-time)
```
🎯 TARGET HIT: AAPL

Entry: $175.00
Target: $180.00
Current: $180.50
📈 Profit: +3.14%

Consider taking profits!
```

### Stop Loss Alert (Real-time)
```
⛔ STOP LOSS: TSLA

Entry: $250.00
Stop: $245.00
Current: $244.80
📉 Loss: -2.08%

Exit position to limit losses!
```

### Daily Summary (4:05 PM)
```
📊 DAILY SUMMARY - Jan 09

Positions: 5
Winners: 3 | Losers: 2
📈 Total P/L: +2.45%

⭐ Top: AAPL (+3.14%)
```

---

## 🎛️ Customization Options

### Change Analysis Period

```powershell
# Faster scans (15-20 days of data)
python daily_trader.py scan --period 1mo

# More comprehensive (65 days)
python daily_trader.py scan --period 3mo

# Long-term (250 days)
python daily_trader.py scan --period 1y
```

**Recommendation**: Use `1mo` for day trading (fastest, most responsive)

### Use Different Watchlist

```powershell
python daily_trader.py scan --watchlist my_stocks.txt
```

### Change Monitoring Frequency

Edit `automated_trader.py`:
```python
'monitor_interval_minutes': 15,  # Check every 15 minutes instead of 30
```

---

## 💡 Pro Tips for Day Trading

1. **Start Small**: Begin with 10-15 stocks you know well
2. **Test First**: Run manual commands before using automated mode
3. **Check Alerts**: Make sure SMS/Email works before market opens
4. **Review Logs**: Check `trading_bot.log` for detailed activity
5. **Monitor Performance**: Use `python backtest_cli.py performance` to track results
6. **Adjust Confidence**: Bot only alerts on 65%+ confidence - adjust in code if needed

---

## 🔧 Troubleshooting

### "No notifications sent"
- Check `.env` file has correct credentials
- Verify `EMAIL_ENABLED=true` or `SMS_ENABLED=true`
- Test with manual command: `python daily_trader.py scan`

### "Watchlist not found"
- Bot will auto-create `watchlist.txt` with popular stocks
- Or create it manually with your tickers

### "Analysis taking too long"
- Reduce watchlist size (aim for 10-20 stocks)
- Use shorter period: `--period 1mo`

### "Bot stops running"
- Check `trading_bot.log` for errors
- Make sure your computer doesn't go to sleep
- Run in background or use cloud server

---

## 🚀 Advanced: Run 24/7 on Cloud

To run the bot continuously without keeping your computer on:

### Option 1: Windows Task Scheduler
1. Create batch file: `start_bot.bat`
   ```batch
   cd c:\Pradeep\ai-stock-agent
   call venv312\Scripts\activate
   python automated_trader.py
   ```
2. Open Task Scheduler → Create Task
3. Trigger: At system startup
4. Action: Run `start_bot.bat`

### Option 2: Cloud (AWS, Azure, Google Cloud)
- Deploy to cloud VM
- Run 24/7 without local computer
- More reliable for critical trading

---

## 📊 Viewing Your Results

```powershell
# See all open positions
python backtest_cli.py positions

# View overall performance
python backtest_cli.py performance

# Check specific stock history
python backtest_cli.py ticker AAPL

# Update position prices
python backtest_cli.py update
```

---

## ⚠️ Important Notes

1. **This is analysis, not financial advice** - Always do your own research
2. **Test thoroughly** before using with real money
3. **Market conditions change** - No system is 100% accurate
4. **Monitor your positions** - Don't rely solely on alerts
5. **Costs**: Email is FREE, Twilio SMS costs ~$0.0075 per message

---

## 🎓 Example Daily Workflow

**9:30 AM** - Market opens
- Bot automatically scans watchlist
- You receive top BUY/SELL opportunities via SMS/Email

**During Day** - Monitor positions
- Bot checks every 30 minutes
- Alerts you if targets/stops hit
- You make trading decisions

**4:00 PM** - Market closes
- Bot sends daily summary
- Review performance
- Plan for tomorrow

---

## 📞 Support

If you need help:
1. Check `trading_bot.log` for detailed errors
2. Review this guide carefully
3. Test with manual commands first
4. Start with email (easier than SMS)

---

## ✅ Ready to Start!

```powershell
# 1. Configure .env with email/SMS
# 2. Create watchlist.txt
# 3. Test it
python daily_trader.py scan

# 4. Run automated bot
python automated_trader.py
```

**Happy Trading! 📈**
