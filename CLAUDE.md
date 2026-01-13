# Proyecto: Agente Portero - Guardia Virtual para Condominios

## Descripcion del Proyecto
Plataforma SaaS de guardia virtual AI para condominios que **reemplaza completamente** a un oficial de seguridad.
Opera via llamadas SIP (Asterisk/FreePBX), WhatsApp bidireccional (Evolution API), camaras Hikvision (ISAPI),
vision AI (YOLO+OCR+Facial), y ofrece dashboard web multi-tenant.

**Capacidades Principales:**
- 🎙️ Conversaciones de voz naturales (OpenAI Realtime)
- 📱 Gestión via WhatsApp (residentes reportan visitantes, abren puerta remota, crean reportes)
- 👁️ Detección automática de placas + reconocimiento facial
- 🚪 Control automático de puertas/barreras
- 📊 Dashboard analytics en tiempo real
- 🔐 Multi-tenant seguro con audit logs

## Principios de Desarrollo

### Design Philosophy
- **KISS**: Soluciones simples primero
- **YAGNI**: Solo lo necesario ahora
- **DRY**: Evitar duplicacion
- **Security-First**: Multi-tenant aislado, audit logs

## Infraestructura de Produccion

### Servidores
| Servidor | Ubicacion | Proposito |
|----------|-----------|-----------|
| **Contabo Cloud** | Nube (Alemania) | Docker Swarm + Portainer (todos los microservicios) |
| **FreePBX** | On-premise (172.20.20.1) | Asterisk PBX para llamadas SIP |
| **Mikrotik** | On-premise | Router/NAT, acceso via puerto 90 |

### Accesos Externos (NAT)
| Servicio | URL Externa | Destino Interno |
|----------|-------------|-----------------|
| Asterisk ARI | integrateccr.ddns.net:8880 | 172.20.20.1:8088 |
| Vision Service | integrateccr.ddns.net:8001 | 172.20.20.1:8001 |
| Mikrotik WebFig | integrateccr.ddns.net:90 | Router admin |

### FreePBX/Asterisk
- **Version**: Asterisk 22.5.2
- **IP Local**: 172.20.20.1
- **SSH**: root / Sitnova20@
- **ARI User**: asterisk / asterisk123
- **Configuracion ARI**: /etc/asterisk/ari_general_additional.conf (enabled=yes, allowed_origins=*)

### Docker/Portainer (Contabo)
- Todos los microservicios corren en Docker Swarm
- Portainer para gestion visual de stacks
- Acceso externo a FreePBX via NAT (no hairpin issues desde la nube)

## Tech Stack & Architecture

### Monorepo Structure
```
agente_portero/
├── services/
│   ├── backend/           # FastAPI + SQLModel (API central, orchestrator)
│   ├── voice-service/     # SIP ↔ OpenAI Realtime (llamadas de voz)
│   ├── whatsapp-service/  # Evolution API ↔ NLP (mensajes bidireccionales)
│   └── vision-service/    # YOLO + OCR + Facial (deteccion automatica)
├── apps/
│   └── dashboard/         # Next.js 15 (multi-tenant UI)
├── supabase/
│   └── migrations/        # SQL migrations
└── docs/                  # Arquitectura y workflows
```

### Documentacion Tecnica
| Documento | Descripcion |
|-----------|-------------|
| `docs/OPENAI_REALTIME_FREEPBX_INTEGRATION.md` | Guia completa de integracion OpenAI Realtime + Asterisk AudioSocket |
| `docs/VOICE_AUDIO_FIX.md` | Historial de fixes de audio en Voice Service |
| `services/voice-service/README.md` | Documentacion del Voice Service |
| `services/vision-service/README.md` | Guia de deployment Edge Computing en FreePBX |

### Backend (FastAPI)
- **Runtime**: Python 3.11
- **Framework**: FastAPI 0.109+
- **ORM**: SQLModel (SQLAlchemy + Pydantic)
- **Database**: PostgreSQL (Supabase)
- **Auth**: Supabase Auth + JWT

### Voice Service (ACTIVO)
- **PBX**: Asterisk/FreePBX 22.5.2 (ARI/AMI)
- **AI**: OpenAI Realtime API (conversacion natural)
- **Voces**: OpenAI voices (fallback ElevenLabs para personalizacion)
- **Protocol**: SIP/WebSocket
- **Latencia**: <500ms (critico para experiencia natural)
- **ARI Endpoint**: integrateccr.ddns.net:8880 (NAT → 172.20.20.1:8088)
- **ARI Credentials**: asterisk / asterisk123
- **Estado**: ARI habilitado y accesible desde internet

