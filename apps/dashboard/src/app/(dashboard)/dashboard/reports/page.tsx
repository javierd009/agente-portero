'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useTenantStore } from '@/store/tenant'
import { apiClient, type Report } from '@/lib/api'
import { formatRelativeTime } from '@/lib/utils'
import {
  FileText,
  AlertCircle,
  CheckCircle,
  Clock,
  Filter,
  RefreshCw,
  MessageSquare,
  Wrench,
  Shield,
  Volume2,
  Sparkles,
  ChevronRight,
} from 'lucide-react'
import { toast } from 'sonner'

const REPORT_TYPE_ICONS: Record<string, typeof Wrench> = {
  maintenance: Wrench,
  security: Shield,
  noise: Volume2,
  cleaning: Sparkles,
  other: FileText,
}

const REPORT_TYPE_LABELS: Record<string, string> = {
  maintenance: 'Mantenimiento',
  security: 'Seguridad',
  noise: 'Ruido',
  cleaning: 'Limpieza',
  other: 'Otro',
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  in_progress: 'bg-blue-100 text-blue-800 border-blue-200',
  resolved: 'bg-green-100 text-green-800 border-green-200',
  closed: 'bg-gray-100 text-gray-800 border-gray-200',
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pendiente',
  in_progress: 'En Progreso',
  resolved: 'Resuelto',
  closed: 'Cerrado',
}

const URGENCY_COLORS: Record<string, string> = {
  low: 'text-gray-500',
  normal: 'text-blue-500',
  high: 'text-orange-500',
  urgent: 'text-red-500',
}

