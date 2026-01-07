'use client'

import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useTenantStore } from '@/store/tenant'
import { apiClient } from '@/lib/api'
import { formatRelativeTime } from '@/lib/utils'
import {
  Users,
  UserCheck,
  Car,
  Shield,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react'

export default function DashboardPage() {
  const { currentTenant } = useTenantStore()
  const tenantId = currentTenant?.id || ''

  const { data: accessLogs } = useQuery({
    queryKey: ['accessLogs', tenantId],
    queryFn: () => apiClient.getAccessLogs(tenantId, { limit: 10 }),
    enabled: !!tenantId,
  })

  const { data: residents } = useQuery({
    queryKey: ['residents', tenantId],
    queryFn: () => apiClient.getResidents(tenantId),
    enabled: !!tenantId,
  })

  const { data: visitors } = useQuery({
    queryKey: ['visitors', tenantId],
    queryFn: () => apiClient.getVisitors(tenantId),
    enabled: !!tenantId,
  })

  const { data: recentPlates } = useQuery({
    queryKey: ['recentPlates', tenantId],
    queryFn: () => apiClient.getRecentPlates(tenantId),
    enabled: !!tenantId,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const stats = [
    {
      title: 'Residentes',
      value: residents?.length || 0,
      icon: Users,
      change: '+2 este mes',
      trend: 'up',
    },
    {
      title: 'Visitantes Hoy',
      value: visitors?.filter(v => {
        const today = new Date().toDateString()
        return new Date(v.created_at).toDateString() === today
      }).length || 0,
      icon: UserCheck,
      change: 'vs ayer',
      trend: 'up',
    },
    {
      title: 'Accesos Hoy',
      value: accessLogs?.filter(l => {
        const today = new Date().toDateString()
        return new Date(l.created_at).toDateString() === today
      }).length || 0,
      icon: Car,
      change: 'entradas/salidas',
      trend: 'neutral',
    },
    {
      title: 'Placas Detectadas',
      value: recentPlates?.plates?.length || 0,
      icon: Shield,
      change: 'últimos 5 min',
      trend: 'neutral',
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">
          Resumen de actividad de {currentTenant?.name || 'tu condominio'}
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.title}
              </CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                {stat.trend === 'up' && <ArrowUpRight className="h-3 w-3 text-green-500" />}
                {stat.trend === 'down' && <ArrowDownRight className="h-3 w-3 text-red-500" />}
                {stat.change}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Recent Activity */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent Access Logs */}
        <Card>
          <CardHeader>
            <CardTitle>Accesos Recientes</CardTitle>
            <CardDescription>Últimos movimientos registrados</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {accessLogs?.slice(0, 5).map((log) => (
                <div key={log.id} className="flex items-center gap-4">
                  <div className={`rounded-full p-2 ${
                    log.event_type === 'entry' ? 'bg-green-100 text-green-600' :
                    log.event_type === 'exit' ? 'bg-blue-100 text-blue-600' :
                    'bg-red-100 text-red-600'
                  }`}>
                    <Car className="h-4 w-4" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">
                      {log.visitor_name || log.vehicle_plate || 'Acceso'}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {log.access_point} - {log.authorization_method}
                    </p>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {formatRelativeTime(log.created_at)}
                  </p>
                </div>
              ))}
              {(!accessLogs || accessLogs.length === 0) && (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No hay accesos recientes
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Recent Plates */}
        <Card>
          <CardHeader>
            <CardTitle>Placas Detectadas</CardTitle>
            <CardDescription>Últimas placas capturadas por cámaras</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentPlates?.plates?.slice(0, 5).map((plate, idx) => (
                <div key={idx} className="flex items-center gap-4">
                  <div className="rounded-full p-2 bg-primary/10 text-primary">
                    <Shield className="h-4 w-4" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-mono font-bold">{plate.plate}</p>
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
                  No hay placas detectadas recientemente
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
