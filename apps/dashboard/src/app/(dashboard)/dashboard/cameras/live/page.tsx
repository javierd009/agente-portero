'use client'

import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { CameraGrid } from '@/components/camera'
import { useTenantStore } from '@/store/tenant'
import { apiClient, visionService } from '@/lib/api'
import {
  Video,
  VideoOff,
  Settings,
  AlertCircle,
  ArrowLeft,
  Cpu,
} from 'lucide-react'
import Link from 'next/link'

export default function LiveCamerasPage() {
  const { currentTenant } = useTenantStore()
  const tenantId = currentTenant?.id || ''

  const [go2rtcStatus, setGo2rtcStatus] = useState<'checking' | 'online' | 'offline'>('checking')

  // Fetch condominium settings
  const { data: condominium } = useQuery({
    queryKey: ['condominium', tenantId],
    queryFn: () => apiClient.getCondominium(tenantId),
    enabled: !!tenantId,
  })

  // Get go2rtc URL from settings (or use default)
  const go2rtcUrl = condominium?.settings?.go2rtc_url || process.env.NEXT_PUBLIC_GO2RTC_URL || ''
  const visionServiceUrl = condominium?.settings?.vision_service_url || ''

  // Fetch cameras
  const { data: cameras, isLoading } = useQuery({
    queryKey: ['cameras', tenantId],
    queryFn: () => apiClient.getCameras(tenantId),
    enabled: !!tenantId,
  })

  // Check go2rtc status
  useEffect(() => {
    if (!go2rtcUrl) {
      setGo2rtcStatus('offline')
      return
    }

    // Try to fetch go2rtc API
    fetch(`${go2rtcUrl}/api/streams`)
      .then(res => {
        setGo2rtcStatus(res.ok ? 'online' : 'offline')
      })
      .catch(() => {
        setGo2rtcStatus('offline')
      })
  }, [go2rtcUrl])

  // Convert cameras to stream config
  const cameraStreams = cameras?.map(camera => ({
    id: camera.id,
    // Stream name format: camera name normalized
    streamName: camera.name.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '') + '_main',
    title: camera.name,
  })) || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/dashboard/cameras">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Volver
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Video className="h-8 w-8" />
            Video en Vivo
          </h1>
          <p className="text-muted-foreground">
            Streaming en tiempo real via WebRTC
          </p>
        </div>
      </div>

      {/* Status Banners */}
      <div className="space-y-2">
        {/* go2rtc Status */}
        <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
          go2rtcStatus === 'online'
            ? 'bg-green-500/10 border border-green-500/20'
            : go2rtcStatus === 'checking'
            ? 'bg-yellow-500/10 border border-yellow-500/20'
            : 'bg-red-500/10 border border-red-500/20'
        }`}>
          <Video className={`h-4 w-4 ${
            go2rtcStatus === 'online'
              ? 'text-green-500'
              : go2rtcStatus === 'checking'
              ? 'text-yellow-500 animate-pulse'
              : 'text-red-500'
          }`} />
          <span className={`text-sm font-medium ${
            go2rtcStatus === 'online'
              ? 'text-green-700 dark:text-green-400'
              : go2rtcStatus === 'checking'
              ? 'text-yellow-700 dark:text-yellow-400'
              : 'text-red-700 dark:text-red-400'
          }`}>
            {go2rtcStatus === 'online'
              ? `Streaming Server Activo - ${go2rtcUrl}`
              : go2rtcStatus === 'checking'
              ? 'Verificando servidor de streaming...'
              : 'Servidor de Streaming Offline'}
          </span>
        </div>
      </div>

      {/* Main Content */}
      {go2rtcStatus === 'offline' && !go2rtcUrl ? (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Configuración requerida</AlertTitle>
          <AlertDescription className="space-y-4">
            <p>
              Para ver video en vivo, necesitas configurar el servidor de streaming (go2rtc).
            </p>
            <div className="space-y-2">
              <p className="font-medium">Pasos:</p>
              <ol className="list-decimal list-inside space-y-1 text-sm">
                <li>Despliega go2rtc en el servidor on-premise (FreePBX)</li>
                <li>Configura las cámaras en go2rtc.yaml</li>
                <li>Agrega la URL de go2rtc en Settings</li>
              </ol>
            </div>
            <div className="flex gap-2">
              <Link href="/dashboard/settings">
                <Button variant="outline" size="sm">
                  <Settings className="h-4 w-4 mr-2" />
                  Ir a Settings
                </Button>
              </Link>
            </div>
          </AlertDescription>
        </Alert>
      ) : go2rtcStatus === 'offline' ? (
        <Alert variant="destructive">
          <VideoOff className="h-4 w-4" />
          <AlertTitle>Servidor de streaming no disponible</AlertTitle>
          <AlertDescription>
            <p>No se puede conectar a {go2rtcUrl}</p>
            <p className="text-sm mt-2">
              Verifica que go2rtc esté corriendo y accesible desde esta red.
            </p>
          </AlertDescription>
        </Alert>
      ) : isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-4">
                <div className="aspect-video bg-muted rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : cameraStreams.length > 0 ? (
        <CameraGrid
          cameras={cameraStreams}
          go2rtcUrl={go2rtcUrl}
          defaultLayout="2x2"
        />
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <VideoOff className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">Sin cámaras configuradas</h3>
            <p className="text-muted-foreground text-center mb-4">
              Agrega cámaras primero para poder ver el video en vivo
            </p>
            <Link href="/dashboard/cameras">
              <Button>
                Ir a Cámaras
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {/* Info Card */}
      <Card className="mt-4">
        <CardHeader>
          <CardTitle className="text-base">Información Técnica</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>
            <strong>Tecnología:</strong> WebRTC via go2rtc
          </p>
          <p>
            <strong>Latencia esperada:</strong> {'<'}1 segundo
          </p>
          <p>
            <strong>Compatibilidad:</strong> Chrome, Firefox, Safari, Edge
          </p>
          <p className="text-xs">
            Nota: Los nombres de streams en go2rtc deben coincidir con los nombres de las cámaras
            (en minúsculas, reemplazando espacios por guiones bajos).
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
