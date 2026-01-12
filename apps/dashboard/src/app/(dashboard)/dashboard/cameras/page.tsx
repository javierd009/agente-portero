'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { useTenantStore } from '@/store/tenant'
import { apiClient, Camera, CameraCreate } from '@/lib/api'
import { formatRelativeTime } from '@/lib/utils'
import {
  Camera as CameraIcon,
  Plus,
  Wifi,
  WifiOff,
  Settings,
  Trash2,
  RefreshCw,
  Image,
  Shield,
  Eye,
} from 'lucide-react'

export default function CamerasPage() {
  const { currentTenant } = useTenantStore()
  const tenantId = currentTenant?.id || ''
  const queryClient = useQueryClient()

  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false)
  const [selectedCamera, setSelectedCamera] = useState<Camera | null>(null)
  const [snapshotData, setSnapshotData] = useState<string | null>(null)
  const [isLoadingSnapshot, setIsLoadingSnapshot] = useState(false)

  // Form state
  const [formData, setFormData] = useState<Partial<CameraCreate>>({
    name: '',
    location: '',
    host: '',
    port: 80,
    username: 'admin',
    password: '',
    camera_type: 'hikvision',
  })

  // Fetch cameras
  const { data: cameras, isLoading } = useQuery({
    queryKey: ['cameras', tenantId],
    queryFn: () => apiClient.getCameras(tenantId),
    enabled: !!tenantId,
    refetchInterval: 30000,
  })

  // Fetch camera events
  const { data: cameraEvents } = useQuery({
    queryKey: ['cameraEvents', tenantId],
    queryFn: () => apiClient.getCameraEvents(tenantId, { limit: 20 }),
    enabled: !!tenantId,
    refetchInterval: 15000,
  })

  // Create camera mutation
  const createMutation = useMutation({
    mutationFn: (data: CameraCreate) => apiClient.createCamera(tenantId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cameras', tenantId] })
      setIsAddDialogOpen(false)
      resetForm()
    },
  })

  // Delete camera mutation
  const deleteMutation = useMutation({
    mutationFn: (cameraId: string) => apiClient.deleteCamera(tenantId, cameraId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cameras', tenantId] })
    },
  })

  // Test connection mutation
  const testMutation = useMutation({
    mutationFn: (cameraId: string) => apiClient.testCameraConnection(tenantId, cameraId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cameras', tenantId] })
    },
  })

  const resetForm = () => {
    setFormData({
      name: '',
      location: '',
      host: '',
      port: 80,
      username: 'admin',
      password: '',
      camera_type: 'hikvision',
    })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.name || !formData.host || !formData.password) return

    createMutation.mutate({
      condominium_id: tenantId,
      name: formData.name!,
      location: formData.location,
      host: formData.host!,
      port: formData.port || 80,
      username: formData.username || 'admin',
      password: formData.password!,
      camera_type: formData.camera_type || 'hikvision',
    })
  }

  const handleGetSnapshot = async (camera: Camera) => {
    setSelectedCamera(camera)
    setIsLoadingSnapshot(true)
    setSnapshotData(null)

    try {
      const result = await apiClient.getCameraSnapshot(tenantId, camera.id)
      setSnapshotData(result.image)
    } catch (error) {
      console.error('Failed to get snapshot:', error)
    } finally {
      setIsLoadingSnapshot(false)
    }
  }

  const onlineCameras = cameras?.filter(c => c.is_online).length || 0
  const totalCameras = cameras?.length || 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Cámaras VMS</h1>
          <p className="text-muted-foreground">
            Gestión y visualización de cámaras Hikvision
          </p>
        </div>
        <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Agregar Cámara
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>Agregar Nueva Cámara</DialogTitle>
              <DialogDescription>
                Configura los datos de conexión de la cámara Hikvision
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit}>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <Label htmlFor="name">Nombre</Label>
                  <Input
                    id="name"
                    placeholder="Entrada Principal"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="location">Ubicación</Label>
                  <Input
                    id="location"
                    placeholder="Portón vehicular"
                    value={formData.location}
                    onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  />
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div className="col-span-2">
                    <Label htmlFor="host">IP de la Cámara</Label>
                    <Input
                      id="host"
                      placeholder="192.168.1.100"
                      value={formData.host}
                      onChange={(e) => setFormData({ ...formData, host: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="port">Puerto</Label>
                    <Input
                      id="port"
                      type="number"
                      value={formData.port}
                      onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) })}
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label htmlFor="username">Usuario</Label>
                    <Input
                      id="username"
                      value={formData.username}
                      onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    />
                  </div>
                  <div>
                    <Label htmlFor="password">Contraseña</Label>
                    <Input
                      id="password"
                      type="password"
                      value={formData.password}
                      onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                      required
                    />
                  </div>
                </div>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setIsAddDialogOpen(false)}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? 'Guardando...' : 'Guardar'}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Cámaras</CardTitle>
            <CameraIcon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalCameras}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">En Línea</CardTitle>
            <Wifi className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{onlineCameras}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Eventos Hoy</CardTitle>
            <Eye className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{cameraEvents?.length || 0}</div>
          </CardContent>
        </Card>
      </div>

      {/* Camera Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {isLoading ? (
          [...Array(3)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-5 bg-muted rounded w-1/2" />
              </CardHeader>
              <CardContent>
                <div className="aspect-video bg-muted rounded" />
              </CardContent>
            </Card>
          ))
        ) : cameras && cameras.length > 0 ? (
          cameras.map((camera) => (
            <Card key={camera.id} className="overflow-hidden">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{camera.name}</CardTitle>
                  <Badge variant={camera.is_online ? 'default' : 'secondary'}>
                    {camera.is_online ? (
                      <><Wifi className="h-3 w-3 mr-1" /> Online</>
                    ) : (
                      <><WifiOff className="h-3 w-3 mr-1" /> Offline</>
                    )}
                  </Badge>
                </div>
                {camera.location && (
                  <CardDescription>{camera.location}</CardDescription>
                )}
              </CardHeader>
              <CardContent>
                {/* Snapshot Preview */}
                <div
                  className="aspect-video bg-muted rounded-lg flex items-center justify-center cursor-pointer hover:bg-muted/80 transition-colors mb-3"
                  onClick={() => handleGetSnapshot(camera)}
                >
                  {selectedCamera?.id === camera.id && snapshotData ? (
                    <img
                      src={snapshotData}
                      alt={camera.name}
                      className="w-full h-full object-cover rounded-lg"
                    />
                  ) : selectedCamera?.id === camera.id && isLoadingSnapshot ? (
                    <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
                  ) : (
                    <div className="text-center">
                      <Image className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                      <p className="text-xs text-muted-foreground">Click para snapshot</p>
                    </div>
                  )}
                </div>

                {/* Capabilities */}
                <div className="flex gap-2 mb-3">
                  {camera.has_anpr && (
                    <Badge variant="outline" className="text-xs">
                      <Shield className="h-3 w-3 mr-1" /> ANPR
                    </Badge>
                  )}
                  {camera.has_ptz && (
                    <Badge variant="outline" className="text-xs">PTZ</Badge>
                  )}
                  {camera.has_face && (
                    <Badge variant="outline" className="text-xs">Face</Badge>
                  )}
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1"
                    onClick={() => testMutation.mutate(camera.id)}
                    disabled={testMutation.isPending}
                  >
                    <RefreshCw className={`h-4 w-4 mr-1 ${testMutation.isPending ? 'animate-spin' : ''}`} />
                    Test
                  </Button>
                  <Button variant="outline" size="sm">
                    <Settings className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-destructive"
                    onClick={() => {
                      if (confirm('¿Eliminar esta cámara?')) {
                        deleteMutation.mutate(camera.id)
                      }
                    }}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>

                {/* Last seen */}
                {camera.last_seen && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Última conexión: {formatRelativeTime(camera.last_seen)}
                  </p>
                )}
              </CardContent>
            </Card>
          ))
        ) : (
          <Card className="col-span-full">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <CameraIcon className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">Sin cámaras configuradas</h3>
              <p className="text-muted-foreground text-center mb-4">
                Agrega tu primera cámara Hikvision para comenzar
              </p>
              <Button onClick={() => setIsAddDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Agregar Cámara
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Recent Events */}
      {cameraEvents && cameraEvents.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Eventos Recientes</CardTitle>
            <CardDescription>Últimos eventos de las cámaras</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-[300px] overflow-y-auto">
              {cameraEvents.map((event) => (
                <div
                  key={event.id}
                  className="flex items-center gap-3 p-2 border rounded-lg"
                >
                  <div className="rounded-full p-2 bg-primary/10 text-primary">
                    {event.plate_number ? (
                      <Shield className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">
                      {event.event_type.replace(/_/g, ' ')}
                      {event.plate_number && (
                        <span className="ml-2 font-mono text-primary">{event.plate_number}</span>
                      )}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Cámara: {event.camera_id}
                    </p>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {formatRelativeTime(event.created_at)}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
