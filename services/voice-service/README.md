# Voice Service - Agente Portero

Servicio de voz inteligente que maneja llamadas telefónicas entrantes usando **OpenAI Realtime API** + **Asterisk/FreePBX**.

## Descripcion

Este servicio recibe llamadas SIP desde Asterisk, las conecta con OpenAI Realtime API para conversaciones naturales en tiempo real, y ejecuta acciones mediante function calling (verificar visitantes, abrir puertas, notificar residentes, etc.).

> **Documentacion Tecnica Detallada**: Ver [docs/OPENAI_REALTIME_FREEPBX_INTEGRATION.md](/docs/OPENAI_REALTIME_FREEPBX_INTEGRATION.md) para la guia completa de integracion, troubleshooting y parametros tunables.

```
Visitante llama → Asterisk → ARI WebSocket → Voice Service
                                                   ↓
                                          OpenAI Realtime API
                                                   ↓
                                          Function Calling (tools)
                                                   ↓
                                          Backend API
                                                   ↓
                                          Hikvision Gate + WhatsApp
```

## Características

- ✅ **Conversaciones naturales** con latencia <500ms (OpenAI Realtime)
- ✅ **Function calling** para acciones en tiempo real
- ✅ **Multi-idioma** (español mexicano por defecto)
- ✅ **Transferencia a guardia humano** en situaciones sospechosas
- ✅ **Integración con Backend** para consultas/registros
- ✅ **Audio bidireccional** vía Asterisk ARI

## Arquitectura

### Componentes

1. **main.py** - Entry point del servicio
2. **ari_handler.py** - Maneja conexión WebSocket con Asterisk ARI
3. **call_session.py** - Gestiona sesión de llamada con OpenAI Realtime
4. **tools.py** - Herramientas (funciones) que el agente puede ejecutar
5. **config.py** - Configuración y settings

### Flujo de una llamada

```
1. Visitante marca el interfon
   ↓
2. Asterisk recibe llamada SIP → envía evento a ARI
   ↓
3. ARIHandler detecta StasisStart → contesta llamada
   ↓
4. CallSession inicia conexión con OpenAI Realtime API
   ↓
5. Agente saluda: "Hola, soy el sistema de seguridad..."
   ↓
6. Visitante responde (audio → OpenAI)
   ↓
7. OpenAI procesa + ejecuta tools si es necesario:
   - check_visitor: ¿Está autorizado?
   - find_resident: ¿Existe el residente?
   - open_gate: Abrir puerta
   - notify_resident: WhatsApp al residente
   ↓
8. Agente responde: "Le abriré la puerta..."
   ↓
9. Registro en access_logs + comando a Hikvision
   ↓
10. Llamada termina
```

## Instalación

### 1. Requisitos

- Python 3.11+
- Asterisk 18+ con ARI habilitado
- OpenAI API key con acceso a Realtime API
- Backend API corriendo

### 2. Setup

```bash
# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales
```

### 3. Configurar Asterisk

#### a) Habilitar ARI en Asterisk

Editar `/etc/asterisk/ari.conf`:

```ini
[general]
enabled = yes
pretty = yes
allowed_origins = *

[asterisk]
type = user
read_only = no
password = asterisk
```

#### b) Crear aplicación Stasis

Editar `/etc/asterisk/extensions.conf`:

```ini
[from-internal]
; Extensión del interfon (ej: 1000)
exten => 1000,1,Noop(Interfon - Agente Virtual)
same => n,Stasis(agente-portero,${EXTEN})
same => n,Hangup()

; Guardia humano (transferencias)
exten => 1001,1,Noop(Guardia de Seguridad)
same => n,Dial(SIP/guardia,30)
same => n,Hangup()
```

#### c) Reiniciar Asterisk

```bash
asterisk -rx "core reload"
asterisk -rx "ari show status"
```

Deberías ver:
```
ARI Status:
  Enabled: Yes
  HTTP Bindaddr: 0.0.0.0:8088
  Websocket Write Timeout: 100 ms
```

## Uso

### Iniciar el servicio

```bash
python main.py
```

Salida esperada:
```
2024-01-06 15:30:00 - __main__ - INFO - Starting Agente Portero Voice Service...
2024-01-06 15:30:00 - ari_handler - INFO - Connecting to ARI WebSocket...
2024-01-06 15:30:01 - ari_handler - INFO - ARI WebSocket connected
2024-01-06 15:30:01 - __main__ - INFO - Connected to Asterisk ARI
```

### Probar una llamada

1. Desde un teléfono SIP registrado en Asterisk, marca `1000`
2. El agente debería contestar: *"Hola, soy el sistema de seguridad de [condominio]. ¿En qué puedo ayudarte?"*
3. Di: *"Vengo a visitar a Juan Pérez en el departamento A-101"*
4. El agente buscará al residente y verificará autorización
5. Si está autorizado, abrirá la puerta y notificará al residente

## Herramientas del Agente

El agente puede ejecutar las siguientes funciones durante la conversación:

