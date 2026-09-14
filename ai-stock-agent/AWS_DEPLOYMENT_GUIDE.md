# 🚀 AWS Deployment Guide - Complete Setup

This guide will help you deploy your AI Stock Market Scanner to AWS EC2 for 24/7 automated operation.

---

## 📋 What You'll Get

After following this guide:
- ✅ **EC2 instance running 24/7** (always on, never stops)
- ✅ **Automatic market scanning** every hour during market hours
- ✅ **Discord alerts** sent to your channel automatically
- ✅ **Auto-restart** if system crashes
- ✅ **Logs and monitoring** to track performance
- ✅ **Secure setup** with best practices
- ✅ **Cost: ~$10-15/month** (t3.small instance)

---

## 🏗 Architecture Overview

```
┌─────────────────────────────────────────┐
│         AWS EC2 Instance                │
│  (Ubuntu 22.04, t3.small/medium)        │
│                                         │
│  ┌───────────────────────────────┐     │
│  │   Ultimate Market Scanner      │     │
│  │   (runs as systemd service)    │     │
│  └───────────────────────────────┘     │
│           │                             │
│           ├─> Yahoo Finance API         │
│           ├─> OpenAI API                │
│           ├─> NewsAPI, Finnhub, etc.    │
│           └─> Discord Webhook           │
│                                         │
│  ┌───────────────────────────────┐     │
│  │   Monitoring & Logs            │     │
│  │   (CloudWatch / local logs)    │     │
│  └───────────────────────────────┘     │
└─────────────────────────────────────────┘
```

---

## 💰 Cost Breakdown

| Component | Cost/Month | Notes |
|-----------|-----------|-------|
| EC2 t3.small (24/7) | $15.18 | 2 vCPU, 2GB RAM |
| EC2 t3.medium (24/7) | $30.37 | 2 vCPU, 4GB RAM (recommended) |
| EBS Storage (20GB) | $2.00 | SSD storage |
| Data Transfer | $0-5 | Usually free tier |
| **Total** | **~$17-35/month** | Depends on instance type |

**Cheaper Alternative:** t3.micro ($7.60/month) - May struggle with ML features

---

## 📝 Prerequisites

Before you start, you need:
- ✅ AWS Account (create at aws.amazon.com)
- ✅ Credit card on file (for AWS billing)
- ✅ OpenAI API key
- ✅ Discord webhook URL
- ✅ Basic terminal knowledge

---

## 🚀 Step-by-Step Deployment

### Phase 1: AWS Setup (15 minutes)

#### 1.1 Create EC2 Instance

1. **Log into AWS Console**: https://console.aws.amazon.com
2. **Go to EC2**: Services → EC2
3. **Click "Launch Instance"**

#### 1.2 Configure Instance

**Name:** `stock-market-scanner`

**Application and OS Images:**
- **AMI:** Ubuntu Server 22.04 LTS (Free tier eligible)
- **Architecture:** 64-bit (x86)

**Instance Type:**
- **Recommended:** t3.medium (2 vCPU, 4 GB RAM)
- **Budget:** t3.small (2 vCPU, 2 GB RAM)
- ⚠️ Don't use t3.micro - too small for AI analysis

**Key Pair:**
- Click "Create new key pair"
- **Name:** `stock-scanner-key`
- **Type:** RSA
- **Format:** .pem (for Mac/Linux) or .ppk (for Windows/PuTTY)
- **Download and save** - you can't download it again!

**Network Settings:**
- ✅ Allow SSH traffic from: My IP (safer) or Anywhere (less safe)
- ✅ Auto-assign public IP: Enable

**Storage:**
- **Size:** 20 GB (minimum, 30 GB recommended)
- **Type:** gp3 (faster, cheaper than gp2)

**Advanced Details:**
- Leave default

**Click "Launch Instance"** 🚀

#### 1.3 Wait for Instance to Start

- Status should show "Running" (takes 1-2 minutes)
- Note down your **Public IPv4 address** (e.g., 54.123.45.67)

---

### Phase 2: Connect to Your EC2 Instance (5 minutes)

#### Option A: Mac/Linux

```bash
# Move your key to .ssh folder
mv ~/Downloads/stock-scanner-key.pem ~/.ssh/

# Set correct permissions
chmod 400 ~/.ssh/stock-scanner-key.pem

# Connect to EC2
ssh -i ~/.ssh/stock-scanner-key.pem ubuntu@YOUR_EC2_PUBLIC_IP

# Example:
# ssh -i ~/.ssh/stock-scanner-key.pem ubuntu@54.123.45.67
```

#### Option B: Windows (using PuTTY)

1. Convert .pem to .ppk using PuTTYgen
2. Open PuTTY
3. Host: `ubuntu@YOUR_EC2_PUBLIC_IP`
4. Auth → Private key: Select your .ppk file
5. Click Open