export default function ReportsPage() {
  const { currentTenant } = useTenantStore()
  const tenantId = currentTenant?.id || ''
  const queryClient = useQueryClient()

  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [selectedReport, setSelectedReport] = useState<Report | null>(null)

  // Fetch reports
  const { data: reports, isLoading, refetch } = useQuery({
    queryKey: ['reports', tenantId, statusFilter, typeFilter],
    queryFn: () => apiClient.getReports(tenantId, {
      status: statusFilter !== 'all' ? statusFilter : undefined,
      report_type: typeFilter !== 'all' ? typeFilter : undefined,
    }),
    enabled: !!tenantId,
  })

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['reportStats', tenantId],
    queryFn: () => apiClient.getReportStats(tenantId),
    enabled: !!tenantId,
  })

  // Update report mutation
  const updateReportMutation = useMutation({
    mutationFn: ({ reportId, data }: { reportId: string; data: any }) =>
      apiClient.updateReport(tenantId, reportId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
      queryClient.invalidateQueries({ queryKey: ['reportStats'] })
      toast.success('Reporte actualizado correctamente')
      setSelectedReport(null)
    },
    onError: (error) => {
      toast.error(`Error al actualizar: ${error.message}`)
    },
  })

  const handleStatusChange = (report: Report, newStatus: string) => {
    updateReportMutation.mutate({
      reportId: report.id,
      data: { status: newStatus },
    })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Reportes</h1>
          <p className="text-muted-foreground">
            Gestiona incidentes y solicitudes de mantenimiento
          </p>
        </div>
        <Button
          variant="outline"
          size="icon"
          onClick={() => refetch()}
          disabled={isLoading}
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Reportes
            </CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Pendientes
            </CardTitle>
            <Clock className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.pending || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              En Progreso
            </CardTitle>
            <AlertCircle className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.in_progress || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Resueltos
            </CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.resolved || 0}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filtros
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <div className="flex-1">
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Estado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los estados</SelectItem>
                  <SelectItem value="pending">Pendiente</SelectItem>
                  <SelectItem value="in_progress">En Progreso</SelectItem>
                  <SelectItem value="resolved">Resuelto</SelectItem>
                  <SelectItem value="closed">Cerrado</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex-1">
              <Select value={typeFilter} onValueChange={setTypeFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="Tipo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los tipos</SelectItem>
                  <SelectItem value="maintenance">Mantenimiento</SelectItem>
                  <SelectItem value="security">Seguridad</SelectItem>
                  <SelectItem value="noise">Ruido</SelectItem>
                  <SelectItem value="cleaning">Limpieza</SelectItem>
                  <SelectItem value="other">Otro</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Reports List */}
      <Card>
        <CardHeader>
          <CardTitle>Reportes</CardTitle>
          <CardDescription>
            {reports?.length || 0} reporte(s) encontrado(s)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {isLoading && (
              <p className="text-center text-muted-foreground py-8">
                Cargando reportes...
              </p>
            )}

            {!isLoading && (!reports || reports.length === 0) && (
              <p className="text-center text-muted-foreground py-8">
                No hay reportes que mostrar
              </p>
            )}

            {reports?.map((report) => {
              const Icon = REPORT_TYPE_ICONS[report.report_type] || FileText

              return (
                <Card key={report.id} className="hover:shadow-md transition-shadow">
                  <CardContent className="p-6">
                    <div className="flex items-start gap-4">
                      {/* Icon */}
                      <div className="rounded-full p-3 bg-primary/10 text-primary">
                        <Icon className="h-5 w-5" />
                      </div>

                      {/* Content */}
                      <div className="flex-1 space-y-2">
                        <div className="flex items-start justify-between">
                          <div className="space-y-1">
                            <h3 className="font-semibold text-lg">{report.title}</h3>
                            <p className="text-sm text-muted-foreground">
                              {report.description}
                            </p>
                          </div>
                        </div>

                        {/* Metadata */}
                        <div className="flex flex-wrap gap-2 text-xs">
                          <Badge variant="outline" className={STATUS_COLORS[report.status]}>
                            {STATUS_LABELS[report.status]}
                          </Badge>
                          <Badge variant="outline">
                            {REPORT_TYPE_LABELS[report.report_type]}
                          </Badge>
                          {report.location && (
                            <span className="text-muted-foreground">📍 {report.location}</span>
                          )}
                          <span className={`font-medium ${URGENCY_COLORS[report.urgency]}`}>
                            Urgencia: {report.urgency}
                          </span>
                          <span className="text-muted-foreground">
                            Fuente: {report.source}
                          </span>
                          <span className="text-muted-foreground ml-auto">
                            {formatRelativeTime(report.created_at)}
                          </span>
                        </div>

                        {/* Actions */}
                        <div className="flex gap-2 pt-2">
                          {report.status === 'pending' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleStatusChange(report, 'in_progress')}
                            >
                              Comenzar
                            </Button>
                          )}
                          {report.status === 'in_progress' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleStatusChange(report, 'resolved')}
                            >
                              Marcar Resuelto
                            </Button>
                          )}
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setSelectedReport(report)}
                          >
                            Ver Detalles
                            <ChevronRight className="h-4 w-4 ml-1" />
                          </Button>
                        </div>

                        {/* Resolution Notes */}
                        {report.resolution_notes && (
                          <div className="mt-3 p-3 bg-muted rounded-md">
                            <p className="text-sm font-medium mb-1">Notas de Resolución:</p>
                            <p className="text-sm text-muted-foreground">
                              {report.resolution_notes}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Report Details Modal would go here */}
      {selectedReport && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-full max-w-2xl max-h-[80vh] overflow-y-auto m-4">
            <CardHeader>
              <CardTitle>Detalles del Reporte</CardTitle>
              <CardDescription>ID: {selectedReport.id}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h3 className="font-semibold mb-2">{selectedReport.title}</h3>
                <p className="text-sm text-muted-foreground">{selectedReport.description}</p>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="font-medium">Estado:</p>
                  <Badge variant="outline" className={STATUS_COLORS[selectedReport.status]}>
                    {STATUS_LABELS[selectedReport.status]}
                  </Badge>
                </div>
                <div>
                  <p className="font-medium">Tipo:</p>
                  <p className="text-muted-foreground">
                    {REPORT_TYPE_LABELS[selectedReport.report_type]}
                  </p>
                </div>
                <div>
                  <p className="font-medium">Urgencia:</p>
                  <p className={URGENCY_COLORS[selectedReport.urgency]}>
                    {selectedReport.urgency}
                  </p>
                </div>
                <div>
                  <p className="font-medium">Ubicación:</p>
                  <p className="text-muted-foreground">{selectedReport.location || 'N/A'}</p>
                </div>
                <div>
                  <p className="font-medium">Fuente:</p>
                  <p className="text-muted-foreground">{selectedReport.source}</p>
                </div>
                <div>
                  <p className="font-medium">Creado:</p>
                  <p className="text-muted-foreground">
                    {new Date(selectedReport.created_at).toLocaleString()}
                  </p>
                </div>
              </div>

              {selectedReport.resolution_notes && (
                <div>
                  <p className="font-medium mb-1">Notas de Resolución:</p>
                  <p className="text-sm text-muted-foreground p-3 bg-muted rounded-md">
                    {selectedReport.resolution_notes}
                  </p>
                </div>
              )}

              <div className="flex gap-2 justify-end pt-4">
                <Button
                  variant="outline"
                  onClick={() => setSelectedReport(null)}
                >
                  Cerrar
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