### Voice Service Fixes (Repo)
- **AudioSocket**: Puerto host `9089` → container `8089` alineado en `freepbx-config/extensions_agente_portero.conf` y `docker-compose.portainer.SIMPLE.yml`
- **Stasis/ARI**: Dialplan ahora fuerza `slin16` para evitar audio grave/distorsionado (`services/voice-service/asterisk/extensions_agente_portero.conf`)
- **Audio Bridge**: Se definio `BYTES_PER_CHUNK` para evitar error en External Media (`services/voice-service/audio_bridge.py`)
- **Logs**: Mensajes de sample rate y deteccion automatica por tamaño de chunk (`services/voice-service/call_session.py`)
- **Playback**: Sample rate y chunk size ahora se ajustan al rate configurado/detectado; buffer de salida mas amplio para evitar cortes (`services/voice-service/call_session.py`)
- **Barge-in**: Ignora barge-in mientras hay audio en reproduccion/cola o el AI hablo recientemente; evita cortar frases (`services/voice-service/call_session.py`)
- **Playout**: Prebuffer con pacing y mas tolerancia a silencios para evitar trabas (`services/voice-service/call_session.py`)
- **Noise Gate**: Silencia ruido bajo para estabilizar VAD (`services/voice-service/call_session.py`)
- **TCP_NODELAY**: Habilitado en AudioSocket para menor latencia (`services/voice-service/audio_bridge.py`)

> **Documentacion Tecnica Completa**: Ver `docs/OPENAI_REALTIME_FREEPBX_INTEGRATION.md` para guia detallada de integracion, troubleshooting y parametros tunables.

### WhatsApp Service (ACTIVO)
- **Platform**: Evolution API Externa (devevoapi.integratec-ia.com)
- **Instancia**: Sitnova_portero
- **NLP**: OpenAI GPT-4 (parseo de intenciones para residentes)
- **AI Agent**: GPT-4o-mini via OpenRouter (conversacion natural)
- **Flujos**:
  - **Visitantes (no registrados)**: AI Security Agent conversa con ellos
  - **Residentes**: Intent parsing para acciones especificas
    - Autorizar visitantes ("Viene Juan en 10 min")
    - Apertura remota de puerta
    - Reportes/bitacora ("Reportar foco fundido")
    - Consultas de logs
  - **Unknown intent**: AI Agent responde naturalmente
- **Caracteristicas del AI Agent**:
  - Bilingue automatico (espanol/ingles)
  - Memoria conversacional por telefono
  - Actua como guardia de seguridad virtual
  - Personalidad: Profesional, amigable, consciente de seguridad
- **Impact**: Reduce llamadas de voz en 40-50%

### Vision Service (Edge Computing)
- **Ubicacion**: On-premise en FreePBX (172.20.20.1:8001)
- **Acceso Externo**: integrateccr.ddns.net:8001 (NAT)
- **Detection**: YOLOv8/v10
- **OCR**: PaddleOCR
- **Camera**: Hikvision ISAPI (172.20.22.111)
- **Runtime**: Docker (sin CUDA en FreePBX)
- **Beneficios Edge Computing**:
  - Baja latencia: Video procesado localmente sin salir a internet
  - Menor ancho de banda: Solo resultados viajan a la nube
  - Acceso directo a camaras sin NAT/firewall issues
  - Funciona aunque internet falle temporalmente
- **API Endpoints**:
  - `GET /health` - Health check
  - `POST /cameras/test` - Probar conexion a camara
  - `GET /cameras/{id}/snapshot/base64` - Captura en base64
  - `POST /detect` - Deteccion YOLO
- **Dashboard Integration**: Configuracion en Settings > Vision Service (Edge Computing)

> **Deployment Manual**: Ver `services/vision-service/README.md` para guia paso a paso de instalacion en FreePBX

### Dashboard (Next.js)
- **Framework**: Next.js 16 (App Router)
- **Styling**: Tailwind CSS + shadcn/ui
- **State**: Zustand + TanStack Query
- **Auth**: Supabase Auth
- **Edge Computing Integration** (`apps/dashboard/src/lib/api.ts`):
  - `visionService.healthCheck(url)` - Verificar conexion al Vision Service
  - `visionService.testCamera(url, credentials)` - Probar camara via edge
  - `visionService.getSnapshot(url, channelId)` - Obtener captura en base64
  - `visionService.listCameras(url)` - Listar camaras del Vision Service
