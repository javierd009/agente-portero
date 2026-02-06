# 🚀 Guía de Deployment - Portainer + Vercel + Supabase

**Stack de Producción:**
- ✅ **Vercel** - Dashboard (Next.js)
- ✅ **Portainer** - Servicios Backend (Docker)
- ✅ **Supabase** - PostgreSQL + Auth

---

## 📋 Prerequisitos

- ✅ Cuenta de Supabase con proyecto creado
- ✅ Servidor con Portainer instalado
- ✅ Cuenta de Vercel
- ✅ Dominio DNS configurado (opcional pero recomendado)
- ✅ OpenAI API key

---

## 🗄️ Paso 1: Setup Supabase (Base de Datos)

### 1.1 Crear Proyecto en Supabase

```bash
# 1. Ve a https://app.supabase.com
# 2. Crear nuevo proyecto
# 3. Guardar:
#    - Database Password
#    - Project URL
#    - API Keys (anon + service_role)
```

### 1.2 Ejecutar Migraciones

**Opción A: Desde Supabase SQL Editor**

1. Ir a `SQL Editor` en Supabase Dashboard
2. Copiar y ejecutar el siguiente SQL:

```sql
-- Crear extensión UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Crear tabla condominiums
CREATE TABLE condominiums (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    address TEXT,
    timezone VARCHAR(50) DEFAULT 'America/Mexico_City',
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Crear tabla agents
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID REFERENCES condominiums(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    extension VARCHAR(50),
    prompt TEXT,
    voice_id VARCHAR(50),
    language VARCHAR(10) DEFAULT 'es-MX',
    is_active BOOLEAN DEFAULT true,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Crear tabla residents
CREATE TABLE residents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID REFERENCES condominiums(id) ON DELETE CASCADE,
    user_id UUID,
    name VARCHAR(255) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    phone VARCHAR(50),
    email VARCHAR(255),
    whatsapp VARCHAR(50),
    authorized_visitors TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Crear tabla visitors
CREATE TABLE visitors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID REFERENCES condominiums(id) ON DELETE CASCADE,
    resident_id UUID REFERENCES residents(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    id_number VARCHAR(100),
    phone VARCHAR(50),
    vehicle_plate VARCHAR(50),
    reason TEXT,
    authorized_by VARCHAR(50),
    valid_until TIMESTAMP,
    notes TEXT,
    entry_time TIMESTAMP,
    exit_time TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Crear tabla vehicles
CREATE TABLE vehicles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID REFERENCES condominiums(id) ON DELETE CASCADE,
    resident_id UUID REFERENCES residents(id) ON DELETE CASCADE,
    plate VARCHAR(50) NOT NULL,
    brand VARCHAR(100),
    model VARCHAR(100),
    color VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Crear tabla access_logs
CREATE TABLE access_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID REFERENCES condominiums(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    access_point VARCHAR(100),
    direction VARCHAR(20),
    resident_id UUID REFERENCES residents(id) ON DELETE SET NULL,
    visitor_id UUID REFERENCES visitors(id) ON DELETE SET NULL,
    visitor_name VARCHAR(255),
    vehicle_plate VARCHAR(50),
    authorization_method VARCHAR(50),
    authorized_by VARCHAR(255),
    camera_snapshot_url TEXT,
    confidence_score FLOAT,
    extra_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Crear tabla reports
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID REFERENCES condominiums(id) ON DELETE CASCADE,
    resident_id UUID REFERENCES residents(id) ON DELETE SET NULL,
    report_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    location VARCHAR(255),
    urgency VARCHAR(20) DEFAULT 'normal',
    status VARCHAR(50) DEFAULT 'pending',
    source VARCHAR(50) DEFAULT 'web',
    photo_urls JSONB DEFAULT '{}',
    assigned_to VARCHAR(255),
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    extra_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Crear tabla camera_events
CREATE TABLE camera_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID REFERENCES condominiums(id) ON DELETE CASCADE,
    camera_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    plate_number VARCHAR(50),
    plate_confidence FLOAT,
    face_id VARCHAR(255),
    face_confidence FLOAT,
    snapshot_url TEXT,
    video_url TEXT,
    extra_data JSONB DEFAULT '{}',
    processed BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Crear tabla notifications
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominium_id UUID REFERENCES condominiums(id) ON DELETE CASCADE,
    resident_id UUID REFERENCES residents(id) ON DELETE SET NULL,
    channel VARCHAR(50) NOT NULL,
    recipient VARCHAR(255) NOT NULL,
    notification_type VARCHAR(50),
    title VARCHAR(255),
    message TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    extra_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX idx_residents_condominium ON residents(condominium_id);
CREATE INDEX idx_residents_whatsapp ON residents(whatsapp);
CREATE INDEX idx_visitors_condominium ON visitors(condominium_id);
CREATE INDEX idx_visitors_status ON visitors(status);
CREATE INDEX idx_access_logs_condominium ON access_logs(condominium_id);
CREATE INDEX idx_access_logs_created ON access_logs(created_at DESC);
CREATE INDEX idx_reports_condominium ON reports(condominium_id);
CREATE INDEX idx_reports_status ON reports(status);
CREATE INDEX idx_camera_events_condominium ON camera_events(condominium_id);
CREATE INDEX idx_camera_events_created ON camera_events(created_at DESC);

-- Row Level Security (RLS) para multi-tenant
ALTER TABLE condominiums ENABLE ROW LEVEL SECURITY;
ALTER TABLE residents ENABLE ROW LEVEL SECURITY;
ALTER TABLE visitors ENABLE ROW LEVEL SECURITY;
ALTER TABLE access_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE camera_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Políticas RLS (ajustar según tus necesidades de auth)
-- Por ahora permitir todo para service_role
CREATE POLICY "Service role full access condominiums" ON condominiums FOR ALL USING (true);
CREATE POLICY "Service role full access residents" ON residents FOR ALL USING (true);
CREATE POLICY "Service role full access visitors" ON visitors FOR ALL USING (true);
CREATE POLICY "Service role full access access_logs" ON access_logs FOR ALL USING (true);
CREATE POLICY "Service role full access reports" ON reports FOR ALL USING (true);
CREATE POLICY "Service role full access camera_events" ON camera_events FOR ALL USING (true);
CREATE POLICY "Service role full access notifications" ON notifications FOR ALL USING (true);
```

