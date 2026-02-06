# Setup Guide - Agente Portero

Guía completa para levantar todo el stack y hacer el primer demo.

## 📋 Pre-requisitos

- Python 3.11+
- Node.js 18+
- Docker Desktop
- PostgreSQL 14+ (o usar Docker)
- Redis 7+ (o usar Docker)

---

## 🚀 Setup Rápido (Con Docker)

### 1. Clonar repositorio
```bash
cd /path/to/agente_portero
```

### 2. Levantar infraestructura (PostgreSQL + Redis)
```bash
docker-compose up -d postgres redis
```

### 3. Setup Backend
```bash
cd services/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copiar .env
cp .env.example .env
# Editar .env con tus credenciales

# Ejecutar
python main.py
# Backend corriendo en http://localhost:8000
```

### 4. Setup WhatsApp Service
```bash
cd services/whatsapp-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copiar .env
cp .env.example .env
# Editar .env con credenciales de Evolution API

# Ejecutar
python main.py
# WhatsApp Service corriendo en http://localhost:8002
```

### 5. Setup Dashboard
```bash
cd apps/dashboard
npm install

# Copiar .env.local
cp .env.example .env.local
# Editar con tu configuración

# Ejecutar
npm run dev
# Dashboard corriendo en http://localhost:3000
```

---

## 📱 Setup Evolution API (WhatsApp Business)

Evolution API es el puente entre WhatsApp y nuestro sistema.

### Opción A: Docker (Recomendado)

```bash
# 1. Crear directorio para Evolution API
mkdir evolution-api && cd evolution-api

# 2. Crear docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  evolution-api:
    image: atendai/evolution-api:latest
    container_name: evolution-api
    ports:
      - "8080:8080"
    environment:
      # Server
      - SERVER_URL=http://localhost:8080
      - CORS_ORIGIN=*
      - CORS_METHODS=POST,GET,PUT,DELETE
      - CORS_CREDENTIALS=true

      # Database (optional)
      - DATABASE_ENABLED=false

      # Authentication
      - AUTHENTICATION_API_KEY=change-me-to-a-secure-key

      # Instance settings
      - CONFIG_SESSION_PHONE_CLIENT=Agente Portero
      - CONFIG_SESSION_PHONE_NAME=Virtual Guard

    volumes:
      - ./evolution_instances:/evolution/instances
      - ./evolution_store:/evolution/store

    restart: unless-stopped

networks:
  default:
    name: agente-portero-network
EOF

# 3. Levantar Evolution API
docker-compose up -d

# 4. Verificar que esté corriendo
curl http://localhost:8080
```

### Opción B: Instalación Manual

Seguir: https://doc.evolution-api.com/v2/pt/install/docker

---

## 🔗 Configurar Instancia WhatsApp

### 1. Crear instancia

```bash
curl -X POST http://localhost:8080/instance/create \
  -H "apikey: change-me-to-a-secure-key" \
  -H "Content-Type: application/json" \
  -d '{
    "instanceName": "agente-portero",
    "qrcode": true
  }'
```

**Respuesta:**
```json
{
  "instance": {
    "instanceName": "agente-portero",
    "status": "created"
  },
  "qrcode": {
    "code": "data:image/png;base64,..."
  }
}
```

### 2. Escanear QR Code

- Abre WhatsApp en tu teléfono
- Ve a: Configuración → Dispositivos vinculados
- Escanea el QR code que apareció en la respuesta

### 3. Verificar conexión

```bash
curl http://localhost:8080/instance/connectionState/agente-portero \
  -H "apikey: change-me-to-a-secure-key"
```

**Respuesta esperada:**
```json
{
  "instance": "agente-portero",
  "state": "open"
}
```

✅ ¡WhatsApp conectado!

---

## 🔔 Configurar Webhook

El webhook permite que Evolution API notifique a nuestro WhatsApp Service cuando llega un mensaje.

### 1. Exponer WhatsApp Service públicamente

**Opción A: Ngrok (para desarrollo)**
```bash
ngrok http 8002
# Copiar URL pública: https://abc123.ngrok.io
```

**Opción B: Cloudflare Tunnel**
```bash
cloudflared tunnel --url http://localhost:8002
```

**Opción C: Deploy en servidor (producción)**
```bash
# Usar tu dominio real
https://whatsapp.agente-portero.com
```

### 2. Configurar webhook en Evolution API

```bash
WEBHOOK_URL="https://abc123.ngrok.io/webhook"  # Tu URL pública

curl -X POST http://localhost:8080/webhook/set/agente-portero \
  -H "apikey: change-me-to-a-secure-key" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"$WEBHOOK_URL\",
    \"webhook_by_events\": false,
    \"webhook_base64\": false,
    \"events\": [
      \"MESSAGES_UPSERT\",
      \"MESSAGES_UPDATE\"
    ]
  }"
```

### 3. Verificar webhook

```bash
curl http://localhost:8080/webhook/find/agente-portero \
  -H "apikey: change-me-to-a-secure-key"
```

✅ Webhook configurado!

---

## 🗄️ Setup Base de Datos

### Opción A: PostgreSQL Local

