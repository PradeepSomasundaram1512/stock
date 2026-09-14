#!/bin/bash
#
# EC2 Setup Script - Run this on your EC2 instance after first connection
# This script will:
#   - Install all dependencies
#   - Set up Python environment
#   - Configure systemd service
#   - Start the market scanner
#
# Usage:
#   chmod +x setup_ec2.sh
#   ./setup_ec2.sh
#

set -e  # Exit on error

echo "========================================="
echo "AI Stock Market Scanner - EC2 Setup"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running on Ubuntu
if [ ! -f /etc/lsb-release ]; then
    echo -e "${RED}Error: This script is designed for Ubuntu${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1:${NC} Updating system packages..."
sudo apt update
sudo apt upgrade -y

echo -e "${GREEN}✓${NC} System updated"
echo ""

echo -e "${YELLOW}Step 2:${NC} Installing Python and dependencies..."
sudo apt install -y \
    python3 \
    python3-venv \
    python3-pip \
    git \
    curl \
    wget \
    build-essential \
    htop

echo -e "${GREEN}✓${NC} Python and tools installed"
echo ""

echo -e "${YELLOW}Step 3:${NC} Creating project directory..."
PROJECT_DIR="$HOME/stock-scanner"
mkdir -p "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/backups"

cd "$PROJECT_DIR"
echo -e "${GREEN}✓${NC} Project directory created: $PROJECT_DIR"
echo ""

echo -e "${YELLOW}Step 4:${NC} Creating Python virtual environment..."
python3 -m venv venv

echo -e "${GREEN}✓${NC} Virtual environment created"
echo ""

echo -e "${YELLOW}Step 5:${NC} Activating virtual environment..."
source venv/bin/activate

echo -e "${YELLOW}Step 6:${NC} Upgrading pip..."
pip install --upgrade pip

echo -e "${GREEN}✓${NC} Pip upgraded"
echo ""

# Check if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}Step 7:${NC} Installing Python dependencies..."
    echo "This may take 5-10 minutes..."
    pip install -r requirements.txt
    echo -e "${GREEN}✓${NC} Dependencies installed"
else
    echo -e "${YELLOW}⚠ requirements.txt not found${NC}"
    echo "Please upload your project files first, then run this script again."
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 8:${NC} Creating systemd service..."

sudo tee /etc/systemd/system/stock-scanner.service > /dev/null <<EOF
[Unit]
Description=Ultimate Stock Market Scanner
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/ultimate_market_scanner.py --monitor
Restart=always
RestartSec=10
StandardOutput=append:$PROJECT_DIR/logs/scanner.log
StandardError=append:$PROJECT_DIR/logs/scanner.error.log

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓${NC} Systemd service created"
echo ""

echo -e "${YELLOW}Step 9:${NC} Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable stock-scanner
sudo systemctl start stock-scanner

echo -e "${GREEN}✓${NC} Service started"
echo ""

echo -e "${YELLOW}Step 10:${NC} Setting up firewall..."
sudo ufw allow 22/tcp
sudo ufw --force enable

echo -e "${GREEN}✓${NC} Firewall configured"
echo ""

echo -e "${YELLOW}Step 11:${NC} Creating management scripts..."

# Create update script
cat > "$PROJECT_DIR/update.sh" <<'EOF'
#!/bin/bash
cd ~/stock-scanner
sudo systemctl stop stock-scanner
git pull || echo "No git repository"
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl start stock-scanner
echo "✓ Scanner updated and restarted"
EOF

# Create backup script
cat > "$PROJECT_DIR/backup.sh" <<'EOF'
#!/bin/bash
BACKUP_DIR=~/stock-scanner/backups
DATE=$(date +%Y%m%d_%H%M%S)
cp ~/.env "$BACKUP_DIR/.env_$DATE"
cp ~/stock-scanner/data/*.db "$BACKUP_DIR/" 2>/dev/null || true
echo "✓ Backup created: $DATE"
EOF

chmod +x "$PROJECT_DIR/update.sh"
chmod +x "$PROJECT_DIR/backup.sh"

echo -e "${GREEN}✓${NC} Management scripts created"
echo ""

echo "========================================="
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo "========================================="
echo ""
echo "Your stock market scanner is now running!"
echo ""
echo "Useful commands:"
echo "  Check status:    sudo systemctl status stock-scanner"
echo "  View logs:       tail -f ~/stock-scanner/logs/scanner.log"
echo "  Restart:         sudo systemctl restart stock-scanner"
echo "  Stop:            sudo systemctl stop stock-scanner"
echo "  Update code:     ~/stock-scanner/update.sh"
echo "  Backup data:     ~/stock-scanner/backup.sh"
echo ""
echo "Check your Discord channel for alerts!"
echo ""
