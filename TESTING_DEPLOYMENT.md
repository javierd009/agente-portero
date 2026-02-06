# 🧪 Testing Deployment - Agente Portero

**Guía completa de pruebas para cada fase del deployment**

---

## 📋 Índice

- [Reglas de Oro](#reglas-de-oro)
- [Tests Disponibles](#tests-disponibles)
- [FASE 1: Tests de Supabase](#fase-1-tests-de-supabase)
- [FASE 2: Tests de Portainer/Contabo](#fase-2-tests-de-portainercontabo)
- [FASE 3: Tests de Vercel](#fase-3-tests-de-vercel)
- [Tests End-to-End](#tests-end-to-end)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Reglas de Oro

### Regla 1: Siempre Documentar Todo
- Antes de empezar algo, **revisar el contexto** en:
  - `DEPLOYMENT_STATUS.md` - Estado actual del deployment
  - `DEPLOYMENT_GUIDE.md` - Guía paso a paso
  - Este archivo - Cómo probar cada fase
- Después de completar algo, **actualizar la documentación**

### Regla 2: Siempre Hacer Pruebas
- **NUNCA** pasar a la siguiente fase sin probar la actual
- **NUNCA** asumir que algo funciona sin verificar
- **SIEMPRE** ejecutar tests después de cada cambio
- **SIEMPRE** revisar logs en caso de error

---

## 📊 Tests Disponibles

| Test | Archivo | Propósito | Cuándo Ejecutar |
|------|---------|-----------|-----------------|
| **FASE 1** | `test_phase1_supabase.py` | Verificar base de datos Supabase | Después de ejecutar SQL schema |
| **FASE 2** | `test_phase2_deployment.sh` | Verificar servicios en Contabo/Portainer | Después de deploy en Portainer |
| **Backend** | `services/backend/test_backend_api.py` | Verificar API endpoints | Después de FASE 2 |
| **WhatsApp** | `services/whatsapp-service/test_whatsapp_flow.py` | Verificar flujos WhatsApp | Después de Evolution API conectado |
| **Voice** | `services/voice-service/test_voice_service.py` | Verificar servicio de voz | Después de configurar Asterisk |
| **All-in-One** | `test_all.sh` | Ejecutar todos los tests | Al final de todo |

---

## ✅ FASE 1: Tests de Supabase

### Prerequisitos

```bash
# Instalar dependencias
pip install sqlalchemy asyncpg python-dotenv
```

### Configuración

Asegúrate de tener tu archivo `.env.production` con:

```env
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
SUPABASE_URL=https://[PROJECT].supabase.co
SUPABASE_SERVICE_KEY=eyJhbGc...
```

### Ejecutar Tests

```bash
# Desde la raíz del proyecto
python test_phase1_supabase.py
```

### Tests Que Se Ejecutan

1. **Database Connection**
   - ✅ DATABASE_URL está configurado
   - ✅ Conexión a Supabase exitosa
   - ✅ PostgreSQL version detectada

2. **Database Tables**
   - ✅ 9 tablas requeridas existen:
     - condominiums
     - agents
     - residents
     - visitors
     - vehicles
     - access_logs
     - reports
     - camera_events
     - notifications

3. **Database Indexes**
   - ✅ Índices críticos existen:
     - idx_residents_whatsapp
     - idx_access_logs_created_at
     - idx_reports_status

4. **Seed Data**
   - ✅ Al menos 1 condominio existe
   - ✅ Al menos 1 residente con WhatsApp existe
   - ✅ Agentes AI configurados (opcional)

5. **Row Level Security (RLS)**
   - ✅ RLS habilitado en tablas principales
   - ⚠️  Advertencia si RLS no está habilitado

6. **Critical Queries**
   - ✅ Query de residente por WhatsApp funciona
   - ✅ Query de access logs recientes funciona
   - ✅ Query de reportes por status funciona

### Resultado Esperado

```
================================
TEST RESULTS SUMMARY
================================

Total Tests: 12
Passed: 12
Failed: 0
Pass Rate: 100%

🎉 ALL TESTS PASSED!
FASE 1 (Supabase) is configured correctly.
```

### Si Falla

1. **"DATABASE_URL not set"**
   - Verifica que `.env.production` existe
   - Verifica que DATABASE_URL está configurado correctamente

2. **"Cannot connect to database"**
   - Verifica que la URL de Supabase es correcta
   - Verifica que el password es correcto
   - Verifica que Supabase permite conexiones desde tu IP
   - En Supabase: Settings > Database > Connection Pooling > Allow all IPs (o agrega tu IP)

3. **"Some tables are missing"**
   - Ejecuta el SQL schema completo desde `DEPLOYMENT_GUIDE.md` Fase 1
   - Verifica en Supabase Table Editor que las tablas existen

4. **"No condominiums found"**
   - Ejecuta la sección de seed data del SQL
   - O inserta datos manualmente vía Supabase Table Editor

---

## 🐳 FASE 2: Tests de Portainer/Contabo

### Prerequisitos

```bash
# El script usa herramientas estándar de Unix/Linux
# No requiere instalación adicional
```

### Ejecutar Tests

**Opción A: Desde tu Mac (Testing Remoto)**
```bash
# Pasar IP de tu servidor Contabo como argumento
./test_phase2_deployment.sh 123.456.789.0
```

**Opción B: Desde Servidor Contabo (Recomendado)**
```bash
# SSH a Contabo
ssh root@tu-servidor-contabo.com

# Ir a directorio del proyecto
cd /opt/agente-portero

# Ejecutar tests locales
./test_phase2_deployment.sh localhost
```

### Tests Que Se Ejecutan

1. **Docker Containers**
   - ✅ agente-portero-backend está corriendo
   - ✅ agente-portero-whatsapp está corriendo
   - ✅ agente-portero-voice está corriendo
   - ✅ agente-portero-evolution está corriendo
   - ✅ agente-portero-redis está corriendo
   - ✅ agente-portero-nginx está corriendo (opcional)

2. **Service Health Checks**
   - ✅ Backend API responde en puerto 8000
   - ✅ WhatsApp Service responde en puerto 8002
   - ⚠️  Voice Service responde en puerto 8001 (puede fallar sin Asterisk)
   - ✅ Evolution API responde en puerto 8080

3. **Backend API Endpoints**
   - ✅ `/health` devuelve JSON válido
   - ✅ `/docs` (OpenAPI) es accesible
   - ✅ `/api/v1/residents/by-phone/...` es responsive

4. **Redis Connection**
   - ✅ Redis responde a ping (si no tiene password)
   - ⚠️  Redis requiere password (esperado en producción)

5. **Evolution API**
   - ✅ Manager UI es accesible
   - ✅ Instance endpoint responde
   - ✅ Instancia "agente_portero" detectada (o array vacío si no creada)

6. **Environment Configuration**
   - ✅ Todas las variables críticas están configuradas
   - ❌ Advertencia si valores default detectados (CAMBIAR!)

7. **Network Connectivity**
   - ✅ Supabase es alcanzable desde el servidor

8. **Docker Logs Inspection**
   - ✅ No errores críticos en logs de backend
   - ✅ No errores críticos en logs de whatsapp-service
   - ✅ No errores críticos en logs de evolution-api

### Resultado Esperado

```
================================
TEST RESULTS SUMMARY
================================

Total Tests: 23
Passed: 21
Failed: 2

🎉 Deployment successful with minor warnings
(Voice Service y Redis password son esperados)
```

### Si Falla

1. **"Container not found"**
   ```bash
   # Verificar que el stack está desplegado
   docker ps -a

   # Ver logs de Portainer
   docker logs portainer

   # Re-deploy stack en Portainer UI
   ```

2. **"Service not accessible"**
   ```bash
   # Verificar logs del servicio
   docker logs agente-portero-backend

   # Verificar que el puerto está expuesto
   docker port agente-portero-backend

   # Verificar firewall
   sudo ufw status
   ```

3. **"Cannot reach Supabase"**
   - Verificar conexión a internet del servidor
   - Verificar que DATABASE_URL es correcto
   - Ping a Supabase: `ping [PROJECT].supabase.co`

4. **"Evolution API QR not loading"**
   ```bash
   # Ver logs
   docker logs agente-portero-evolution

   # Restart servicio
   docker restart agente-portero-evolution

   # Verificar puerto 8080
   curl http://localhost:8080
   ```

---

## ☁️ FASE 3: Tests de Vercel

### Tests Manuales (Por Ahora)

1. **Acceso al Dashboard**
   ```
   URL: https://tu-app.vercel.app
   ✅ Dashboard carga sin errores
   ✅ No errores en consola del navegador
   ```

2. **API Connection**
   ```
   En Dashboard:
   ✅ Métricas se cargan correctamente
   ✅ Tablas muestran datos
   ✅ Gráficas renderizan
   ```

3. **Authentication**
   ```
   ✅ Login con Supabase funciona
   ✅ Sesión persiste al recargar
   ✅ Logout funciona correctamente
   ```

4. **Multi-Tenant**
   ```
   ✅ Selector de condominio visible
   ✅ Cambiar condominio actualiza datos
   ✅ Datos están aislados por tenant
   ```

### Verificación en Navegador

```javascript
// Abrir consola del navegador (F12)

// Test 1: Verificar API URL
console.log(process.env.NEXT_PUBLIC_API_URL)
// Debe mostrar: http://[IP-CONTABO]:8000

// Test 2: Hacer fetch manual
fetch('http://[IP-CONTABO]:8000/health')
  .then(r => r.json())
  .then(console.log)
// Debe devolver: {status: "healthy", ...}
```

### Si Falla

1. **"Cannot load dashboard"**
   - Verificar build logs en Vercel
   - Verificar que `apps/dashboard` es el root directory correcto
   - Verificar Next.js version compatibility

2. **"API calls fail with CORS error"**
   - Agregar dominio de Vercel a CORS en backend
   - En `services/backend/main.py`:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://tu-app.vercel.app"],
       ...
   )
   ```

3. **"Environment variables not found"**
   - Verificar en Vercel > Settings > Environment Variables
   - Re-deploy después de cambiar variables

---

## 🔄 Tests End-to-End

### Test E2E 1: Flujo WhatsApp Completo

```bash
# 1. Enviar mensaje de WhatsApp al número del sistema
"Hola, me viene a buscar María González en un auto placa ABC123"

# 2. Verificar respuesta del sistema
Esperado: "✅ Visitante autorizado..."

# 3. Verificar en Dashboard
- Ir a /dashboard/visitors
- Buscar "María González"
- Estado debe ser "approved"
- Autorizado por "whatsapp"

# 4. Verificar en base de datos
SELECT * FROM visitors WHERE visitor_name = 'María González';
```

### Test E2E 2: Flujo de Reportes

```bash
# 1. Enviar reporte via WhatsApp
"Reporte: La luz del pasillo no funciona, urgente"

# 2. Verificar respuesta
Esperado: "✅ Reporte creado exitosamente..."

# 3. Verificar en Dashboard
- Ir a /dashboard/reports
- Buscar reporte reciente
- Status debe ser "pending"
- Source debe ser "whatsapp"

# 4. Actualizar status en Dashboard
- Click en "Comenzar"
- Status cambia a "in_progress"
- Marcar como resuelto
- Status cambia a "resolved"

# 5. Verificar en base de datos
SELECT status FROM reports WHERE title LIKE '%luz%pasillo%';
```

### Test E2E 3: Logs de Acceso

```bash
# 1. Simular evento de acceso (vía API)
curl -X POST http://[IP]:8000/api/v1/access/logs \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: [TENANT-UUID]" \
  -d '{
    "condominium_id": "[UUID]",
    "event_type": "entry",
    "access_point": "main_gate",
    "metadata": {"test": true}
  }'

# 2. Verificar en Dashboard
- Ir a /dashboard/access-logs
- Log debe aparecer en la lista
- Event type debe ser "entry"

# 3. Verificar auto-refresh
- Esperar 30 segundos
- Dashboard debe actualizar automáticamente
```

---

## 🔍 Troubleshooting General

### Comandos Útiles

```bash
# Ver todos los contenedores
docker ps -a

# Ver logs de un servicio específico
docker logs agente-portero-backend -f --tail 100

# Restart un servicio
docker restart agente-portero-backend

# Ver uso de recursos
docker stats

# Verificar red de Docker
docker network inspect agente-portero

# Ejecutar comando dentro de contenedor
docker exec -it agente-portero-backend bash

# Ver variables de entorno de un contenedor
docker exec agente-portero-backend env

# Probar conexión entre servicios
docker exec agente-portero-whatsapp curl http://backend:8000/health
```

### Verificación de Ports

```bash
# Verificar qué está usando un puerto
lsof -i :8000
lsof -i :8002
lsof -i :8080

# Ver puertos abiertos
netstat -tuln | grep LISTEN

# Verificar firewall
sudo ufw status
```

### Verificación de Logs

```bash
# Logs de todos los servicios
docker-compose -f docker-compose.production.yml logs -f

# Filtrar por nivel de error
docker logs agente-portero-backend 2>&1 | grep -i error

# Últimas 100 líneas
docker logs agente-portero-whatsapp --tail 100
```

---

## 📝 Checklist de Testing Completo

### Pre-Deployment
- [ ] Código del proyecto está actualizado
- [ ] Todas las dependencias instaladas
- [ ] Variables de entorno configuradas
- [ ] Tests locales pasan (`test_all.sh`)

### Post-FASE 1 (Supabase)
- [ ] `python test_phase1_supabase.py` pasa al 100%
- [ ] Tablas visibles en Supabase Table Editor
- [ ] Seed data presente
- [ ] RLS habilitado
- [ ] **ACTUALIZAR** `DEPLOYMENT_STATUS.md` con ✅

### Post-FASE 2 (Portainer)
- [ ] `./test_phase2_deployment.sh [IP]` pasa con >90%
- [ ] Todos los contenedores corriendo
- [ ] Health checks verdes
- [ ] Evolution API conectado a WhatsApp (QR escaneado)
- [ ] Webhook configurado
- [ ] No errores críticos en logs
- [ ] **ACTUALIZAR** `DEPLOYMENT_STATUS.md` con ✅

### Post-FASE 3 (Vercel)
- [ ] Dashboard accesible en URL de Vercel
- [ ] Login funciona
- [ ] API calls exitosos
- [ ] Todas las páginas cargan
- [ ] No errores en consola
- [ ] **ACTUALIZAR** `DEPLOYMENT_STATUS.md` con ✅

### Post-Deployment Completo
- [ ] Test E2E: WhatsApp → Dashboard funciona
- [ ] Test E2E: Reportes vía WhatsApp funciona
- [ ] Test E2E: Logs de acceso se registran
- [ ] Performance aceptable (<2s load time)
- [ ] Security check: No secrets expuestos
- [ ] Monitoring configurado (opcional)
- [ ] **ACTUALIZAR** `DEPLOYMENT_STATUS.md` con estado final

---

## 🎯 Métricas de Éxito

### Performance
- ✅ Backend API response time < 200ms
- ✅ Dashboard load time < 2s
- ✅ WhatsApp message processing < 3s

### Reliability
- ✅ All health checks green
- ✅ Zero critical errors in logs
- ✅ Services restart automatically on failure

### Functionality
- ✅ WhatsApp bidirectional works
- ✅ Multi-tenant isolation works
- ✅ Dashboard shows real-time data
- ✅ Reports create and update correctly

---

## 📞 Support

Si encuentras problemas:

1. **Revisa logs** con los comandos de troubleshooting
2. **Consulta** `DEPLOYMENT_STATUS.md` para ver estado actual
3. **Revisa** `DEPLOYMENT_GUIDE.md` para pasos de deployment
4. **Ejecuta tests** correspondientes a la fase donde estás

---

**Última actualización:** 2026-01-06
**Versión:** 1.0
