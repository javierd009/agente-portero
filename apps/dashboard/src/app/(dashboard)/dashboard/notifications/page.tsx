'use client'

import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useTenantStore } from '@/store/tenant'
import { apiClient } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { Bell, MessageSquare, Phone, Mail, CheckCircle, Clock, XCircle } from 'lucide-react'

export default function NotificationsPage() {
  const { currentTenant } = useTenantStore()
  const tenantId = currentTenant?.id || ''

  const { data: notifications, isLoading } = useQuery({
    queryKey: ['notifications', tenantId],
    queryFn: () => apiClient.getNotifications(tenantId),
    enabled: !!tenantId,
  })

  const getChannelIcon = (channel: string) => {
    switch (channel) {
      case 'whatsapp':
        return <MessageSquare className="h-4 w-4" />
      case 'sms':
        return <Phone className="h-4 w-4" />
      case 'email':
        return <Mail className="h-4 w-4" />
      default:
        return <Bell className="h-4 w-4" />
    }
  }

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'delivered':
        return { icon: CheckCircle, color: 'text-green-600', label: 'Entregado' }
      case 'sent':
        return { icon: CheckCircle, color: 'text-blue-600', label: 'Enviado' }
      case 'pending':
        return { icon: Clock, color: 'text-yellow-600', label: 'Pendiente' }
      case 'failed':
        return { icon: XCircle, color: 'text-red-600', label: 'Fallido' }
      default:
        return { icon: Clock, color: 'text-gray-600', label: status }
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Notificaciones</h1>
        <p className="text-muted-foreground">
          Historial de notificaciones enviadas a residentes
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Historial</CardTitle>
          <CardDescription>WhatsApp, SMS y otras notificaciones</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="animate-pulse flex items-start gap-4 p-4 border rounded-lg">
                  <div className="h-10 w-10 bg-muted rounded-full" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-muted rounded w-1/3" />
                    <div className="h-3 bg-muted rounded w-2/3" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {notifications?.map((notification) => {
                const status = getStatusConfig(notification.status)
                const StatusIcon = status.icon
                return (
                  <div
                    key={notification.id}
                    className="flex items-start gap-4 p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                  >
                    <div className="rounded-full p-3 bg-primary/10 text-primary">
                      {getChannelIcon(notification.channel)}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-medium">{notification.title}</p>
                        <span className={`flex items-center gap-1 text-xs ${status.color}`}>
                          <StatusIcon className="h-3 w-3" />
                          {status.label}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">
                        {notification.message}
                      </p>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        <span className="capitalize">{notification.channel}</span>
                        <span>•</span>
                        <span>{notification.recipient}</span>
                        <span>•</span>
                        <span>{notification.notification_type.replace(/_/g, ' ')}</span>
                      </div>
                    </div>

                    <div className="text-right text-xs text-muted-foreground">
                      <p>{formatDate(notification.created_at)}</p>
                      {notification.delivered_at && (
                        <p className="text-green-600">
                          Entregado: {formatDate(notification.delivered_at)}
                        </p>
                      )}
                    </div>
                  </div>
                )
              })}
              {(!notifications || notifications.length === 0) && (
                <div className="text-center py-12">
                  <Bell className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                  <p className="text-muted-foreground">No hay notificaciones</p>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
