# 🚀 Daily Trading Bot - Quick Start

## ⚡ 5-Minute Setup

### Option 1: Automated Setup (Easiest)

```powershell
cd "c:\Pradeep\ai-stock-agent"
.\setup_daily_trading.ps1
```

### Option 2: Manual Setup

```powershell
# 1. Install packages
pip install schedule twilio

# 2. Configure .env (add your email + OpenAI key)
notepad .env

# 3. Create watchlist
notepad watchlist.txt

# 4. Test it
python daily_trader.py scan
```

---

## 📱 What You'll Get

### 🌅 Morning Alert (9:35 AM)
```
🟢 TOP BUYS:
1. AAPL @ $180.50 (85%)
2. NVDA @ $520.30 (82%)

🔴 TOP SELLS:
1. TSLA @ $245.20 (88%)
```

### 🎯 Real-Time Alerts
- Target hit: "🎯 AAPL hit $180 target (+3.14% profit)"
- Stop loss: "⛔ TSLA stop loss at $245 (-2% loss)"
- Big moves: "🚨 AMD moved +5.2% - review position"

### 🌙 End-of-Day Summary (4:05 PM)
```
📊 DAILY SUMMARY
Positions: 5
Winners: 3 | Losers: 2
📈 Total P/L: +2.45%
⭐ Top: AAPL (+3.14%)
```

---

## 🎯 Three Ways to Use It

### 1. **Manual Mode** (Test & Learn)
```powershell
# Morning scan
python daily_trader.py scan

# Check positions
python daily_trader.py monitor

# EOD summary
python daily_trader.py summary
```

### 2. **Automated Mode** (Set & Forget)
```powershell
# Runs all day automatically
python automated_trader.py
```

**Schedule:**
- 9:35 AM: Morning scan
- Every 30 min: Position monitoring
- 4:05 PM: Daily summary

### 3. **Custom Watchlist**
```powershell
# Use your own stock list
python daily_trader.py scan --watchlist my_stocks.txt
```

---

## 🔧 Configuration (.env file)

### Minimum Required:
```env
# Email (FREE!)
EMAIL_ENABLED=true
EMAIL_ADDRESS=your.email@gmail.com
EMAIL_PASSWORD=your_gmail_app_password

# AI Analysis
OPENAI_API_KEY=your_openai_key
```

### Optional (Better Alerts):
```env
# SMS (Paid - $0.0075/message)
SMS_ENABLED=true
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=+1234567890
YOUR_PHONE_NUMBER=+1234567890
```

---

## 📊 Watchlist (watchlist.txt)

```
# Your day trading stocks
AAPL
MSFT
NVDA
TSLA
AMD
SPY
QQQ
```

**Tip**: Start with 10-20 stocks for fast scans!

---

## 💡 Pro Tips

1. **Email is easier than SMS** - Start with email notifications
2. **Test before market opens** - Run `python daily_trader.py scan` first
3. **Keep watchlist focused** - 10-20 quality stocks > 100 random stocks
4. **Check the logs** - `trading_bot.log` shows everything
5. **Track performance** - `python backtest_cli.py performance`

---

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| No alerts sent | Check `.env` has `EMAIL_ENABLED=true` |
| Gmail errors | Use App Password, not regular password |
| Bot stops | Check `trading_bot.log` for errors |
| Slow scans | Reduce watchlist size, use `--period 1mo` |

---

## 📖 Full Documentation

- **Complete Guide**: [DAILY_TRADING_SETUP.md](DAILY_TRADING_SETUP.md)
- **Email Setup**: Get Gmail App Password at https://myaccount.google.com/apppasswords
- **SMS Setup**: Sign up at https://www.twilio.com ($15 free credit)

---

## ✅ Quick Test

```powershell
# 1. Setup
.\setup_daily_trading.ps1

# 2. Configure .env with your email

# 3. Test
python daily_trader.py scan

# 4. Go live
python automated_trader.py
```

---

## 🎯 Perfect For

✅ Day traders who want automated morning scans
✅ Busy professionals who can't watch markets all day
✅ Anyone who wants SMS/Email alerts for trades
✅ Traders who want to track multiple stocks easily

---

**Ready? Let's go! 📈**

```powershell
python automated_trader.py
```

🤖 **Bot will handle the rest!**
