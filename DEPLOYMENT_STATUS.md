# 🚀 Deployment Status - Agente Portero

**Fecha de inicio:** 2026-01-06
**Stack:** Vercel + Portainer (Contabo) + Supabase
**Responsable:** Deployment en producción

---

## 📋 Estado General del Deployment

| Fase | Estado | Fecha Completada | Notas |
|------|--------|------------------|-------|
| **FASE 1: Supabase** | ✅ COMPLETADA | 2026-01-06 | Base de datos configurada con 9 tablas + seed data |
| **FASE 2: Portainer/Contabo** | ✅ PREPARADA | 2026-01-07 | GitHub Actions, Docker images, guías completas - **Listo para deployment** |
| **FASE 3: Vercel Dashboard** | ⏳ PENDIENTE | - | Después de FASE 2 |

---

## ✅ FASE 1: Supabase Database - COMPLETADA

### Tareas Realizadas
- [x] Creación de proyecto en Supabase
- [x] SQL schema completo ejecutado (9 tablas)
- [x] Seed data insertado
- [x] Credenciales obtenidas

### Recursos Creados
**Tablas creadas (9):**
1. `condominiums` - Condominios con configuración
2. `agents` - Agentes de voz AI
3. `residents` - Residentes con WhatsApp/Email
4. `visitors` - Visitantes autorizados
5. `vehicles` - Vehículos de residentes
6. `access_logs` - Registro de accesos
7. `reports` - Reportes de mantenimiento/seguridad
8. `camera_events` - Eventos de cámaras (placas)
9. `notifications` - Notificaciones enviadas

**Índices creados:**
- `idx_residents_whatsapp` - Para búsquedas por teléfono (CRÍTICO para WhatsApp)
- `idx_access_logs_created_at` - Para queries de logs recientes
- `idx_reports_status` - Para filtros de reportes
- Más índices en DEPLOYMENT_GUIDE.md

**RLS Policies:**
- Row Level Security habilitado en todas las tablas
- Políticas multi-tenant configuradas

**Seed Data:**
- 1 Condominio: "Residencial del Valle"
- 3 Residentes con WhatsApp válidos
- 2 Vehículos
- 1 Agente AI configurado
- Visitantes y reportes de ejemplo

### Credenciales Obtenidas
```env
SUPABASE_URL=https://[PROJECT].supabase.co
SUPABASE_SERVICE_KEY=eyJhbGc...
SUPABASE_ANON_KEY=eyJhbGc...
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
```

### Verificación Realizada
- [x] ✅ COMPLETADO: Verificar tablas en Supabase Table Editor (9 tablas)
- [x] ✅ COMPLETADO: Confirmar seed data visible (11 registros totales)
- [x] ⚠️ NOTA: Conexión local no disponible por IPv6, funcionará en Contabo

---

## ✅ FASE 2: Portainer/Contabo Services - PREPARACIÓN COMPLETA

### Estado Actual
**✅ TODO LISTO PARA DEPLOYMENT.** Repositorio GitHub configurado, imágenes Docker publicadas en ghcr.io, DNS configurados, guías y scripts preparados.

**Servidor:** 147.93.147.12
**Dominios configurados:**
- api-portero.integratec-ia.com → 147.93.147.12 ✅
- whatsapp-portero.integratec-ia.com → 147.93.147.12 ✅
- voice-portero.integratec-ia.com → 147.93.147.12 ✅
- evolution-portero.integratec-ia.com → 147.93.147.12 ✅

**Container Registry:**
- ghcr.io/javierd009/agente-portero-backend:latest ✅
- ghcr.io/javierd009/agente-portero-whatsapp:latest ✅
- ghcr.io/javierd009/agente-portero-voice:latest ✅

### Tareas Completadas

#### 2.1 Preparación Inicial
- [x] Repositorio GitHub creado: https://github.com/javierd009/agente-portero
- [x] Variables de entorno preparadas en `.env.portainer`
- [x] Docker Compose adaptado a infraestructura Portainer con Traefik + Swarm
- [x] DNS configurados apuntando a servidor

