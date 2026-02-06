#!/bin/bash

# =============================================================================
# Test FASE 2: Portainer/Contabo Deployment
# Verifica que todos los servicios estén funcionando correctamente
# =============================================================================

set -e  # Exit on error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables
CONTABO_IP="${1:-localhost}"  # Pasar IP de Contabo como argumento, default localhost para testing local
BACKEND_URL="http://${CONTABO_IP}:8000"
WHATSAPP_URL="http://${CONTABO_IP}:8002"
VOICE_URL="http://${CONTABO_IP}:8001"
EVOLUTION_URL="http://${CONTABO_IP}:8080"
REDIS_PORT="6379"

# Counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_test() {
    echo -e "${YELLOW}[TEST $TESTS_TOTAL] $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ PASS: $1${NC}"
    ((TESTS_PASSED++))
}

print_fail() {
    echo -e "${RED}❌ FAIL: $1${NC}"
    echo -e "${RED}   Error: $2${NC}"
    ((TESTS_FAILED++))
}

print_warning() {
    echo -e "${YELLOW}⚠️  WARNING: $1${NC}"
}

test_service() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}

    ((TESTS_TOTAL++))
    print_test "Testing $name health check at $url"

    if response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>&1); then
        if [ "$response" = "$expected_status" ]; then
            print_success "$name is healthy (HTTP $response)"
            return 0
        else
            print_fail "$name returned unexpected status" "Expected $expected_status, got $response"
            return 1
        fi
    else
        print_fail "$name is not accessible" "$response"
        return 1
    fi
}

test_docker_container() {
    local container_name=$1

    ((TESTS_TOTAL++))
    print_test "Checking if Docker container '$container_name' is running"

    if docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
        local status=$(docker inspect -f '{{.State.Status}}' "$container_name")
        if [ "$status" = "running" ]; then
            print_success "Container '$container_name' is running"
            return 0
        else
            print_fail "Container '$container_name' exists but is not running" "Status: $status"
            return 1
        fi
    else
        print_fail "Container '$container_name' not found" "Check docker-compose deployment"
        return 1
    fi
}

# =============================================================================
# TEST SUITE
# =============================================================================

print_header "FASE 2 DEPLOYMENT TESTS"

echo -e "\n${BLUE}Target Server: ${CONTABO_IP}${NC}"
echo -e "${BLUE}Started at: $(date)${NC}\n"

# -----------------------------------------------------------------------------
# Test 1: Docker Containers Running
# -----------------------------------------------------------------------------

print_header "1. DOCKER CONTAINERS"

if command -v docker &> /dev/null; then
    test_docker_container "agente-portero-backend"
    test_docker_container "agente-portero-whatsapp"
    test_docker_container "agente-portero-voice"
    test_docker_container "agente-portero-evolution"
    test_docker_container "agente-portero-redis"
else
    print_warning "Docker not found on local machine. Skipping container checks."
    print_warning "Run this script on Contabo server to check containers."
fi

# -----------------------------------------------------------------------------
# Test 2: Service Health Checks
# -----------------------------------------------------------------------------

print_header "2. SERVICE HEALTH CHECKS"

test_service "Backend API" "$BACKEND_URL/health"
test_service "WhatsApp Service" "$WHATSAPP_URL/health"

# Voice service may fail if Asterisk is not configured
((TESTS_TOTAL++))
print_test "Testing Voice Service health check (may fail without Asterisk)"
if response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$VOICE_URL/health" 2>&1); then
    print_success "Voice Service is accessible (HTTP $response)"
else
    print_warning "Voice Service not accessible (expected if Asterisk not configured)"
fi

test_service "Evolution API" "$EVOLUTION_URL" 200

# -----------------------------------------------------------------------------
# Test 3: Backend API Endpoints
# -----------------------------------------------------------------------------

print_header "3. BACKEND API ENDPOINTS"

