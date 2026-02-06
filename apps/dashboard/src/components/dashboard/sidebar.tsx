'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  Shield,
  LayoutDashboard,
  Users,
  UserCheck,
  Car,
  Camera,
  Bell,
  Bot,
  Settings,
  LogOut,
} from 'lucide-react'
import { TenantSelector } from './tenant-selector'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Residentes', href: '/dashboard/residents', icon: Users },
  { name: 'Visitantes', href: '/dashboard/visitors', icon: UserCheck },
  { name: 'Accesos', href: '/dashboard/access-logs', icon: Car },
  { name: 'Cámaras', href: '/dashboard/cameras', icon: Camera },
  { name: 'Notificaciones', href: '/dashboard/notifications', icon: Bell },
  { name: 'Agentes', href: '/dashboard/agents', icon: Bot },
  { name: 'Configuración', href: '/dashboard/settings', icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="flex w-64 flex-col border-r bg-card">
      {/* Logo */}
      <div className="flex h-16 items-center gap-2 border-b px-6">
        <Shield className="h-8 w-8 text-primary" />
        <span className="text-lg font-semibold">Agente Portero</span>
      </div>

      {/* Tenant Selector */}
      <div className="border-b p-4">
        <TenantSelector />
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-4">
        {navigation.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.name}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="border-t p-4">
        <Link
          href="/api/auth/signout"
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <LogOut className="h-5 w-5" />
          Cerrar sesión
        </Link>
      </div>
    </aside>
  )
}
