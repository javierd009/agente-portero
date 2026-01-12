# OpenAI Realtime API + FreePBX/Asterisk Integration Guide

> **Documento de referencia técnica** para integrar agentes de voz con OpenAI Realtime API y Asterisk/FreePBX usando AudioSocket.
>
> Este documento resume 3 días de troubleshooting y las soluciones definitivas encontradas.

## Tabla de Contenidos

1. [Arquitectura](#arquitectura)
2. [Problema Principal](#problema-principal)
3. [Solución: AudioSocket](#solución-audiosocket)
4. [Configuración Crítica de Audio](#configuración-crítica-de-audio)
5. [Código Python del Voice Service](#código-python-del-voice-service)
6. [Configuración de Asterisk](#configuración-de-asterisk)
7. [Docker Compose](#docker-compose)
8. [Parámetros Tunables](#parámetros-tunables)
9. [Troubleshooting](#troubleshooting)
10. [Checklist de Implementación](#checklist-de-implementación)

---

## Arquitectura

```
┌─────────────────┐     SIP      ┌─────────────────┐    AudioSocket    ┌─────────────────┐
│   Teléfono/     │ ──────────── │    Asterisk     │ ───────────────── │  Voice Service  │
│   Interfon     │              │    FreePBX      │    TCP:8089       │    (Python)     │
└─────────────────┘              └─────────────────┘                    └────────┬────────┘
                                                                                 │
                                                                                 │ WebSocket
                                                                                 │
                                                                        ┌────────▼────────┐
                                                                        │  OpenAI         │
                                                                        │  Realtime API   │
                                                                        │  (GPT-4o)       │
                                                                        └─────────────────┘
```

**Flujo de Audio:**
1. Visitante llama → Asterisk recibe llamada SIP
2. Dialplan ejecuta `AudioSocket()` → Conecta TCP al Voice Service
3. Voice Service recibe audio 8kHz → Resamplea a 24kHz → Envía a OpenAI
4. OpenAI responde audio 24kHz → Resamplea a 8kHz → Envía a Asterisk
5. Asterisk reproduce audio al visitante

---

## Problema Principal

### Síntomas Observados
- Audio entrecortado, "enredado", ininteligible
- Velocidad de reproducción incorrecta (muy rápido o muy lento)
- Cortes frecuentes en la respuesta del agente
- "Playback paused (buffer empty)" en logs
- "Audio queue full! Dropped X chunks" en logs

### Causa Raíz
**Sample rate incorrecto**: AudioSocket de Asterisk **SIEMPRE** usa 8kHz (slin), independientemente de la configuración del canal.

```
❌ INCORRECTO: Asumir 16kHz o detectar del canal
✅ CORRECTO: AudioSocket = 8kHz signed linear 16-bit mono PCM
```

Documentación oficial: https://docs.asterisk.org/Configuration/Channel-Drivers/AudioSocket/

---

## Solución: AudioSocket

### ¿Por qué AudioSocket y no ARI/External Media?

| Método | Pros | Contras |
|--------|------|---------|
| **ARI + External Media** | Más control | Complejo, UDP, RTP headers |
| **AudioSocket** | Simple, TCP, bidireccional | Menos documentado |

**AudioSocket es la mejor opción** para integración con AI porque:
- TCP garantiza orden de paquetes
- Protocolo simple (3-byte header + payload)
- Bidireccional nativo
- No requiere parsear RTP

### Protocolo AudioSocket

```
Header: 3 bytes
├── Byte 0: Message Type
│   ├── 0x01 = UUID (channel ID)
│   ├── 0x10 = Audio data
│   ├── 0x00 = Hangup
│   └── 0x02 = Error
├── Bytes 1-2: Payload length (big-endian uint16)
└── Payload: variable length

Audio Format: signed linear 16-bit 8kHz mono PCM (slin)
Chunk Size: 320 bytes = 20ms @ 8kHz
```

---

## Configuración Crítica de Audio

### Constantes Fundamentales

```python
# AudioSocket SIEMPRE usa 8kHz - NO ES CONFIGURABLE
ASTERISK_SAMPLE_RATE = 8000   # Hz
OPENAI_SAMPLE_RATE = 24000    # Hz (OpenAI Realtime API)
BYTES_PER_SAMPLE = 2          # 16-bit signed PCM
CHUNK_MS = 20                 # 20ms por chunk
CHUNK_BYTES = 320             # 8000 * 0.020 * 2 = 320 bytes
```

### Ratio de Resampling

```
Asterisk → OpenAI: 8kHz → 24kHz = ratio 3x (upsample)
OpenAI → Asterisk: 24kHz → 8kHz = ratio 0.33x (downsample)
```

### Resampler de Alta Calidad

```python
from scipy import signal
from math import gcd

class AudioResampler:
    """Resampler usando filtro polifásico de scipy."""

    def __init__(self, from_rate: int, to_rate: int):
        self.from_rate = from_rate
        self.to_rate = to_rate
        g = gcd(from_rate, to_rate)
        self.up = to_rate // g
        self.down = from_rate // g

    def resample(self, audio_data: bytes) -> bytes:
        if self.from_rate == self.to_rate or len(audio_data) < 2:
            return audio_data

        # PCM16 little-endian
        audio_array = np.frombuffer(audio_data, dtype='<i2').astype(np.float64)
        if len(audio_array) == 0:
            return audio_data

        # Polyphase resampling con anti-aliasing
        resampled = signal.resample_poly(audio_array, self.up, self.down)

        # Clip y convertir a int16
        resampled = np.clip(resampled, -32768, 32767).astype('<i2')
        return resampled.tobytes()
```

**Importante**: NO usar overlap/crossfade en el resampler - scipy's `resample_poly` ya maneja la continuidad.

---

## Código Python del Voice Service

### Estructura de Archivos

```
voice-service/
├── main.py              # Entry point, HTTP health server
├── config.py            # Pydantic Settings
├── audio_bridge.py      # AudioSocket TCP server
├── call_session.py      # OpenAI Realtime session manager
├── tools.py             # Function calling tools
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

### config.py - Configuración

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Audio Bridge (AudioSocket)
    audio_bridge_host: str = "0.0.0.0"
    audio_bridge_port: int = 8089
    audio_sample_rate: int = 8000   # AudioSocket SIEMPRE usa 8kHz
    audio_chunk_ms: int = 20        # 20ms chunks = 320 bytes

    # Noise Gate - Silencia ruido bajo para estabilizar VAD
    noise_gate_threshold: int = 200  # RMS threshold (0 = deshabilitado)

    # Playback Buffer - Absorbe jitter de red
    playback_prebuffer_frames: int = 10  # 200ms de prebuffer
    output_audio_queue_maxsize: int = 1000  # ~20 segundos de audio

    # OpenAI
    openai_api_key: str = ""
    openai_realtime_model: str = "gpt-4o-realtime-preview-2024-12-17"
    openai_realtime_url: str = "wss://api.openai.com/v1/realtime"

    # VAD tuning (server-side en OpenAI)
    vad_threshold: float = 0.6       # 0.5-0.9, más alto = menos falsos positivos
    vad_prefix_padding_ms: int = 300
    vad_silence_duration_ms: int = 800  # Tiempo de silencio antes de responder

    # Voice - Opciones: alloy, shimmer, coral, sage, echo, ash, ballad, verse
    default_voice: str = "shimmer"  # Shimmer es más claro para español

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### audio_bridge.py - AudioSocket Server

```python
import asyncio
import struct
import socket
import logging

logger = logging.getLogger(__name__)

class AudioSocketBridge:
    """TCP server para protocolo AudioSocket de Asterisk."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8089):
        self.host = host
        self.port = port
        self.sessions = {}
        self.server = None
        self.on_new_session = None

    async def start(self, on_new_session=None):
        self.on_new_session = on_new_session
        self.server = await asyncio.start_server(
            self._handle_connection,
            self.host,
            self.port
        )
        logger.info(f"AudioSocket bridge listening on TCP {self.host}:{self.port}")

    async def _handle_connection(self, reader, writer):
        channel_id = None

        try:
            # CRÍTICO: Deshabilitar Nagle's algorithm para audio en tiempo real
            sock = writer.get_extra_info('socket')
            if sock:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            # Primer mensaje: UUID del canal
            msg_type, payload = await self._read_message(reader)
            if msg_type != 0x01:
                logger.error(f"Expected UUID message, got type {msg_type}")
                return

            # UUID puede ser 16 bytes binarios o texto
            if len(payload) == 16:
                import uuid
                channel_id = str(uuid.UUID(bytes=payload))
            else:
                channel_id = payload.decode('utf-8').strip('\x00')

            logger.info(f"AudioSocket connection from channel {channel_id}")

            # Crear sesión
            session = AudioSession(channel_id, reader, writer)
            self.sessions[channel_id] = session

            # Notificar nueva sesión
            if self.on_new_session:
                if asyncio.iscoroutinefunction(self.on_new_session):
                    await self.on_new_session(channel_id)
                else:
                    self.on_new_session(channel_id)

            # Loop de lectura de audio
            while session.running:
                msg_type, payload = await asyncio.wait_for(
                    self._read_message(reader),
                    timeout=30.0
                )

                if msg_type == 0x10:  # Audio
                    if session.on_audio_received:
                        session.on_audio_received(payload)
                elif msg_type == 0x00:  # Hangup
                    break

        except asyncio.IncompleteReadError:
            pass
        except Exception as e:
            logger.error(f"AudioSocket error: {e}")
        finally:
            if channel_id:
                await self.close_session(channel_id)
            writer.close()

    async def _read_message(self, reader):
        """Lee mensaje AudioSocket: 1 byte type + 2 bytes length + payload"""
        header = await reader.readexactly(3)
        msg_type = header[0]
        length = struct.unpack('>H', header[1:3])[0]
        payload = await reader.readexactly(length) if length > 0 else b''
        return msg_type, payload

    async def send_audio(self, channel_id: str, audio_data: bytes):
        """Envía audio a Asterisk"""
        if channel_id not in self.sessions:
            return
        session = self.sessions[channel_id]
        if not session.writer or not session.running:
            return

        # AudioSocket message: type (1) + length (2) + payload
        header = struct.pack('>BH', 0x10, len(audio_data))
        session.writer.write(header + audio_data)
        await session.writer.drain()
```

### call_session.py - Playback con Buffer

```python
async def _playback_audio(self):
    """Task dedicado para playback suave a Asterisk."""

    CHUNK_DURATION_NS = int(self.chunk_ms * 1_000_000)  # 20ms en nanosegundos
    PREBUFFER_FRAMES = self.playback_prebuffer_frames   # 10 frames = 200ms
    MAX_SILENCE_FRAMES = 40  # 800ms antes de pausar playback

    silence_chunk = b'\x00' * self.chunk_bytes
    playing = False
    session_start_ns = None
    chunks_sent = 0

    while self.running:
        if not playing:
            # IDLE: Esperar primer chunk de audio
            try:
                chunk = await asyncio.wait_for(
                    self.output_audio_queue.get(),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                continue

            # Prebuffer: acumular frames antes de empezar
            prebuffer = [chunk]
            while len(prebuffer) < PREBUFFER_FRAMES:
                try:
                    chunk = await asyncio.wait_for(
                        self.output_audio_queue.get(),
                        timeout=0.1
                    )
                    prebuffer.append(chunk)
                except asyncio.TimeoutError:
                    break

            # Iniciar playback
            playing = True
            session_start_ns = time.monotonic_ns()
            chunks_sent = 0

            # Enviar prebuffer con timing preciso
            for chunk in prebuffer:
                await self.audio_bridge.send_audio(self.channel_id, chunk)
                chunks_sent += 1

        else:
            # PLAYING: Enviar chunks con timing preciso cada 20ms
            if not self.output_audio_queue.empty():
                chunk = self.output_audio_queue.get_nowait()
                consecutive_silence = 0
            else:
                # Buffer vacío - insertar silencio
                consecutive_silence += 1
                if consecutive_silence >= MAX_SILENCE_FRAMES:
                    playing = False
                    continue
                chunk = silence_chunk

            # Timing preciso
            expected_time_ns = session_start_ns + (chunks_sent * CHUNK_DURATION_NS)
            wait_ns = expected_time_ns - time.monotonic_ns()
            if wait_ns > 1_000_000:  # >1ms
                await asyncio.sleep(wait_ns / 1_000_000_000)

            await self.audio_bridge.send_audio(self.channel_id, chunk)
            chunks_sent += 1
```

### Noise Gate

```python
import audioop

def _apply_noise_gate(self, audio_data: bytes) -> bytes:
    """Silencia ruido bajo para estabilizar VAD de OpenAI."""
    if self.noise_gate_threshold <= 0:
        return audio_data

    rms = audioop.rms(audio_data, 2)  # 2 bytes per sample

    if rms < self.noise_gate_threshold:
        return b'\x00' * len(audio_data)  # Silencio

    return audio_data
```

---

## Configuración de Asterisk

### Dialplan (extensions_agente_portero.conf)

```ini
; /etc/asterisk/extensions_agente_portero.conf
; AudioSocket SIEMPRE usa 8kHz slin - no se puede cambiar

[agente-portero-sitnova]
exten => 1010,1,NoOp(=== AGENTE PORTERO AI ===)
 same => n,Answer()
 same => n,Wait(0.5)
 same => n,Set(UUID=${SHELL(cat /proc/sys/kernel/random/uuid | tr -d '\n')})
 same => n,NoOp(UUID generado: ${UUID})
 same => n,AudioSocket(${UUID},127.0.0.1:8089)
 same => n,Hangup()
```

### Incluir en extensions.conf

```ini
; /etc/asterisk/extensions.conf
#include extensions_agente_portero.conf
```

### Recargar Dialplan

```bash
asterisk -rx "dialplan reload"
asterisk -rx "dialplan show agente-portero-sitnova"
```

---

## Docker Compose

### docker-compose.yml

```yaml
version: '3.8'

services:
  voice-service:
    build: .
    image: voice-service:local
    container_name: voice-service
    restart: unless-stopped

    # CRÍTICO: network_mode: host para que 127.0.0.1:8089 funcione
    # desde Asterisk (que corre en el mismo host)
    network_mode: host

    environment:
      # OpenAI
      - OPENAI_API_KEY=${OPENAI_API_KEY}

      # Audio tuning
      - NOISE_GATE_THRESHOLD=200
      - PLAYBACK_PREBUFFER_FRAMES=10
      - OUTPUT_AUDIO_QUEUE_MAXSIZE=1000

      # VAD tuning
      - VAD_THRESHOLD=0.7
      - VAD_SILENCE_DURATION_MS=600

      # Debug
      - DEBUG=false

    volumes:
      - .:/app

    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

### requirements.txt

```
aiohttp>=3.9.0
websockets>=12.0
httpx>=0.26.0
python-dotenv>=1.0.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
numpy>=1.26.0
scipy>=1.11.0
```

---

## Parámetros Tunables

### Variables de Entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `NOISE_GATE_THRESHOLD` | 200 | RMS threshold. 0=deshabilitado. 150-300 típico |
| `PLAYBACK_PREBUFFER_FRAMES` | 10 | Frames a acumular antes de playback (200ms) |
| `OUTPUT_AUDIO_QUEUE_MAXSIZE` | 1000 | Tamaño máximo de cola (~20s de audio) |
| `VAD_THRESHOLD` | 0.6 | Sensibilidad VAD OpenAI. 0.5-0.9 |
| `VAD_SILENCE_DURATION_MS` | 800 | Silencio antes de respuesta AI |
| `VAD_PREFIX_PADDING_MS` | 300 | Audio antes de detección de voz |
| `DEFAULT_VOICE` | shimmer | Voz OpenAI: alloy, shimmer, coral, sage, echo, ash, ballad, verse |

### Ajustes según Problema

| Problema | Ajuste |
|----------|--------|
| Audio entrecortado | Aumentar `OUTPUT_AUDIO_QUEUE_MAXSIZE` |
| AI interrumpe mucho | Aumentar `VAD_THRESHOLD` (0.7→0.8) |
| AI tarda en responder | Reducir `VAD_SILENCE_DURATION_MS` |
| Ruido activa VAD | Aumentar `NOISE_GATE_THRESHOLD` |
| Delay inicial | Reducir `PLAYBACK_PREBUFFER_FRAMES` |

---

## Troubleshooting

### Verificar que el servicio está corriendo

```bash
curl -s http://127.0.0.1:8091/health
# Respuesta: {"status": "healthy", "service": "voice-service", "active_calls": 0}
```

### Ver logs durante llamada

```bash
docker logs -f --since 30s voice-service | egrep -i "Playback|queue|silence|Noise gate|error|closed"
```

### Logs saludables

```
AudioSocket connection from channel xxx
Detected 8000Hz AudioSocket chunk size (320 bytes)
Starting playback with 10 prebuffered frames
Playback: 50 chunks, queue=198, drift=-19ms, silence=0
```

### Logs problemáticos y soluciones

| Log | Problema | Solución |
|-----|----------|----------|
| `Audio queue full! Dropped X` | Cola llena | Aumentar `OUTPUT_AUDIO_QUEUE_MAXSIZE` |
| `Playback paused (buffer empty)` | Sin audio | Aumentar `PLAYBACK_PREBUFFER_FRAMES` |
| `drift=+500ms` | Timing desincronizado | Revisar timing loop |
| `Expected UUID, got type X` | Protocolo mal | Verificar dialplan |

### Verificar dialplan

```bash
asterisk -rx "dialplan show agente-portero-sitnova"
```

### Verificar puerto

```bash
netstat -tlnp | grep 8089
# Debería mostrar: tcp 0.0.0.0:8089 LISTEN python
```

---

## Checklist de Implementación

### Pre-requisitos

- [ ] Asterisk/FreePBX instalado y funcionando
- [ ] Python 3.11+
- [ ] Docker y Docker Compose
- [ ] API Key de OpenAI con acceso a Realtime API

### Configuración

- [ ] Sample rate = 8000 Hz (hardcoded, AudioSocket siempre usa 8kHz)
- [ ] Dialplan usa `AudioSocket()` apuntando a `127.0.0.1:8089`
- [ ] Docker usa `network_mode: host`
- [ ] TCP_NODELAY habilitado en socket
- [ ] Resampler usa scipy `resample_poly` (no overlap manual)

### Parámetros de Audio

- [ ] `NOISE_GATE_THRESHOLD=200`
- [ ] `PLAYBACK_PREBUFFER_FRAMES=10`
- [ ] `OUTPUT_AUDIO_QUEUE_MAXSIZE=1000`
- [ ] `VAD_THRESHOLD=0.7`
- [ ] `VAD_SILENCE_DURATION_MS=600`

### Verificación

- [ ] Health check responde OK
- [ ] Llamada de prueba conecta
- [ ] AI saluda correctamente
- [ ] Audio bidireccional funciona
- [ ] No hay "Audio queue full" en logs
- [ ] Drift estable (~±20ms)

---

## Créditos y Referencias

- **OpenAI Realtime API**: https://platform.openai.com/docs/guides/realtime
- **Asterisk AudioSocket**: https://docs.asterisk.org/Configuration/Channel-Drivers/AudioSocket/
- **scipy resample_poly**: https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.resample_poly.html

---

*Documento creado: Enero 2026*
*Proyecto: Agente Portero - Guardia Virtual para Condominios*