#### 2.2 GitHub Actions & Docker Images
- [x] GitHub Actions workflow configurado (`.github/workflows/build-images.yml`)
- [x] Dockerfiles creados para todos los servicios (backend, whatsapp, voice)
- [x] Dependencias corregidas (asyncio-ari → aioari)
- [x] Build exitoso de las 3 imágenes ✅
- [x] Imágenes publicadas en ghcr.io (públicas, no requieren autenticación)
- [x] CI/CD configurado: Push a main → Auto-build → Auto-publish

#### 2.3 Archivos de Deployment
- [x] `docker-compose.portainer.yml` - Swarm-compatible con Traefik labels
- [x] `.env.portainer` - Variables listas para copiar/pegar
- [x] `PORTAINER_DEPLOYMENT.md` - Guía completa paso a paso ⭐
- [x] `scripts/verify-deployment.sh` - Verificación automática
- [x] `scripts/configure-evolution.sh` - Configuración WhatsApp

### Tareas Pendientes (Usuario debe ejecutar)

**📖 GUÍA COMPLETA:** Ver [PORTAINER_DEPLOYMENT.md](PORTAINER_DEPLOYMENT.md)

#### 2.4 Deploy Stack via Portainer
- [ ] Login a Portainer
- [ ] Crear nuevo Stack "agente-portero" con **Web editor**
- [ ] Pegar contenido de `docker-compose.portainer.yml`
- [ ] Copiar variables desde `.env.portainer`
- [ ] Click en **Deploy the stack**
- [ ] Esperar a que Portainer descargue las imágenes desde ghcr.io

#### 2.5 Verificar Servicios Running
- [ ] Verificar 4 servicios corriendo en Portainer:
  - [ ] `backend` - Backend API
  - [ ] `whatsapp-service` - WhatsApp Service
  - [ ] `voice-service` - Voice Service
  - [ ] `evolution-api` - Evolution API

#### 2.6 Health Checks vía URLs públicas
- [ ] `https://api-portero.integratec-ia.com/health` - Backend API
- [ ] `https://whatsapp-portero.integratec-ia.com/health` - WhatsApp Service
- [ ] `https://voice-portero.integratec-ia.com` - Voice Service
- [ ] `https://evolution-portero.integratec-ia.com` - Evolution API

#### 2.7 Configurar Evolution API WhatsApp (CRÍTICO)
- [ ] Ejecutar: `bash scripts/configure-evolution.sh`
- [ ] Escanear QR code con WhatsApp Business
- [ ] Confirmar estado "Connected"
- [ ] Webhook se configurará automáticamente: `https://whatsapp-portero.integratec-ia.com/webhook`

### Servicios Docker

**Backend (FastAPI)** - Puerto 8000
- Endpoints: `/api/v1/residents`, `/api/v1/visitors`, `/api/v1/reports`, `/api/v1/access`
- Depende de: Redis, Supabase
- Health check: `GET /health`

**WhatsApp Service** - Puerto 8002
- Webhook handler para Evolution API
- GPT-4 function calling para intents
- Depende de: Backend, Redis, Evolution API
- Health check: `GET /health`

**Voice Service** - Puerto 8001
- OpenAI Realtime API
- Asterisk ARI integration
- Depende de: Backend, Asterisk (externo)
- Health check: `GET /health`

**Evolution API** - Puerto 8080
- WhatsApp Business API
- QR Code authentication
- Webhook para mensajes
- UI: `http://[IP]:8080`

**Redis** - Puerto 6379
- Cache y sessions
- Persistencia habilitada
- Password protegido

**Nginx** (Opcional) - Puertos 80/443
- Reverse proxy
- SSL/TLS termination
- Rate limiting

### Troubleshooting Común

**Error: "Cannot connect to database"**
```bash
# Verificar DATABASE_URL en .env.production
# Verificar que Supabase permite conexiones desde IP de Contabo
# En Supabase: Settings > Database > Connection Pooling > Allow connections from all IPs
```

