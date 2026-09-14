#!/bin/bash
# Deploy fixes to EC2 - Fresh prices + More stocks

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        🚀 Deploying Stock Scanner Fixes to EC2 🚀          ║${NC}"
echo -e "${GREEN}╠════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Fix 1: Fresh prices (15-min cache TTL)                   ║${NC}"
echo -e "${GREEN}║  Fix 2: Scan ALL ~493 S&P 500 stocks (not just 110)      ║${NC}"
echo -e "${GREEN}║  Fix 3: Faster scanning (0.2s delay, ~4-5 min per scan)   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Get EC2 IP from user
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage: $0 <EC2_IP> [SSH_KEY_PATH]${NC}"
    echo ""
    echo "Example:"
    echo "  $0 3.238.127.158"
    echo "  $0 100.28.131.76 ~/.ssh/my-key.pem"
    echo ""
    exit 1
fi

EC2_IP="$1"
SSH_KEY="${2:-~/.ssh/id_rsa}"
EC2_USER="ubuntu"
REMOTE_PATH="~/stock-scanner"

echo -e "${YELLOW}🔧 Configuration:${NC}"
echo "  EC2 IP: $EC2_IP"
echo "  SSH Key: $SSH_KEY"
echo "  User: $EC2_USER"
echo "  Remote Path: $REMOTE_PATH"
echo ""

# Test SSH connection
echo -e "${YELLOW}🔌 Testing SSH connection...${NC}"
if ! ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$EC2_USER@$EC2_IP" "echo 'Connected'" 2>/dev/null; then
    echo -e "${RED}❌ Cannot connect to EC2!${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo "1. Check Security Group - Allow SSH (port 22) from your IP"
    echo "2. Verify EC2 IP: $EC2_IP"
    echo "3. Check SSH key: $SSH_KEY"
    echo ""
    echo "To update Security Group:"
    echo "  AWS Console → EC2 → Security Groups → Edit Inbound Rules"
    echo "  Add rule: SSH (22) from your IP or 0.0.0.0/0"
    exit 1
fi
echo -e "${GREEN}✓ SSH connection successful${NC}"
echo ""

# Upload fixed files
echo -e "${YELLOW}📤 Uploading fixed files...${NC}"

FILES=(
    "agents/data_agent.py"
    "agents/autonomous_reasoning_agent.py"
    "graph/autonomous_decision_graph.py"
    "ultimate_market_scanner.py"
    "swing_trader.py"
)

for file in "${FILES[@]}"; do
    echo "  → $file"
    scp -i "$SSH_KEY" -o StrictHostKeyChecking=no "$file" "$EC2_USER@$EC2_IP:$REMOTE_PATH/$file"
done

echo -e "${GREEN}✓ Files uploaded${NC}"
echo ""

# Restart scanner service
echo -e "${YELLOW}🔄 Restarting stock scanner service...${NC}"
ssh -i "$SSH_KEY" "$EC2_USER@$EC2_IP" << 'ENDSSH'
sudo systemctl restart stock-scanner
sleep 2
sudo systemctl status stock-scanner --no-pager
ENDSSH

echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo -e "${YELLOW}📊 What to expect in Discord:${NC}"
echo "  ✓ Fresh, real-time stock prices (15-min cache TTL)"
echo "  ✓ ALL ~493 S&P 500 stocks scanned per run"
echo "  ✓ Only stocks ≤\$50 shown as Discord recommendations"
echo ""
echo -e "${YELLOW}🔍 Check logs:${NC}"
echo "  ssh -i $SSH_KEY $EC2_USER@$EC2_IP 'sudo journalctl -u stock-scanner -f'"
echo ""
echo -e "${YELLOW}Look for these log messages:${NC}"
echo "  • 'Universe: 493 stocks'"
echo "  • 'Pre-screen: X/493 stocks returned valid data'"
echo "  • 'Step 2/2: Deep LLM analysis on X stocks'"
echo "  • Discord footer: 'Scanned 493 stocks in Xs'"
echo ""