### 1. `check_visitor`
Verifica si un visitante está pre-autorizado.

**Parámetros:**
- `name`: Nombre del visitante
- `plate`: Placa del vehículo
- `id_number`: Número de identificación

**Uso en conversación:**
> **Agente**: "¿Me puede decir su nombre?"
> **Visitante**: "Soy María González"
> *(El agente llama a `check_visitor(name="María González")`)*

### 2. `find_resident`
Busca un residente por nombre o unidad.

**Parámetros:**
- `name`: Nombre del residente
- `unit`: Número de unidad (ej: A-101)

**Uso:**
> **Visitante**: "Vengo a visitar a Juan Pérez"
> *(El agente llama a `find_resident(name="Juan Pérez")`)*

### 3. `notify_resident`
Notifica al residente via WhatsApp.

**Parámetros:**
- `resident_id`: ID del residente
- `visitor_name`: Nombre del visitante
- `visitor_plate`: Placa (opcional)

### 4. `open_gate`
Abre la puerta de acceso.

**Parámetros:**
- `visitor_name`: Nombre del visitante
- `resident_id`: ID del residente (opcional)
- `gate_id`: ID de la puerta (default: main_gate)

**Registro automático:**
- Crea access_log en la base de datos
- Envía comando a Hikvision
- Notifica al residente

### 5. `get_recent_plates`
Obtiene placas detectadas recientemente por las cámaras.

**Parámetros:**
- `minutes`: Minutos hacia atrás (default: 5)

**Uso:**
> **Agente**: "¿Me puede decir la placa de su vehículo?"
> **Visitante**: "No la recuerdo"
> *(El agente llama a `get_recent_plates()` para ver si la cámara la detectó)*

### 6. `transfer_to_guard`
Transfiere la llamada a un guardia humano.

**Parámetros:**
- `reason`: Razón de la transferencia

**Uso:**
> Si el visitante parece sospechoso o no proporciona información clara
> *(El agente llama a `transfer_to_guard(reason="Información insuficiente")`)*

### 7. `register_visitor`
Registra un nuevo visitante.

**Parámetros:**
- `name`: Nombre del visitante
- `resident_id`: ID del residente
- `reason`: Motivo de la visita
- `vehicle_plate`: Placa (opcional)
- `id_number`: ID (opcional)

## Configuración

### Variables de entorno

```env
# Asterisk ARI
ASTERISK_ARI_URL=http://localhost:8088/ari
ASTERISK_ARI_USER=asterisk
ASTERISK_ARI_PASSWORD=asterisk
ASTERISK_ARI_APP=agente-portero

# OpenAI Realtime
OPENAI_API_KEY=sk-your-api-key
OPENAI_REALTIME_MODEL=gpt-4o-realtime-preview-2024-12-17

# Backend API
BACKEND_API_URL=http://localhost:8000

# Voz
DEFAULT_VOICE=shimmer  # Opciones: alloy, shimmer, coral, sage, echo, ash, ballad, verse
DEFAULT_LANGUAGE=es-MX

# Audio Tuning
NOISE_GATE_THRESHOLD=200      # RMS threshold para silenciar ruido (0=deshabilitado)
PLAYBACK_PREBUFFER_FRAMES=10  # Frames a prebuffer antes de playback (200ms)
OUTPUT_AUDIO_QUEUE_MAXSIZE=1000  # Tamano maximo de cola (~20s de audio)

# VAD Tuning (server-side en OpenAI)
VAD_THRESHOLD=0.6             # Sensibilidad VAD (0.5-0.9)
VAD_PREFIX_PADDING_MS=300     # Audio antes de deteccion de voz
VAD_SILENCE_DURATION_MS=800   # Silencio antes de respuesta AI

# Debug
DEBUG=true
```

### Voces disponibles

OpenAI Realtime ofrece las siguientes voces:
- `alloy` - Voz neutral
- `shimmer` - Voz femenina calida (recomendada para espanol)
- `coral` - Voz femenina clara
- `sage` - Voz masculina tranquila
- `echo` - Voz masculina profunda
- `ash` - Voz masculina suave
- `ballad` - Voz expresiva
- `verse` - Voz versatil

## Testing

### Test local (sin Asterisk)

```bash
# Simular evento de llamada
python test_voice_service.py
```

### Test con Asterisk (simulación)

```bash
# 1. Iniciar Voice Service
python main.py

# 2. Desde Asterisk CLI
asterisk -rx "originate Local/1000@from-internal application Playback demo-congrats"
```

### Test completo (llamada real)

1. Configurar un softphone SIP (ej: Zoiper, Linphone)
2. Registrar en Asterisk
3. Marcar extensión `1000`
4. Interactuar con el agente de voz

## Monitoreo y Logs

### Niveles de log

```bash
# Debug completo
DEBUG=true python main.py

# Solo INFO y errores
DEBUG=false python main.py
```

### Logs útiles