# Test health endpoint with details
((TESTS_TOTAL++))
print_test "Testing Backend API health endpoint with JSON response"
if response=$(curl -s --max-time 5 "$BACKEND_URL/health"); then
    if echo "$response" | grep -q "status"; then
        print_success "Backend API health returns valid JSON"
        echo "   Response: $response"
    else
        print_fail "Backend API health invalid response" "$response"
    fi
else
    print_fail "Backend API health failed" "No response"
fi

# Test OpenAPI docs
((TESTS_TOTAL++))
print_test "Testing Backend API OpenAPI docs"
if response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$BACKEND_URL/docs" 2>&1); then
    if [ "$response" = "200" ]; then
        print_success "OpenAPI docs accessible"
    else
        print_fail "OpenAPI docs not accessible" "HTTP $response"
    fi
else
    print_fail "OpenAPI docs failed" "$response"
fi

# Test critical endpoints (without authentication for now)
((TESTS_TOTAL++))
print_test "Testing Backend /api/v1/residents endpoint"
if response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$BACKEND_URL/api/v1/residents/by-phone/5218112345678" 2>&1); then
    if [ "$response" = "200" ] || [ "$response" = "404" ] || [ "$response" = "422" ]; then
        print_success "Residents endpoint is responsive (HTTP $response)"
    else
        print_fail "Residents endpoint error" "HTTP $response"
    fi
else
    print_fail "Residents endpoint failed" "$response"
fi

# -----------------------------------------------------------------------------
# Test 4: Redis Connection
# -----------------------------------------------------------------------------

print_header "4. REDIS CONNECTION"

if command -v redis-cli &> /dev/null; then
    ((TESTS_TOTAL++))
    print_test "Testing Redis connection"
    if redis-cli -h "$CONTABO_IP" -p "$REDIS_PORT" ping > /dev/null 2>&1; then
        print_success "Redis is accessible and responding"
    else
        print_warning "Redis requires password or not accessible"
        print_warning "This is expected if REDIS_PASSWORD is set"
    fi
else
    print_warning "redis-cli not installed. Skipping Redis tests."
fi

# -----------------------------------------------------------------------------
# Test 5: Evolution API Status
# -----------------------------------------------------------------------------

print_header "5. EVOLUTION API"

((TESTS_TOTAL++))
print_test "Testing Evolution API Manager UI"
if response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$EVOLUTION_URL" 2>&1); then
    if [ "$response" = "200" ]; then
        print_success "Evolution API Manager is accessible"
        echo "   🔗 Access at: $EVOLUTION_URL"
    else
        print_fail "Evolution API Manager not accessible" "HTTP $response"
    fi
else
    print_fail "Evolution API Manager failed" "$response"
fi

# Test Evolution API instance endpoint
((TESTS_TOTAL++))
print_test "Testing Evolution API instance endpoint"
if response=$(curl -s --max-time 5 "$EVOLUTION_URL/instance/fetchInstances" 2>&1); then
    if echo "$response" | grep -q "agente_portero" || echo "$response" | grep -q "\[\]"; then
        print_success "Evolution API instances endpoint responsive"
    else
        print_warning "Evolution API instances endpoint returned unexpected response"
        echo "   Response preview: ${response:0:100}"
    fi
else
    print_warning "Evolution API instances endpoint not accessible"
fi

# -----------------------------------------------------------------------------
# Test 6: Environment Variables (if .env.production exists)
# -----------------------------------------------------------------------------

print_header "6. ENVIRONMENT CONFIGURATION"

