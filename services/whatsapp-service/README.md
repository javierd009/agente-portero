# WhatsApp Service - Agente Portero

Servicio de comunicacion bidireccional via WhatsApp usando Evolution API externa + AI Security Agent.

## 🎯 Proposito

**Para Residentes:**
- Autorizar visitantes esperados
- Abrir puerta remotamente
- Reportar incidentes
- Consultar logs de acceso

**Para Visitantes (no registrados):**
- Conversacion natural con AI Security Agent bilingue
- El agente pregunta a quien visitan y recopila informacion

**Impacto**: Reduce llamadas de voz en 40-50%, mejorando experiencia y reduciendo costos.

## Configuracion Actual

- **Evolution API Externa**: devevoapi.integratec-ia.com
- **Instancia**: Sitnova_portero
- **AI Agent**: GPT-4o-mini via OpenRouter (bilingue ES/EN)

## 🏗️ Arquitectura

```
FLUJO VISITANTE (no registrado):
─────────────────────────────────
Visitante WhatsApp → Evolution API Externa → Webhook
                                               ↓
                                    Verificar telefono → NO es residente
                                               ↓
                                    AI Security Agent (OpenRouter GPT-4o-mini)
                                               ↓
                                    Respuesta bilingue (ES/EN)


FLUJO RESIDENTE:
─────────────────
Residente WhatsApp → Evolution API Externa → Webhook
                                               ↓
                                    Verificar telefono → SI es residente
                                               ↓
                                    NLP Parser (GPT-4) → Intent detectado?
                                               ↓
                    ┌──────────────────────────┴──────────────────────────┐
                    ▼                                                      ▼
              Intent conocido                                      Intent desconocido
           (authorize, open_gate,                                          ↓
            create_report, query)                              AI Security Agent
                    ↓                                          (con contexto residente)
           Intent Handler → Backend API
                    ↓
           Accion + Respuesta estructurada
```

## 🚀 Setup

### 1. Instalar dependencias

```bash
cd services/whatsapp-service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales
```

### 3. Ejecutar servicio

```bash
python main.py
```

El servicio estará disponible en `http://localhost:8002`

## 📱 Configurar Evolution API

**Configuracion actual (Evolution API Externa):**

1. URL: `https://devevoapi.integratec-ia.com`
2. Instancia: `Sitnova_portero`
3. Webhook configurado para recibir mensajes

**Para nueva instalacion:**
1. Instalar Evolution API: https://doc.evolution-api.com
2. Crear instancia de WhatsApp Business
3. Configurar webhook:
   ```
   POST https://your-domain.com/webhook
   Events: messages.upsert
   ```

## 🤖 Flujos Soportados

### Para Visitantes (AI Security Agent)
```
Visitante → "Hola, vengo a visitar a alguien"
AI Agent  → "Bienvenido a Residencial Sitnova. Soy el sistema de seguridad virtual.
             ¿A quien viene a visitar y podria darme su nombre?"

Visitante → "Hi, I'm here to visit John"
AI Agent  → "Welcome to Residencial Sitnova. I'm the virtual security system.
             Could you please give me your name and John's unit number?"
```

### Para Residentes

**Autorizar visitante:**
```
Residente → "Viene Juan Perez en 10 minutos"
Sistema   → ✅ Juan Perez autorizado hasta 16:30
```

**Abrir puerta:**
```
Residente → "Abrir puerta"
Sistema   → ✅ Puerta abierta (foto adjunta)
```

**Reportar incidente:**
```
Residente → "Reportar: luz fundida en estacionamiento"
Sistema   → ✅ Reporte #1234 creado. Admin notificado
```

**Consultar logs:**
```
Residente → "¿Quien vino hoy?"
Sistema   → 📋 Registros de acceso (today)
            - 14:32 - Juan Perez (visitor_entry)
            - 16:10 - Uber delivery (visitor_entry)
```

**Consulta general (AI Agent):**
```
Residente → "¿Cual es el horario de la piscina?"
AI Agent  → (respuesta conversacional con contexto del residente)
```

## 🧪 Testing

### Health check
```bash
curl http://localhost:8002/health
```

### Enviar mensaje de prueba
```bash
curl -X POST http://localhost:8002/send-message \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "5215512345678",
    "message": "Hola desde Agente Portero"
  }'
```

## 🔧 Endpoints

- `GET /health` - Health check
- `POST /webhook` - Evolution API webhook (llamado por Evolution)
- `POST /send-message` - Enviar mensaje programáticamente
- `GET /docs` - Swagger documentation

## 📊 Monitoring

Logs estructurados en JSON:
```json
{
  "event": "message_received",
  "phone": "5215512345678",
  "intent": "authorize_visitor",
  "timestamp": "2025-01-06T19:30:00Z"
}
```

## 🔐 Security

- Verificación de residente en backend
- WhatsApp números registrados únicamente
- Rate limiting (TODO)
- Audit logging de todas las acciones

## 💰 Costos Estimados

- **GPT-4 NLP (intent parsing)**: ~$0.01 por mensaje
- **GPT-4o-mini (AI Agent via OpenRouter)**: ~$0.0015 por mensaje
- **Evolution API**: Gratis (self-hosted) o $20-50/mes (cloud)
- **Total**: ~$30-80/mes para 50 casas

vs

- **Llamadas OpenAI Realtime ahorradas**: $200-300/mes

**Ahorro neto: ~$150-250/mes**

## 📁 Archivos Principales

| Archivo | Descripcion |
|---------|-------------|
| `main.py` | FastAPI server + webhook endpoint |
| `webhook_handler.py` | Procesa mensajes, enruta visitantes/residentes |
| `security_agent.py` | AI Security Agent bilingue (OpenRouter) |
| `nlp_parser.py` | Intent parsing con GPT-4 |
| `evolution_client.py` | Cliente para Evolution API |
| `config.py` | Configuracion del servicio |