```log
# Llamada entrante
2024-01-06 15:30:05 - ari_handler - INFO - New call from +5218112345678 on channel 1234567890.123

# Sesión OpenAI iniciada
2024-01-06 15:30:06 - call_session - INFO - Connected to OpenAI Realtime for channel 1234567890.123

# Transcripción de usuario
2024-01-06 15:30:10 - call_session - INFO - User said: Vengo a visitar a Juan Pérez

# Function call
2024-01-06 15:30:11 - tools - INFO - Function call: find_resident({"name": "Juan Pérez"})

# Respuesta del agente
2024-01-06 15:30:12 - call_session - INFO - AI said: Perfecto, veo que Juan Pérez vive en la unidad A-101. Le voy a notificar de su llegada.
```

## Costos

### OpenAI Realtime API

Precios (Diciembre 2024):
- **Audio input**: $0.06 / minuto
- **Audio output**: $0.24 / minuto
- **Total por minuto**: ~$0.30

**Ejemplo condominio 50 casas:**
- Promedio: 3 llamadas/día × 1.5 min/llamada = 4.5 min/día
- Mensual: 4.5 × 30 = 135 minutos/mes
- **Costo mensual**: 135 × $0.30 = **$40.50/mes**

### Optimización de costos

- ✅ **WhatsApp pre-autorización** reduce llamadas en 40-50%
- ✅ **Conversaciones cortas** con flujo optimizado
- ✅ **Transfer rápido** a guardia si es necesario

## Troubleshooting

### "Cannot connect to Asterisk ARI"

**Problema**: No se puede conectar al WebSocket de ARI.

**Solución**:
```bash
# 1. Verificar que ARI está habilitado
asterisk -rx "ari show status"

# 2. Verificar credenciales en .env
cat .env | grep ASTERISK_ARI

# 3. Probar conectividad
curl -u asterisk:asterisk http://localhost:8088/ari/asterisk/info
```

### "OpenAI API key invalid"

**Problema**: API key de OpenAI no funciona.

**Solución**:
```bash
# 1. Verificar que tienes acceso a Realtime API
# (Requiere tier 1+ en OpenAI)

# 2. Verificar el API key
echo $OPENAI_API_KEY

# 3. Testear con curl
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### "Function call fails"

**Problema**: Las herramientas no funcionan.

**Solución**:
1. Verificar que el Backend API está corriendo
2. Verificar logs del Backend para errores
3. Verificar que el tenant_id es correcto

### Ajustes de audio (ruido/VAD)

Si el audio se corta o el agente deja de responder, ajusta estos parametros:

- `NOISE_GATE_THRESHOLD`: RMS minimo para considerar audio como voz (ej: 200-400)
- `PLAYBACK_PREBUFFER_FRAMES`: frames a prebuffer antes de reproducir (ej: 10-15)
- `OUTPUT_AUDIO_QUEUE_MAXSIZE`: tamano del buffer de salida (ej: 1000 = ~20s)
- `VAD_THRESHOLD`: sensibilidad del VAD del servidor (ej: 0.6-0.8)
- `VAD_SILENCE_DURATION_MS`: ms de silencio antes de responder (ej: 600-800)

### "No audio / garbled audio"

**Problema**: No se escucha audio o está distorsionado.

**Solución**:
1. Verificar formato de audio (debe ser PCM16)
2. Verificar configuración de external media en Asterisk
3. Verificar que el codec es `slin16`
4. Si usas AudioSocket, confirma que el puerto expuesto coincida (host `9089` → container `8089`)
5. Si usas Stasis/ARI, fuerza `slin16` con `CHANNEL(audioreadformat)` y `CHANNEL(audiowriteformat)`
6. Si el audio sigue grave o muy rápido, revisa el tamaño del primer chunk en logs (320 bytes ≈ 8kHz, 640 bytes ≈ 16kHz)

### "Audio se corta / habla muy rápido"

**Problema**: El agente empieza a hablar y corta palabras o se acelera.

**Solución**:
1. Verificar que el sample rate del canal coincide con `AUDIO_SAMPLE_RATE`.
2. Revisar logs de `User speech started - clearing audio queue` (barge-in) mientras el AI habla.
3. Revisar logs de `Playback: ... silence=...` para detectar cortes por jitter.

## Arquitectura Avanzada

### Multi-tenant

El servicio detecta el `tenant_id` desde:
1. La extensión llamada (ej: `1000` = Condominio A, `2000` = Condominio B)
2. DID (número marcado)
3. Variable de canal personalizada

### Escalabilidad

Para manejar múltiples llamadas simultáneas:
- Cada llamada = 1 CallSession independiente
- Conexión WebSocket separada a OpenAI por llamada
- Límite: Depende de tu tier en OpenAI (típicamente 100 sesiones concurrentes)

### High Availability

```bash
# Usar supervisor o systemd para auto-restart
sudo systemctl enable voice-service
sudo systemctl start voice-service
```

---

**¿Necesitas ayuda?** Revisa los logs o abre un issue en el repositorio.