**Error: "Evolution API QR not loading"**
```bash
# Verificar contenedor corriendo
docker logs agente-portero-evolution

# Verificar puerto 8080 accesible
curl http://localhost:8080
```

**Error: "WhatsApp Service webhook fails"**
```bash
# Verificar logs
docker logs agente-portero-whatsapp -f

# Verificar webhook URL en Evolution API settings
# Debe ser: http://whatsapp-service:8002/webhook (nombre del servicio, NO localhost)
```

---

## ⏳ FASE 3: Vercel Dashboard - PENDIENTE

### Tareas Planificadas

#### 3.1 Preparar Repositorio
- [ ] Push código a GitHub/GitLab
- [ ] Verificar `apps/dashboard` en raíz o subdirectorio

#### 3.2 Crear Proyecto en Vercel
- [ ] Login a Vercel
- [ ] Import repository
- [ ] Framework preset: Next.js
- [ ] Root directory: `apps/dashboard`

#### 3.3 Configurar Variables de Entorno
Variables necesarias en Vercel:
```env
NEXT_PUBLIC_SUPABASE_URL=https://[PROJECT].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...
NEXT_PUBLIC_API_URL=http://[IP-CONTABO]:8000
```

#### 3.4 Deploy
- [ ] Deploy automático desde main branch
- [ ] Verificar build exitoso
- [ ] Obtener URL de producción
- [ ] Configurar dominio custom (opcional)

#### 3.5 Verificación
- [ ] Dashboard carga correctamente
- [ ] Conexión a Backend API funciona
- [ ] Login con Supabase funciona
- [ ] Multi-tenant selector funciona
- [ ] Métricas se muestran correctamente

---

## 🧪 Testing Checklist (REGLA 2: Probar Todo)

### Tests Locales (Antes de Deploy)
- [x] Backend API tests: `services/backend/test_backend_api.py`
- [x] WhatsApp flow tests: `services/whatsapp-service/test_whatsapp_flow.py`
- [x] Voice service tests: `services/voice-service/test_voice_service.py`
- [x] All-in-one test: `test_all.sh`

### Tests Post-FASE 1 (Supabase)
- [ ] ⚠️ PENDIENTE: Conexión a base de datos desde local
- [ ] ⚠️ PENDIENTE: Query a tabla `condominiums` exitoso
- [ ] ⚠️ PENDIENTE: Query a `residents` con WhatsApp exitoso
- [ ] ⚠️ PENDIENTE: RLS policies funcionando

### Tests Post-FASE 2 (Portainer)
- [ ] ⚠️ PENDIENTE: Health checks de todos los servicios OK
- [ ] ⚠️ PENDIENTE: Backend API responde a requests
- [ ] ⚠️ PENDIENTE: WhatsApp webhook recibe mensajes
- [ ] ⚠️ PENDIENTE: Evolution API conectado a WhatsApp
- [ ] ⚠️ PENDIENTE: Redis cache funciona
- [ ] ⚠️ PENDIENTE: Logs no muestran errores críticos

### Tests Post-FASE 3 (Vercel)
- [ ] ⚠️ PENDIENTE: Dashboard carga en producción
- [ ] ⚠️ PENDIENTE: Login funciona
- [ ] ⚠️ PENDIENTE: API calls al backend exitosos
- [ ] ⚠️ PENDIENTE: Páginas principales cargan
- [ ] ⚠️ PENDIENTE: Reportes se muestran correctamente

### Tests End-to-End (Después de Todo)
- [ ] ⚠️ PENDIENTE: Flujo completo WhatsApp: Residente envía mensaje → Sistema responde
- [ ] ⚠️ PENDIENTE: Autorizar visitante via WhatsApp → Ver en dashboard
- [ ] ⚠️ PENDIENTE: Crear reporte via WhatsApp → Ver en dashboard
- [ ] ⚠️ PENDIENTE: Llamada entrante → Voice Agent responde (requiere Asterisk)
- [ ] ⚠️ PENDIENTE: Detección de placa → Evento en dashboard (requiere cámara)