You should now be connected to your EC2 instance! 🎉

---

### Phase 3: Install Dependencies on EC2 (10 minutes)

**Copy and paste these commands one by one:**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install system dependencies
sudo apt install -y git curl wget build-essential

# Create project directory
mkdir -p ~/stock-scanner
cd ~/stock-scanner
```

---

### Phase 4: Upload Your Project to EC2 (10 minutes)

#### Option A: Using SCP (From Your Mac)

**Open a NEW terminal on your Mac** (don't close the EC2 connection):

```bash
# Navigate to your project
cd "/Users/pradeepsomasundaram/Documents/AI Stock Market/stock/ai-stock-agent"

# Copy entire project to EC2
scp -i ~/.ssh/stock-scanner-key.pem -r \
  ./{agents,app,backtesting,enhancements,graph,ml,notifications,portfolio,rag,scheduler,tools,prompts,data,*.py,*.txt,.env} \
  ubuntu@YOUR_EC2_PUBLIC_IP:~/stock-scanner/

# Example:
# scp -i ~/.ssh/stock-scanner-key.pem -r ./* ubuntu@54.123.45.67:~/stock-scanner/
```

#### Option B: Using Git (If you have a GitHub repo)

**On EC2:**
```bash
cd ~/stock-scanner
git clone YOUR_GITHUB_REPO_URL .
```

#### Option C: Manual Upload (Smaller files)

Use FileZilla or Cyberduck to drag and drop files.

---

### Phase 5: Setup Python Environment on EC2 (5 minutes)

**On EC2 terminal:**

```bash
cd ~/stock-scanner

# Create virtual environment
python3.11 -m venv venv

# Activate it
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# This will take 5-10 minutes
```

---

### Phase 6: Configure Environment Variables (5 minutes)

**On EC2:**

```bash
cd ~/stock-scanner

# Edit .env file
nano .env

# Make sure these are set:
# OPENAI_API_KEY=sk-...
# DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
# DISCORD_ENABLED=true
# LLM_MODEL=gpt-4o-mini
# (All your other API keys)

# Save: Ctrl+X, Y, Enter
```

**Test that everything works:**

```bash
source venv/bin/activate
python ultimate_market_scanner.py --test-discord
```

You should see a Discord notification! 🎉

---

### Phase 7: Create Systemd Service (Auto-Start) (10 minutes)

This makes the scanner run automatically and restart if it crashes.

**Create service file:**

```bash
sudo nano /etc/systemd/system/stock-scanner.service
```

**Paste this content:**

```ini
[Unit]
Description=Ultimate Stock Market Scanner
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/stock-scanner
Environment="PATH=/home/ubuntu/stock-scanner/venv/bin"
ExecStart=/home/ubuntu/stock-scanner/venv/bin/python /home/ubuntu/stock-scanner/ultimate_market_scanner.py --monitor
Restart=always
RestartSec=10
StandardOutput=append:/home/ubuntu/stock-scanner/logs/scanner.log
StandardError=append:/home/ubuntu/stock-scanner/logs/scanner.error.log

[Install]
WantedBy=multi-user.target
```

**Save:** Ctrl+X, Y, Enter

**Create logs directory:**

```bash
mkdir -p ~/stock-scanner/logs
```

**Enable and start service:**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable stock-scanner

# Start service now
sudo systemctl start stock-scanner

# Check status
sudo systemctl status stock-scanner
```

You should see "Active (running)" in green! 🟢

---

### Phase 8: Verify Everything Works (5 minutes)

**Check logs:**

```bash
# Watch live logs
tail -f ~/stock-scanner/logs/scanner.log

# Check for errors
tail -f ~/stock-scanner/logs/scanner.error.log

# View service status
sudo systemctl status stock-scanner

# See what's running
ps aux | grep python
```

**You should see:**
- Service status: Active (running)
- Logs showing scanner initialization
- Discord test messages appearing

**Manual test scan:**

```bash
cd ~/stock-scanner
source venv/bin/activate
python ultimate_market_scanner.py --scan-now --quick
```

---

## 🎛 Managing Your Scanner

### Start/Stop/Restart

```bash
# Stop scanner
sudo systemctl stop stock-scanner

# Start scanner
sudo systemctl start stock-scanner

# Restart scanner
sudo systemctl restart stock-scanner

# Check status
sudo systemctl status stock-scanner

# Disable auto-start
sudo systemctl disable stock-scanner
```

### View Logs

```bash
# Live logs
tail -f ~/stock-scanner/logs/scanner.log

# Last 100 lines
tail -n 100 ~/stock-scanner/logs/scanner.log

# Search logs
grep "ERROR" ~/stock-scanner/logs/scanner.error.log

# View all logs
less ~/stock-scanner/logs/scanner.log
```

### Update Code

