#!/bin/bash

# =============================================================================
# Script de Verificación Post-Deployment
# Ejecutar después de que los servicios estén corriendo en Portainer
# =============================================================================

set -e

echo "=========================================="
echo "Verificación de Deployment - Agente Portero"
echo "=========================================="
echo ""

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para verificar endpoint
check_endpoint() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}

    echo -n "Verificando $name... "

    # Intentar curl con timeout de 10 segundos
    if response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null); then
        if [ "$response" -eq "$expected_code" ] || [ "$response" -eq 200 ] || [ "$response" -eq 404 ]; then
            echo -e "${GREEN}✓ OK${NC} (HTTP $response)"
            return 0
        else
            echo -e "${RED}✗ FAIL${NC} (HTTP $response)"
            return 1
        fi
    else
        echo -e "${RED}✗ TIMEOUT/ERROR${NC}"
        return 1
    fi
}

# Verificar conectividad al servidor
echo "1. Verificando conectividad al servidor..."
if ping -c 1 147.93.147.12 &> /dev/null; then
    echo -e "${GREEN}✓ Servidor accesible${NC}"
else
    echo -e "${RED}✗ Servidor no responde${NC}"
    exit 1
fi
echo ""

# Verificar DNS
echo "2. Verificando resolución DNS..."
for domain in api-portero whatsapp-portero voice-portero evolution-portero; do
    echo -n "  $domain.integratec-ia.com... "
    if host "$domain.integratec-ia.com" &> /dev/null; then
        echo -e "${GREEN}✓ Resuelve${NC}"
    else
        echo -e "${YELLOW}⚠ No resuelve (puede tardar en propagar)${NC}"
    fi
done
echo ""

# Verificar servicios HTTP/HTTPS
echo "3. Verificando servicios (HTTP)..."
check_endpoint "Backend API" "http://147.93.147.12:8000/health" || true
check_endpoint "WhatsApp Service" "http://147.93.147.12:8002/health" || true
check_endpoint "Voice Service" "http://147.93.147.12:8001/health" || true
check_endpoint "Evolution API" "http://147.93.147.12:8080" || true
echo ""

# Verificar servicios HTTPS (con dominios)
echo "4. Verificando servicios con SSL (HTTPS)..."
echo "   (Espera 2-3 minutos si los DNS acaban de propagarse)"
check_endpoint "Backend API (SSL)" "https://api-portero.integratec-ia.com/health" || true
check_endpoint "WhatsApp Service (SSL)" "https://whatsapp-portero.integratec-ia.com/health" || true
check_endpoint "Voice Service (SSL)" "https://voice-portero.integratec-ia.com/health" || true
check_endpoint "Evolution API (SSL)" "https://evolution-portero.integratec-ia.com" || true
echo ""

# Test de base de datos (desde backend)
echo "5. Verificando conexión a base de datos..."
echo "   (Esto requiere que el backend esté funcionando)"
if response=$(curl -s "https://api-portero.integratec-ia.com/health" 2>/dev/null); then
    if echo "$response" | grep -q "database"; then
        echo -e "${GREEN}✓ Backend responde con info de DB${NC}"
    else
        echo -e "${YELLOW}⚠ Backend responde pero sin info de DB${NC}"
    fi
else
    echo -e "${RED}✗ No se puede verificar${NC}"
fi
echo ""

# Resumen
echo "=========================================="
echo "Verificación Completada"
echo "=========================================="
echo ""
echo "Próximos pasos:"
echo "1. ✅ Si todos los servicios están en verde, continuar con configuración de Evolution API"
echo "2. ⚠️  Si hay servicios en amarillo, revisar logs en Portainer"
echo "3. ❌ Si hay errores en rojo, verificar configuración y variables de entorno"
echo ""
echo "Para ver logs en Portainer:"
echo "  Stacks → agente-portero → Click en servicio → Logs"
echo ""
