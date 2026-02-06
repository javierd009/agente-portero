#!/bin/bash
# Vision Service - FreePBX Deployment Script
# Run on FreePBX server (172.20.20.1)
#
# DEPLOYMENT STEPS:
# 1. SSH to FreePBX: ssh root@172.20.20.1
# 2. Clone repo: git clone https://github.com/YOUR_USER/agente_portero.git
# 3. cd agente_portero/services/vision-service
# 4. ./deploy-freepbx.sh
#
# After deployment:
# 1. Configure NAT on Mikrotik to expose port 8001
# 2. Add VISION_SERVICE_URL to backend .env in Portainer

set -e

echo "=== Agente Portero - Vision Service Deployment ==="
echo ""
echo "Camera: 172.20.22.111 (Hikvision)"
echo "Backend: https://api-portero.integratec-ia.com"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp .env.freepbx .env
    echo ""
    echo "Default configuration:"
    echo "  HIKVISION_HOST=172.20.22.111"
    echo "  HIKVISION_PORT=80"
    echo "  HIKVISION_USER=admin"
    echo "  HIKVISION_PASSWORD=integratec20"
    echo ""
    echo "Edit .env if you need to change these values."
    echo ""
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "Docker installed"
fi

# Check Docker Compose (v1 or v2)
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    echo "Docker Compose not found. Installing..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    COMPOSE_CMD="docker-compose"
    echo "Docker Compose installed"
fi

# Try to pull image first, fallback to build if not available
echo ""
echo "Attempting to pull image from registry..."
if $COMPOSE_CMD -f docker-compose.freepbx.yml pull 2>/dev/null; then
    echo "Image pulled successfully"
else
    echo "Image not found in registry. Building locally..."
    $COMPOSE_CMD -f docker-compose.freepbx.yml build
    echo "Image built locally"
fi

echo ""
echo "Starting vision-service..."
$COMPOSE_CMD -f docker-compose.freepbx.yml up -d

# Wait for service to start
echo ""
echo "Waiting for service to start..."
sleep 10

# Health check
if curl -s http://localhost:8001/health | grep -q "healthy"; then
    echo "Vision Service is healthy!"
else
    echo "Service may still be starting. Check logs:"
    echo "   $COMPOSE_CMD -f docker-compose.freepbx.yml logs -f"
fi

echo ""
echo "=========================================="
echo "DEPLOYMENT COMPLETE"
echo "=========================================="
echo ""
echo "Service URL: http://172.20.20.1:8001"
echo ""
echo "Useful commands:"
echo "  Check status:  $COMPOSE_CMD -f docker-compose.freepbx.yml ps"
echo "  View logs:     $COMPOSE_CMD -f docker-compose.freepbx.yml logs -f"
echo "  Restart:       $COMPOSE_CMD -f docker-compose.freepbx.yml restart"
echo "  Stop:          $COMPOSE_CMD -f docker-compose.freepbx.yml down"
echo ""
echo "Test endpoints:"
echo "  Health:        curl http://localhost:8001/health"
echo "  Test camera:   curl -X POST http://localhost:8001/cameras/test"
echo "  List cameras:  curl http://localhost:8001/cameras"
echo ""
echo "=========================================="
echo "NEXT STEPS:"
echo "=========================================="
echo ""
echo "1. Configure NAT on Mikrotik router:"
echo "   - External port: 8001"
echo "   - Internal IP: 172.20.20.1"
echo "   - Internal port: 8001"
echo "   - Protocol: TCP"
echo ""
echo "2. Add to backend .env in Portainer:"
echo "   VISION_SERVICE_URL=http://integrateccr.ddns.net:8001"
echo ""
echo "3. Redeploy backend stack in Portainer"
echo ""