---

## 📊 Métricas de Éxito

### Performance
- [ ] Backend API response time < 200ms
- [ ] Dashboard load time < 2s
- [ ] WhatsApp message processing < 3s

### Reliability
- [ ] Uptime > 99.5%
- [ ] Zero critical errors en logs
- [ ] Todos los health checks verdes

### Functionality
- [ ] Multi-tenant isolation funciona
- [ ] WhatsApp bidireccional funciona
- [ ] Dashboard muestra datos en tiempo real
- [ ] Reportes se crean y actualizan correctamente

---

## 🔐 Security Checklist

### Supabase
- [x] RLS habilitado en todas las tablas
- [ ] ⚠️ PENDIENTE: Verificar policies multi-tenant
- [ ] ⚠️ PENDIENTE: Service key solo en backend (no en frontend)

### Portainer/Contabo
- [ ] ⚠️ PENDIENTE: `.env.production` con permisos 600
- [ ] ⚠️ PENDIENTE: JWT_SECRET aleatorio y seguro
- [ ] ⚠️ PENDIENTE: Redis password configurado
- [ ] ⚠️ PENDIENTE: Evolution API key cambiado del default
- [ ] ⚠️ PENDIENTE: Firewall configurado (solo puertos necesarios)
- [ ] ⚠️ PENDIENTE: SSL/TLS con Let's Encrypt (post-deployment)

### Vercel
- [ ] ⚠️ PENDIENTE: Environment variables correctamente configuradas
- [ ] ⚠️ PENDIENTE: CORS configurado en backend para dominio Vercel
- [ ] ⚠️ PENDIENTE: HTTPS habilitado por defecto

---

## 📝 Notas de Deployment

### Credenciales Importantes
**Guardar en 1Password/Bitwarden:**
- Supabase Project URL + Service Key
- JWT_SECRET
- Redis Password
- Evolution API Key
- OpenRouter API Key
- Contabo SSH credentials
- Vercel account access

### URLs de Servicios
**Supabase:**
- Dashboard: https://app.supabase.com/project/[PROJECT]
- Database URL: Ver .env.production

**Contabo:**
- SSH: root@[IP]
- Portainer: http://[IP]:9000
- Backend API: http://[IP]:8000
- Evolution API: http://[IP]:8080

**Vercel:**
- Dashboard: https://vercel.com/[usuario]/agente-portero
- Production URL: (después de deploy)

---

## 🐛 Issues Conocidos

### Issues Resueltos
✅ Dict/List types en SQLModel - Solucionado con `Column(JSON)`
✅ Metadata field conflict - Renombrado a `extra_data`
✅ Database import-time error - Lazy initialization con `get_engine()`

### Issues Pendientes
⚠️ Voice Service requiere Asterisk configurado (post-deployment)
⚠️ Camera Events requiere cámaras Hikvision (post-deployment)
⚠️ SSL/TLS certificates (post-deployment)

---

## 🔄 Próximos Pasos (Después de FASE 3)

1. **Configurar Asterisk/FreePBX** para Voice Service
2. **Integrar cámaras Hikvision** para detección de placas
3. **Configurar SSL/TLS** con Let's Encrypt
4. **Setup monitoring** con Prometheus + Grafana
5. **Configurar alerting** para downtime
6. **Load testing** con K6 o Locust
7. **Security audit** completo
8. **Documentación de usuario final**
9. **Training materials** para administradores
10. **Onboarding first condominium**

---

## 📞 Contactos de Soporte

**Servicios Cloud:**
- Supabase: https://supabase.com/support
- Vercel: https://vercel.com/support
- Contabo: https://contabo.com/support

**APIs:**
- OpenRouter: https://openrouter.ai/docs
- Evolution API: https://github.com/EvolutionAPI/evolution-api

---

**Última actualización:** 2026-01-07
**Próxima revisión:** Después de deployment en Portainer (FASE 2)
