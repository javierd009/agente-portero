#!/bin/bash

# =============================================================================
# Script de Configuración de Evolution API
# Ejecutar DESPUÉS de verificar que los servicios están corriendo
# =============================================================================

set -e

# Variables
EVOLUTION_URL="https://evolution-portero.integratec-ia.com"
API_KEY="b7e8f9a0c1d2e3f4g5h6i7j8k9l0m1n2"
INSTANCE_NAME="agente_portero"
WEBHOOK_URL="https://whatsapp-portero.integratec-ia.com/webhook"

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "Configuración de Evolution API"
echo "=========================================="
echo ""

# Paso 1: Verificar que Evolution API está accesible
echo "1. Verificando Evolution API..."
if curl -s --max-time 5 "$EVOLUTION_URL" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Evolution API accesible${NC}"
else
    echo -e "${RED}✗ Evolution API no responde${NC}"
    echo "Verifica que el servicio esté corriendo en Portainer"
    exit 1
fi
echo ""

# Paso 2: Crear instancia
echo "2. Creando instancia de WhatsApp: $INSTANCE_NAME"
response=$(curl -s -X POST "$EVOLUTION_URL/instance/create" \
  -H "apikey: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"instanceName\": \"$INSTANCE_NAME\",
    \"qrcode\": true,
    \"integration\": \"WHATSAPP-BAILEYS\"
  }")

if echo "$response" | grep -q "error"; then
    echo -e "${YELLOW}⚠ Posible error (puede que la instancia ya exista):${NC}"
    echo "$response" | jq '.' 2>/dev/null || echo "$response"
else
    echo -e "${GREEN}✓ Instancia creada/verificada${NC}"
fi
echo ""

# Paso 3: Obtener QR Code
echo "3. Obteniendo QR Code para vincular WhatsApp..."
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}ESCANEA ESTE QR CODE CON WHATSAPP BUSINESS:${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

qr_response=$(curl -s "$EVOLUTION_URL/instance/connect/$INSTANCE_NAME" \
  -H "apikey: $API_KEY")

# Intentar mostrar el QR en la terminal
if command -v qrencode &> /dev/null; then
    echo "$qr_response" | jq -r '.qrcode.code' 2>/dev/null | qrencode -t UTF8
else
    echo "$qr_response" | jq '.' 2>/dev/null || echo "$qr_response"
fi

echo ""
echo -e "${YELLOW}INSTRUCCIONES:${NC}"
echo "1. Abre WhatsApp Business en tu teléfono"
echo "2. Ve a: Configuración → Dispositivos vinculados"
echo "3. Toca: Vincular un dispositivo"
echo "4. Escanea el QR code mostrado arriba"
echo ""
echo "Si no puedes ver el QR en la terminal, accede a:"
echo -e "${BLUE}$EVOLUTION_URL/instance/connect/$INSTANCE_NAME${NC}"
echo ""

# Esperar confirmación del usuario
echo -n "Presiona ENTER cuando hayas escaneado el QR code... "
read

# Paso 4: Verificar conexión
echo ""
echo "4. Verificando conexión de WhatsApp..."
status_response=$(curl -s "$EVOLUTION_URL/instance/connectionState/$INSTANCE_NAME" \
  -H "apikey: $API_KEY")

if echo "$status_response" | grep -q "open"; then
    echo -e "${GREEN}✓ WhatsApp conectado exitosamente${NC}"
else
    echo -e "${YELLOW}⚠ Estado: ${NC}"
    echo "$status_response" | jq '.' 2>/dev/null || echo "$status_response"
fi
echo ""

# Paso 5: Configurar Webhook
echo "5. Configurando webhook para eventos de WhatsApp..."
webhook_response=$(curl -s -X POST "$EVOLUTION_URL/webhook/set/$INSTANCE_NAME" \
  -H "apikey: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"$WEBHOOK_URL\",
    \"webhook_by_events\": true,
    \"webhook_base64\": true,
    \"events\": [
      \"MESSAGES_UPSERT\",
      \"MESSAGES_UPDATE\",
      \"SEND_MESSAGE\",
      \"CONNECTION_UPDATE\"
    ]
  }")

if echo "$webhook_response" | grep -q "error"; then
    echo -e "${RED}✗ Error configurando webhook:${NC}"
    echo "$webhook_response" | jq '.' 2>/dev/null || echo "$webhook_response"
else
    echo -e "${GREEN}✓ Webhook configurado${NC}"
    echo "  URL: $WEBHOOK_URL"
fi
echo ""

# Paso 6: Test de envío de mensaje
echo "6. ¿Quieres enviar un mensaje de prueba? (s/n)"
read -r send_test

if [ "$send_test" = "s" ] || [ "$send_test" = "S" ]; then
    echo "Ingresa el número de destino (formato: 521234567890):"
    read -r phone_number

    test_response=$(curl -s -X POST "$EVOLUTION_URL/message/sendText/$INSTANCE_NAME" \
      -H "apikey: $API_KEY" \
      -H "Content-Type: application/json" \
      -d "{
        \"number\": \"$phone_number\",
        \"text\": \"🤖 Hola! Soy el Agente Portero, tu guardia virtual. Este es un mensaje de prueba.\",
        \"delay\": 0
      }")

    if echo "$test_response" | grep -q "key"; then
        echo -e "${GREEN}✓ Mensaje enviado${NC}"
    else
        echo -e "${RED}✗ Error enviando mensaje:${NC}"
        echo "$test_response" | jq '.' 2>/dev/null || echo "$test_response"
    fi
fi
echo ""

# Resumen
echo "=========================================="
echo "Configuración Completada"
echo "=========================================="
echo ""
echo "Estado de la configuración:"
echo "  ✅ Instancia: $INSTANCE_NAME"
echo "  ✅ Webhook: $WEBHOOK_URL"
echo ""
echo "Para verificar el estado en cualquier momento:"
echo "  curl $EVOLUTION_URL/instance/connectionState/$INSTANCE_NAME -H 'apikey: $API_KEY'"
echo ""
echo "Panel de Evolution API:"
echo "  $EVOLUTION_URL"
echo ""
