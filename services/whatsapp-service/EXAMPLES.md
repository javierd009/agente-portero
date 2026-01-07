# Ejemplos de Uso - WhatsApp Service

## 📱 Flujos Completos de Usuario

### Caso 1: Residente Autoriza Visitante

```
13:45 - Residente Juan (casa 42)
─────────────────────────────────
Juan → WhatsApp: "Viene mi hermano Pedro García en 15 minutos en un auto rojo"

Sistema (GPT-4 parsea):
{
  "intent": "authorize_visitor",
  "visitor_name": "Pedro García",
  "expected_time": "15 minutos",
  "notes": "auto rojo"
}

Sistema → Backend API:
POST /api/v1/visitors/authorize
{
  "resident_id": "uuid-juan",
  "visitor_name": "Pedro García",
  "valid_until": "2025-01-06T16:00:00Z",
  "notes": "auto rojo, autorizado via WhatsApp"
}

Sistema → WhatsApp Juan:
"✅ Visitante autorizado

👤 Nombre: Pedro García
🚗 Placa: No especificada
⏰ Válido hasta: 06/01 16:00

Cuando llegue, la puerta se abrirá automáticamente y te enviaré una notificación."

14:05 - Pedro llega al intercom
────────────────────────────────
Pedro → Llama al intercom

Voice Service → OpenAI Realtime:
AI: "Bienvenido, ¿a quién busca?"
Pedro: "Pedro García, vengo a ver a Juan de la casa 42"

AI → Backend: ¿Está autorizado "Pedro García" para casa 42?
Backend → Cache: ✅ Sí (autorizado hasta 16:00)

Backend → Hikvision: Abrir puerta principal
Backend → WhatsApp Juan:
"🚪 Pedro García ingresó a las 14:05 (foto adjunta)"

COSTO: $0 (sin llamada larga, solo verificación)
```

---

### Caso 2: Uber Delivery Sin Aviso Previo

```
17:30 - Uber llega sin aviso
────────────────────────────
Uber → Llama al intercom

Voice Service → OpenAI Realtime:
AI: "Bienvenido, ¿a quién busca?"
Uber: "Tengo un pedido para la casa 12"

AI → Backend: ¿Hay autorización para casa 12?
Backend: ❌ No hay autorizaciones activas

Backend → WhatsApp Residente (casa 12):
"🚗 Visitante en puerta

📦 Tipo: Delivery
📍 Destino: Casa 12
⏰ Hora: 17:30

¿Autorizar entrada?
[✅ Sí] [❌ No]"

Residente → Tap "✅ Sí"

Backend → Hikvision: Abrir puerta
Backend → WhatsApp Residente:
"✅ Puerta abierta. Delivery autorizado (foto adjunta)"

Voice Service → AI:
AI: "La puerta se está abriendo. Bienvenido."

COSTO: ~$0.30 (llamada corta 30 seg + WhatsApp)
```

---

### Caso 3: Apertura Remota (Residente Olvidó Llaves)

```
20:15 - Residente María llega sin llaves
─────────────────────────────────────────
María → WhatsApp: "Abrir puerta urgente"

Sistema (GPT-4 parsea):
{
  "intent": "open_gate",
  "urgency": "urgent"
}

Sistema → Backend:
POST /api/v1/gates/open
{
  "resident_id": "uuid-maria",
  "gate_name": "main",
  "method": "whatsapp_remote"
}

Backend → Hikvision: Abrir puerta + Capturar foto
Backend → Access Log: Registrar evento

Sistema → WhatsApp María:
"✅ Puerta main abierta

🕐 Hora: 20:15:32
👤 Solicitado por: María González

📸 Captura del momento (foto adjunta)"

COSTO: $0 (solo GPT-4 parsing ~$0.01)
```

---

### Caso 4: Reporte de Mantenimiento

