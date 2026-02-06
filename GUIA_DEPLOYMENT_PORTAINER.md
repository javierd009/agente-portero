# Guía de Deployment en Portainer - Agente Portero

## Paso 1: Preparación en Portainer

### 1.1 Acceder a Portainer
- URL: Tu servidor Contabo con Portainer
- Navega a: **Stacks** → **Add stack**

### 1.2 Configuración del Stack
- **Name:** `agente-portero`
- **Build method:** Seleccionar **Repository**

### 1.3 Configurar Repository
```
Repository URL: https://github.com/javierd009/agente-portero
Repository reference: refs/heads/main
Compose path: docker-compose.portainer-build.yml
```

⚠️ **IMPORTANTE:** Usar `docker-compose.portainer-build.yml` para el primer deploy (construye las imágenes localmente).

## Paso 2: Variables de Entorno

Copiar y pegar las siguientes variables en la sección **Environment variables**:

```env
DATABASE_URL=postgresql://postgres:QaWiHpNHNCGZVAsu@db.datrxcbcvlfhjivncddr.supabase.co:6543/postgres
SUPABASE_URL=https://datrxcbcvlfhjivncddr.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRhdHJ4Y2JjdmxmaGppdm5jZGRyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Nzc1NDg1OSwiZXhwIjoyMDgzMzMwODU5fQ.3Cv-feIrtonkpBjR3PGAr5Z4sYJ9MDIAAKO0XWmtYYM
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRhdHJ4Y2JjdmxmaGppdm5jZGRyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc3NTQ4NTksImV4cCI6MjA4MzMzMDg1OX0.S_1WaOZC_jL9h5DCiWKwUN4w0tweKLOgNvV5tYVm-NQ
OPENAI_API_KEY=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
EVOLUTION_API_URL=http://evolution-api:8080
EVOLUTION_API_KEY=b7e8f9a0c1d2e3f4g5h6i7j8k9l0m1n2
EVOLUTION_INSTANCE=agente_portero
ASTERISK_ARI_URL=http://asterisk:8088/ari
ASTERISK_ARI_USER=asterisk
ASTERISK_ARI_PASSWORD=changeme
JWT_SECRET=e52a4bf16cb37061f6427e6493b42acb31c4fc64944121767d9398edecd5c28c
```

## Paso 3: Deploy

1. Click en **Deploy the stack**
2. Portainer clonará el repositorio y construirá las imágenes
3. Este proceso puede tardar 5-10 minutos (es la primera vez)

## Paso 4: Verificar Servicios

Una vez completado el deploy, verificar que los siguientes servicios estén corriendo:

### Servicios Esperados:
- ✅ `agente-portero_backend` (Puerto 8000)
- ✅ `agente-portero_whatsapp-service` (Puerto 8002)
- ✅ `agente-portero_voice-service` (Puerto 8001)
- ✅ `agente-portero_evolution-api` (Puerto 8080)

### Dominios Traefik (verificar en Traefik dashboard):
- https://api-portero.integratec-ia.com (Backend API)
- https://whatsapp-portero.integratec-ia.com (WhatsApp Service)
- https://voice-portero.integratec-ia.com (Voice Service)
- https://evolution-portero.integratec-ia.com (Evolution API)

## Paso 5: Configurar Evolution API

### 5.1 Crear Instancia de WhatsApp
```bash
curl -X POST https://evolution-portero.integratec-ia.com/instance/create \
  -H "apikey: b7e8f9a0c1d2e3f4g5h6i7j8k9l0m1n2" \
  -H "Content-Type: application/json" \
  -d '{
    "instanceName": "agente_portero",
    "qrcode": true
  }'
```

### 5.2 Obtener QR Code
```bash
curl https://evolution-portero.integratec-ia.com/instance/connect/agente_portero \
  -H "apikey: b7e8f9a0c1d2e3f4g5h6i7j8k9l0m1n2"
```

### 5.3 Escanear QR
- Abrir WhatsApp Business en el teléfono
- Configuración → Dispositivos vinculados
- Escanear el QR code mostrado

### 5.4 Configurar Webhook
```bash
curl -X POST https://evolution-portero.integratec-ia.com/webhook/set/agente_portero \
  -H "apikey: b7e8f9a0c1d2e3f4g5h6i7j8k9l0m1n2" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://whatsapp-portero.integratec-ia.com/webhook",
    "webhook_by_events": true,
    "events": [
      "MESSAGES_UPSERT",
      "MESSAGES_UPDATE",
      "SEND_MESSAGE"
    ]
  }'
```

## Paso 6: Tests de Verificación

### 6.1 Health Check Backend
```bash
curl https://api-portero.integratec-ia.com/health
```

**Respuesta esperada:**
```json
{
  "status": "healthy",
  "service": "agente-portero-backend",
  "database": "connected",
  "redis": "connected"
}
```

### 6.2 Health Check WhatsApp Service
```bash
curl https://whatsapp-portero.integratec-ia.com/health
```

### 6.3 Health Check Voice Service
```bash
curl https://voice-portero.integratec-ia.com/health
```

## Paso 7: Verificar Logs

En Portainer, verificar logs de cada servicio:

1. Navegar a **Stacks** → `agente-portero`
2. Click en cada servicio
3. Ver logs para confirmar que no hay errores

**Logs esperados en backend:**
```
INFO: Started server process
INFO: Waiting for application startup
INFO: Application startup complete
INFO: Uvicorn running on http://0.0.0.0:8000
```

## Troubleshooting

### Error: "Network IntegratecNet not found"
- Verificar que la red `IntegratecNet` existe en Docker
- Si no existe, crearla:
```bash
docker network create --driver overlay IntegratecNet
```

### Error: "Failed to build image"
- Verificar que Portainer tiene acceso a GitHub
- Revisar los logs del build para identificar el error específico
- Verificar que los Dockerfiles están correctos

### Error: "Database connection failed"
- Verificar que las variables de entorno están correctas
- Probar conexión desde el servidor:
```bash
docker exec -it agente-portero_backend_1 python -c "from sqlalchemy import create_engine; engine = create_engine('$DATABASE_URL'); print(engine.execute('SELECT 1').scalar())"
```

## Próximos Pasos (FASE 3)

Una vez que todos los servicios estén funcionando:

1. Deploy del Dashboard en Vercel
2. Configurar variables de entorno en Vercel
3. Conectar Dashboard al Backend API
4. Configurar Asterisk/FreePBX para llamadas SIP (cuando esté disponible)

---

## Notas Importantes

- ⚠️ Este deployment usa `docker-compose.portainer-build.yml` que construye las imágenes localmente
- 🔄 Para deploys futuros, se recomienda:
  1. Agregar GitHub Actions workflow para auto-build
  2. Cambiar a `docker-compose.portainer.yml` que usa imágenes pre-construidas de ghcr.io
  3. Esto hace que los deploys sean más rápidos (solo pull, no build)

- 📝 **Redis:** El stack usa `evolution_redis` que ya existe en tu IntegratecNet
  - Si no existe, agrégalo al docker-compose o usa el Redis existente

- 🔐 **Seguridad:**
  - Las credenciales están en variables de entorno
  - JWT_SECRET es único para este proyecto
  - Cambiar EVOLUTION_API_KEY y ASTERISK_ARI_PASSWORD en producción
