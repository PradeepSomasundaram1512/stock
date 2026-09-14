#!/bin/bash
#
# Monitor Script for EC2
# Run this on EC2 to check system health and scanner status
#

echo "========================================="
echo "Stock Market Scanner - System Monitor"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Service status
echo -e "${YELLOW}Service Status:${NC}"
sudo systemctl status stock-scanner --no-pager | head -n 10
echo ""

# Disk usage
echo -e "${YELLOW}Disk Usage:${NC}"
df -h / | grep -v Filesystem
echo ""

# Memory usage
echo -e "${YELLOW}Memory Usage:${NC}"
free -h | grep -E "Mem|Swap"
echo ""

# CPU load
echo -e "${YELLOW}CPU Load:${NC}"
uptime
echo ""

# Recent logs
echo -e "${YELLOW}Recent Log Entries (last 10):${NC}"
tail -n 10 ~/stock-scanner/logs/scanner.log
echo ""

# Recent errors
ERROR_COUNT=$(grep -c "ERROR" ~/stock-scanner/logs/scanner.error.log 2>/dev/null || echo "0")
if [ "$ERROR_COUNT" -gt 0 ]; then
    echo -e "${RED}⚠ Found $ERROR_COUNT errors${NC}"
    echo "Last 5 errors:"
    tail -n 5 ~/stock-scanner/logs/scanner.error.log
else
    echo -e "${GREEN}✓ No recent errors${NC}"
fi
echo ""

# Network connectivity
echo -e "${YELLOW}Network Test:${NC}"
if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Internet connection OK${NC}"
else
    echo -e "${RED}✗ No internet connection${NC}"
fi
echo ""

# API connectivity
echo -e "${YELLOW}API Tests:${NC}"
if curl -s https://api.openai.com > /dev/null 2>&1; then
    echo -e "${GREEN}✓ OpenAI API reachable${NC}"
else
    echo -e "${RED}✗ OpenAI API unreachable${NC}"
fi
echo ""

# Process check
echo -e "${YELLOW}Scanner Process:${NC}"
if ps aux | grep -v grep | grep "ultimate_market_scanner" > /dev/null; then
    echo -e "${GREEN}✓ Scanner is running${NC}"
    ps aux | grep -v grep | grep "ultimate_market_scanner" | awk '{print "  PID: "$2", CPU: "$3"%, MEM: "$4"%"}'
else
    echo -e "${RED}✗ Scanner is not running${NC}"
fi
echo ""

echo "========================================="
echo "Quick Commands:"
echo "  Restart scanner:  sudo systemctl restart stock-scanner"
echo "  View full logs:   tail -f ~/stock-scanner/logs/scanner.log"
echo "  Check errors:     tail -f ~/stock-scanner/logs/scanner.error.log"
echo "========================================="
