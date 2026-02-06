'use client'

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useTenantStore } from '@/store/tenant'
import { apiClient, visionService, CondominiumSettings } from '@/lib/api'
import { Building2, Camera, Phone, MessageSquare, Bell, Shield, Cpu, CheckCircle, XCircle, Loader2 } from 'lucide-react'

export default function SettingsPage() {
  const { currentTenant } = useTenantStore()
  const tenantId = currentTenant?.id || ''
  const queryClient = useQueryClient()

  // Form state for Vision Service
  const [visionUrl, setVisionUrl] = useState('')
  const [visionStatus, setVisionStatus] = useState<'idle' | 'testing' | 'online' | 'offline'>('idle')

  // Fetch current condominium settings
  const { data: condominium } = useQuery({
    queryKey: ['condominium', tenantId],
    queryFn: () => apiClient.getCondominium(tenantId),
    enabled: !!tenantId,
  })

  // Update settings when condominium data loads
  useEffect(() => {
    if (condominium?.settings) {
      setVisionUrl(condominium.settings.vision_service_url || '')
    }
  }, [condominium])

  // Save settings mutation
  const saveMutation = useMutation({
    mutationFn: (settings: CondominiumSettings) =>
      apiClient.updateCondominium(tenantId, { settings }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['condominium', tenantId] })
    },
  })

  // Test Vision Service connection
  const testVisionService = async () => {
    if (!visionUrl) return
    setVisionStatus('testing')
    try {
      const isOnline = await visionService.healthCheck(visionUrl)
      setVisionStatus(isOnline ? 'online' : 'offline')
    } catch {
      setVisionStatus('offline')
    }
  }

  // Save Vision Service URL
  const saveVisionSettings = () => {
    const newSettings: CondominiumSettings = {
      ...condominium?.settings,
      vision_service_url: visionUrl || undefined,
    }
    saveMutation.mutate(newSettings)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Configuracion</h1>
        <p className="text-muted-foreground">
          Configura tu condominio y las integraciones
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Vision Service - Edge Computing */}
        <Card className="border-2 border-primary/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cpu className="h-5 w-5" />
              Vision Service (Edge Computing)
            </CardTitle>
            <CardDescription>
              Servicio local para procesamiento de video con baja latencia.
              Corre en FreePBX junto a las camaras.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="vision_url">URL del Vision Service</Label>
              <div className="flex gap-2">
                <Input
                  id="vision_url"
                  placeholder="http://integrateccr.ddns.net:8001"
                  value={visionUrl}
                  onChange={(e) => setVisionUrl(e.target.value)}
                />
                {visionStatus === 'online' && (
                  <CheckCircle className="h-5 w-5 text-green-500 self-center" />
                )}
                {visionStatus === 'offline' && (
                  <XCircle className="h-5 w-5 text-red-500 self-center" />
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                Ejemplo: http://integrateccr.ddns.net:8001
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={testVisionService}
                disabled={!visionUrl || visionStatus === 'testing'}
              >
                {visionStatus === 'testing' ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Probando...
                  </>
                ) : (
                  'Probar Conexion'
                )}
              </Button>
              <Button
                onClick={saveVisionSettings}
                disabled={saveMutation.isPending}
              >
                {saveMutation.isPending ? 'Guardando...' : 'Guardar'}
              </Button>
            </div>
            {visionStatus === 'online' && (
              <p className="text-sm text-green-600">
                Vision Service conectado correctamente
              </p>
            )}
            {visionStatus === 'offline' && (
              <p className="text-sm text-red-600">
                No se pudo conectar. Verifica la URL y que el servicio este corriendo.
              </p>
            )}
          </CardContent>
        </Card>

        {/* General Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              Informacion General
            </CardTitle>
            <CardDescription>Datos basicos del condominio</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Nombre del Condominio</Label>
              <Input id="name" defaultValue={currentTenant?.name} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="slug">Identificador (slug)</Label>
              <Input id="slug" defaultValue={currentTenant?.slug} disabled />
            </div>
            <div className="space-y-2">
              <Label htmlFor="timezone">Zona Horaria</Label>
              <Input id="timezone" defaultValue="America/Mexico_City" />
            </div>
            <Button disabled title="Proximamente">Guardar Cambios</Button>
          </CardContent>
        </Card>

        {/* Camera Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Camera className="h-5 w-5" />
              Camaras Hikvision
            </CardTitle>
            <CardDescription>
              Las camaras se configuran individualmente en la seccion Camaras.
              El Vision Service se conecta automaticamente.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Cuando el Vision Service esta configurado, todas las pruebas de
              camara y capturas de video pasan por el servicio local (edge computing),
              logrando menor latencia y mejor rendimiento.
            </p>
            <Button variant="outline" onClick={() => window.location.href = '/dashboard/cameras'}>
              Ir a Camaras
            </Button>
          </CardContent>
        </Card>

        {/* PBX Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Phone className="h-5 w-5" />
              PBX / Asterisk
            </CardTitle>
            <CardDescription>Conexion al sistema telefonico (FreePBX)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="ari_url">URL de ARI</Label>
              <Input id="ari_url" placeholder="http://integrateccr.ddns.net:8880/ari" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="ari_user">Usuario ARI</Label>
                <Input id="ari_user" placeholder="asterisk" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ari_pass">Contrasena</Label>
                <Input id="ari_pass" type="password" />
              </div>
            </div>
            <Button variant="outline" disabled title="Proximamente">
              Probar Conexion
            </Button>
          </CardContent>
        </Card>

        {/* WhatsApp Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              WhatsApp (Evolution API)
            </CardTitle>
            <CardDescription>Notificaciones por WhatsApp</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="evolution_url">URL de Evolution API</Label>
              <Input id="evolution_url" defaultValue="https://devevoapi.integratec-ia.com" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="evolution_instance">Nombre de Instancia</Label>
              <Input id="evolution_instance" defaultValue="Sitnova_portero" />
            </div>
            <Button variant="outline" disabled title="Proximamente">
              Probar Conexion
            </Button>
          </CardContent>
        </Card>

        {/* Notification Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Notificaciones
            </CardTitle>
            <CardDescription>Preferencias de notificacion</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Notificar llegada de visitantes</p>
                <p className="text-sm text-muted-foreground">
                  Enviar WhatsApp cuando llegue un visitante
                </p>
              </div>
              <input type="checkbox" defaultChecked className="h-4 w-4" />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Alertas de acceso denegado</p>
                <p className="text-sm text-muted-foreground">
                  Notificar intentos de acceso no autorizados
                </p>
              </div>
              <input type="checkbox" defaultChecked className="h-4 w-4" />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Resumen diario</p>
                <p className="text-sm text-muted-foreground">
                  Enviar resumen de actividad del dia
                </p>
              </div>
              <input type="checkbox" className="h-4 w-4" />
            </div>
          </CardContent>
        </Card>

        {/* Security Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Seguridad
            </CardTitle>
            <CardDescription>Configuracion de seguridad</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Auto-apertura por placa</p>
                <p className="text-sm text-muted-foreground">
                  Abrir automaticamente para vehiculos registrados
                </p>
              </div>
              <input type="checkbox" defaultChecked className="h-4 w-4" />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Verificacion doble</p>
                <p className="text-sm text-muted-foreground">
                  Requerir confirmacion del residente
                </p>
              </div>
              <input type="checkbox" className="h-4 w-4" />
            </div>
            <div className="space-y-2">
              <Label>Tiempo maximo de espera (segundos)</Label>
              <Input type="number" defaultValue={30} />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
