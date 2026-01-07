'use client'

import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useTenantStore } from '@/store/tenant'
import { apiClient } from '@/lib/api'
import { formatRelativeTime } from '@/lib/utils'
import { Camera, Shield, Eye, AlertTriangle } from 'lucide-react'

export default function CamerasPage() {
  const { currentTenant } = useTenantStore()
  const tenantId = currentTenant?.id || ''

  const { data: cameraEvents, isLoading } = useQuery({
    queryKey: ['cameraEvents', tenantId],
    queryFn: () => apiClient.getCameraEvents(tenantId, { limit: 50 }),
    enabled: !!tenantId,
    refetchInterval: 15000,
  })

  const { data: recentPlates } = useQuery({
    queryKey: ['recentPlates', tenantId],
    queryFn: () => apiClient.getRecentPlates(tenantId),
    enabled: !!tenantId,
    refetchInterval: 10000,
  })

  const getEventIcon = (type: string) => {
    if (type.includes('plate')) return <Shield className="h-4 w-4" />
    if (type.includes('motion')) return <Eye className="h-4 w-4" />
    if (type.includes('alert')) return <AlertTriangle className="h-4 w-4" />
    return <Camera className="h-4 w-4" />
  }

  const getEventColor = (type: string) => {
    if (type.includes('plate')) return 'bg-primary/10 text-primary'
    if (type.includes('motion')) return 'bg-yellow-100 text-yellow-600'
    if (type.includes('alert')) return 'bg-red-100 text-red-600'
    return 'bg-gray-100 text-gray-600'
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Cámaras</h1>
        <p className="text-muted-foreground">
          Eventos de cámaras y detección de placas
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Recent Plates - Highlighted */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              Placas Recientes
            </CardTitle>
            <CardDescription>Últimos 5 minutos</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recentPlates?.plates?.map((plate, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-3 bg-primary/5 rounded-lg border border-primary/20"
                >
                  <div>
                    <p className="font-mono text-lg font-bold text-primary">
                      {plate.plate}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Cámara: {plate.camera_id}
                    </p>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {formatRelativeTime(plate.timestamp)}
                  </p>
                </div>
              ))}
              {(!recentPlates?.plates || recentPlates.plates.length === 0) && (
                <p className="text-sm text-muted-foreground text-center py-4">
                  Sin placas detectadas
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* All Camera Events */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Eventos de Cámara</CardTitle>
            <CardDescription>Se actualiza cada 15 segundos</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="animate-pulse flex items-center gap-3 p-3 border rounded-lg">
                    <div className="h-8 w-8 bg-muted rounded-full" />
                    <div className="flex-1 space-y-2">
                      <div className="h-4 bg-muted rounded w-1/4" />
                      <div className="h-3 bg-muted rounded w-1/3" />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-2 max-h-[500px] overflow-y-auto">
                {cameraEvents?.map((event) => (
                  <div
                    key={event.id}
                    className="flex items-center gap-3 p-3 border rounded-lg hover:bg-muted/50 transition-colors"
                  >
                    <div className={`rounded-full p-2 ${getEventColor(event.event_type)}`}>
                      {getEventIcon(event.event_type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium">
                          {event.event_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </p>
                        {event.plate_number && (
                          <span className="px-2 py-0.5 bg-primary/10 text-primary rounded text-xs font-mono font-bold">
                            {event.plate_number}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Cámara: {event.camera_id}
                        {event.plate_confidence && ` • Confianza: ${(event.plate_confidence * 100).toFixed(0)}%`}
                      </p>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {formatRelativeTime(event.created_at)}
                    </p>
                  </div>
                ))}
                {(!cameraEvents || cameraEvents.length === 0) && (
                  <div className="text-center py-8">
                    <Camera className="h-10 w-10 mx-auto text-muted-foreground/50 mb-3" />
                    <p className="text-sm text-muted-foreground">
                      No hay eventos de cámara
                    </p>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
