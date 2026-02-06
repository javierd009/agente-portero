# Dashboard - Agente Portero

**Interface de administración multi-tenant para el sistema Agente Portero**

Dashboard web moderno construido con Next.js 15, React 19, TypeScript, Tailwind CSS y shadcn/ui.

---

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Tech Stack](#-tech-stack)
- [Instalación](#-instalación)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Páginas Implementadas](#-páginas-implementadas)
- [Uso](#-uso)
- [Configuración](#-configuración)
- [Desarrollo](#-desarrollo)

---

## ✨ Características

### Funcionalidades Principales

✅ **Dashboard Principal**
- Métricas en tiempo real (residentes, visitantes, accesos, placas)
- Logs de acceso recientes
- Detección de placas por cámaras
- Gráficos y estadísticas

✅ **Gestión de Reportes**
- Lista completa de reportes de mantenimiento/seguridad
- Filtros por estado y tipo
- Estadísticas de reportes
- Actualización de estado en tiempo real
- Detalles completos de cada reporte

✅ **Gestión de Residentes**
- Listado de todos los residentes
- Búsqueda por unidad
- Información de contacto (teléfono, email, WhatsApp)
- Visitantes autorizados por residente

✅ **Gestión de Visitantes**
- Registro de visitantes
- Estado de autorización
- Historial de visitas
- Vinculación con residentes

✅ **Logs de Acceso**
- Registro completo de entradas/salidas
- Filtros por fecha y tipo de evento
- Información de autorización
- Snapshots de cámaras

✅ **Configuración de Agentes**
- Configuración de agentes de voz
- Prompts personalizables
- Settings de voz y lenguaje

✅ **Sistema de Notificaciones**
- Historial de notificaciones enviadas
- Estado de entrega
- Canales (WhatsApp, SMS, email)

### Características Técnicas

- ✅ **Multi-tenant**: Aislamiento completo de datos por condominio
- ✅ **Real-time**: Actualización automática cada 30 segundos
- ✅ **Responsive**: Diseño adaptable a móvil, tablet y desktop
- ✅ **Dark Mode Ready**: Preparado para modo oscuro
- ✅ **Type-safe**: TypeScript en todo el proyecto
- ✅ **Optimizado**: React Server Components donde es posible
- ✅ **Accesible**: Componentes accesibles con Radix UI

---

## 🛠️ Tech Stack

| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| **Next.js** | 15.1.0 | Framework React con App Router |
| **React** | 19.0.0 | UI library |
| **TypeScript** | 5.7.0 | Type safety |
| **Tailwind CSS** | 3.4.0 | Utility-first CSS |
| **shadcn/ui** | Latest | Component library (Radix UI) |
| **TanStack Query** | 5.60.0 | Data fetching & caching |
| **Zustand** | 5.0.0 | State management |
| **Recharts** | 2.14.0 | Charts & graphs |
| **Supabase** | 2.45.0 | Auth & database |
| **Sonner** | 1.7.0 | Toast notifications |
| **Lucide React** | 0.460.0 | Icons |

---

## 🚀 Instalación

### Prerequisitos

- Node.js 18+
- npm o yarn
- Backend API corriendo en `http://localhost:8000`

### Setup

```bash
# 1. Navegar al directorio del dashboard
cd apps/dashboard

# 2. Instalar dependencias
npm install

# 3. Configurar variables de entorno
cp .env.example .env.local

# 4. Editar .env.local con tus credenciales
nano .env.local
```

### Variables de Entorno

```env
# Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Supabase (opcional, para auth)
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### Ejecutar en Desarrollo

```bash
npm run dev
```

El dashboard estará disponible en `http://localhost:3000`

### Build para Producción

```bash
npm run build
npm start
```

---

## 📁 Estructura del Proyecto

```
apps/dashboard/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── (auth)/            # Rutas de autenticación
│   │   │   └── login/
│   │   ├── (dashboard)/       # Rutas del dashboard
│   │   │   └── dashboard/
│   │   │       ├── page.tsx              # Dashboard principal
│   │   │       ├── reports/page.tsx      # Reportes
│   │   │       ├── residents/page.tsx    # Residentes
│   │   │       ├── visitors/page.tsx     # Visitantes
│   │   │       ├── access-logs/page.tsx  # Logs de acceso
│   │   │       ├── agents/page.tsx       # Agentes de voz
│   │   │       ├── cameras/page.tsx      # Cámaras
│   │   │       ├── notifications/page.tsx # Notificaciones
│   │   │       └── settings/page.tsx     # Configuración
│   │   ├── api/               # API routes (auth, etc.)
│   │   └── layout.tsx         # Root layout
│   │
│   ├── components/
│   │   └── ui/                # shadcn/ui components
│   │       ├── button.tsx
│   │       ├── card.tsx
│   │       ├── input.tsx
│   │       ├── badge.tsx
│   │       ├── select.tsx
│   │       └── ...
│   │
│   ├── lib/
│   │   ├── api.ts             # API client + TypeScript types
│   │   └── utils.ts           # Utility functions
│   │
│   └── store/
│       └── tenant.ts          # Zustand store (multi-tenant)
│
├── public/                    # Static assets
├── next.config.ts             # Next.js config
├── tailwind.config.ts         # Tailwind config
├── tsconfig.json              # TypeScript config
└── package.json
```

---

## 📄 Páginas Implementadas

### 1. Dashboard Principal (`/dashboard`)

**Métricas mostradas:**
- Total de residentes
- Visitantes hoy
- Accesos hoy
- Placas detectadas (últimos 5 min)

**Secciones:**
- Accesos recientes con tipo (entrada/salida/denegado)
- Placas detectadas por cámaras en tiempo real

**Auto-refresh**: Cada 30 segundos

### 2. Reportes (`/dashboard/reports`)

**Funcionalidades:**
- Lista completa de reportes con estado
- Filtros por:
  - Estado: Pendiente, En Progreso, Resuelto, Cerrado
  - Tipo: Mantenimiento, Seguridad, Ruido, Limpieza, Otro
- Estadísticas:
  - Total de reportes
  - Pendientes
  - En progreso
  - Resueltos
- Acciones:
  - Comenzar reporte (Pendiente → En Progreso)
  - Marcar como resuelto (En Progreso → Resuelto)
  - Ver detalles completos
- Modal de detalles con:
  - Información completa
  - Notas de resolución
  - Metadata (fuente, ubicación, urgencia)

### 3. Residentes (`/dashboard/residents`)

**Funcionalidades:**
- Lista de todos los residentes del condominio
- Información por residente:
  - Nombre
  - Unidad
  - Teléfono / Email / WhatsApp
  - Visitantes autorizados
  - Estado (activo/inactivo)
- Filtro por unidad

### 4. Visitantes (`/dashboard/visitors`)

**Funcionalidades:**
- Registro de visitantes
- Estado de autorización
- Vinculación con residente
- Historial de visitas (entrada/salida)
- Filtros por estado

### 5. Logs de Acceso (`/dashboard/access-logs`)

**Funcionalidades:**
- Registro completo de entradas y salidas
- Información mostrada:
  - Tipo de evento
  - Punto de acceso
  - Nombre del visitante o residente
  - Placa del vehículo
  - Método de autorización
  - Timestamp
- Filtros avanzados:
  - Por tipo de evento
  - Por fecha (hoy, ayer, semana)
  - Por residente
  - Por nombre de visitante

### 6. Agentes (`/dashboard/agents`)

**Funcionalidades:**
- Configuración de agentes de voz
- Edición de prompts del sistema
- Configuración de voz (alloy, echo, fable, etc.)
- Configuración de idioma
- Settings avanzados

### 7. Cámaras (`/dashboard/cameras`)

**Funcionalidades:**
- Eventos de cámaras
- Detección de placas
- Snapshots de eventos
- Estadísticas por cámara

### 8. Notificaciones (`/dashboard/notifications`)

**Funcionalidades:**
- Historial de notificaciones enviadas
- Estado de entrega
- Canales (WhatsApp, SMS, Email)
- Residente destinatario

### 9. Configuración (`/dashboard/settings`)

**Funcionalidades:**
- Configuración del condominio
- Ajustes generales
- Integración con sistemas externos
- API keys

---

## 💻 Uso

### Multi-Tenant

El dashboard soporta múltiples condominios en una sola instalación. El tenant actual se selecciona mediante:

```typescript
import { useTenantStore } from '@/store/tenant'

const { currentTenant } = useTenantStore()
const tenantId = currentTenant?.id
```

Todas las llamadas al API incluyen automáticamente el header `X-Tenant-ID`.

### Fetching de Datos

El dashboard usa **TanStack Query** para data fetching:

```typescript
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'

const { data, isLoading, error } = useQuery({
  queryKey: ['reports', tenantId],
  queryFn: () => apiClient.getReports(tenantId),
  enabled: !!tenantId,
  refetchInterval: 30000, // Auto-refresh cada 30s
})
```

### Actualización de Datos

Para actualizar datos usar **mutations**:

```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query'

const queryClient = useQueryClient()

const mutation = useMutation({
  mutationFn: (data) => apiClient.updateReport(tenantId, reportId, data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['reports'] })
    toast.success('Reporte actualizado')
  }
})
```

### Notificaciones

Usar **Sonner** para toast notifications:

```typescript
import { toast } from 'sonner'

toast.success('Operación exitosa')
toast.error('Hubo un error')
toast.info('Información importante')
```

---

## ⚙️ Configuración

### Agregar Nueva Página

1. Crear archivo en `src/app/(dashboard)/dashboard/mi-pagina/page.tsx`:

```typescript
'use client'

export default function MiPaginaPage() {
  return (
    <div>
      <h1>Mi Nueva Página</h1>
    </div>
  )
}
```

2. Agregar ruta al navigation (si existe un sidebar/navbar component)

### Agregar Nuevo Endpoint al API Client

Editar `src/lib/api.ts`:

```typescript
export const apiClient = {
  // ... otros endpoints

  getMiNuevoEndpoint: (tenantId: string) =>
    api<MiTipo[]>('/api/v1/mi-endpoint', { tenantId }),
}

export interface MiTipo {
  id: string
  name: string
  // ...
}
```

### Agregar Componente UI

Usar shadcn/ui CLI (recomendado):

```bash
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add table
npx shadcn-ui@latest add dropdown-menu
```

O crear manualmente en `src/components/ui/`

---

## 🔧 Desarrollo

### Scripts Disponibles

```bash
# Desarrollo
npm run dev

# Build para producción
npm run build

# Iniciar producción
npm start

# Linter
npm run lint

# Type-check
npm run type-check
```

### Testing

```bash
# Ejecutar tests (cuando estén implementados)
npm test
```

### Hot Reload

Next.js incluye hot reload por defecto. Los cambios se reflejan automáticamente en el navegador.

---

## 🎨 Personalización

### Colores y Tema

Editar `tailwind.config.ts` para cambiar el tema:

```typescript
export default {
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        // ...
      },
    },
  },
}
```

### Fuentes

Editar `src/app/layout.tsx` para cambiar fuentes:

```typescript
import { Inter } from 'next/font/google'

const inter = Inter({ subsets: ['latin'] })
```

---

## 📊 Performance

### Optimizaciones Implementadas

- ✅ React Server Components donde es posible
- ✅ Lazy loading de componentes pesados
- ✅ Caching con TanStack Query
- ✅ Imágenes optimizadas con next/image
- ✅ Code splitting automático

### Métricas Objetivo

- **First Contentful Paint**: < 1.5s
- **Time to Interactive**: < 3s
- **Lighthouse Score**: > 90

---

## 🚀 Deploy

### Vercel (Recomendado)

```bash
# 1. Instalar Vercel CLI
npm i -g vercel

# 2. Deploy
vercel
```

### Docker

```bash
# Build imagen
docker build -t agente-portero-dashboard .

# Run contenedor
docker run -p 3000:3000 agente-portero-dashboard
```

---

## 🐛 Troubleshooting

### "Cannot connect to API"

**Problema**: El dashboard no puede conectarse al backend.

**Solución**:
1. Verificar que el backend está corriendo en `http://localhost:8000`
2. Verificar `NEXT_PUBLIC_API_URL` en `.env.local`
3. Verificar CORS en el backend (debe permitir `http://localhost:3000`)

### "Tenant ID not found"

**Problema**: No se ha seleccionado un condominio.

**Solución**:
1. Implementar selector de tenant en el UI
2. O establecer tenant por defecto en el store

### "Build errors"

**Problema**: Errores de TypeScript al hacer build.

**Solución**:
```bash
# Ver errores específicos
npm run type-check

# Fix automático de algunos errores
npm run lint --fix
```

---

## 📝 Notas

- El dashboard requiere que el Backend API esté corriendo
- Los datos se obtienen en tiempo real desde el backend
- El sistema es completamente type-safe con TypeScript
- Todos los componentes UI son accesibles (WAI-ARIA)

---

## 🔗 Links Útiles

- [Next.js Docs](https://nextjs.org/docs)
- [shadcn/ui Components](https://ui.shadcn.com)
- [TanStack Query](https://tanstack.com/query/latest)
- [Tailwind CSS](https://tailwindcss.com/docs)

---

**Dashboard v1.0** - Parte del sistema Agente Portero

Para más información del proyecto completo, ver: [Project README](../../README.md)
