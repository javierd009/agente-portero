# Streaming Service - go2rtc

Servicio de streaming que convierte RTSP de cámaras Hikvision a WebRTC para visualización en tiempo real en el dashboard.

## Arquitectura

```
Dashboard (WebRTC) ← go2rtc ← RTSP ← Cámara Hikvision
     │                │
     │           Puerto 8555
     │           (WebRTC)
     │
  Puerto 1984
  (Web UI/API)
```

## Ventajas de WebRTC vs RTSP directo

| Aspecto | WebRTC (go2rtc) | RTSP directo |
|---------|-----------------|--------------|
| Latencia | <1 segundo | 5-10 segundos |
| Compatibilidad | Todos los navegadores | Requiere plugins/VLC |
| Audio bidireccional | Sí | No en navegadores |
| CPU Server | Bajo | N/A |

## Deployment

### En FreePBX (On-Premise) - Recomendado

El streaming service debe correr en el mismo servidor que tiene acceso a las cámaras locales.

```bash
# Conectar a FreePBX
ssh root@172.20.20.1

# Navegar al directorio
cd /opt/agente-portero/services/streaming

# Crear .env con credenciales
cp .env.example .env
nano .env  # Editar con credenciales reales

# Iniciar servicio
docker-compose up -d

# Verificar
docker logs -f portero-streaming
```

### Verificar funcionamiento

1. **Web UI**: http://172.20.20.1:1984
2. **API**: http://172.20.20.1:1984/api/streams
3. **WebRTC**: ws://172.20.20.1:8555

## Configuración de Cámaras

Editar `go2rtc.yaml` para agregar cámaras:

```yaml
streams:
  # Formato: nombre_stream
  mi_camara:
    - "rtsp://usuario:password@ip:554/Streaming/Channels/101"
```

### URLs RTSP Hikvision

```
Main stream (alta calidad):
rtsp://admin:password@172.20.22.111:554/Streaming/Channels/101

Sub stream (baja calidad):
rtsp://admin:password@172.20.22.111:554/Streaming/Channels/102

Con audio bidireccional:
rtsp://admin:password@172.20.22.111:554/Streaming/Channels/101?backchannel=yes
```

## Integración con Dashboard

El dashboard se conecta via WebRTC:

```typescript
// En el componente de video
const wsUrl = 'ws://172.20.20.1:8555/api/ws?src=entrada_main';
```

## Comandos Útiles

```bash
# Ver logs
docker logs -f portero-streaming

# Reiniciar
docker-compose restart

# Detener
docker-compose down

# Actualizar imagen
docker-compose pull && docker-compose up -d
```

## Troubleshooting

### No se ve el stream
1. Verificar que la cámara esté accesible: `curl http://172.20.22.111`
2. Verificar credenciales RTSP
3. Revisar logs: `docker logs portero-streaming`

### Alta latencia
1. Usar sub-stream en lugar de main
2. Verificar ancho de banda de red

### WebRTC no conecta
1. Verificar puertos 8555 TCP/UDP abiertos
2. Revisar configuración de ICE candidates
