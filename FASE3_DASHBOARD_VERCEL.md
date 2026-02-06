# FASE 3: Deploy Dashboard en Vercel

## Pre-requisitos
- ✅ FASE 1 completada (Supabase configurado)
- ✅ FASE 2 completada (Backend y servicios en Portainer)
- ✅ Evolution API configurado y WhatsApp vinculado

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    Vercel (Dashboard)                        │
│                  apps/dashboard (Next.js 16)                 │
│                                                               │
│  - Multi-tenant UI                                           │
│  - Supabase Auth (login de usuarios)                        │
│  - API calls a Backend                                       │
│  - Real-time updates (Supabase Realtime)                    │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ├─────────────────────┐
                  │                     │
                  ▼                     ▼
        ┌──────────────────┐  ┌──────────────────┐
        │   Supabase       │  │  Backend API     │
        │   (Auth + DB)    │  │  (Contabo)       │
        └──────────────────┘  └──────────────────┘
```

## Paso 1: Preparar Variables de Entorno en Vercel

### 1.1 Crear proyecto en Vercel
```bash
cd apps/dashboard
vercel
```

### 1.2 Configurar variables de entorno

En Vercel Dashboard → Settings → Environment Variables, agregar:

```env
# Supabase (públicas - seguro exponerlas)
NEXT_PUBLIC_SUPABASE_URL=https://datrxcbcvlfhjivncddr.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRhdHJ4Y2JjdmxmaGppdm5jZGRyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc3NTQ4NTksImV4cCI6MjA4MzMzMDg1OX0.S_1WaOZC_jL9h5DCiWKwUN4w0tweKLOgNvV5tYVm-NQ

# Backend API
NEXT_PUBLIC_API_URL=https://api-portero.integratec-ia.com

# WhatsApp Service
NEXT_PUBLIC_WHATSAPP_URL=https://whatsapp-portero.integratec-ia.com

# Voice Service (cuando esté configurado)
NEXT_PUBLIC_VOICE_URL=https://voice-portero.integratec-ia.com

# Environment
NEXT_PUBLIC_ENVIRONMENT=production
```

## Paso 2: Build y Deploy

### 2.1 Deploy desde CLI
```bash
cd apps/dashboard
vercel --prod
```

### 2.2 O conectar con GitHub
1. En Vercel Dashboard → New Project
2. Import repository: `javierd009/agente-portero`
3. Root Directory: `apps/dashboard`
4. Framework Preset: Next.js
5. Deploy

## Paso 3: Configurar Dominio (Opcional)

Si quieres usar un dominio personalizado:

```
dashboard-portero.integratec-ia.com → Vercel Project
```

1. Vercel → Settings → Domains
2. Add Domain: `dashboard-portero.integratec-ia.com`
3. Configurar DNS:
   - Type: CNAME
   - Name: dashboard-portero
   - Value: cname.vercel-dns.com

## Paso 4: Verificar Dashboard

### 4.1 Acceder al Dashboard
- URL: `https://[tu-proyecto].vercel.app`
- O dominio custom si lo configuraste

### 4.2 Test de Login
1. Crear usuario de prueba en Supabase Auth
2. Login en el dashboard
3. Verificar que se carga correctamente

### 4.3 Verificar conexiones
- ✅ Dashboard → Supabase (Auth)
- ✅ Dashboard → Backend API
- ✅ Backend → Supabase (DB)
- ✅ Real-time updates funcionando

## Paso 5: Configurar Supabase Auth

### 5.1 Configurar URL del sitio
En Supabase Dashboard:
1. Authentication → URL Configuration
2. Site URL: `https://[tu-proyecto].vercel.app`
3. Redirect URLs:
   - `https://[tu-proyecto].vercel.app/auth/callback`
   - `http://localhost:3000/auth/callback` (desarrollo)

### 5.2 Crear usuarios iniciales
```sql
-- En Supabase SQL Editor
INSERT INTO auth.users (email, encrypted_password, email_confirmed_at)
VALUES ('admin@ejemplo.com', crypt('password123', gen_salt('bf')), now());

-- Asociar con condominio
INSERT INTO public.residents (condominium_id, name, email, role, is_active)
VALUES (
  (SELECT id FROM condominiums LIMIT 1),
  'Admin Usuario',
  'admin@ejemplo.com',
  'admin',
  true
);
```

## Paso 6: Tests Post-Deploy

### 6.1 Test de funcionalidades
- [ ] Login/Logout funciona
- [ ] Dashboard carga datos de Supabase
- [ ] Llamadas a Backend API funcionan
- [ ] Multi-tenant: selector de condominio funciona
- [ ] Panel de agentes muestra datos
- [ ] Logs de acceso se visualizan
- [ ] Notificaciones se muestran

### 6.2 Test de permisos
- [ ] Usuario admin puede ver todo
- [ ] Usuario resident solo ve su data
- [ ] Tenant isolation funciona (no se mezclan condominios)

## Paso 7: Monitoreo y Logs

### 7.1 Vercel Analytics
- Activar Vercel Analytics para monitorear performance
- Vercel → Analytics → Enable

### 7.2 Logs de errores
- Vercel → Functions → View logs
- Verificar que no hay errores en las API routes

## Troubleshooting

### Error: "Supabase client error"
- Verificar que las variables NEXT_PUBLIC_SUPABASE_* están correctas
- Verificar que SUPABASE_ANON_KEY es la pública (no service_role)

### Error: "Backend API not reachable"
- Verificar que https://api-portero.integratec-ia.com responde
- Verificar CORS en backend (debe permitir dominio de Vercel)

### Error: "Auth redirect failed"
- Verificar Site URL en Supabase
- Verificar Redirect URLs incluyen dominio de Vercel

## Configuración CORS en Backend

Asegurar que el backend acepta requests desde Vercel:

```python
# services/backend/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.vercel.app",
        "https://dashboard-portero.integratec-ia.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Próximos Pasos

Una vez el dashboard esté funcionando:

1. ✅ Configurar Asterisk/FreePBX para llamadas SIP
2. ✅ Configurar cámaras Hikvision
3. ✅ Deploy de Vision Service (YOLO + OCR)
4. ✅ Configurar notificaciones WhatsApp en tiempo real
5. ✅ Tests end-to-end de flujos completos

---

**Estado:** Listo para ejecutar cuando FASE 2 esté completada
