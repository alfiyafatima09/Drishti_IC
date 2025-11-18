#!/bin/bash
# Development environment setup script

set -e

echo "🚀 Setting up Drishti IC Verification System..."

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running from project root
if [ ! -f "Makefile" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

# Create necessary directories
echo -e "${BLUE}Creating directories...${NC}"
mkdir -p logs cache/datasheets data/images data/processed data/logos data/fonts

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${BLUE}Creating .env file...${NC}"
    cp env.example .env
    echo -e "${YELLOW}⚠️  Please update .env with your configuration${NC}"
fi

# Check Python version
echo -e "${BLUE}Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Check Node version
echo -e "${BLUE}Checking Node version...${NC}"
node_version=$(node --version)
echo "Node version: $node_version"

# Install backend dependencies
echo -e "${BLUE}Installing backend dependencies...${NC}"
cd backend
pip3 install -r ../models/requirements.txt
cd ..

# Install frontend dependencies
echo -e "${BLUE}Installing frontend dependencies...${NC}"
cd frontend
npm install
cd ..

# Initialize database
echo -e "${BLUE}Initializing database...${NC}"
python3 -c "import sys; sys.path.insert(0, 'backend'); from models.database import init_database; init_database()"

echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Update .env with your configuration"
echo "  2. Run 'make dev' to start development servers"
echo "  3. Access:"
echo "     - Frontend: http://localhost:3000"
echo "     - Backend API: http://localhost:8000"
echo "     - API Docs: http://localhost:8000/docs"
echo ""
echo -e "${GREEN}Happy coding! 🎉${NC}"
