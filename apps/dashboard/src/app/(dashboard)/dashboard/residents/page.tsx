'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useTenantStore } from '@/store/tenant'
import { apiClient, ResidentCreate } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { Plus, Search, Phone, Mail, MessageSquare, Home } from 'lucide-react'

export default function ResidentsPage() {
  const { currentTenant } = useTenantStore()
  const tenantId = currentTenant?.id || ''
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Form state
  const [formData, setFormData] = useState<Partial<ResidentCreate>>({
    name: '',
    unit: '',
    phone: '',
    email: '',
    whatsapp: '',
  })

  const { data: residents, isLoading } = useQuery({
    queryKey: ['residents', tenantId],
    queryFn: () => apiClient.getResidents(tenantId),
    enabled: !!tenantId,
  })

  // Create resident mutation
  const createMutation = useMutation({
    mutationFn: (data: ResidentCreate) => {
      if (!tenantId) {
        throw new Error('No hay condominio seleccionado')
      }
      return apiClient.createResident(tenantId, data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['residents', tenantId] })
      setIsAddDialogOpen(false)
      setFormError(null)
      resetForm()
    },
    onError: (error: Error) => {
      console.error('Error creating resident:', error)
      setFormError(error.message)
    },
  })

  const resetForm = () => {
    setFormData({
      name: '',
      unit: '',
      phone: '',
      email: '',
      whatsapp: '',
    })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.name || !formData.unit) return

    createMutation.mutate({
      condominium_id: tenantId,
      name: formData.name,
      unit: formData.unit,
      phone: formData.phone || undefined,
      email: formData.email || undefined,
      whatsapp: formData.whatsapp || undefined,
    })
  }

  const filteredResidents = residents?.filter(r =>
    r.name.toLowerCase().includes(search.toLowerCase()) ||
    r.unit.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Residentes</h1>
          <p className="text-muted-foreground">
            Administra los residentes del condominio
          </p>
        </div>
        <Button onClick={() => setIsAddDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Agregar Residente
        </Button>
      </div>

      {/* Add Resident Dialog */}
      <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Agregar Nuevo Residente</DialogTitle>
            <DialogDescription>
              Ingresa los datos del nuevo residente
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="name">Nombre completo *</Label>
                <Input
                  id="name"
                  placeholder="Juan Perez"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="unit">Unidad/Departamento *</Label>
                <Input
                  id="unit"
                  placeholder="A-101"
                  value={formData.unit}
                  onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                  required
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="phone">Telefono</Label>
                <Input
                  id="phone"
                  placeholder="+52 555 123 4567"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="juan@email.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="whatsapp">WhatsApp</Label>
                <Input
                  id="whatsapp"
                  placeholder="+52 555 123 4567"
                  value={formData.whatsapp}
                  onChange={(e) => setFormData({ ...formData, whatsapp: e.target.value })}
                />
              </div>
            </div>
            {formError && (
              <p className="text-sm text-destructive mb-4">{formError}</p>
            )}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => {
                setIsAddDialogOpen(false)
                setFormError(null)
                resetForm()
              }}>
                Cancelar
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Guardando...' : 'Guardar'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="search"
          placeholder="Buscar por nombre o unidad..."
          className="pl-9"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Residents Grid */}
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-4 bg-muted rounded w-3/4" />
                <div className="h-3 bg-muted rounded w-1/2" />
              </CardHeader>
              <CardContent>
                <div className="h-20 bg-muted rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredResidents?.map((resident) => (
            <Card key={resident.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-lg">{resident.name}</CardTitle>
                    <CardDescription className="flex items-center gap-1">
                      <Home className="h-3 w-3" />
                      Unidad {resident.unit}
                    </CardDescription>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    resident.is_active
                      ? 'bg-green-100 text-green-700'
                      : 'bg-gray-100 text-gray-700'
                  }`}>
                    {resident.is_active ? 'Activo' : 'Inactivo'}
                  </span>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {resident.phone && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Phone className="h-4 w-4" />
                    {resident.phone}
                  </div>
                )}
                {resident.email && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Mail className="h-4 w-4" />
                    {resident.email}
                  </div>
                )}
                {resident.whatsapp && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <MessageSquare className="h-4 w-4" />
                    {resident.whatsapp}
                  </div>
                )}
                {resident.authorized_visitors?.length > 0 && (
                  <div className="pt-2 border-t">
                    <p className="text-xs text-muted-foreground mb-1">
                      Visitantes autorizados:
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {resident.authorized_visitors.slice(0, 3).map((name, i) => (
                        <span key={i} className="px-2 py-0.5 bg-muted rounded text-xs">
                          {name}
                        </span>
                      ))}
                      {resident.authorized_visitors.length > 3 && (
                        <span className="px-2 py-0.5 bg-muted rounded text-xs">
                          +{resident.authorized_visitors.length - 3}
                        </span>
                      )}
                    </div>
                  </div>
                )}
                <p className="text-xs text-muted-foreground pt-2">
                  Registrado: {formatDate(resident.created_at)}
                </p>
              </CardContent>
            </Card>
          ))}
          {filteredResidents?.length === 0 && (
            <div className="col-span-full text-center py-12">
              <p className="text-muted-foreground">No se encontraron residentes</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