```
09:00 - Residente detecta problema
───────────────────────────────────
Residente → WhatsApp: "Reportar: la luz del pasillo 3 está fundida"

Sistema (GPT-4 parsea):
{
  "intent": "create_report",
  "report_type": "maintenance",
  "description": "luz del pasillo 3 está fundida",
  "location": "pasillo 3",
  "urgency": "normal"
}

Sistema → Backend:
POST /api/v1/reports
{
  "resident_id": "uuid",
  "report_type": "maintenance",
  "description": "luz del pasillo 3 está fundida",
  "location": "pasillo 3",
  "urgency": "normal"
}

Backend → Notifica admin del condominio

Sistema → WhatsApp Residente:
"✅ Reporte creado

📋 Folio: #a7f3c21e
📝 Tipo: maintenance
📍 Ubicación: pasillo 3
⚠️ Urgencia: normal

El administrador ha sido notificado."

Backend → WhatsApp Admin:
"📋 Nuevo reporte

🏢 Condominio: Residencial del Valle
👤 Reportado por: Juan Pérez (Casa 42)
📝 Problema: luz del pasillo 3 está fundida
⏰ Hora: 09:00

Ver detalles: https://dashboard.com/reports/a7f3c21e"

COSTO: $0.01 (GPT-4 parsing)
```

---

### Caso 5: Consulta de Logs

```
18:00 - Residente quiere saber quién vino
──────────────────────────────────────────
Residente → WhatsApp: "¿Quién vino hoy a mi casa?"

Sistema (GPT-4 parsea):
{
  "intent": "query_logs",
  "query_type": "today"
}

Sistema → Backend:
GET /api/v1/access/logs?resident_id=uuid&query_type=today

Backend → Responde con logs del día:
[
  {
    "visitor_name": "Pedro García",
    "event_type": "visitor_entry",
    "created_at": "2025-01-06T14:05:00Z"
  },
  {
    "visitor_name": "Uber delivery",
    "event_type": "visitor_entry",
    "created_at": "2025-01-06T17:30:00Z"
  }
]

Sistema → WhatsApp Residente:
"📋 Registros de acceso (today)

• 06/01 14:05 - Pedro García (visitor_entry)
• 06/01 17:30 - Uber delivery (visitor_entry)"

COSTO: $0.01 (GPT-4 parsing)
```

---

## 📊 Comparativa de Costos: Con vs Sin WhatsApp

### Escenario: 50 casas, 100 eventos/día durante 30 días

**SIN WhatsApp (Solo voz):**
```
100 eventos/día × 30 días = 3,000 eventos/mes
70% requieren llamada = 2,100 llamadas
Promedio 60 seg/llamada = 2,100 minutos

Costo OpenAI Realtime:
- Input: 2,100 × $0.06 = $126
- Output: 2,100 × $0.24 = $504
TOTAL: $630/mes
```

**CON WhatsApp:**
```
3,000 eventos/mes:
- 40% autorizados por WhatsApp (no llamada) = 1,200 eventos → $0
- 30% detectados por placa (no llamada) = 900 eventos → $0
- 30% requieren llamada = 900 eventos → 900 minutos

Costo OpenAI Realtime (solo 900 min):
- Input: 900 × $0.06 = $54
- Output: 900 × $0.24 = $216
Subtotal: $270

Costo WhatsApp (1,200 mensajes):
- GPT-4 parsing: 1,200 × $0.01 = $12
- Evolution API: $30/mes (self-hosted)
Subtotal: $42

TOTAL: $312/mes

AHORRO: $318/mes (50.5%) 🎉
```

---

## 🎯 Métricas de Éxito

### KPIs a medir:
- % de eventos resueltos sin llamada
- Tiempo promedio de autorización
- Satisfacción de residentes (NPS)
- Costo por evento procesado
- Uptime del servicio

### Targets:
- ✅ 40%+ eventos sin llamada (WhatsApp)
- ✅ 30%+ eventos por detección automática
- ✅ <30% eventos requieren llamada
- ✅ <10 seg tiempo de respuesta WhatsApp
- ✅ 99.9% uptime
