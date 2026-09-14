# Stock Scanner Fixes - Feb 6, 2026

## Problems Fixed

### 1. ❌ STALE PRICES (Frozen for Days)
**Issue:** Stock prices stayed the same for 10+ days
- ORCL stuck at $162.00 from Jan 26 - Feb 3
- NOW stuck at $115.37
- INTU stuck at $498.26

**Root Cause:** `agents/data_agent.py` had in-memory cache with NO expiration
- Singleton pattern kept cache alive forever
- First fetch cached indefinitely until restart

**Fix:** Added 15-minute TTL cache expiration
```python
# Before: Cache forever
if cache_key in self.cache:
    return self.cache[cache_key]  # Never expires!

# After: Check cache age
cache_age = now - self.cache_timestamps[cache_key]
if cache_age < self.cache_ttl:  # 15 minutes
    return self.cache[cache_key]
else:
    # EXPIRED - fetch fresh data
```

### 2. ❌ ONLY 8-10 STOCKS ANALYZED
**Issue:** Same stocks appeared repeatedly
- Only ORCL, NOW, INTU, TSLA, INTC, TXN, CRM, GOOGL

**Root Cause:** `ultimate_market_scanner.py` used `quick=True`
- Limited to 20 stocks from SP500_POPULAR (110 stocks)
- Only first 20 analyzed every scan

**Fix:** Changed to scan ALL stocks (110 stocks)
```python
# Before: Only 20 stocks
scan_market(SP500_POPULAR, quick=True)  # Limits to 20

# After: ALL 110 stocks
data_agent.expire_cache()  # Force fresh data
scan_market(SP500_POPULAR, quick=False)  # ALL stocks (no limit)
```

**Performance:** Reduced delay from 1s to 0.2s → ~4-5 min per scan (fits within hourly schedule)

## Files Modified

1. **agents/data_agent.py**
   - Added `cache_timestamps` dict to track cache age
   - Added `cache_ttl` (15 minute expiration)
   - Updated `fetch_stock_data()` to check cache age
   - Added `expire_cache()` method to force refresh
   - Added `get_cache_stats()` for debugging

2. **ultimate_market_scanner.py**
   - Added `data_agent.expire_cache()` before each scan
   - Changed `quick=True` to `quick=False` in `run_hourly_scan()`
   - Changed `max_stocks` default from 50 to None (scans ALL stocks)
   - Reduced delay from 1s to 0.2s for faster scanning
   - Also added cache expiration to `--scan-now` command

## Expected Results

### Before:
- Same 8 stocks every scan
- Prices frozen for days
- Boring/repetitive Discord alerts

### After:
- ALL 110 stocks analyzed per scan
- Fresh prices every scan (cache expires before scan)
- Maximum variety in recommendations
- Real-time price updates
- Scan completes in ~4-5 minutes

## Testing Locally (Optional)

```bash
cd "/Users/pradeepsomasundaram/Documents/AI Stock Market/stock/ai-stock-agent"
source venv/bin/activate

# Test single scan (will analyze ALL 110 stocks - takes ~4-5 minutes)
python ultimate_market_scanner.py --scan-now

# Quick test (only 20 stocks)
python ultimate_market_scanner.py --scan-now --quick

# Monitor cache stats
python -c "from agents.data_agent import get_data_agent; import json; print(json.dumps(get_data_agent().get_cache_stats(), indent=2))"
```

## Deploy to EC2

### Step 1: Fix Security Group (If Needed)
If you can't connect to EC2, update Security Group:
1. Go to AWS Console → EC2 → Security Groups
2. Find your security group
3. Edit Inbound Rules → SSH (port 22)
4. Change from `184.93.1.206/32` to your current IP or `0.0.0.0/0` (for now)

### Step 2: Upload Files

```bash
# Replace with your EC2 IP
EC2_IP="3.238.127.158"  # or 100.28.131.76

# Upload fixed files
scp -i ~/.ssh/your-key.pem \
  agents/data_agent.py \
  ultimate_market_scanner.py \
  ubuntu@$EC2_IP:~/ai-stock-agent/

# Or use the quick update script
cd "/Users/pradeepsomasundaram/Documents/AI Stock Market/stock"
./ai-stock-agent/deploy/quick_update.sh $EC2_IP
```

### Step 3: Restart Scanner on EC2

```bash
# SSH to EC2
ssh -i ~/.ssh/your-key.pem ubuntu@$EC2_IP

# Restart the scanner service
sudo systemctl restart stock-scanner
sudo systemctl status stock-scanner

# Check logs for fresh data
sudo journalctl -u stock-scanner -f

# Look for these log messages:
# "Expiring cache to get fresh stock prices..."
# "Fetching FRESH data for AAPL..."
# "Scanning ALL 110 stocks"
```

## Verify Fixes

After deploying, check Discord notifications:
- ✅ Stock prices should be CURRENT (not frozen)
- ✅ Should see MANY different stocks across scans (from 110 total)
- ✅ Maximum variety in recommendations each hour
- ✅ Prices match real-time market data
- ✅ Scan completes in ~4-5 minutes

## Cache Behavior

| Scenario | Cache Behavior |
|----------|----------------|
| **First scan** | Fetches fresh data, caches for 15 min |
| **Within 15 min** | Uses cached data (fast) |
| **After 15 min** | Cache expired → fetches fresh data |
| **Hourly scan** | Manually expires cache → always fresh |
| **Manual scan** | Manually expires cache → always fresh |

## Rollback (If Needed)

If something breaks:
```bash
cd ~/ai-stock-agent
git status
git diff agents/data_agent.py
git checkout agents/data_agent.py ultimate_market_scanner.py
sudo systemctl restart stock-scanner
```
