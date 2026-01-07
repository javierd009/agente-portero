import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface Condominium {
  id: string
  name: string
  slug: string
}

interface TenantState {
  currentTenant: Condominium | null
  availableTenants: Condominium[]
  setCurrentTenant: (tenant: Condominium) => void
  setAvailableTenants: (tenants: Condominium[]) => void
  clearTenant: () => void
}

export const useTenantStore = create<TenantState>()(
  persist(
    (set) => ({
      currentTenant: null,
      availableTenants: [],
      setCurrentTenant: (tenant) => set({ currentTenant: tenant }),
      setAvailableTenants: (tenants) => set({ availableTenants: tenants }),
      clearTenant: () => set({ currentTenant: null, availableTenants: [] }),
    }),
    {
      name: 'tenant-storage',
    }
  )
)