```bash
# Stop scanner
sudo systemctl stop stock-scanner

# Update code (if using git)
cd ~/stock-scanner
git pull

# Or upload new files via SCP from your Mac

# Restart scanner
sudo systemctl start stock-scanner
```

---

## 📊 Monitoring

### Set up CloudWatch (Optional)

AWS can automatically monitor your EC2:

1. Go to EC2 Console → Your Instance
2. Monitoring tab → Manage detailed monitoring
3. Enable detailed monitoring
4. Set up alarms for CPU, memory, disk

### Local Monitoring

```bash
# Check disk space
df -h

# Check memory
free -h

# Check CPU
top

# Check what's using resources
htop  # (install with: sudo apt install htop)

# Check network
sudo netstat -tulpn | grep python
```

---

## 🔒 Security Best Practices

### 1. Secure Your Instance

```bash
# Update security group (in AWS Console)
# EC2 → Security Groups → Your instance's SG
# Edit inbound rules:
# - SSH: Only from your IP (not 0.0.0.0/0)
# - Delete any unnecessary rules
```

### 2. Set up Firewall

```bash
sudo ufw allow 22/tcp
sudo ufw enable
sudo ufw status
```

### 3. Regular Updates

```bash
# Create update script
nano ~/update.sh

# Paste:
#!/bin/bash
sudo apt update
sudo apt upgrade -y
sudo systemctl restart stock-scanner

# Make executable
chmod +x ~/update.sh

# Run weekly
crontab -e
# Add:
0 2 * * 0 /home/ubuntu/update.sh
```

### 4. Backup Important Data

```bash
# Backup .env file
cp ~/.env ~/.env.backup

# Backup database
cp ~/stock-scanner/data/*.db ~/backups/
```

---

## 💡 Optimization Tips

### Reduce Costs

1. **Use Spot Instances** (70% cheaper, but can be interrupted)
2. **Schedule EC2** to run only during market hours (9 AM - 4 PM ET)
3. **Use t3.small** instead of t3.medium if performance is acceptable
4. **Use Reserved Instances** for 1-year commitment (40% discount)

### Improve Performance

1. **Increase instance size** to t3.medium or t3.large
2. **Add swap space** for memory-intensive operations
3. **Use gp3 EBS** instead of gp2 (faster, cheaper)
4. **Cache frequently accessed data**

### Save on API Costs

1. **Use gpt-4o-mini** instead of gpt-4o (90% cheaper)
2. **Reduce scan frequency** (every 2 hours instead of hourly)
3. **Scan fewer stocks** (top 50 instead of 100)
4. **Cache news for 30 minutes** to avoid re-fetching

---

## 🆘 Troubleshooting

### Service Won't Start

```bash
# Check status
sudo systemctl status stock-scanner

# Check logs
journalctl -u stock-scanner -n 100

# Manually run to see errors
cd ~/stock-scanner
source venv/bin/activate
python ultimate_market_scanner.py --monitor
```

### Out of Memory

```bash
# Add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Can't Connect to EC2

```bash
# Check security group allows SSH from your IP
# Check instance is running
# Check you're using correct key file
# Check key permissions: chmod 400 key.pem
```

### Dependencies Failed

```bash
# Install build tools
sudo apt install -y build-essential python3-dev

# Reinstall dependencies
pip install --upgrade --force-reinstall -r requirements.txt
```

---

## 📋 Maintenance Checklist

### Daily
- ✅ Check Discord for alerts
- ✅ Verify scanner is running: `sudo systemctl status stock-scanner`

### Weekly
- ✅ Review logs for errors
- ✅ Check disk space: `df -h`
- ✅ Monitor AWS costs in billing dashboard

### Monthly
- ✅ Update system: `sudo apt update && sudo apt upgrade`
- ✅ Review and optimize stock list
- ✅ Check API usage and costs
- ✅ Backup important data

---

## 🎉 You're Done!

Your Ultimate Stock Market Scanner is now:
- ✅ Running 24/7 on AWS
- ✅ Sending hourly Discord alerts
- ✅ Auto-restarting if it crashes
- ✅ Fully automated

**Next Steps:**
1. Check your Discord channel for hourly alerts
2. Monitor the first few scans to ensure quality
3. Adjust stock list or scan frequency as needed
4. Enjoy automated market intelligence! 📈

---

## 📞 Quick Reference Commands

```bash
# Connect to EC2
ssh -i ~/.ssh/stock-scanner-key.pem ubuntu@YOUR_IP

# Check scanner status
sudo systemctl status stock-scanner

# View live logs
tail -f ~/stock-scanner/logs/scanner.log

# Restart scanner
sudo systemctl restart stock-scanner

# Manual scan
cd ~/stock-scanner && source venv/bin/activate
python ultimate_market_scanner.py --scan-now --quick

# Update code and restart
sudo systemctl stop stock-scanner
cd ~/stock-scanner && git pull
sudo systemctl start stock-scanner
```

Happy automated trading! 🚀📈
