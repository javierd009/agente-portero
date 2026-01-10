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

## Tech Stack & Architecture

### Monorepo Structure
```
agente_portero/
├── services/
│   ├── backend/           # FastAPI + SQLModel (API central, orchestrator)
│   ├── voice-service/     # SIP ↔ OpenAI Realtime (llamadas de voz)
│   ├── whatsapp-service/  # Evolution API ↔ NLP (mensajes bidireccionales)
│   └── vision-service/    # YOLO + OCR + Facial (detección automática)
├── apps/
│   └── dashboard/         # Next.js 15 (multi-tenant UI)
├── supabase/
│   └── migrations/        # SQL migrations
└── docs/                  # Arquitectura y workflows
```

### Backend (FastAPI)
- **Runtime**: Python 3.11
- **Framework**: FastAPI 0.109+
- **ORM**: SQLModel (SQLAlchemy + Pydantic)
- **Database**: PostgreSQL (Supabase)
- **Auth**: Supabase Auth + JWT

### Voice Service (PENDIENTE - NAT ISSUE)
- **PBX**: Asterisk/FreePBX (ARI/AMI)
- **AI**: OpenAI Realtime API (conversacion natural)
- **Voces**: OpenAI voices (fallback ElevenLabs para personalizacion)
- **Protocol**: SIP/WebSocket
- **Latencia**: <500ms (critico para experiencia natural)
- **Estado**: Pendiente por problemas de NAT con Asterisk ARI

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

### Vision Service (Edge)
- **Detection**: YOLOv8/v10
- **OCR**: PaddleOCR
- **Camera**: Hikvision ISAPI
- **Runtime**: Docker + CUDA

### Dashboard (Next.js)
- **Framework**: Next.js 16 (App Router)
- **Styling**: Tailwind CSS + shadcn/ui
- **State**: Zustand + TanStack Query
- **Auth**: Supabase Auth

## Arquitectura Multi-Tenant (Actualizada)

```
┌──────────────────────────────────────────────────────────────┐
│                      Dashboard (Next.js)                      │
│   Gestión multi-condominio, analytics, configuración         │
└─────────────────────────────┬────────────────────────────────┘
                              │ REST API + WebSocket
┌─────────────────────────────▼────────────────────────────────┐
│                    Backend (FastAPI)                          │
│  Orchestrator central: autorizaciones, audit, multi-tenant   │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐    │
│  │ Visitor │  │ Access  │  │  Gate   │  │   Reports   │    │
│  │ Manager │  │ Control │  │ Control │  │   System    │    │
│  └─────────┘  └─────────┘  └─────────┘  └─────────────┘    │
└────────┬──────────┬──────────┬──────────┬──────────┬─────────┘
         │          │          │          │          │
    ┌────▼────┐ ┌──▼────┐ ┌───▼──────┐ ┌─▼───────┐ │
    │ Voice   │ │WhatsApp│ │  Vision  │ │Supabase │ │
    │ Service │ │Service │ │ Service  │ │   DB    │ │
    └────┬────┘ └──┬─────┘ └────┬─────┘ └─────────┘ │
         │         │            │                    │
    ┌────▼────┐ ┌──▼────────┐ ┌▼─────────┐    ┌────▼─────┐
    │Asterisk │ │ Evolution │ │Hikvision │    │  Redis   │
    │ FreePBX │ │    API    │ │ Cameras  │    │  Cache   │
    └─────────┘ └───────────┘ └──────────┘    └──────────┘

FLUJOS PRINCIPALES:
1. Visitante llama → Voice Service → Backend → Decision
2. Residente WhatsApp → WhatsApp Service → Backend → Action
3. Cámara detecta placa → Vision Service → Backend → Auto-open
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

### Vision Service (Docker)
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
ASTERISK_ARI_URL=http://pbx:8088/ari
ASTERISK_ARI_USER=xxx
ASTERISK_ARI_PASSWORD=xxx
OPENAI_API_KEY=xxx
BACKEND_API_URL=http://localhost:8000
```

### Vision Service (.env)
```env
HIKVISION_HOST=192.168.1.100
HIKVISION_USER=admin
HIKVISION_PASSWORD=xxx
BACKEND_API_URL=http://localhost:8000
```

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
1. **Voice Service** - Resolver NAT issue con Asterisk ARI (bloqueado)
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
