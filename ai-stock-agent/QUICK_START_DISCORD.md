# Quick Start with Discord Alerts

Get FREE trading alerts in 5 minutes!

## Step 1: Install Dependencies

```powershell
pip install yfinance requests
```

## Step 2: Create Discord Server

1. Open Discord (desktop or web: https://discord.com)
2. Click the "+" on left sidebar
3. "Create My Own" → "For me and my friends"
4. Name: "Trading Alerts"

## Step 3: Create Webhook

1. Right-click your server name
2. "Server Settings" → "Integrations"
3. "Create Webhook" (or "Webhooks" → "New Webhook")
4. Name: "AI Stock Bot"
5. Channel: #general (or create a #trading channel)
6. **COPY WEBHOOK URL** (looks like: https://discord.com/api/webhooks/123...)

## Step 4: Configure .env

Edit your `.env` file and add:

```env
DISCORD_ENABLED=true
DISCORD_WEBHOOK_URL=paste_your_webhook_url_here
```

## Step 5: Test It

```powershell
python test_features.py discord
```

You should see a test message in your Discord channel!

## Step 6: Run Daily Trader

```powershell
# Scan market for opportunities
python daily_trader.py scan

# Start automated trading (runs all day)
python automated_trader.py
```

## What You'll Get

### Morning (9:35 AM)
Discord message with:
- Top 3 BUY opportunities
- Price, confidence, targets, stops
- $1000 investment plan

### During Day (every 30 min)
Alerts when positions:
- Hit profit targets
- Hit stop losses
- Need attention

### End of Day (4:05 PM)
Daily summary with:
- Total P/L
- Winners vs losers
- Best performer

## Discord on Phone

1. Download Discord app (iOS/Android)
2. Log in
3. Enable notifications for your trading server
4. Get instant alerts anywhere!

## Troubleshooting

### "Discord notifications disabled"
- Make sure `.env` has `DISCORD_ENABLED=true`
- Restart Python script after editing .env

### "Discord webhook failed"
- Check webhook URL is correct in .env
- Make sure webhook still exists in Discord
- Don't include quotes around the URL in .env

### No messages appearing
- Check the correct channel in Discord
- Verify webhook channel in Discord settings
- Try sending test: `python test_features.py discord`

## Cost

**$0.00 - Completely FREE forever!**

No API keys, no credits, no limits. Discord webhooks are 100% free.

## Next Steps

- Add multi-timeframe analysis
- Enable voice alerts
- Customize watchlist
- Share server with trading buddies

**Happy trading! 🚀**
