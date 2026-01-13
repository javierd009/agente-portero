# Vision Service - Edge Computing para Agente Portero

Servicio de procesamiento de video que corre **on-premise** en el servidor FreePBX para lograr baja latencia en la comunicacion con camaras Hikvision.

## Arquitectura Edge Computing

```
                                          ┌──────────────────┐
    CLOUD (Contabo)                       │    Dashboard     │
    ┌───────────────────┐                 │    (Next.js)     │
    │     Backend       │                 └────────┬─────────┘
    │    (FastAPI)      │                          │
    └───────────────────┘                          │ Llamadas directas
                                                   │ (menor latencia)
    ═══════════════════════════════════════════════╪═══════════════════
                                                   │
    ON-PREMISE (FreePBX 172.20.20.1)               │
    ┌───────────────────────────────────────────────▼──────────────────┐
    │                    Vision Service (:8002)                         │
    │                                                                   │
    │   • Test conexion de camaras                                      │
    │   • Captura de snapshots                                          │
    │   • Deteccion YOLO (placas, personas)                            │
    │   • OCR para lectura de placas                                    │
    │                                                                   │
    └───────────────────────────────────────────────┬──────────────────┘
                                                    │ Red local
                                                    │ (172.20.x.x)
    ┌───────────────────────────────────────────────▼──────────────────┐
    │                   Camaras Hikvision                               │
    │                   172.20.22.111:80                                │
    └──────────────────────────────────────────────────────────────────┘
```

## Beneficios del Edge Computing

- **Baja latencia**: El video se procesa localmente sin salir a internet
- **Menor consumo de ancho de banda**: Solo resultados viajan a la nube
- **Mayor confiabilidad**: Funciona aunque internet falle temporalmente
- **Acceso directo a camaras**: Sin problemas de NAT o firewall

## Deployment Manual en FreePBX

### Requisitos Previos

- Servidor FreePBX con Docker instalado
- Acceso SSH al servidor (root@172.20.20.1)
- Acceso de red a las camaras Hikvision

### Paso 1: Conectar al Servidor

```bash
ssh root@172.20.20.1
# Password: Sitnova20@
```

### Paso 2: Instalar Docker (si no esta instalado)

```bash
# Verificar si Docker esta instalado
docker --version

# Si no esta instalado:
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker
```

### Paso 3: Clonar el Repositorio

```bash
# Crear directorio de trabajo
mkdir -p /opt/agente-portero
cd /opt/agente-portero

# Clonar solo el vision-service (shallow clone)
git clone --depth 1 https://github.com/javierd009/agente_portero.git .
cd services/vision-service
```

### Paso 4: Configurar Variables de Entorno

```bash
# Copiar el template de configuracion
cp .env.freepbx .env

# Editar si es necesario (las credenciales ya estan configuradas)
nano .env
```

Contenido actual de `.env`:
```env
HIKVISION_HOST=172.20.22.111
HIKVISION_PORT=80
HIKVISION_USER=admin
HIKVISION_PASSWORD=integratec20
BACKEND_API_URL=https://api-portero.integratec-ia.com
```

### Paso 5: Ejecutar el Script de Deployment

```bash
chmod +x deploy-freepbx.sh
./deploy-freepbx.sh
```

Este script:
1. Verifica Docker y Docker Compose
2. Intenta descargar la imagen de GitHub Container Registry
3. Si no esta disponible, construye la imagen localmente
4. Inicia el servicio
5. Verifica el health check

### Paso 6: Verificar el Servicio

```bash
# Ver estado del contenedor
docker ps | grep portero-vision

# Ver logs
docker logs portero-vision

# Probar health endpoint
curl http://localhost:8002/health

# Probar conexion a camara
curl -X POST "http://localhost:8002/cameras/test?host=172.20.22.111&port=80&username=admin&password=integratec20"

# Obtener snapshot
curl http://localhost:8002/cameras/1/snapshot/base64
```

### Paso 7: Configurar NAT en Mikrotik

Para que el dashboard pueda acceder al Vision Service desde internet:

1. Acceder a Mikrotik: http://integrateccr.ddns.net:90
2. Ir a: IP > Firewall > NAT
3. Agregar regla:
   - Chain: dstnat
   - Protocol: TCP
   - Dst. Port: 8002
   - Action: dst-nat
   - To Addresses: 172.20.20.1
   - To Ports: 8002

### Paso 8: Configurar en Dashboard

1. Ir a **Dashboard > Configuracion**
2. En la seccion "Vision Service (Edge Computing)":
   - URL: `http://integrateccr.ddns.net:8002`
3. Click "Probar Conexion"
4. Si sale verde, click "Guardar"

## Comandos Utiles

```bash
# Ver logs en tiempo real
docker logs -f portero-vision

# Reiniciar servicio
cd /opt/agente-portero/services/vision-service
docker-compose -f docker-compose.freepbx.yml restart

# Detener servicio
docker-compose -f docker-compose.freepbx.yml down

# Actualizar a nueva version
git pull origin main
docker-compose -f docker-compose.freepbx.yml pull
docker-compose -f docker-compose.freepbx.yml up -d

# Ver uso de recursos
docker stats portero-vision
```

## API Endpoints

| Endpoint | Metodo | Descripcion |
|----------|--------|-------------|
| `/health` | GET | Health check del servicio |
| `/cameras/test` | POST | Probar conexion a camara |
| `/cameras/{id}/snapshot` | GET | Obtener snapshot como archivo |
| `/cameras/{id}/snapshot/base64` | GET | Obtener snapshot en base64 |
| `/detect` | POST | Detectar objetos con YOLO |

### Ejemplo: Probar Camara

```bash
curl -X POST "http://localhost:8002/cameras/test" \
  -H "Content-Type: application/json" \
  -d '{"host": "172.20.22.111", "port": 80, "username": "admin", "password": "integratec20"}'
```

Respuesta:
```json
{
  "host": "172.20.22.111",
  "port": 80,
  "is_online": true,
  "device_info": {
    "model": "DS-2CD2043G2-I",
    "firmware": "V5.6.2"
  }
}
```

## Troubleshooting

### El servicio no inicia

```bash
# Ver logs de error
docker logs portero-vision

# Verificar que el puerto 8002 este libre
netstat -tlnp | grep 8002

# Reiniciar Docker
systemctl restart docker
```

### No conecta a la camara

```bash
# Verificar conectividad de red
ping 172.20.22.111

# Probar acceso HTTP a la camara
curl -u admin:integratec20 http://172.20.22.111/ISAPI/System/deviceInfo

# Verificar credenciales correctas en .env
cat .env | grep HIKVISION
```

### Dashboard no conecta al Vision Service

1. Verificar NAT en Mikrotik
2. Probar desde internet: `curl http://integrateccr.ddns.net:8002/health`
3. Verificar firewall en FreePBX: `iptables -L -n | grep 8002`

## Estructura de Archivos

```
services/vision-service/
├── main.py                    # Servidor FastAPI
├── hikvision.py               # Cliente Hikvision ISAPI
├── detector.py                # YOLO + OCR
├── config.py                  # Configuracion
├── Dockerfile                 # Imagen Docker
├── docker-compose.freepbx.yml # Compose para FreePBX
├── deploy-freepbx.sh          # Script de deployment
├── .env.freepbx               # Template de variables
└── requirements.txt           # Dependencias Python
```
