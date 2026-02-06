# Guía de Deployment en Portainer - Agente Portero

## Pre-requisitos Completados ✅

- ✅ Repositorio GitHub creado: https://github.com/javierd009/agente-portero
- ✅ GitHub Actions configurado y ejecutando
- ✅ Imágenes Docker publicadas en ghcr.io:
  - `ghcr.io/javierd009/agente-portero-backend:latest`
  - `ghcr.io/javierd009/agente-portero-whatsapp:latest`
  - `ghcr.io/javierd009/agente-portero-voice:latest`
- ✅ DNS configurados apuntando a 147.93.147.12:
  - api-portero.integratec-ia.com
  - whatsapp-portero.integratec-ia.com
  - voice-portero.integratec-ia.com
  - evolution-portero.integratec-ia.com

## Paso 1: Acceder a Portainer

1. Abre tu navegador y ve a tu instancia de Portainer
2. Inicia sesión con tus credenciales

## Paso 2: Crear el Stack

1. En el menú lateral, selecciona **Stacks**
2. Click en **+ Add stack**
3. Nombre del stack: `agente-portero`
4. Método de build: **Web editor**

## Paso 3: Pegar el Docker Compose

Copia y pega el contenido del archivo `docker-compose.portainer.yml`:

```yaml
version: '3.8'

services:
  # Backend API (FastAPI)
  backend:
    image: ghcr.io/javierd009/agente-portero-backend:latest
    environment:
      # Supabase Database
      - DATABASE_URL=${DATABASE_URL}
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}

      # JWT
      - JWT_SECRET=${JWT_SECRET}

      # Redis
      - REDIS_URL=redis://evolution_redis:6379

      # Environment
      - ENVIRONMENT=production
      - DEBUG=false
    networks:
      - IntegratecNet
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure
      labels:
        - "traefik.enable=true"
        - "traefik.http.routers.portero-api.rule=Host(`api-portero.integratec-ia.com`)"
        - "traefik.http.routers.portero-api.entrypoints=websecure"
        - "traefik.http.routers.portero-api.tls.certresolver=letsencryptresolver"
        - "traefik.http.services.portero-api.loadbalancer.server.port=8000"

  # WhatsApp Service
  whatsapp-service:
    image: ghcr.io/javierd009/agente-portero-whatsapp:latest
    environment:
      # Evolution API
      - EVOLUTION_API_URL=${EVOLUTION_API_URL}
      - EVOLUTION_API_KEY=${EVOLUTION_API_KEY}
      - EVOLUTION_INSTANCE=${EVOLUTION_INSTANCE:-agente_portero}

      # OpenAI
      - OPENAI_API_KEY=${OPENAI_API_KEY}

      # Backend
      - BACKEND_API_URL=http://backend:8000

      # Redis
      - REDIS_URL=redis://evolution_redis:6379

      # Environment
      - DEBUG=false
    networks:
      - IntegratecNet
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure
      labels:
        - "traefik.enable=true"
        - "traefik.http.routers.portero-whatsapp.rule=Host(`whatsapp-portero.integratec-ia.com`)"
        - "traefik.http.routers.portero-whatsapp.entrypoints=websecure"
        - "traefik.http.routers.portero-whatsapp.tls.certresolver=letsencryptresolver"
        - "traefik.http.services.portero-whatsapp.loadbalancer.server.port=8002"

  # Voice Service
  voice-service:
    image: ghcr.io/javierd009/agente-portero-voice:latest
    environment:
      # Asterisk ARI
      - ASTERISK_ARI_URL=${ASTERISK_ARI_URL}
      - ASTERISK_ARI_USER=${ASTERISK_ARI_USER}
      - ASTERISK_ARI_PASSWORD=${ASTERISK_ARI_PASSWORD}
      - ASTERISK_ARI_APP=agente-portero

      # OpenAI Realtime
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_REALTIME_MODEL=gpt-4o-realtime-preview-2024-12-17

      # Backend
      - BACKEND_API_URL=http://backend:8000

      # Environment
      - DEBUG=false
    networks:
      - IntegratecNet
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure
      labels:
        - "traefik.enable=true"
        - "traefik.http.routers.portero-voice.rule=Host(`voice-portero.integratec-ia.com`)"
        - "traefik.http.routers.portero-voice.entrypoints=websecure"
        - "traefik.http.routers.portero-voice.tls.certresolver=letsencryptresolver"
        - "traefik.http.services.portero-voice.loadbalancer.server.port=8001"

  # Evolution API (WhatsApp) - Si no lo tienes ya corriendo
  evolution-api:
    image: atendai/evolution-api:latest
    environment:
      - AUTHENTICATION_API_KEY=${EVOLUTION_API_KEY}
      - DATABASE_ENABLED=false
      - QRCODE_COLOR=#198754
    volumes:
      - evolution_instances:/evolution/instances
      - evolution_store:/evolution/store
    networks:
      - IntegratecNet
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure
      labels:
        - "traefik.enable=true"
        - "traefik.http.routers.portero-evolution.rule=Host(`evolution-portero.integratec-ia.com`)"
        - "traefik.http.routers.portero-evolution.entrypoints=websecure"
        - "traefik.http.routers.portero-evolution.tls.certresolver=letsencryptresolver"
        - "traefik.http.services.portero-evolution.loadbalancer.server.port=8080"

networks:
  IntegratecNet:
    external: true

volumes:
  evolution_instances:
  evolution_store:
```

## Paso 4: Agregar Variables de Entorno