```bash
# Crear base de datos
createdb agente_portero

# Actualizar .env en backend
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agente_portero
```

### Opción B: Supabase (Recomendado para producción)

1. Ir a https://supabase.com
2. Crear nuevo proyecto
3. Copiar connection string
4. Actualizar .env:

```env
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
SUPABASE_URL=https://[PROJECT-REF].supabase.co
SUPABASE_SERVICE_KEY=eyJ...
```

### Opción C: Docker (más fácil)

```bash
docker-compose up -d postgres

# .env ya configurado para Docker
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agente_portero
```

---

## 🌱 Seed Data (Datos de Prueba)

```bash
cd services/backend
source venv/bin/activate
python seed_data.py
```

Esto crea:
- ✅ 1 Condominio: "Residencial del Valle"
- ✅ 3 Residentes con WhatsApp
- ✅ 1 Agente AI
- ✅ Algunos reportes de ejemplo

---

## 🧪 Testing del Flujo Completo

### Test 1: Backend Health Check

```bash
curl http://localhost:8000/health
# Respuesta: {"status":"healthy","service":"agente-portero-backend"}
```

### Test 2: WhatsApp Service Health Check

```bash
curl http://localhost:8002/health
# Respuesta: {"status":"healthy","service":"whatsapp-service"}
```

### Test 3: Enviar mensaje de prueba

```bash
# Obtener tu número de WhatsApp (con código de país)
# Ejemplo: 5215512345678

curl -X POST http://localhost:8002/send-message \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "5215512345678",
    "message": "🤖 Hola! Soy el Agente Portero. Puedo ayudarte con:\n\n1️⃣ Autorizar visitantes\n2️⃣ Abrir puerta\n3️⃣ Reportar incidentes\n4️⃣ Consultar logs\n\nEscribe tu solicitud!"
  }'
```

✅ Deberías recibir el mensaje en WhatsApp

### Test 4: Simular autorización de visitante

```bash
# Enviar desde tu WhatsApp al número del bot:
"Viene Juan Pérez en 10 minutos"

# El sistema debe responder:
# "✅ Visitante autorizado
# 👤 Nombre: Juan Pérez
# ⏰ Válido hasta: ..."
```

### Test 5: Verificar en Backend

```bash
# Obtener condominium_id del seed data
curl http://localhost:8000/api/v1/visitors \
  -H "x-tenant-id: [UUID-del-condominio]"

# Deberías ver el visitante autorizado
```

---

## 📊 Dashboard de Monitoreo

### Ver logs en tiempo real

**Backend:**
```bash
cd services/backend
tail -f logs/backend.log
```

**WhatsApp Service:**
```bash
cd services/whatsapp-service
tail -f logs/whatsapp.log
```

### Swagger UI

- Backend: http://localhost:8000/docs
- WhatsApp Service: http://localhost:8002/docs

---

## 🐛 Troubleshooting

### Evolution API no conecta

```bash
# Revisar logs
docker logs evolution-api

# Reiniciar instancia
curl -X DELETE http://localhost:8080/instance/logout/agente-portero \
  -H "apikey: your-key"

# Crear nueva instancia
curl -X POST http://localhost:8080/instance/create ...
```

### Webhook no recibe mensajes

```bash
# Verificar URL pública
curl https://your-ngrok-url.ngrok.io/webhook

# Ver logs del WhatsApp Service
cd services/whatsapp-service
python main.py  # Ver output en consola
```

### Backend no inicia

```bash
# Verificar DATABASE_URL
echo $DATABASE_URL

# Probar conexión a DB
psql $DATABASE_URL -c "SELECT 1"

# Ver logs detallados
cd services/backend
DEBUG=true python main.py
```

---

## 🎯 Checklist de Setup Completo

- [ ] PostgreSQL corriendo
- [ ] Redis corriendo
- [ ] Backend iniciado (puerto 8000)
- [ ] WhatsApp Service iniciado (puerto 8002)
- [ ] Dashboard iniciado (puerto 3000)
- [ ] Evolution API corriendo (puerto 8080)
- [ ] WhatsApp conectado (QR escaneado)
- [ ] Webhook configurado
- [ ] Seed data ejecutado
- [ ] Test de mensaje enviado ✅
- [ ] Test de autorización funcionando ✅

---

## 🚀 Siguiente Paso: Voice Service

Una vez que WhatsApp está funcionando, el siguiente paso es:

```bash
cd services/voice-service
# Setup Asterisk/FreePBX
# Configurar OpenAI Realtime API
# Conectar todo el flujo
```

---

## 📚 Recursos

- [Evolution API Docs](https://doc.evolution-api.com)
- [Supabase Docs](https://supabase.com/docs)
- [FastAPI Docs](https://fastapi.tiangolo.com)
- [Next.js Docs](https://nextjs.org/docs)

---

**¿Listo para el demo?** 🎉

Una vez completado este setup, tendrás:
- ✅ Sistema completo funcionando
- ✅ WhatsApp bidireccional operativo
- ✅ Backend con todos los endpoints
- ✅ Base de datos con datos de prueba
- ✅ Dashboard para visualización

**Ahorro estimado: 50% en costos de voz** 💰
