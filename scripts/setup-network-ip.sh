#!/bin/bash

# Setup Network IP for Mobile Testing
# This script configures the frontend to use your network IP for backend

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔧 Network IP Setup for Mobile Testing${NC}"
echo ""

# Detect OS and get IP
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    LOCAL_IP=$(hostname -I | awk '{print $1}')
else
    # Windows (Git Bash)
    LOCAL_IP=$(ipconfig | grep "IPv4" | head -1 | awk '{print $NF}')
fi

if [ -z "$LOCAL_IP" ]; then
    echo -e "${RED}❌ Could not detect local IP address${NC}"
    echo -e "${YELLOW}Please find your IP manually:${NC}"
    echo "  macOS/Linux: ifconfig"
    echo "  Windows: ipconfig"
    exit 1
fi

echo -e "${GREEN}✅ Detected IP: ${LOCAL_IP}${NC}"
echo ""

# Create .env.local
ENV_FILE="frontend/.env.local"

echo -e "${BLUE}Creating ${ENV_FILE}...${NC}"

cat > "$ENV_FILE" << EOF
# Auto-generated network IP configuration
# Created: $(date)

# Backend URLs using network IP
NEXT_PUBLIC_API_URL=http://${LOCAL_IP}:8000
NEXT_PUBLIC_WS_URL=ws://${LOCAL_IP}:8000

# This allows your phone to access the backend on the same network
EOF

echo -e "${GREEN}✅ Configuration created!${NC}"
echo ""
echo -e "${BLUE}📋 Configuration:${NC}"
echo "  API URL: http://${LOCAL_IP}:8000"
echo "  WS URL:  ws://${LOCAL_IP}:8000"
echo ""
echo -e "${YELLOW}📱 Next Steps:${NC}"
echo "  1. Start backend:  ${BLUE}make backend${NC}"
echo "  2. Start frontend: ${BLUE}make frontend${NC}"
echo "  3. On your phone, open: ${GREEN}http://${LOCAL_IP}:3000/mobile${NC}"
echo ""
echo -e "${YELLOW}💡 Make sure your phone is on the same WiFi network!${NC}"

