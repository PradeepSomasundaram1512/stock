#!/bin/bash
#
# Upload Project to EC2
# Run this script from your Mac to upload the entire project to EC2
#
# Usage:
#   ./upload_to_ec2.sh YOUR_EC2_IP_ADDRESS
#
# Example:
#   ./upload_to_ec2.sh 54.123.45.67
#

if [ -z "$1" ]; then
    echo "Error: EC2 IP address required"
    echo "Usage: ./upload_to_ec2.sh YOUR_EC2_IP_ADDRESS"
    echo "Example: ./upload_to_ec2.sh 54.123.45.67"
    exit 1
fi

EC2_IP="$1"
KEY_FILE="$HOME/.ssh/stock.pem"
REMOTE_USER="ubuntu"
REMOTE_DIR="/home/ubuntu/stock-scanner"

echo "========================================="
echo "Uploading AI Stock Scanner to EC2"
echo "========================================="
echo "EC2 IP: $EC2_IP"
echo "Key: $KEY_FILE"
echo ""

# Check if key file exists
if [ ! -f "$KEY_FILE" ]; then
    echo "Error: Key file not found at $KEY_FILE"
    echo "Please update KEY_FILE variable in this script"
    exit 1
fi

# Check key permissions
chmod 400 "$KEY_FILE"

echo "Creating remote directory..."
ssh -i "$KEY_FILE" "$REMOTE_USER@$EC2_IP" "mkdir -p $REMOTE_DIR"

echo ""
echo "Uploading project files..."
echo "This may take a few minutes..."
echo ""

# Upload all necessary files and directories
scp -i "$KEY_FILE" -r \
    agents \
    app \
    backtesting \
    data \
    enhancements \
    graph \
    ml \
    notifications \
    portfolio \
    prompts \
    rag \
    scheduler \
    tools \
    *.py \
    requirements.txt \
    .env \
    "$REMOTE_USER@$EC2_IP:$REMOTE_DIR/"

echo ""
echo "Uploading deployment scripts..."
scp -i "$KEY_FILE" deploy/setup_ec2.sh "$REMOTE_USER@$EC2_IP:$REMOTE_DIR/"

echo ""
echo "✓ Upload complete!"
echo ""
echo "Next steps:"
echo "1. Connect to EC2:"
echo "   ssh -i $KEY_FILE $REMOTE_USER@$EC2_IP"
echo ""
echo "2. Run setup script:"
echo "   cd ~/stock-scanner"
echo "   chmod +x setup_ec2.sh"
echo "   ./setup_ec2.sh"
echo ""
echo "3. Monitor logs:"
echo "   tail -f ~/stock-scanner/logs/scanner.log"
echo ""