En la sección **Environment variables** de Portainer, pega el contenido del archivo `.env.portainer`:

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
REDIS_PASSWORD=3ebcca147b57120eda25e39ab8a5c069ad5fdfe1a80e9f2253e0cc88ffc6446b
```

## Paso 5: Deploy del Stack

1. Verifica que todo esté correcto
2. Click en **Deploy the stack**
3. Portainer comenzará a descargar las imágenes desde ghcr.io
4. Los contenedores se iniciarán automáticamente
5. Traefik generará los certificados SSL automáticamente

## Paso 6: Verificar el Deployment

### Opción A: Desde la UI de Portainer

1. Ve a **Stacks** > **agente-portero**
2. Verifica que todos los servicios estén **running**
3. Revisa los logs de cada servicio para verificar que no haya errores

### Opción B: Ejecutar el script de verificación

```bash
bash scripts/verify-deployment.sh
```

Este script verificará:
- ✅ Servicios corriendo
- ✅ Health checks pasando
- ✅ Conectividad entre servicios
- ✅ Acceso a URLs públicas

## Paso 7: Configurar Evolution API

Una vez que el stack esté corriendo:

1. Ejecuta el script de configuración:
```bash
bash scripts/configure-evolution.sh
```

2. El script:
   - Creará la instancia de WhatsApp
   - Generará el QR code
   - Te pedirá que lo escanees con tu WhatsApp Business
   - Configurará el webhook: `https://whatsapp-portero.integratec-ia.com/webhook`

## Endpoints Disponibles

Una vez desplegado, tendrás acceso a:

- **Backend API**: https://api-portero.integratec-ia.com
  - Docs: https://api-portero.integratec-ia.com/docs
  - Health: https://api-portero.integratec-ia.com/health

- **WhatsApp Service**: https://whatsapp-portero.integratec-ia.com
  - Docs: https://whatsapp-portero.integratec-ia.com/docs
  - Health: https://whatsapp-portero.integratec-ia.com/health

- **Voice Service**: https://voice-portero.integratec-ia.com

- **Evolution API**: https://evolution-portero.integratec-ia.com
  - Manager: https://evolution-portero.integratec-ia.com/manager

## Troubleshooting

### Problema: Backend error "Network is unreachable" al conectar a Supabase

**Síntomas:** Backend falla en startup con `OSError: [Errno 101] Network is unreachable`

**Causas posibles:**
1. Los contenedores no tienen acceso a Internet
2. Falta configuración de DNS en Docker
3. Firewall bloqueando conexiones salientes

**Soluciones:**

1. **Verificar que la red tiene acceso a Internet:**
   ```bash
   # Entrar al contenedor backend
   docker exec -it <backend-container-id> sh

   # Probar conectividad
   ping -c 3 8.8.8.8
   ping -c 3 google.com

   # Probar conexión a Supabase
   nc -zv db.datrxcbcvlfhjivncddr.supabase.co 6543
   ```

2. **Verificar DNS en los contenedores:**
   ```bash
   # En el servidor, verificar DNS de Docker
   cat /etc/docker/daemon.json

   # Si no existe o falta DNS, crear/editar:
   {
     "dns": ["8.8.8.8", "8.8.4.4"]
   }

   # Reiniciar Docker
   systemctl restart docker
   ```

3. **Verificar que Supabase permite la IP del servidor:**
   - Ve a Supabase > Settings > Database
   - Verifica que no haya IP blocking
   - Confirma que "Allow connections from all IPs" está habilitado

4. **Verificar variables de entorno:**
   ```bash
   # En Portainer, verifica que DATABASE_URL está correcta
   # Debe usar puerto 6543 (Transaction Pooler), no 5432
   DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:6543/postgres
   ```

### Problema: Redis connection refused

**Solución:**
- Verifica que el servicio `evolution_redis` está corriendo
- Confirma que `REDIS_PASSWORD` está configurado en variables de entorno
- La URL debe ser: `redis://:PASSWORD@evolution_redis:6379`

### Problema: Servicios no inician

1. Verifica los logs en Portainer:
   ```
   Stacks > agente-portero > [servicio] > Logs
   ```

2. Verifica que la red `IntegratecNet` exista:
   ```bash
   docker network ls | grep IntegratecNet
   ```

### Problema: Certificados SSL no se generan

1. Verifica los logs de Traefik
2. Confirma que los DNS apuntan a 147.93.147.12
3. Verifica que el puerto 80 y 443 estén abiertos

### Problema: Imágenes no se descargan

1. Las imágenes son públicas en ghcr.io, no requieren autenticación
2. Si hay problemas de red, intenta pull manual:
   ```bash
   docker pull ghcr.io/javierd009/agente-portero-backend:latest
   ```

## Actualizaciones Futuras

Cada vez que hagas push a `main` en GitHub:

1. GitHub Actions construirá y publicará nuevas imágenes automáticamente
2. En Portainer:
   - Ve a **Stacks** > **agente-portero**
   - Click en **Pull and redeploy**
   - Portainer descargará las últimas imágenes `:latest`
   - Los contenedores se recrearán automáticamente

## Próximos Pasos

1. ✅ Deploy del stack en Portainer
2. ⏳ Verificar servicios con `verify-deployment.sh`
3. ⏳ Configurar Evolution API con `configure-evolution.sh`
4. ⏳ Configurar FreePBX para conectar con Voice Service
5. ⏳ Deploy del Dashboard a Vercel (FASE 3)

---

**Webhook URL para Evolution API:**
`https://whatsapp-portero.integratec-ia.com/webhook`

**Repositorio GitHub:**
https://github.com/javierd009/agente-portero

**Container Registry:**
https://github.com/users/javierd009/packages?repo_name=agente-portero
