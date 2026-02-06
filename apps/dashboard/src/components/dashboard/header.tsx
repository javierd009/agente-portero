'use client'

import { User } from '@supabase/supabase-js'
import { Bell, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface HeaderProps {
  user: User
}

export function Header({ user }: HeaderProps) {
  return (
    <header className="flex h-16 items-center justify-between border-b bg-card px-6">
      {/* Search */}
      <div className="flex items-center gap-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Buscar..."
            className="w-64 pl-9"
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-destructive" />
        </Button>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-sm font-medium">{user.email}</p>
            <p className="text-xs text-muted-foreground">Administrador</p>
          </div>
          <div className="h-9 w-9 rounded-full bg-primary flex items-center justify-center text-primary-foreground font-medium">
            {user.email?.[0].toUpperCase()}
          </div>
        </div>
      </div>
    </header>
  )
}
