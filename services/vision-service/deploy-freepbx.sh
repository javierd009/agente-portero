#!/bin/bash
# Vision Service - FreePBX Deployment Script
# Run on FreePBX server (172.20.20.1)

set -e

echo "=== Agente Portero - Vision Service Deployment ==="

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp .env.freepbx .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env with your camera details:"
    echo "   nano .env"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Installing..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Installing..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

echo "Pulling latest image..."
docker-compose -f docker-compose.freepbx.yml pull

echo "Starting vision-service..."
docker-compose -f docker-compose.freepbx.yml up -d

echo ""
echo "✅ Vision Service deployed!"
echo ""
echo "Check status:  docker-compose -f docker-compose.freepbx.yml ps"
echo "View logs:     docker-compose -f docker-compose.freepbx.yml logs -f"
echo "Health check:  curl http://localhost:8001/health"
echo ""
