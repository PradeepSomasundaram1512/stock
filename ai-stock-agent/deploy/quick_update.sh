#!/bin/bash
#
# Quick Update Script - Run this on your Mac to update EC2
# Usage: ./deploy/quick_update.sh YOUR_EC2_IP
#

if [ -z "$1" ]; then
    echo "Error: EC2 IP address required"
    echo "Usage: ./deploy/quick_update.sh YOUR_EC2_IP"
    exit 1
fi

EC2_IP="$1"
KEY_FILE="$HOME/.ssh/stock.pem"

echo "========================================="
echo "Quick Update to EC2"
echo "========================================="
echo ""

# Upload project files
echo "Uploading files..."
./deploy/upload_to_ec2.sh "$EC2_IP"

echo ""
echo "Restarting scanner..."
ssh -i "$KEY_FILE" ubuntu@"$EC2_IP" "sudo systemctl restart stock-scanner"

echo ""
echo "Checking status..."
ssh -i "$KEY_FILE" ubuntu@"$EC2_IP" "sudo systemctl status stock-scanner --no-pager | head -20"

echo ""
echo "✓ Update complete!"
echo ""
echo "View logs:"
echo "  ssh -i $KEY_FILE ubuntu@$EC2_IP"
echo "  tail -f ~/stock-scanner/logs/scanner.log"
echo ""
