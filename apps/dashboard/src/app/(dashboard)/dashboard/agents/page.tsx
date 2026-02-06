'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useTenantStore } from '@/store/tenant'
import { apiClient, AgentCreate } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { Plus, Bot, Phone, Volume2, Settings, Power } from 'lucide-react'

export default function AgentsPage() {
  const { currentTenant } = useTenantStore()
  const tenantId = currentTenant?.id || ''
  const queryClient = useQueryClient()
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Form state
  const [formData, setFormData] = useState<Partial<AgentCreate>>({
    name: '',
    extension: '',
    prompt: '',
    language: 'es',
    voice_id: 'shimmer',
  })

  const { data: agents, isLoading } = useQuery({
    queryKey: ['agents', tenantId],
    queryFn: () => apiClient.getAgents(tenantId),
    enabled: !!tenantId,
  })

  // Create agent mutation
  const createMutation = useMutation({
    mutationFn: (data: AgentCreate) => {
      if (!tenantId) {
        throw new Error('No hay condominio seleccionado')
      }
      return apiClient.createAgent(tenantId, data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents', tenantId] })
      setIsAddDialogOpen(false)
      setFormError(null)
      resetForm()
    },
    onError: (error: Error) => {
      console.error('Error creating agent:', error)
      setFormError(error.message)
    },
  })

  const resetForm = () => {
    setFormData({
      name: '',
      extension: '',
      prompt: '',
      language: 'es',
      voice_id: 'shimmer',
    })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.name || !formData.extension) return

    createMutation.mutate({
      condominium_id: tenantId,
      name: formData.name,
      extension: formData.extension,
      prompt: formData.prompt || undefined,
      language: formData.language || 'es',
      voice_id: formData.voice_id || undefined,
    })
  }

  const openAddDialog = () => {
    setFormError(null)
    resetForm()
    setIsAddDialogOpen(true)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Agentes Virtuales</h1>
          <p className="text-muted-foreground">
            Configura los agentes de IA que atienden llamadas
          </p>
        </div>
        <Button onClick={openAddDialog}>
          <Plus className="mr-2 h-4 w-4" />
          Crear Agente
        </Button>
      </div>

      {/* Add Agent Dialog */}
      <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Crear Nuevo Agente</DialogTitle>
            <DialogDescription>
              Configura un nuevo agente virtual para atender llamadas
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="name">Nombre del agente *</Label>
                <Input
                  id="name"
                  placeholder="Agente Principal"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="extension">Extension PBX *</Label>
                  <Input
                    id="extension"
                    placeholder="100"
                    value={formData.extension}
                    onChange={(e) => setFormData({ ...formData, extension: e.target.value })}
                    required
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="language">Idioma</Label>
                  <Input
                    id="language"
                    placeholder="es"
                    value={formData.language}
                    onChange={(e) => setFormData({ ...formData, language: e.target.value })}
                  />
                </div>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="voice_id">Voz (OpenAI)</Label>
                <Input
                  id="voice_id"
                  placeholder="shimmer, alloy, echo, sage..."
                  value={formData.voice_id}
                  onChange={(e) => setFormData({ ...formData, voice_id: e.target.value })}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="prompt">Prompt del sistema</Label>
                <Textarea
                  id="prompt"
                  placeholder="Eres un agente de seguridad virtual para un condominio..."
                  value={formData.prompt}
                  onChange={(e) => setFormData({ ...formData, prompt: e.target.value })}
                  rows={4}
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
              }}>
                Cancelar
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Creando...' : 'Crear Agente'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {[...Array(2)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-5 bg-muted rounded w-1/2" />
                <div className="h-4 bg-muted rounded w-1/3" />
              </CardHeader>
              <CardContent>
                <div className="h-32 bg-muted rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {agents?.map((agent) => (
            <Card key={agent.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`rounded-full p-3 ${
                      agent.is_active
                        ? 'bg-green-100 text-green-600'
                        : 'bg-gray-100 text-gray-600'
                    }`}>
                      <Bot className="h-6 w-6" />
                    </div>
                    <div>
                      <CardTitle className="text-lg">{agent.name}</CardTitle>
                      <CardDescription className="flex items-center gap-1">
                        <Phone className="h-3 w-3" />
                        Extension {agent.extension}
                      </CardDescription>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1 ${
                    agent.is_active
                      ? 'bg-green-100 text-green-700'
                      : 'bg-gray-100 text-gray-700'
                  }`}>
                    <Power className="h-3 w-3" />
                    {agent.is_active ? 'Activo' : 'Inactivo'}
                  </span>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Idioma</p>
                    <p className="font-medium">{agent.language}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Voz</p>
                    <p className="font-medium flex items-center gap-1">
                      <Volume2 className="h-3 w-3" />
                      {agent.voice_id || 'Default'}
                    </p>
                  </div>
                </div>

                {agent.prompt && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Prompt del sistema:</p>
                    <p className="text-sm bg-muted p-2 rounded line-clamp-3">
                      {agent.prompt}
                    </p>
                  </div>
                )}

                <div className="flex items-center justify-between pt-3 border-t">
                  <p className="text-xs text-muted-foreground">
                    Creado: {formatDate(agent.created_at)}
                  </p>
                  <Button variant="outline" size="sm" disabled title="Proximamente">
                    <Settings className="h-4 w-4 mr-1" />
                    Configurar
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
          {(!agents || agents.length === 0) && (
            <Card className="col-span-full">
              <CardContent className="text-center py-12">
                <Bot className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
                <h3 className="font-medium mb-2">No hay agentes configurados</h3>
                <p className="text-muted-foreground mb-4">
                  Crea un agente virtual para atender llamadas automaticamente
                </p>
                <Button onClick={openAddDialog}>
                  <Plus className="mr-2 h-4 w-4" />
                  Crear primer agente
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