### 1.3 Seed Data (Opcional para Testing)

```sql
-- Insertar condominio de prueba
INSERT INTO condominiums (name, slug, address, timezone, is_active)
VALUES ('Residencial del Valle', 'residencial-del-valle', 'Av. Principal 1234, Monterrey, NL', 'America/Mexico_City', true)
RETURNING id;

-- Copiar el ID del condominio y usarlo en los siguientes inserts
-- Reemplazar [CONDO_ID] con el UUID generado

-- Insertar residentes de prueba
INSERT INTO residents (condominium_id, name, unit, phone, email, whatsapp, is_active)
VALUES
('[CONDO_ID]', 'Juan Pérez García', 'A-101', '+52 81 1234 5678', 'juan.perez@gmail.com', '5218112345678', true),
('[CONDO_ID]', 'María Rodríguez López', 'A-205', '+52 81 9876 5432', 'maria.rodriguez@gmail.com', '5218198765432', true),
('[CONDO_ID]', 'Carlos Martínez Hernández', 'B-103', '+52 81 5555 1234', 'carlos.martinez@gmail.com', '5218155551234', true);
```

### 1.4 Obtener Connection String

```bash
# En Supabase Dashboard → Settings → Database
# Copiar "Connection string" en formato URI

# Ejemplo:
postgresql://postgres:[YOUR-PASSWORD]@db.abcdefghijk.supabase.co:5432/postgres
```

---

## 🐳 Paso 2: Deploy en Portainer (Servicios Backend)

### 2.1 Preparar Variables de Entorno

1. En tu servidor con Portainer, crear archivo `.env.production`:

```bash
# En tu servidor
cd /opt/agente-portero  # O la ruta que prefieras
nano .env.production
```

2. Copiar el contenido de `.env.production.example` y llenar con tus valores reales

### 2.2 Subir Código al Servidor

```bash
# Opción A: Git (recomendado)
ssh usuario@tu-servidor
cd /opt/agente-portero
git clone https://github.com/tu-usuario/agente-portero.git .
git checkout main

# Opción B: SCP/SFTP
# Desde tu máquina local:
scp -r agente_portero/ usuario@tu-servidor:/opt/agente-portero/
```

