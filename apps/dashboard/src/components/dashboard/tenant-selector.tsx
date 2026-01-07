'use client'

import { useEffect } from 'react'
import { Building2, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useTenantStore } from '@/store/tenant'

export function TenantSelector() {
  const { currentTenant, availableTenants, setCurrentTenant, setAvailableTenants } = useTenantStore()

  useEffect(() => {
    // TODO: Fetch available tenants from API based on user's access
    // For now, use mock data
    const mockTenants = [
      { id: '1', name: 'Residencial Las Palmas', slug: 'las-palmas' },
      { id: '2', name: 'Torres del Valle', slug: 'torres-valle' },
    ]
    setAvailableTenants(mockTenants)
    if (!currentTenant && mockTenants.length > 0) {
      setCurrentTenant(mockTenants[0])
    }
  }, [currentTenant, setAvailableTenants, setCurrentTenant])

  return (
    <Button
      variant="outline"
      className="w-full justify-between"
      onClick={() => {
        // TODO: Open tenant selector dialog
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
      <ChevronDown className="h-4 w-4 opacity-50" />
    </Button>
  )
}