- **Paginas con Edge Computing**:
  - `/dashboard/settings` - Configurar vision_service_url por condominio
  - `/dashboard/cameras` - Banner de estado, usa Vision Service si disponible

## Arquitectura Multi-Tenant (Actualizada)

```
┌──────────────────────────────────────────────────────────────┐
│                      Dashboard (Next.js)                      │
│   Gestión multi-condominio, analytics, configuración         │
└────────────────┬────────────────────────────┬────────────────┘
                 │ REST API                    │ Llamadas directas
                 │                             │ (Edge Computing)
┌────────────────▼────────────────┐            │
│         Backend (FastAPI)        │            │
│  Orchestrator: auth, audit,      │            │
│  multi-tenant, configuracion     │            │
└────────┬──────────┬──────────┬───┘            │
         │          │          │                │
    ┌────▼────┐ ┌──▼────┐  ┌──▼────┐           │
    │ Voice   │ │WhatsApp│  │Supabase│           │
    │ Service │ │Service │  │  DB    │           │
    └────┬────┘ └──┬─────┘  └────────┘           │
         │         │                             │
═════════╪═════════╪═════════════════════════════╪═══════════════
         │         │    ON-PREMISE (FreePBX)     │
         │         │    172.20.20.1              │
    ┌────▼────┐ ┌──▼────────┐  ┌─────────────────▼──────────────┐
    │Asterisk │ │ Evolution │  │      Vision Service (:8001)    │
    │ FreePBX │ │    API    │  │   YOLO + OCR + Hikvision ISAPI │
    └─────────┘ └───────────┘  └─────────────────┬──────────────┘
                                                 │ Red local
                                          ┌──────▼──────┐
                                          │  Hikvision  │
                                          │   Cameras   │
                                          │172.20.22.111│
                                          └─────────────┘

FLUJOS PRINCIPALES:
1. Visitante llama → Voice Service → Backend → Decision
2. Residente WhatsApp → WhatsApp Service → Backend → Action
3. Dashboard → Vision Service (directo) → Snapshot/Test camara
4. Cámara detecta placa → Vision Service → Backend → Auto-open
```

## Flujos Principales

### 1️⃣ Flujo: Llamada de Voz (Voice Service)

```
1. Visitante llama al interfon → Asterisk recibe llamada SIP
2. ARI notifica a voice-service → Inicia sesión OpenAI Realtime
3. AI Agent saluda y pregunta datos del visitante
4. Mientras conversa, Vision Service detecta placa/cédula (si aplica)
5. AI consulta backend: ¿Visitante autorizado? ¿Residente existe?
6. Si NO está autorizado previamente:
   a. WhatsApp al residente: "Visitante X en puerta. ¿Autorizar? [Sí][No]"
   b. Residente responde → Backend procesa decisión
7. Si autorizado (o residente aprueba):
   a. Backend → Hikvision: Abrir puerta
   b. WhatsApp al residente: "✅ Visitante ingresó (foto + hora)"
   c. Registra en access_logs
8. Si no autorizado:
   a. AI explica al visitante
   b. Registra intento en audit_logs
```

### 2️⃣ Flujo: WhatsApp Bidireccional (Reduce 40% llamadas)

