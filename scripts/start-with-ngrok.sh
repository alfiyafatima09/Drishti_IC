#!/bin/bash

# Start Both Frontend and Backend with Ngrok
# This solves the mixed content (HTTPS/HTTP) issue

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Backend and Frontend with Ngrok${NC}"
echo ""

# Check if ngrok is installed
if ! command -v ngrok >/dev/null 2>&1; then
    echo -e "${RED}❌ ngrok not found!${NC}"
    echo -e "${YELLOW}Install ngrok:${NC}"
    echo "  macOS: ${BLUE}brew install ngrok/ngrok/ngrok${NC}"
    echo "  Or download: ${BLUE}https://ngrok.com/download${NC}"
    exit 1
fi

# Check if user has ngrok auth
echo -e "${YELLOW}⚠️  Note: This requires ngrok account with 2 tunnel support${NC}"
echo -e "${YELLOW}   Free account = 1 tunnel only${NC}"
echo -e "${YELLOW}   Paid account = multiple tunnels${NC}"
echo ""
read -p "Continue? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Cancelled. Use 'make setup-network-ip' instead for free alternative.${NC}"
    exit 0
fi

# Kill existing processes
echo -e "${BLUE}🧹 Cleaning up existing processes...${NC}"
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "npm.*dev" 2>/dev/null || true
pkill -f "ngrok" 2>/dev/null || true
sleep 2

# Start backend
echo -e "${GREEN}1️⃣ Starting backend...${NC}"
cd backend
python main.py > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
cd ..
sleep 3

# Start backend ngrok
echo -e "${GREEN}2️⃣ Starting backend ngrok tunnel...${NC}"
ngrok http 8000 --log=stdout > /tmp/ngrok-backend.log 2>&1 &
NGROK_BACKEND_PID=$!
sleep 5

# Get backend ngrok URL
BACKEND_NGROK_URL=""
for i in {1..10}; do
    BACKEND_NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['tunnels'][0]['public_url'] if data.get('tunnels') else '')" 2>/dev/null)
    if [ -n "$BACKEND_NGROK_URL" ]; then
        break
    fi
    sleep 1
done

if [ -z "$BACKEND_NGROK_URL" ]; then
    echo -e "${RED}❌ Failed to get backend ngrok URL${NC}"
    echo -e "${YELLOW}Check if you have ngrok account with 2 tunnels${NC}"
    kill $BACKEND_PID $NGROK_BACKEND_PID 2>/dev/null
    exit 1
fi

# Convert to WSS for WebSocket
BACKEND_WS_URL=$(echo "$BACKEND_NGROK_URL" | sed 's|https://|wss://|')

echo -e "${GREEN}✅ Backend URL: ${BACKEND_NGROK_URL}${NC}"

# Create .env.local for frontend
echo -e "${GREEN}3️⃣ Configuring frontend...${NC}"
cat > frontend/.env.local << EOF
# Auto-generated ngrok configuration
# Created: $(date)

# Backend ngrok URLs (HTTPS and WSS)
NEXT_PUBLIC_API_URL=${BACKEND_NGROK_URL}
NEXT_PUBLIC_WS_URL=${BACKEND_WS_URL}
EOF

# Start frontend
echo -e "${GREEN}4️⃣ Starting frontend...${NC}"
cd frontend
npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
sleep 5

# Start frontend ngrok
echo -e "${GREEN}5️⃣ Starting frontend ngrok tunnel...${NC}"
# Use different port for ngrok API (4041)
ngrok http 3000 --log=stdout --web-addr=localhost:4041 > /tmp/ngrok-frontend.log 2>&1 &
NGROK_FRONTEND_PID=$!
sleep 5

# Get frontend ngrok URL
FRONTEND_NGROK_URL=""
for i in {1..10}; do
    FRONTEND_NGROK_URL=$(curl -s http://localhost:4041/api/tunnels 2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['tunnels'][0]['public_url'] if data.get('tunnels') else '')" 2>/dev/null)
    if [ -n "$FRONTEND_NGROK_URL" ]; then
        break
    fi
    sleep 1
done

if [ -z "$FRONTEND_NGROK_URL" ]; then
    echo -e "${RED}❌ Failed to get frontend ngrok URL${NC}"
    echo -e "${YELLOW}You might have reached ngrok tunnel limit${NC}"
    kill $BACKEND_PID $NGROK_BACKEND_PID $FRONTEND_PID $NGROK_FRONTEND_PID 2>/dev/null
    exit 1
fi

# Add skip warning parameter
FRONTEND_NGROK_URL_SKIP="${FRONTEND_NGROK_URL}?ngrok-skip-browser-warning=1"

# Display results
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅ Both Services Running on Ngrok (HTTPS)${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}📱 Use this URL on your phone:${NC}"
echo -e "  ${GREEN}${FRONTEND_NGROK_URL_SKIP}/mobile${NC}"
echo ""
echo -e "${BLUE}🔧 Backend URL:${NC}"
echo -e "  ${GREEN}${BACKEND_NGROK_URL}${NC}"
echo ""
echo -e "${BLUE}📊 Ngrok Dashboards:${NC}"
echo -e "  Backend:  ${BLUE}http://localhost:4040${NC}"
echo -e "  Frontend: ${BLUE}http://localhost:4041${NC}"
echo ""
echo -e "${YELLOW}💡 Both frontend and backend on HTTPS now!${NC}"
echo -e "${YELLOW}   Camera will work properly on mobile${NC}"
echo -e "${YELLOW}   No mixed content errors${NC}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services...${NC}"

# Keep script running
trap "echo ''; echo 'Stopping services...'; kill $BACKEND_PID $NGROK_BACKEND_PID $FRONTEND_PID $NGROK_FRONTEND_PID 2>/dev/null; exit 0" INT

wait

