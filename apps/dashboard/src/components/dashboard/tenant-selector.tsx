'use client'

import { useEffect, useState } from 'react'
import { Building2, ChevronDown, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useTenantStore } from '@/store/tenant'
import { createClient } from '@/lib/supabase/client'

export function TenantSelector() {
  const { currentTenant, availableTenants, setCurrentTenant, setAvailableTenants } = useTenantStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadCondominiums() {
      const supabase = createClient()

      // Get condominiums the user has access to via their resident record
      const { data: condominiums, error } = await supabase
        .from('condominiums')
        .select('id, name, slug')
        .order('name')

      if (error) {
        console.error('Error loading condominiums:', error)
        setLoading(false)
        return
      }

      if (condominiums && condominiums.length > 0) {
        setAvailableTenants(condominiums)
        if (!currentTenant) {
          setCurrentTenant(condominiums[0])
        }
      }
      setLoading(false)
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
