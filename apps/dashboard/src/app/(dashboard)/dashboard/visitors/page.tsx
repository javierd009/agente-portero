'use client'

import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useTenantStore } from '@/store/tenant'
import { apiClient } from '@/lib/api'
import { formatDate, formatRelativeTime } from '@/lib/utils'
import { Plus, UserCheck, Clock, Car, CheckCircle, XCircle, AlertCircle } from 'lucide-react'

export default function VisitorsPage() {
  const { currentTenant } = useTenantStore()
  const tenantId = currentTenant?.id || ''

  const { data: visitors, isLoading } = useQuery({
    queryKey: ['visitors', tenantId],
    queryFn: () => apiClient.getVisitors(tenantId),
    enabled: !!tenantId,
  })

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'approved':
        return { icon: CheckCircle, color: 'text-green-600 bg-green-100', label: 'Aprobado' }
      case 'denied':
        return { icon: XCircle, color: 'text-red-600 bg-red-100', label: 'Denegado' }
      case 'pending':
        return { icon: AlertCircle, color: 'text-yellow-600 bg-yellow-100', label: 'Pendiente' }
      case 'inside':
        return { icon: UserCheck, color: 'text-blue-600 bg-blue-100', label: 'Dentro' }
      case 'exited':
        return { icon: Clock, color: 'text-gray-600 bg-gray-100', label: 'Salió' }
      default:
        return { icon: AlertCircle, color: 'text-gray-600 bg-gray-100', label: status }
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Visitantes</h1>
          <p className="text-muted-foreground">
            Registro y gestión de visitantes
          </p>
        </div>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Registrar Visitante
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Historial de Visitantes</CardTitle>
          <CardDescription>Todos los visitantes registrados</CardDescription>
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
              {visitors?.map((visitor) => {
                const status = getStatusConfig(visitor.status)
                const StatusIcon = status.icon
                return (
                  <div
                    key={visitor.id}
                    className="flex items-center gap-4 p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                  >
                    <div className={`rounded-full p-3 ${status.color}`}>
                      <StatusIcon className="h-4 w-4" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{visitor.name}</p>
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${status.color}`}>
                          {status.label}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1">
                        {visitor.reason && <span>{visitor.reason}</span>}
                        {visitor.vehicle_plate && (
                          <>
                            <span>•</span>
                            <span className="flex items-center gap-1 font-mono">
                              <Car className="h-3 w-3" />
                              {visitor.vehicle_plate}
                            </span>
                          </>
                        )}
                        {visitor.authorized_by && (
                          <>
                            <span>•</span>
                            <span>Por: {visitor.authorized_by}</span>
                          </>
                        )}
                      </div>
                    </div>

                    <div className="text-right text-sm">
                      {visitor.entry_time && (
                        <p className="text-green-600">
                          Entrada: {formatRelativeTime(visitor.entry_time)}
                        </p>
                      )}
                      {visitor.exit_time && (
                        <p className="text-blue-600">
                          Salida: {formatRelativeTime(visitor.exit_time)}
                        </p>
                      )}
                      <p className="text-xs text-muted-foreground mt-1">
                        {formatDate(visitor.created_at)}
                      </p>
                    </div>
                  </div>
                )
              })}
              {(!visitors || visitors.length === 0) && (
                <div className="text-center py-12">
                  <UserCheck className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                  <p className="text-muted-foreground">No hay visitantes registrados</p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
