# WhatsApp Service - Agente Portero

Servicio de comunicación bidireccional vía WhatsApp usando Evolution API.

## 🎯 Propósito

Permite a los residentes:
- ✅ Autorizar visitantes esperados
- 🚪 Abrir puerta remotamente
- 📝 Reportar incidentes
- 📋 Consultar logs de acceso

**Impacto**: Reduce llamadas de voz en 40-50%, mejorando experiencia y reduciendo costos.

## 🏗️ Arquitectura

```
Residente WhatsApp → Evolution API → Webhook → NLP Parser (GPT-4)
                                        ↓
                            Intent Handler → Backend API
                                        ↓
                            Acción (abrir puerta, crear log, etc.)
                                        ↓
                            Respuesta → WhatsApp al residente
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

1. Instalar Evolution API: https://doc.evolution-api.com
2. Crear instancia de WhatsApp Business
3. Configurar webhook:
   ```
   POST https://your-domain.com/webhook
   Events: messages.upsert
   ```

## 🤖 Comandos Soportados

### Autorizar visitante
```
Residente → "Viene Juan Pérez en 10 minutos"
Sistema   → ✅ Juan Pérez autorizado hasta 16:30
```

### Abrir puerta
```
Residente → "Abrir puerta"
Sistema   → ✅ Puerta abierta (foto adjunta)
```

### Reportar incidente
```
Residente → "Reportar: luz fundida en estacionamiento"
Sistema   → ✅ Reporte #1234 creado. Admin notificado
```

### Consultar logs
```
Residente → "¿Quién vino hoy?"
Sistema   → 📋 Registros de acceso (today)
            • 14:32 - Juan Pérez (visitor_entry)
            • 16:10 - Uber delivery (visitor_entry)
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

- **GPT-4 NLP**: ~$0.01 por mensaje parseado
- **Evolution API**: Gratis (self-hosted) o $20-50/mes (cloud)
- **Total**: ~$30-80/mes para 50 casas

vs

- **Llamadas OpenAI Realtime ahorradas**: $200-300/mes

**Ahorro neto: ~$150-250/mes** 🎉
