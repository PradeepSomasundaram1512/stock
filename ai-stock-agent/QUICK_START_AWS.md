# 🚀 Quick Start - Deploy to AWS in 30 Minutes

## Overview

This guide gets your AI Stock Market Scanner running on AWS EC2 in ~30 minutes.

**What you'll have:**
- ✅ Scanner running 24/7 on AWS
- ✅ Hourly Discord alerts during market hours
- ✅ Auto-restart if crashes
- ✅ Complete monitoring and logs

**Cost:** ~$17-35/month depending on instance size

---

## Prerequisites Checklist

Before starting, make sure you have:
- [ ] AWS account (create at aws.amazon.com)
- [ ] Credit card on AWS account
- [ ] OpenAI API key
- [ ] Discord webhook URL (COMPLETE, not cut off!)
- [ ] Your .env file configured correctly
- [ ] This project folder on your Mac

---

## 🚀 3-Step Deployment

### Step 1: Create EC2 Instance (10 min)

1. **Log into AWS**: https://console.aws.amazon.com
2. **Go to EC2** → Click "Launch Instance"
3. **Configure:**
   - **Name:** `stock-market-scanner`
   - **OS:** Ubuntu Server 22.04 LTS
   - **Instance type:** `t3.medium` (recommended) or `t3.small` (budget)
   - **Key pair:** Create new → Name: `stock-scanner-key` → Download .pem file
   - **Network:** Allow SSH from "My IP"
   - **Storage:** 20-30 GB gp3
4. **Click "Launch Instance"**
5. **Wait for status:** "Running" (takes 1-2 min)
6. **Note your Public IP:** Something like `54.123.45.67`

---

### Step 2: Upload Project (5 min)

**On your Mac terminal:**

```bash
# 1. Move your downloaded key to .ssh folder
mv ~/Downloads/stock-scanner-key.pem ~/.ssh/
chmod 400 ~/.ssh/stock-scanner-key.pem

# 2. Make upload script executable
cd "/Users/pradeepsomasundaram/Documents/AI Stock Market/stock/ai-stock-agent"
chmod +x deploy/upload_to_ec2.sh

# 3. Upload everything to EC2 (replace with YOUR IP)
./deploy/upload_to_ec2.sh 54.123.45.67
```

This will upload all your project files to EC2. Takes ~5 minutes.

---

### Step 3: Setup and Start (15 min)

**Connect to EC2:**

```bash
# Replace with YOUR EC2 IP
ssh -i ~/.ssh/stock-scanner-key.pem ubuntu@54.123.45.67
```

**Run automated setup:**

```bash
cd ~/stock-scanner
chmod +x setup_ec2.sh
./setup_ec2.sh
```

This script will:
- ✅ Install Python 3.11 and all dependencies
- ✅ Create virtual environment
- ✅ Set up systemd service (auto-start)
- ✅ Start the scanner
- ✅ Configure firewall

Takes ~10-15 minutes.

---

## ✅ Verify It's Working

**Check service status:**
```bash
sudo systemctl status stock-scanner
```

Should show: **Active (running)** in green ✅

**Watch live logs:**
```bash
tail -f ~/stock-scanner/logs/scanner.log
```

You should see:
- Knowledge base loading
- Market scanner initializing
- "Waiting for market hours..." (if market is closed)
- Or scanning activity (if market is open)

**Check Discord:**
- You should receive test notifications
- During market hours: hourly updates with top stocks

---

## 📊 Monitor Your Scanner

**Run monitor script:**
```bash
chmod +x ~/stock-scanner/monitor.sh
./monitor.sh
```

This shows:
- Service status
- Disk/memory/CPU usage
- Recent logs
- Errors (if any)
- API connectivity

---

## 🛠 Common Management Tasks

### Restart Scanner
```bash
sudo systemctl restart stock-scanner
```

### Stop Scanner
```bash
sudo systemctl stop stock-scanner
```

### View Logs
```bash
# Live logs
tail -f ~/stock-scanner/logs/scanner.log

# Errors only
tail -f ~/stock-scanner/logs/scanner.error.log

# Last 100 lines
tail -n 100 ~/stock-scanner/logs/scanner.log
```

### Update Code
```bash
# Stop scanner
sudo systemctl stop stock-scanner

# Upload new files from your Mac
# (use upload_to_ec2.sh script again)

# Or if using git
cd ~/stock-scanner
git pull

# Restart scanner
sudo systemctl start stock-scanner
```

### Backup Data
```bash
~/stock-scanner/backup.sh
```

---

## 🔍 Troubleshooting

### Scanner Not Starting

```bash
# Check status
sudo systemctl status stock-scanner

# Check logs for errors
tail -n 50 ~/stock-scanner/logs/scanner.error.log

# Try running manually to see error
cd ~/stock-scanner
source venv/bin/activate
python ultimate_market_scanner.py --test-discord
```