### 2.3 Deploy con Portainer

#### Opción A: Via Portainer UI

1. Abrir Portainer: `https://tu-servidor:9000`
2. Ir a **Stacks** → **Add stack**
3. **Name**: `agente-portero`
4. **Build method**: Repository
5. **Repository URL**: Tu repo de Git
6. O **Upload**: Subir `docker-compose.production.yml`
7. **Environment variables**:
   - Cargar desde `.env.production`
   - O agregar manualmente una por una
8. **Deploy the stack**

#### Opción B: Via Docker Compose CLI

```bash
# En el servidor
cd /opt/agente-portero

# Cargar variables de entorno
export $(cat .env.production | xargs)

# Deploy
docker-compose -f docker-compose.production.yml up -d

# Ver logs
docker-compose -f docker-compose.production.yml logs -f
```

### 2.4 Verificar Servicios

```bash
# Ver contenedores corriendo
docker ps

# Deberías ver:
# - agente-portero-backend (port 8000)
# - agente-portero-whatsapp (port 8002)
# - agente-portero-voice (port 8001)
# - agente-portero-evolution (port 8080)
# - agente-portero-redis (port 6379)

# Test health checks
curl http://localhost:8000/health
# {"status": "ok"}

curl http://localhost:8002/health
# {"status": "ok"}
```

### 2.5 Configurar Nginx (Reverse Proxy)

Crear `nginx/nginx.conf`:

```nginx
server {
    listen 80;
    server_name api.agente-portero.com;

    # Backend API
    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WhatsApp Webhook
    location /webhook {
        proxy_pass http://whatsapp-service:8002/webhook;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Evolution API (admin)
    location /evolution/ {
        proxy_pass http://evolution-api:8080/;
        proxy_set_header Host $host;
    }

    # SSL redirect (después de configurar Certbot)
    # return 301 https://$server_name$request_uri;
}

# HTTPS (después de Certbot)
# server {
#     listen 443 ssl;
#     server_name api.agente-portero.com;
#
#     ssl_certificate /etc/letsencrypt/live/api.agente-portero.com/fullchain.pem;
#     ssl_certificate_key /etc/letsencrypt/live/api.agente-portero.com/privkey.pem;
#
#     # ... same location blocks as above
# }
```

---

## ☁️ Paso 3: Deploy Dashboard en Vercel

### 3.1 Conectar Repositorio

```bash
# Opción A: Via Vercel CLI
cd apps/dashboard
npm install -g vercel
vercel login
vercel

# Opción B: Via Vercel Dashboard
# 1. Ir a https://vercel.com/new
# 2. Import Git Repository
# 3. Seleccionar el repo de agente_portero
```

### 3.2 Configurar Proyecto

En Vercel Dashboard → Settings:

**Framework Preset**: Next.js
**Root Directory**: `apps/dashboard`
**Build Command**: `npm run build`
**Output Directory**: `.next`
**Install Command**: `npm install`

### 3.3 Variables de Entorno

En Vercel Dashboard → Settings → Environment Variables:

```env
# Backend API (tu Portainer con dominio público)
NEXT_PUBLIC_API_URL=https://api.agente-portero.com

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://[PROJECT].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...  # Anon key (es pública)
```

### 3.4 Deploy

```bash
# Automático: Push a main branch
git push origin main

# Manual: Trigger deploy
vercel --prod
```

### 3.5 Configurar Dominio Personalizado (Opcional)

1. Vercel Dashboard → Settings → Domains
2. Agregar: `dashboard.agente-portero.com`
3. Configurar DNS:
   ```
   Type: CNAME
   Name: dashboard
   Value: cname.vercel-dns.com
   ```

**Resultado**: Dashboard en `https://dashboard.agente-portero.com` ✅

---

## ⚙️ Paso 4: Configurar Evolution API (WhatsApp)

### 4.1 Acceder a Evolution API

```bash
# Via navegador (si usas Nginx):
https://api.agente-portero.com/evolution/

# O directo (IP del servidor):
http://[IP-SERVIDOR]:8080
```

### 4.2 Crear Instancia

```bash
# Via API
curl -X POST https://api.agente-portero.com/evolution/instance/create \
  -H "apikey: B6D711FCDE4D4FD5936544120E713976" \
  -H "Content-Type: application/json" \
  -d '{
    "instanceName": "agente_portero",
    "qrcode": true
  }'
```

