# Backend API Endpoints - Agente Portero

Documentación completa de todos los endpoints disponibles.

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
La mayoría de endpoints requieren header `x-tenant-id` para multi-tenant isolation:
```
x-tenant-id: {uuid-del-condominio}
```

---

## 🏢 **Condominiums**

### `GET /condominiums`
Lista todos los condominios

### `POST /condominiums`
Crea nuevo condominio

### `GET /condominiums/{id}`
Obtiene condominio específico

### `PATCH /condominiums/{id}`
Actualiza condominio

---

## 👤 **Residents**

### `GET /residents`
Lista residentes del condominio
- Query params: `unit`, `skip`, `limit`

### `GET /residents/by-phone/{phone}` ⭐ **NUEVO**
Obtiene residente por teléfono WhatsApp (para WhatsApp Service)
- **No requiere x-tenant-id**
- Usado por WhatsApp Service para identificar al usuario

### `POST /residents`
Crea nuevo residente

### `GET /residents/{id}`
Obtiene residente específico

### `PATCH /residents/{id}`
Actualiza residente

### `DELETE /residents/{id}`
Elimina residente

---

## 🚶 **Visitors** ⭐ **NUEVO**

### `POST /visitors/authorize` ⭐ **CRÍTICO**
Autoriza visitante temporalmente (desde WhatsApp)
```json
{
  "condominium_id": "uuid",
  "resident_id": "uuid",
  "visitor_name": "Juan Pérez",
  "vehicle_plate": "ABC-123",
  "valid_until": "2025-01-06T18:00:00Z",
  "notes": "Autorizado via WhatsApp"
}
```
**Returns**: Visitor object with status "approved"

### `GET /visitors/check-authorization/{visitor_name}`
Verifica si visitante está autorizado (para Voice Service)
- Query params: `resident_id`

### `GET /visitors`
Lista visitantes
- Query params: `status`, `resident_id`, `skip`, `limit`

### `POST /visitors`
Crea nuevo visitante

### `GET /visitors/{id}`
Obtiene visitante específico

### `PATCH /visitors/{id}`
Actualiza visitante

### `DELETE /visitors/{id}`
Elimina visitante

---

## 📋 **Reports** ⭐ **NUEVO**

### `POST /reports`
Crea nuevo reporte (incidente/mantenimiento)
```json
{
  "condominium_id": "uuid",
  "resident_id": "uuid",
  "report_type": "maintenance",  // maintenance, security, noise, cleaning, other
  "title": "Luz fundida",
  "description": "La luz del pasillo 3 está fundida",
  "location": "Pasillo 3",
  "urgency": "normal",  // low, normal, high, urgent
  "source": "whatsapp"  // web, whatsapp, voice, email
}
```

### `GET /reports`
Lista reportes
- Query params: `status`, `report_type`, `resident_id`, `skip`, `limit`

### `GET /reports/{id}`
Obtiene reporte específico

### `PATCH /reports/{id}`
Actualiza reporte (cambiar status, asignar, resolver)

### `DELETE /reports/{id}`
Elimina reporte

### `GET /reports/stats/summary`
Obtiene estadísticas de reportes
```json
{
  "total": 42,
  "pending": 12,
  "in_progress": 8,
  "resolved": 22,
  "by_status": {...},
  "by_type": {...},
  "by_urgency": {...}
}
```

---

## 🚪 **Access Logs**

### `GET /access/logs` ⭐ **ACTUALIZADO**
Lista logs de acceso con filtros mejorados
- Query params:
  - `access_type`: entry, exit, denied
  - `resident_id`: filtrar por residente
  - `visitor_name`: buscar por nombre
  - `query_type`: **today, yesterday, week** ⭐ (para WhatsApp)
  - `start_date`, `end_date`
  - `skip`, `limit`

### `POST /access/logs`
Crea log de acceso

### `GET /access/residents`
Lista residentes (alias)

### `POST /access/residents`
Crea residente (alias)

### `GET /access/residents/{id}`
Obtiene residente (alias)

### `PATCH /access/residents/{id}`
Actualiza residente (alias)

### `GET /access/visitors`
Lista visitantes (alias)

### `POST /access/visitors`
Crea visitante (alias)

### `GET /access/visitors/check`
Verifica autorización de visitante

---

## 🤖 **Agents**

### `GET /agents`
Lista agentes AI del condominio

### `POST /agents`
Crea nuevo agente

### `GET /agents/{id}`
Obtiene agente específico

### `PATCH /agents/{id}`
Actualiza agente

---

## 📱 **Notifications**

### `GET /notifications`
Lista notificaciones

### `POST /notifications`
Crea notificación

### `GET /notifications/{id}`
Obtiene notificación específica

---

## 📹 **Camera Events**

### `GET /camera-events`
Lista eventos de cámara

### `POST /camera-events`
Crea evento de cámara

---

## 🚧 **Gates**

### `POST /gates/open`
Abre puerta/portón
```json
{
  "condominium_id": "uuid",
  "resident_id": "uuid",
  "gate_name": "main",  // main, pedestrian, parking
  "method": "whatsapp_remote"
}
```

---

## 🔐 **Health Check**

### `GET /health`
Verifica estado del servicio
```json
{
  "status": "healthy",
  "service": "agente-portero-backend"
}
```

### `GET /`
Info del API
```json
{
  "message": "Agente Portero API",
  "docs": "/docs"
}
```

---

## 📚 **Swagger Documentation**

Visita `/docs` para documentación interactiva completa con todos los schemas.

---

## 🔗 **Integración con WhatsApp Service**

El WhatsApp Service usa estos endpoints:

1. **Identificar residente**: `GET /residents/by-phone/{phone}`
2. **Autorizar visitante**: `POST /visitors/authorize`
3. **Abrir puerta**: `POST /gates/open`
4. **Crear reporte**: `POST /reports`
5. **Consultar logs**: `GET /access/logs?query_type=today&resident_id=xxx`

---

## 🧪 **Testing con cURL**

### Autorizar visitante (WhatsApp)
```bash
curl -X POST http://localhost:8000/api/v1/visitors/authorize \
  -H "Content-Type: application/json" \
  -d '{
    "condominium_id": "uuid-here",
    "resident_id": "uuid-here",
    "visitor_name": "Juan Pérez",
    "vehicle_plate": "ABC-123",
    "notes": "Test desde WhatsApp"
  }'
```

### Consultar logs de hoy
```bash
curl "http://localhost:8000/api/v1/access/logs?query_type=today" \
  -H "x-tenant-id: uuid-here"
```

### Crear reporte
```bash
curl -X POST http://localhost:8000/api/v1/reports \
  -H "Content-Type: application/json" \
  -d '{
    "condominium_id": "uuid-here",
    "resident_id": "uuid-here",
    "report_type": "maintenance",
    "title": "Luz fundida",
    "description": "Pasillo 3",
    "urgency": "normal",
    "source": "whatsapp"
  }'
```