```
CASO A: Visitante no registrado escribe
────────────────────────────────────────
Visitante → WhatsApp: "Hola, vengo a visitar a alguien"
        ↓
WhatsApp Service: Verifica si es residente → NO
        ↓
AI Security Agent (OpenRouter GPT-4o-mini):
  - Saluda profesionalmente
  - Pregunta a quien visita
  - Solicita nombre del visitante
  - Mantiene memoria conversacional
        ↓
WhatsApp al visitante: Respuesta bilingue automatica (ES/EN)


CASO B: Residente avisa visitante esperado
─────────────────────────────────────────
Residente → WhatsApp: "Viene Juan Perez en 10 minutos"
        ↓
WhatsApp Service: Verifica si es residente → SI
        ↓
Intent Parser (GPT-4):
  - Intent: authorize_visitor
  - Parse: nombre="Juan Perez", tiempo="10min"
  - Crea autorizacion temporal (2 horas)
        ↓
Backend → WhatsApp: "✅ Juan Perez autorizado hasta 16:30"
        ↓
[Visitante llega y llama interfon]
        ↓
AI reconoce nombre O Vision detecta placa registrada
        ↓
Backend: Match con autorizacion → Abrir automaticamente
        ↓
WhatsApp al residente: "🚪 Juan Perez ingreso a las 14:32 (foto)"

COSTO: $0 (sin llamada de voz) vs $0.50 (con llamada)


CASO C: Apertura remota
─────────────────────────
Residente → WhatsApp: "Abrir puerta"
        ↓
WhatsApp Service: Intent: open_gate
        ↓
Backend → Hikvision: Abrir puerta + Capturar foto
        ↓
WhatsApp al residente: "✅ Puerta abierta (foto adjunta)"
Backend → Registra en access_logs


CASO D: Reportar incidente
────────────────────────────
Residente → WhatsApp: "Reportar: Luz del estacionamiento fundida"
        ↓
WhatsApp Service: Intent: create_report
        ↓
Backend → Crea report en DB + Notifica admin
        ↓
WhatsApp al residente: "✅ Reporte #1234 creado. Admin notificado"


CASO E: Consulta general (Unknown Intent)
─────────────────────────────────────────
Residente → WhatsApp: "Cual es el horario de la piscina?"
        ↓
WhatsApp Service: Intent: unknown
        ↓
AI Security Agent: Responde naturalmente con contexto de residente
        ↓
WhatsApp al residente: Respuesta conversacional
```

### 3️⃣ Flujo: Detección Automática (Vision + Cache)

```
Vehículo se acerca a puerta
        ↓
Vision Service: Detecta placa "ABC-123"
        ↓
Backend (Redis cache): ¿Placa conocida?
        ↓
SÍ → Abrir automáticamente + Log + WhatsApp opcional
NO → Activar llamada de voz + Vision continúa analizando

COSTO: $0 (cache hit) + Vision processing (marginal)
```

### 4️⃣ Flujo: Edge Computing (Dashboard → Vision Service)

```
CONFIGURACION:
────────────────
Admin → Dashboard > Settings > Vision Service
        ↓
Ingresa URL: http://integrateccr.ddns.net:8001
        ↓
Click "Probar Conexion" → visionService.healthCheck()
        ↓
Si OK (verde) → Guardar en condominium.settings.vision_service_url


USO EN CAMARAS:
────────────────
Usuario → Dashboard > Camaras
        ↓
Dashboard verifica: condominium.settings.vision_service_url existe?
        ↓
SI → Banner verde "Edge Computing Activo"
   → Llamadas van directo a Vision Service (menor latencia)
   → Test camara: visionService.testCamera(url, credentials)
   → Snapshot: visionService.getSnapshot(url, channelId)
        ↓
NO → Banner rojo "Vision Service Offline"
   → Fallback a Backend API (mayor latencia)
   → Link a Configuracion para setup

BENEFICIO: Latencia ~50ms (local) vs ~500ms (cloud roundtrip)
```

## Comandos de Desarrollo

### Backend
```bash
cd services/backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python dev_server.py  # Auto-port 8000-8006
```

### Voice Service
```bash
cd services/voice-service
pip install -r requirements.txt
python main.py
```

### Vision Service (Edge Computing - FreePBX)
```bash
# Deployment en FreePBX (on-premise)
ssh root@172.20.20.1
cd /opt/agente-portero/services/vision-service
./deploy-freepbx.sh

# Ver logs
docker logs -f portero-vision

# Reiniciar
docker-compose -f docker-compose.freepbx.yml restart

# Test local
curl http://localhost:8001/health
```

### Vision Service (Desarrollo local)
```bash
cd services/vision-service
docker-compose up -d
```

### Dashboard
```bash
cd apps/dashboard
npm install
npm run dev  # Auto-port 3000-3006
```

## Convenciones de Codigo

### Python (Backend/Services)
- **Naming**: snake_case para variables/funciones
- **Classes**: PascalCase
- **Constants**: UPPER_SNAKE_CASE
- **Type hints**: Obligatorios en funciones publicas

### TypeScript (Dashboard)
- **Naming**: camelCase para variables/funciones
- **Components**: PascalCase
- **Files**: kebab-case.tsx

