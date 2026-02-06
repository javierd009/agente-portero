'use client'

import { useEffect, useState } from 'react'
import { Building2, ChevronDown, Loader2, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useTenantStore } from '@/store/tenant'
import { createClient } from '@/lib/supabase/client'

export function TenantSelector() {
  const { currentTenant, availableTenants, setCurrentTenant, setAvailableTenants } = useTenantStore()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadCondominiums() {
      try {
        const supabase = createClient()

        // First check if user is authenticated
        const { data: { user }, error: authError } = await supabase.auth.getUser()
        if (authError || !user) {
          console.error('Auth error:', authError)
          setError('No autenticado')
          setLoading(false)
          return
        }

        console.log('User authenticated:', user.id, user.email)

        // Get condominiums the user has access to via their resident record
        const { data: condominiums, error: dbError } = await supabase
          .from('condominiums')
          .select('id, name, slug')
          .order('name')

        if (dbError) {
          console.error('Error loading condominiums:', dbError)
          setError(dbError.message)
          setLoading(false)
          return
        }

        console.log('Condominiums loaded:', condominiums)

        if (condominiums && condominiums.length > 0) {
          setAvailableTenants(condominiums)
          if (!currentTenant) {
            setCurrentTenant(condominiums[0])
          }
        }
        setLoading(false)
      } catch (e) {
        console.error('Unexpected error:', e)
        setError('Error inesperado')
        setLoading(false)
      }
    }

    loadCondominiums()
  }, [currentTenant, setAvailableTenants, setCurrentTenant])

  if (loading) {
    return (
      <Button variant="outline" className="w-full justify-between" disabled>
        <div className="flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Cargando...</span>
        </div>
      </Button>
    )
  }

  if (error) {
    return (
      <Button variant="outline" className="w-full justify-between text-destructive" disabled>
        <div className="flex items-center gap-2">
          <AlertCircle className="h-4 w-4" />
          <span className="truncate text-xs">{error}</span>
        </div>
      </Button>
    )
  }

  if (availableTenants.length === 0) {
    return (
      <Button variant="outline" className="w-full justify-between" disabled>
        <div className="flex items-center gap-2">
          <Building2 className="h-4 w-4" />
          <span className="truncate text-muted-foreground">Sin condominios</span>
        </div>
      </Button>
    )
  }

  return (
    <Button
      variant="outline"
      className="w-full justify-between"
      onClick={() => {
        if (availableTenants.length > 1) {
          const nextIndex = availableTenants.findIndex(t => t.id === currentTenant?.id) + 1
          setCurrentTenant(availableTenants[nextIndex % availableTenants.length])
        }
      }}
    >
      <div className="flex items-center gap-2">
        <Building2 className="h-4 w-4" />
        <span className="truncate">{currentTenant?.name || 'Seleccionar'}</span>
      </div>
      {availableTenants.length > 1 && <ChevronDown className="h-4 w-4 opacity-50" />}
    </Button>
  )
}
