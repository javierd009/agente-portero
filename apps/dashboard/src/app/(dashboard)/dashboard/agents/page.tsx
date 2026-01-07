'use client'

import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useTenantStore } from '@/store/tenant'
import { apiClient } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { Plus, Bot, Phone, Volume2, Settings, Power } from 'lucide-react'

export default function AgentsPage() {
  const { currentTenant } = useTenantStore()
  const tenantId = currentTenant?.id || ''

  const { data: agents, isLoading } = useQuery({
    queryKey: ['agents', tenantId],
    queryFn: () => apiClient.getAgents(tenantId),
    enabled: !!tenantId,
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Agentes Virtuales</h1>
          <p className="text-muted-foreground">
            Configura los agentes de IA que atienden llamadas
          </p>
        </div>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Crear Agente
        </Button>
      </div>

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
                        Extensión {agent.extension}
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
                  <Button variant="outline" size="sm">
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
                  Crea un agente virtual para atender llamadas automáticamente
                </p>
                <Button>
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
