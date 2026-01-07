'use client'

import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useTenantStore } from '@/store/tenant'
import { apiClient } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { Car, LogIn, LogOut, XCircle, Bot, User, Camera } from 'lucide-react'

export default function AccessLogsPage() {
  const { currentTenant } = useTenantStore()
  const tenantId = currentTenant?.id || ''

  const { data: accessLogs, isLoading } = useQuery({
    queryKey: ['accessLogs', tenantId],
    queryFn: () => apiClient.getAccessLogs(tenantId, { limit: 50 }),
    enabled: !!tenantId,
    refetchInterval: 30000,
  })

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'entry':
      case 'visitor_entry':
        return <LogIn className="h-4 w-4" />
      case 'exit':
        return <LogOut className="h-4 w-4" />
      case 'denied':
        return <XCircle className="h-4 w-4" />
      default:
        return <Car className="h-4 w-4" />
    }
  }

  const getEventColor = (type: string) => {
    switch (type) {
      case 'entry':
      case 'visitor_entry':
        return 'bg-green-100 text-green-600 border-green-200'
      case 'exit':
        return 'bg-blue-100 text-blue-600 border-blue-200'
      case 'denied':
        return 'bg-red-100 text-red-600 border-red-200'
      default:
        return 'bg-gray-100 text-gray-600 border-gray-200'
    }
  }

  const getAuthMethodIcon = (method: string) => {
    switch (method) {
      case 'ai_agent':
        return <Bot className="h-3 w-3" />
      case 'manual_guard':
        return <User className="h-3 w-3" />
      case 'auto_plate':
        return <Camera className="h-3 w-3" />
      default:
        return null
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Registro de Accesos</h1>
        <p className="text-muted-foreground">
          Historial de entradas, salidas y eventos de acceso
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Actividad Reciente</CardTitle>
          <CardDescription>Se actualiza automáticamente cada 30 segundos</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="animate-pulse flex items-center gap-4 p-4 border rounded-lg">
                  <div className="h-10 w-10 bg-muted rounded-full" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-muted rounded w-1/3" />
                    <div className="h-3 bg-muted rounded w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {accessLogs?.map((log) => (
                <div
                  key={log.id}
                  className="flex items-center gap-4 p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className={`rounded-full p-3 border ${getEventColor(log.event_type)}`}>
                    {getEventIcon(log.event_type)}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium truncate">
                        {log.visitor_name || log.vehicle_plate || 'Acceso registrado'}
                      </p>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${getEventColor(log.event_type)}`}>
                        {log.event_type === 'entry' || log.event_type === 'visitor_entry' ? 'Entrada' :
                         log.event_type === 'exit' ? 'Salida' :
                         log.event_type === 'denied' ? 'Denegado' : log.event_type}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1">
                      <span>{log.access_point}</span>
                      {log.vehicle_plate && log.visitor_name && (
                        <>
                          <span>•</span>
                          <span className="font-mono">{log.vehicle_plate}</span>
                        </>
                      )}
                      <span>•</span>
                      <span className="flex items-center gap-1">
                        {getAuthMethodIcon(log.authorization_method)}
                        {log.authorization_method === 'ai_agent' ? 'Agente IA' :
                         log.authorization_method === 'manual_guard' ? 'Guardia' :
                         log.authorization_method === 'auto_plate' ? 'Auto (placa)' :
                         log.authorization_method}
                      </span>
                    </div>
                  </div>

                  <div className="text-right">
                    <p className="text-sm">{formatDate(log.created_at)}</p>
                    {log.confidence_score && (
                      <p className="text-xs text-muted-foreground">
                        Confianza: {(log.confidence_score * 100).toFixed(0)}%
                      </p>
                    )}
                  </div>
                </div>
              ))}
              {(!accessLogs || accessLogs.length === 0) && (
                <div className="text-center py-12">
                  <Car className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                  <p className="text-muted-foreground">No hay registros de acceso</p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
