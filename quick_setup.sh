#!/bin/bash
# Quick setup script for local development and testing
# This sets up the entire Agente Portero system for local testing

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Agente Portero - Quick Setup for Local Testing        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Start Docker services
echo -e "${YELLOW}📦 Step 1: Starting Docker services (PostgreSQL + Redis)${NC}"
docker-compose up -d postgres redis
echo -e "${GREEN}✅ Docker services started${NC}"
echo ""

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}⏳ Waiting for PostgreSQL to be ready...${NC}"
sleep 5
echo -e "${GREEN}✅ PostgreSQL should be ready${NC}"
echo ""

# Step 2: Check if backend venv exists
echo -e "${YELLOW}🐍 Step 2: Setting up Backend environment${NC}"
if [ ! -d "services/backend/venv" ]; then
    echo "   Creating virtual environment for backend..."
    cd services/backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ../..
    echo -e "${GREEN}✅ Backend environment created${NC}"
else
    echo -e "${GREEN}✅ Backend environment exists${NC}"
fi
echo ""

# Step 3: Seed database
echo -e "${YELLOW}🌱 Step 3: Seeding database with test data${NC}"
cd services/backend
source venv/bin/activate
python seed_data.py --clear
cd ../..
echo -e "${GREEN}✅ Database seeded${NC}"
echo ""

# Step 4: Check if WhatsApp Service venv exists
echo -e "${YELLOW}🐍 Step 4: Setting up WhatsApp Service environment${NC}"
if [ ! -d "services/whatsapp-service/venv" ]; then
    echo "   Creating virtual environment for WhatsApp Service..."
    cd services/whatsapp-service
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ../..
    echo -e "${GREEN}✅ WhatsApp Service environment created${NC}"
else
    echo -e "${GREEN}✅ WhatsApp Service environment exists${NC}"
fi
echo ""

# Step 5: Check .env files
echo -e "${YELLOW}⚙️  Step 5: Checking .env files${NC}"
if [ ! -f "services/backend/.env" ]; then
    echo -e "${YELLOW}⚠️  Backend .env not found - creating from example${NC}"
    cp services/backend/.env.example services/backend/.env
    echo -e "${RED}   ⚠️  IMPORTANT: Edit services/backend/.env with your credentials${NC}"
fi

if [ ! -f "services/whatsapp-service/.env" ]; then
    echo -e "${YELLOW}⚠️  WhatsApp Service .env not found - creating from example${NC}"
    cp services/whatsapp-service/.env.example services/whatsapp-service/.env
    echo -e "${RED}   ⚠️  IMPORTANT: Edit services/whatsapp-service/.env with your credentials${NC}"
fi
echo -e "${GREEN}✅ .env files checked${NC}"
echo ""

# Summary
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              ✅ Setup Complete!                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}📊 Database seeded with:${NC}"
echo "   • 1 Condominium: Residencial del Valle"
echo "   • 3 Residents with WhatsApp numbers:"
echo "     - Juan Pérez García (5218112345678) - Unit A-101"
echo "     - María Rodríguez López (5218198765432) - Unit A-205"
echo "     - Carlos Martínez Hernández (5218155551234) - Unit B-103"
echo "   • 2 Vehicles (with plates)"
echo "   • 1 AI Agent"
echo "   • Sample visitors and reports"
echo ""

echo -e "${YELLOW}🚀 Next steps:${NC}"
echo ""
echo -e "${BLUE}1. Start Backend Service:${NC}"
echo "   cd services/backend"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
echo -e "${BLUE}2. Start WhatsApp Service (in new terminal):${NC}"
echo "   cd services/whatsapp-service"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
echo -e "${BLUE}3. Run tests (in new terminal):${NC}"
echo "   ./test_all.sh"
echo ""
echo -e "${BLUE}4. (Optional) Start Evolution API:${NC}"
echo "   docker-compose up -d evolution-api"
echo "   Open: http://localhost:8080"
echo "   Create instance: agente_portero"
echo "   Scan QR code with WhatsApp Business"
echo ""
echo -e "${YELLOW}📖 Documentation:${NC}"
echo "   • SETUP.md - Complete setup guide"
echo "   • TESTING.md - Testing guide"
echo "   • API_ENDPOINTS.md - API documentation"
echo ""
echo -e "${GREEN}Happy coding! 🎉${NC}"