### 4.3 Escanear QR Code

```bash
# Obtener QR code
curl https://api.agente-portero.com/evolution/instance/connect/agente_portero \
  -H "apikey: B6D711FCDE4D4FD5936544120E713976"

# Escanear con WhatsApp Business
# WhatsApp → Dispositivos vinculados → Vincular dispositivo
```

### 4.4 Configurar Webhook

```bash
curl -X POST https://api.agente-portero.com/evolution/webhook/set/agente_portero \
  -H "apikey: B6D711FCDE4D4FD5936544120E713976" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.agente-portero.com/webhook",
    "webhook_by_events": false,
    "events": ["MESSAGES_UPSERT"]
  }'
```

---

## ✅ Paso 5: Verificación Final

### 5.1 Test Backend API

```bash
# Health check
curl https://api.agente-portero.com/api/v1/health

# Swagger docs
open https://api.agente-portero.com/docs

# Test endpoint (con tenant_id del seed data)
curl https://api.agente-portero.com/api/v1/residents/by-phone/5218112345678
```

### 5.2 Test WhatsApp

```bash
# Enviar mensaje de WhatsApp desde el número configurado
# "Viene María González en 10 minutos"

# Ver logs
docker logs agente-portero-whatsapp -f
```

### 5.3 Test Dashboard

```bash
# Abrir en navegador
open https://dashboard.agente-portero.com

# Login con Supabase Auth
# Verificar que carga datos del backend
```

---

## 📊 Monitoreo

### Logs en Portainer

```bash
# Ver logs de todos los servicios
docker-compose -f docker-compose.production.yml logs -f

# Logs de un servicio específico
docker logs agente-portero-backend -f
docker logs agente-portero-whatsapp -f
docker logs agente-portero-voice -f
```

### Métricas en Vercel

- Ir a Vercel Dashboard → Analytics
- Ver: Page views, Load times, Errors

### Database en Supabase

- Ir a Supabase Dashboard → Database → Tables
- Ver datos en tiempo real
- Ejecutar queries SQL

---

## 🔒 Security Checklist

- [ ] Cambiar todos los passwords por defecto
- [ ] Configurar firewall en servidor (solo puertos necesarios)
- [ ] Configurar SSL/TLS con Let's Encrypt
- [ ] Habilitar Row Level Security en Supabase
- [ ] Configurar rate limiting en Nginx
- [ ] Rotar API keys regularmente
- [ ] Backups automáticos de Supabase (incluido en plan)
- [ ] Configurar alertas de monitoring

---

## 🚨 Troubleshooting

### Backend no conecta a Supabase

```bash
# Verificar DATABASE_URL
docker exec agente-portero-backend env | grep DATABASE_URL

# Test conexión desde container
docker exec -it agente-portero-backend bash
python -c "
import asyncpg
import asyncio
asyncio.run(asyncpg.connect('$DATABASE_URL'))
print('Connected!')
"
```

### WhatsApp Service no recibe webhooks

```bash
# Verificar webhook está configurado
curl https://api.agente-portero.com/evolution/webhook/find/agente_portero \
  -H "apikey: YOUR_KEY"

# Verificar logs
docker logs agente-portero-whatsapp -f

# Test webhook manualmente
curl -X POST https://api.agente-portero.com/webhook \
  -H "Content-Type: application/json" \
  -d '{"event": "messages.upsert", "data": {...}}'
```

### Dashboard no carga datos

```bash
# Verificar NEXT_PUBLIC_API_URL en Vercel
# Debe apuntar a tu backend público

# Test desde browser console:
fetch('https://api.agente-portero.com/api/v1/health')
  .then(r => r.json())
  .then(console.log)

# Verificar CORS en backend
```

---

## 🎯 Próximos Pasos

1. ✅ Configurar SSL/TLS (Certbot + Let's Encrypt)
2. ✅ Setup CI/CD (GitHub Actions → Auto deploy)
3. ✅ Configurar monitoring (Prometheus + Grafana)
4. ✅ Setup alertas (PagerDuty, email, Slack)
5. ✅ Load testing (k6, Apache JMeter)

---

**¡Listo! Tu sistema Agente Portero está en producción.** 🚀

Cualquier duda, revisa los logs de los servicios o consulta la documentación principal.
