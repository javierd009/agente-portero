'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useTenantStore } from '@/store/tenant'
import { Building2, Camera, Phone, MessageSquare, Bell, Shield } from 'lucide-react'

export default function SettingsPage() {
  const { currentTenant } = useTenantStore()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Configuración</h1>
        <p className="text-muted-foreground">
          Configura tu condominio y las integraciones
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* General Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              Información General
            </CardTitle>
            <CardDescription>Datos básicos del condominio</CardDescription>
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
            <Button>Guardar Cambios</Button>
          </CardContent>
        </Card>

        {/* Camera Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Camera className="h-5 w-5" />
              Cámaras Hikvision
            </CardTitle>
            <CardDescription>Configuración de cámaras ISAPI</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="camera_host">Host / IP</Label>
              <Input id="camera_host" placeholder="192.168.1.100" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="camera_user">Usuario</Label>
                <Input id="camera_user" placeholder="admin" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="camera_pass">Contraseña</Label>
                <Input id="camera_pass" type="password" />
              </div>
            </div>
            <Button variant="outline">Probar Conexión</Button>
          </CardContent>
        </Card>

        {/* PBX Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Phone className="h-5 w-5" />
              PBX / Asterisk
            </CardTitle>
            <CardDescription>Conexión al sistema telefónico</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="ari_url">URL de ARI</Label>
              <Input id="ari_url" placeholder="http://pbx:8088/ari" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="ari_user">Usuario ARI</Label>
                <Input id="ari_user" placeholder="asterisk" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ari_pass">Contraseña</Label>
                <Input id="ari_pass" type="password" />
              </div>
            </div>
            <Button variant="outline">Probar Conexión</Button>
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
              <Input id="evolution_url" placeholder="http://localhost:8080" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="evolution_key">API Key</Label>
              <Input id="evolution_key" type="password" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="evolution_instance">Nombre de Instancia</Label>
              <Input id="evolution_instance" placeholder="agente-portero" />
            </div>
            <Button variant="outline">Probar Conexión</Button>
          </CardContent>
        </Card>

        {/* Notification Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Notificaciones
            </CardTitle>
            <CardDescription>Preferencias de notificación</CardDescription>
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
                  Enviar resumen de actividad del día
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
            <CardDescription>Configuración de seguridad</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Auto-apertura por placa</p>
                <p className="text-sm text-muted-foreground">
                  Abrir automáticamente para vehículos registrados
                </p>
              </div>
              <input type="checkbox" defaultChecked className="h-4 w-4" />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Verificación doble</p>
                <p className="text-sm text-muted-foreground">
                  Requerir confirmación del residente
                </p>
              </div>
              <input type="checkbox" className="h-4 w-4" />
            </div>
            <div className="space-y-2">
              <Label>Tiempo máximo de espera (segundos)</Label>
              <Input type="number" defaultValue={30} />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