### Discord Not Working

1. Check .env file has complete webhook URL
2. Test: `python ultimate_market_scanner.py --test-discord`
3. Verify webhook URL in Discord (Settings → Integrations)

### Out of Memory

```bash
# Add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Can't SSH to EC2

1. Check security group allows SSH from your IP
2. Check instance is running
3. Verify key file permissions: `chmod 400 ~/.ssh/stock-scanner-key.pem`
4. Try: `ssh -v -i ~/.ssh/stock-scanner-key.pem ubuntu@YOUR_IP`

---

## 💰 Cost Management

### Current Cost (t3.medium)
- EC2: ~$30/month
- Storage: ~$2/month
- **Total: ~$32/month**

### Save Money

**Option 1: Use Smaller Instance**
```bash
# Stop instance
# Change instance type to t3.small
# Saves ~$15/month
# Total: ~$17/month
```

**Option 2: Run Only During Market Hours**
```bash
# Set up scheduled start/stop
# Saves ~70% on EC2 costs
# Total: ~$10/month
```

**Option 3: Use Spot Instances**
- 70% cheaper than on-demand
- Can be interrupted (rare)
- Best for non-critical workloads

### Monitor Costs

1. Go to AWS Console → Billing Dashboard
2. Set up budget alerts
3. Review "Cost Explorer"

---

## 🎯 What to Expect

### During Market Hours (9:30 AM - 4:00 PM ET)

**Every hour you'll receive Discord alerts:**
```
📊 Market Scan Complete - 11:00 AM ET

🟢 TOP BUY OPPORTUNITIES
1. $NVDA @ $875.50
   • Confidence: 78%
   • Target: $950.00 (+8.5%)
   ...

🔴 TOP SELL OPPORTUNITIES
1. $TSLA @ $412.30
   • Confidence: 72%
   ...
```

### Outside Market Hours

Scanner waits and will resume automatically when market opens.

---

## 📱 Mobile Setup

**Get alerts on your phone:**

1. Install Discord mobile app
2. Join your server
3. Enable push notifications for your alerts channel
4. You'll get real-time alerts all day! 📲

---

## 🔒 Security Checklist

- [ ] SSH key stored securely (chmod 400)
- [ ] Security group limits SSH to your IP only
- [ ] Firewall enabled on EC2
- [ ] .env file contains API keys (never commit to git)
- [ ] Regular backups scheduled
- [ ] Monitoring alerts set up

---

## 📋 Daily Workflow

**Morning:**
1. Check Discord for any overnight alerts (if configured)
2. Verify scanner is running: `ssh ... && sudo systemctl status stock-scanner`

**During Day:**
3. Receive hourly Discord alerts automatically
4. Review top opportunities
5. Use `ultimate_analysis.py` locally for deep dives

**Evening:**
6. Review all alerts from the day
7. Plan trades for tomorrow
8. Check logs for any issues

---

## 🎉 Success Checklist

Your deployment is successful if:
- [ ] Service shows "Active (running)"
- [ ] Logs show scanner initialization
- [ ] Discord webhook test works
- [ ] Hourly alerts arrive during market hours
- [ ] No errors in error logs
- [ ] System resources under 80% usage
- [ ] Costs tracking within budget

---

## 📞 Quick Reference

```bash
# === Connection ===
ssh -i ~/.ssh/stock-scanner-key.pem ubuntu@YOUR_IP

# === Management ===
sudo systemctl status stock-scanner      # Check status
sudo systemctl restart stock-scanner     # Restart
tail -f ~/stock-scanner/logs/scanner.log # View logs
./monitor.sh                             # Full system check

# === From Your Mac ===
./deploy/upload_to_ec2.sh YOUR_IP       # Upload updates

# === Manual Operations ===
cd ~/stock-scanner
source venv/bin/activate
python ultimate_market_scanner.py --scan-now --quick
```

---

## 🆘 Need Help?

1. Check logs: `tail -f ~/stock-scanner/logs/scanner.error.log`
2. Run monitor: `./monitor.sh`
3. Test manually: `python ultimate_market_scanner.py --test-discord`
4. Review [AWS_DEPLOYMENT_GUIDE.md](AWS_DEPLOYMENT_GUIDE.md) for detailed troubleshooting

---

## 🎓 Next Steps

**After successful deployment:**

1. **Optimize stock list** - Edit `SP500_POPULAR` in `ultimate_market_scanner.py`
2. **Adjust scan frequency** - Modify hourly to every 2 hours if needed
3. **Set up CloudWatch** - For advanced monitoring
4. **Create backups** - Schedule daily backups
5. **Monitor costs** - Set AWS budget alerts

---

**You're all set! Your AI Stock Market Scanner is now running 24/7 on AWS!** 🚀📈

Check Discord for your first hourly alert during market hours!