### Arquitectura Backend: Clean Architecture
```
services/backend/
├── api/                 # FastAPI routers
│   └── v1/
│       ├── agents.py
│       ├── access.py
│       ├── notifications.py
│       └── camera_events.py
├── application/         # Use cases, DTOs
│   ├── services/
│   └── schemas/
├── domain/              # Entities, interfaces
│   ├── models/
│   └── interfaces/
├── infrastructure/      # Implementations
│   ├── database/
│   ├── hikvision/
│   ├── asterisk/
│   └── whatsapp/
└── main.py
```

## Variables de Entorno

### Backend (.env)
```env
DATABASE_URL=postgresql://...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=xxx
JWT_SECRET=xxx
```

### Voice Service (.env)
```env
# Asterisk ARI
ASTERISK_ARI_URL=http://pbx:8088/ari
ASTERISK_ARI_USER=xxx
ASTERISK_ARI_PASSWORD=xxx

# OpenAI
OPENAI_API_KEY=xxx

# Backend
BACKEND_API_URL=http://localhost:8000

# Audio Tuning
AUDIO_SAMPLE_RATE=8000              # AudioSocket siempre usa 8kHz
NOISE_GATE_THRESHOLD=200            # RMS threshold (0=deshabilitado)
PLAYBACK_PREBUFFER_FRAMES=10        # Frames a prebuffer (200ms)
OUTPUT_AUDIO_QUEUE_MAXSIZE=1000     # ~20s de audio

# VAD Tuning
VAD_THRESHOLD=0.6                   # Sensibilidad (0.5-0.9)
VAD_PREFIX_PADDING_MS=300
VAD_SILENCE_DURATION_MS=800

# Voice
DEFAULT_VOICE=shimmer               # alloy, shimmer, coral, sage, echo, ash, ballad, verse
```

### Vision Service (.env) - Edge Computing en FreePBX
```env
# Camara Hikvision (red local del condominio)
HIKVISION_HOST=172.20.22.111
HIKVISION_PORT=80
HIKVISION_USER=admin
HIKVISION_PASSWORD=xxx

# Backend (para reportar eventos)
BACKEND_API_URL=https://api-portero.integratec-ia.com
```

> **Nota**: Ver `services/vision-service/.env.freepbx` para template completo

### WhatsApp Service (.env)
```env
# Evolution API Externa
EVOLUTION_API_URL=https://devevoapi.integratec-ia.com
EVOLUTION_API_KEY=xxx
EVOLUTION_INSTANCE=Sitnova_portero

# OpenAI/OpenRouter (para AI Agent)
OPENAI_API_KEY=xxx  # OpenRouter API key

# Backend
BACKEND_API_URL=http://localhost:8000
BACKEND_API_KEY=xxx

# Redis
REDIS_URL=redis://localhost:6379/0
```

### Dashboard (.env.local)
```env
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxx
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Testing Strategy

### Unit Tests
- Backend: pytest + httpx
- Dashboard: Jest + React Testing Library

### Integration Tests
- API endpoints con test database
- Voice service con mock ARI

### E2E Tests
- Playwright para dashboard flows

## Security Checklist

- [ ] Multi-tenant isolation (RLS en Supabase)
- [ ] JWT validation en todos los endpoints
- [ ] Audit logging de todas las acciones
- [ ] Rate limiting en API
- [ ] Validacion de input (Pydantic/Zod)
- [ ] HTTPS en produccion
- [ ] Secrets en variables de entorno

## No Hacer (Critical)

- NO exponer secrets en codigo
- NO permitir acceso cross-tenant
- NO omitir audit logs en acciones criticas
- NO hardcodear IPs de camaras/PBX
- NO usar `any` en TypeScript
- NO saltarse validacion de entrada
- NO hacer queries sin tenant_id filter

## AI Assistant Guidelines

### Prioridades de Desarrollo
1. **Voice Service** - ARI conectado, implementar audio streaming bidireccional
2. **WhatsApp Service** - Ya implementado con AI Security Agent bilingue
3. **Vision Service** - YOLO + OCR para placas/cedulas
4. **Dashboard** - UI multi-condominio

### Cuando Generar Codigo
- Incluir type hints/annotations
- Implementar tenant isolation
- Agregar audit logging
- Incluir error handling
- Seguir Clean Architecture

---

*Sistema de Guardia Virtual - Multi-tenant SaaS para Condominios*