if [ -f ".env.production" ]; then
    ((TESTS_TOTAL++))
    print_test "Checking .env.production file"

    # Check critical env vars are set (not empty)
    critical_vars=("DATABASE_URL" "SUPABASE_URL" "SUPABASE_SERVICE_KEY" "OPENAI_API_KEY" "JWT_SECRET")
    all_present=true

    for var in "${critical_vars[@]}"; do
        if grep -q "^${var}=" .env.production && ! grep -q "^${var}=$" .env.production; then
            echo "   ✅ $var is set"
        else
            echo "   ❌ $var is missing or empty"
            all_present=false
        fi
    done

    if [ "$all_present" = true ]; then
        print_success "All critical environment variables are configured"
    else
        print_fail "Some environment variables are missing" "Check .env.production"
    fi

    # Check if default values are still present (security issue)
    ((TESTS_TOTAL++))
    print_test "Checking for default/insecure values"
    insecure=false

    if grep -q "B6D711FCDE4D4FD5936544120E713976" .env.production; then
        print_warning "EVOLUTION_API_KEY still has default value - CHANGE IT!"
        insecure=true
    fi

    if grep -q "tu-password-redis-seguro" .env.production; then
        print_warning "REDIS_PASSWORD still has default value - CHANGE IT!"
        insecure=true
    fi

    if grep -q "cambiar-en-produccion" .env.production; then
        print_warning "Some passwords still have placeholder values - CHANGE THEM!"
        insecure=true
    fi

    if [ "$insecure" = false ]; then
        print_success "No default/insecure values detected"
    else
        print_fail "Security issue: Default values detected" "Update .env.production with secure values"
    fi
else
    print_warning ".env.production not found in current directory"
    print_warning "Run this script from project root or on Contabo server"
fi

# -----------------------------------------------------------------------------
# Test 7: Network Connectivity
# -----------------------------------------------------------------------------

print_header "7. NETWORK CONNECTIVITY"

((TESTS_TOTAL++))
print_test "Testing Supabase connectivity"
if grep -q "SUPABASE_URL" .env.production 2>/dev/null; then
    SUPABASE_URL=$(grep "^SUPABASE_URL=" .env.production | cut -d'=' -f2)
    if response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$SUPABASE_URL/rest/v1/" 2>&1); then
        print_success "Supabase is reachable from this machine"
    else
        print_fail "Cannot reach Supabase" "Check internet connection and SUPABASE_URL"
    fi
else
    print_warning "SUPABASE_URL not configured, skipping connectivity test"
fi

# -----------------------------------------------------------------------------
# Test 8: Docker Logs Check
# -----------------------------------------------------------------------------

print_header "8. DOCKER LOGS INSPECTION"

if command -v docker &> /dev/null; then
    containers=("agente-portero-backend" "agente-portero-whatsapp" "agente-portero-evolution")

    for container in "${containers[@]}"; do
        ((TESTS_TOTAL++))
        print_test "Checking logs for errors in '$container'"

        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            # Get last 50 lines of logs
            logs=$(docker logs "$container" --tail 50 2>&1)

            # Check for common error patterns
            if echo "$logs" | grep -qi "error\|exception\|failed\|critical"; then
                print_warning "Found potential errors in $container logs"
                echo "   Run 'docker logs $container' to investigate"
            else
                print_success "No obvious errors in $container logs"
            fi
        else
            print_warning "Container $container not running, skipping log check"
        fi
    done
else
    print_warning "Docker not available, skipping log checks"
fi

# =============================================================================
# RESULTS SUMMARY
# =============================================================================

print_header "TEST RESULTS SUMMARY"

echo -e "\n${BLUE}Total Tests:${NC} $TESTS_TOTAL"
echo -e "${GREEN}Passed:${NC} $TESTS_PASSED"
echo -e "${RED}Failed:${NC} $TESTS_FAILED"

PASS_RATE=$((TESTS_PASSED * 100 / TESTS_TOTAL))
echo -e "${BLUE}Pass Rate:${NC} ${PASS_RATE}%"

echo -e "\n${BLUE}Finished at: $(date)${NC}\n"

# Exit code based on results
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
    echo -e "${GREEN}FASE 2 deployment appears to be successful.${NC}\n"
    exit 0
elif [ $TESTS_FAILED -le 2 ]; then
    echo -e "${YELLOW}⚠️  SOME TESTS FAILED${NC}"
    echo -e "${YELLOW}Review failed tests above. Minor issues may be acceptable.${NC}\n"
    exit 1
else
    echo -e "${RED}❌ MULTIPLE TESTS FAILED${NC}"
    echo -e "${RED}FASE 2 deployment has issues that need to be addressed.${NC}\n"
    exit 2
fi
