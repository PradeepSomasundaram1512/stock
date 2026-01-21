# Discord Webhook Setup Guide

Discord webhooks are **100% FREE** and perfect for trading alerts!

## Why Discord?
- ✅ **Completely FREE** (no limits!)
- ✅ Rich formatting with colors and embeds
- ✅ Works on desktop, web, and mobile
- ✅ No authentication needed (just a webhook URL)
- ✅ Instant notifications
- ✅ Message history preserved forever

---

## Step 1: Create a Discord Server (2 minutes)

1. Open Discord (desktop or web)
2. Click the "+" button on the left sidebar
3. Choose "Create My Own"
4. Choose "For me and my friends"
5. Name it: "Trading Bot Alerts" (or whatever you like)
6. Click "Create"

---

## Step 2: Create a Webhook (1 minute)

1. Right-click your new server
2. Click "Server Settings"
3. Click "Integrations" in the left menu
4. Click "Create Webhook" (or "Webhooks" → "New Webhook")
5. Name it: "AI Stock Bot"
6. Select the channel (usually #general)
7. Click "Copy Webhook URL"
8. Save this URL - you'll need it for .env

Your webhook URL looks like:
```
https://discord.com/api/webhooks/1234567890/AbCdEfGhIjKlMnOpQrStUvWxYz...
```

---

## Step 3: Configure .env

Add these lines to your `.env` file:

```env
# Discord Alerts (100% FREE!)
DISCORD_ENABLED=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL_HERE
```

**Replace** `YOUR_WEBHOOK_URL_HERE` with the webhook URL you copied in Step 2.

---

## Step 4: Test It

```powershell
# Test Discord alerts
python test_features.py discord
```

You should see a test message appear in your Discord channel!

---

## What You'll Receive

### 1. Market Open Alerts
Every morning at 9:35 AM:
```
🌅 MARKET OPEN ALERT
Jan 21, 2026

🟢 TOP BUYS
1. AAPL @ $180.50
   Confidence: 85%
   🎯 Target: $185.50 (+2.8%)
   ⛔ Stop: $175.00 (-3.0%)

2. NVDA @ $520.30
   Confidence: 82%
   🎯 Target: $540.00 (+3.8%)
   ⛔ Stop: $505.00 (-2.9%)
```

### 2. Position Alerts
When your positions need attention:
```
🚨 POSITION ALERT: AAPL
Action: SELL
Current Price: $185.50
Entry Price: $180.50
📈 P/L: +2.77%
Reason: Target hit - take profits
```

### 3. Target Hit Alerts
When profit targets are reached:
```
🎯 TARGET HIT: AAPL
💰 Consider taking profits!

Entry: $180.50
Target: $185.00
Current: $185.50
📈 Profit: +2.77%
```

### 4. Stop Loss Alerts
When stop losses are triggered:
```
⛔ STOP LOSS: TSLA
⚠️ Exit position to limit losses!

Entry: $250.00
Stop: $242.50
Current: $241.00
📉 Loss: -3.60%
```

### 5. Daily Summary
End of day at 4:05 PM:
```
📊 DAILY SUMMARY
Jan 21

Positions: 5
Winners: 3 | Losers: 2
📈 Total P/L: +1.8%

⭐ Top Performer: NVDA (+5.2%)
```

### 6. Multi-Timeframe Alerts
When strong signals appear:
```
🟢 MULTI-TIMEFRAME ALERT
🔥 HIGH CONVICTION SIGNAL!

Ticker: AAPL
Signal: BUY
Confidence: 95%
Alignment: 3/3 timeframes
```

---

## Discord on Your Phone

1. Download Discord app (iOS/Android)
2. Log in with your account
3. Your server will appear
4. Enable push notifications for that channel
5. Never miss a trade alert!

---

## Update daily_trader.py

Your `daily_trader.py` already supports Discord! Just make sure it's imported:

```python
from notifications.discord_notifier import get_discord_notifier

# In __init__:
self.discord = get_discord_notifier()

# When sending alerts:
if self.discord.enabled:
    self.discord.send_market_open_alert(top_buys, top_sells)
```

---

## Troubleshooting

### "Discord message failed"
- Check that your webhook URL is correct in .env
- Make sure the webhook wasn't deleted in Discord
- Test the webhook manually:
  ```powershell
  curl -X POST -H "Content-Type: application/json" -d "{\"content\":\"Test\"}" YOUR_WEBHOOK_URL
  ```

### "Discord notifications disabled"
- Check `.env` has `DISCORD_ENABLED=true`
- Restart your Python script after editing .env

### No notifications appearing
- Check the Discord channel you selected for the webhook
- Make sure Discord is running
- Check notification settings in Discord app

---

## Cost Comparison

| Method | Cost | Pros | Cons |
|--------|------|------|------|
| **Discord** | **FREE** | Rich formatting, unlimited, mobile app | Need Discord account |
| SMS (Twilio) | $0.0075/msg | Direct to phone | Costs money |
| WhatsApp (Twilio) | FREE (sandbox) | Free, familiar | Sandbox limitations |
| Email | FREE | Universal | Can go to spam |
| Voice | FREE | Can't miss it | Need computer on |

---

## Pro Tips

1. **Create Separate Channels**
   - #market-open (morning scans)
   - #alerts (urgent position updates)
   - #daily-summary (EOD summaries)
   - Configure different webhooks for each

2. **Mobile Notifications**
   - Set Discord to "All Messages" for trading channels
   - Use different notification sounds for different channels

3. **Multiple Servers**
   - Create different servers for different strategies
   - Paper trading vs real trading

4. **Share with Friends**
   - Invite friends to your trading server
   - They'll see all the same alerts
   - Great for trading groups!

---

## Next Steps

After Discord is working:

1. **Test it**: `python test_features.py discord`
2. **Run morning scan**: `python daily_trader.py scan`
3. **Start automated trading**: `python automated_trader.py`

---

**You now have FREE, rich, instant trading alerts on any device! 🚀**
