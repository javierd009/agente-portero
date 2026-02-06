#!/bin/bash
# Complete testing script for Agente Portero
# Runs all tests in sequence: Evolution API → Backend API → WhatsApp Flow

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        Agente Portero - Complete Test Suite               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if services are running
check_service() {
    local url=$1
    local name=$2

    if curl -s "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $name is running${NC}"
        return 0
    else
        echo -e "${RED}❌ $name is NOT running${NC}"
        return 1
    fi
}

echo -e "${YELLOW}📋 Step 0: Pre-flight checks${NC}"
echo ""

# Check Backend
if ! check_service "http://localhost:8000/health" "Backend API"; then
    echo -e "${YELLOW}💡 Start backend: cd services/backend && python main.py${NC}"
    exit 1
fi

# Check WhatsApp Service
if ! check_service "http://localhost:8002/health" "WhatsApp Service"; then
    echo -e "${YELLOW}💡 Start WhatsApp Service: cd services/whatsapp-service && python main.py${NC}"
    exit 1
fi

# Check Evolution API (optional)
if check_service "http://localhost:8080" "Evolution API"; then
    EVOLUTION_AVAILABLE=true
else
    echo -e "${YELLOW}⚠️  Evolution API not running (optional for webhook tests)${NC}"
    EVOLUTION_AVAILABLE=false
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Test 1: Evolution API (if available)
if [ "$EVOLUTION_AVAILABLE" = true ]; then
    echo -e "${YELLOW}📋 Step 1: Testing Evolution API${NC}"
    echo ""
    cd services/whatsapp-service
    python test_evolution_api.py
    cd ../..
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
else
    echo -e "${YELLOW}⏭️  Skipping Evolution API test (not running)${NC}"
    echo ""
fi

# Test 2: Backend API
echo -e "${YELLOW}📋 Step 2: Testing Backend API${NC}"
echo ""
cd services/backend
python test_backend_api.py
cd ../..
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Test 3: WhatsApp Flow
echo -e "${YELLOW}📋 Step 3: Testing WhatsApp Service Flow${NC}"
echo ""
cd services/whatsapp-service
python test_whatsapp_flow.py
cd ../..
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Summary
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✅ All Tests Completed!                       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}📊 Test Summary:${NC}"
echo "   ✅ Backend API endpoints working"
echo "   ✅ WhatsApp Service webhook processing working"
echo "   ✅ Intent parsing (GPT-4) working"
echo "   ✅ Backend integration working"
if [ "$EVOLUTION_AVAILABLE" = true ]; then
    echo "   ✅ Evolution API connectivity working"
fi
echo ""
echo -e "${YELLOW}🚀 Next Steps:${NC}"
echo "   1. Configure Evolution API webhook:"
echo "      URL: http://YOUR_NGROK_URL/webhook"
echo "   2. Test with real WhatsApp messages"
echo "   3. Monitor logs in real-time:"
echo "      - Backend: services/backend/main.py"
echo "      - WhatsApp: services/whatsapp-service/main.py"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
