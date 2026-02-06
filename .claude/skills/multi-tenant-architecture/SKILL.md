---
name: multi-tenant-architecture
description: Implement multi-tenant SaaS architecture with tenant isolation, RBAC, and shared infrastructure. Use for condominiums, companies, organizations as tenants.
license: MIT
---

# Multi-Tenant Architecture Skill

## Purpose
Implement secure multi-tenant architecture where each tenant (condominium, company, organization) has isolated data while sharing infrastructure.

## When to Use
- Building SaaS for multiple organizations
- Need tenant isolation (condominiums, companies, etc.)
- Implementing Role-Based Access Control (RBAC)
- Shared database with row-level security
- Multi-organization dashboards

## Architecture Pattern

### Database-per-Row (Recommended for <1000 tenants)
```
┌─────────────────────────────────────────────────────┐
│                   PostgreSQL                         │
│  ┌─────────────────────────────────────────────────┐│
│  │  tenants table                                   ││
│  │  ├── id (UUID)                                  ││
│  │  ├── name                                       ││
│  │  ├── slug (unique)                              ││
│  │  └── settings (JSONB)                           ││
│  └─────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────┐│
│  │  All other tables have tenant_id FK             ││
│  │  + Row Level Security (RLS) policies            ││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

## Database Schema

### Core Tables

```sql
-- Tenants (condominiums, organizations, etc.)
CREATE TABLE tenants (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  settings JSONB DEFAULT '{}'::jsonb,
  plan TEXT DEFAULT 'free' CHECK (plan IN ('free', 'basic', 'pro', 'enterprise')),
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_tenants_slug ON tenants(slug);

-- User-Tenant relationship (users can belong to multiple tenants)
CREATE TABLE user_tenants (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
  permissions JSONB DEFAULT '[]'::jsonb,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  UNIQUE(user_id, tenant_id)
);

CREATE INDEX idx_user_tenants_user ON user_tenants(user_id);
CREATE INDEX idx_user_tenants_tenant ON user_tenants(tenant_id);

-- Example tenant-scoped table (adapt for your domain)
CREATE TABLE tenant_resources (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  data JSONB DEFAULT '{}'::jsonb,
  created_by UUID REFERENCES auth.users(id),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_tenant_resources_tenant ON tenant_resources(tenant_id);
```

### Row Level Security (RLS)

```sql
-- Enable RLS on all tenant-scoped tables
ALTER TABLE tenant_resources ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see resources from their tenants
CREATE POLICY tenant_resources_select ON tenant_resources
  FOR SELECT
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_tenants
      WHERE user_id = auth.uid() AND is_active = true
    )
  );

-- Policy: Only admins/owners can insert
CREATE POLICY tenant_resources_insert ON tenant_resources
  FOR INSERT
  WITH CHECK (
    tenant_id IN (
      SELECT tenant_id FROM user_tenants
      WHERE user_id = auth.uid()
      AND role IN ('owner', 'admin')
      AND is_active = true
    )
  );

-- Policy: Only admins/owners can update
CREATE POLICY tenant_resources_update ON tenant_resources
  FOR UPDATE
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_tenants
      WHERE user_id = auth.uid()
      AND role IN ('owner', 'admin')
      AND is_active = true
    )
  );

-- Policy: Only owners can delete
CREATE POLICY tenant_resources_delete ON tenant_resources
  FOR DELETE
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_tenants
      WHERE user_id = auth.uid()
      AND role = 'owner'
      AND is_active = true
    )
  );
```

## Backend Implementation (FastAPI)

### Tenant Context Middleware

```python
# middleware/tenant.py
from fastapi import Request, HTTPException
from typing import Optional
import uuid

class TenantContext:
    def __init__(self, tenant_id: uuid.UUID, tenant_slug: str, user_role: str):
        self.tenant_id = tenant_id
        self.tenant_slug = tenant_slug
        self.user_role = user_role

async def get_tenant_context(request: Request) -> TenantContext:
    """Extract tenant from header or subdomain"""
    # Option 1: From header
    tenant_slug = request.headers.get("X-Tenant-ID")

    # Option 2: From subdomain (tenant.app.com)
    if not tenant_slug:
        host = request.headers.get("host", "")
        parts = host.split(".")
        if len(parts) > 2:
            tenant_slug = parts[0]

    if not tenant_slug:
        raise HTTPException(status_code=400, detail="Tenant not specified")

    # Verify user has access to this tenant
    user_id = request.state.user_id  # From auth middleware

    tenant_access = await verify_tenant_access(user_id, tenant_slug)
    if not tenant_access:
        raise HTTPException(status_code=403, detail="No access to this tenant")

    return TenantContext(
        tenant_id=tenant_access["tenant_id"],
        tenant_slug=tenant_slug,
        user_role=tenant_access["role"]
    )
```

### Tenant-Scoped Repository

```python
# repositories/base.py
from typing import Generic, TypeVar, List, Optional
from sqlmodel import SQLModel, Session, select
import uuid

T = TypeVar("T", bound=SQLModel)

class TenantScopedRepository(Generic[T]):
    def __init__(self, model: type[T], session: Session, tenant_id: uuid.UUID):
        self.model = model
        self.session = session
        self.tenant_id = tenant_id

    async def get_all(self) -> List[T]:
        statement = select(self.model).where(
            self.model.tenant_id == self.tenant_id
        )
        return self.session.exec(statement).all()

    async def get_by_id(self, id: uuid.UUID) -> Optional[T]:
        statement = select(self.model).where(
            self.model.id == id,
            self.model.tenant_id == self.tenant_id  # Always filter by tenant!
        )
        return self.session.exec(statement).first()

    async def create(self, data: dict) -> T:
        obj = self.model(**data, tenant_id=self.tenant_id)
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    async def update(self, id: uuid.UUID, data: dict) -> Optional[T]:
        obj = await self.get_by_id(id)
        if not obj:
            return None
        for key, value in data.items():
            setattr(obj, key, value)
        self.session.commit()
        return obj

    async def delete(self, id: uuid.UUID) -> bool:
        obj = await self.get_by_id(id)
        if not obj:
            return False
        self.session.delete(obj)
        self.session.commit()
        return True
```

### Role-Based Access Control (RBAC)

```python
# auth/rbac.py
from enum import Enum
from functools import wraps
from fastapi import HTTPException

class Permission(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"

ROLE_PERMISSIONS = {
    "viewer": [Permission.READ],
    "member": [Permission.READ, Permission.WRITE],
    "admin": [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN],
    "owner": [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN],
}

def require_permission(permission: Permission):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tenant_ctx = kwargs.get("tenant_ctx")
            if not tenant_ctx:
                raise HTTPException(status_code=401, detail="No tenant context")

            user_permissions = ROLE_PERMISSIONS.get(tenant_ctx.user_role, [])
            if permission not in user_permissions:
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {permission.value} required"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage in endpoints
@router.delete("/resources/{id}")
@require_permission(Permission.DELETE)
async def delete_resource(id: uuid.UUID, tenant_ctx: TenantContext = Depends(get_tenant_context)):
    # Only admins/owners can reach here
    pass
```

## Frontend Implementation (Next.js)

### Tenant Provider

```typescript
// contexts/TenantContext.tsx
'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useRouter } from 'next/navigation';

interface Tenant {
  id: string;
  name: string;
  slug: string;
  role: 'owner' | 'admin' | 'member' | 'viewer';
}

interface TenantContextType {
  currentTenant: Tenant | null;
  tenants: Tenant[];
  switchTenant: (slug: string) => void;
  isLoading: boolean;
}

const TenantContext = createContext<TenantContextType | undefined>(undefined);

export function TenantProvider({ children }: { children: ReactNode }) {
  const [currentTenant, setCurrentTenant] = useState<Tenant | null>(null);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    loadTenants();
  }, []);

  async function loadTenants() {
    try {
      const res = await fetch('/api/tenants/my');
      const data = await res.json();
      setTenants(data);

      // Auto-select first tenant or from localStorage
      const savedSlug = localStorage.getItem('currentTenant');
      const tenant = data.find((t: Tenant) => t.slug === savedSlug) || data[0];
      if (tenant) {
        setCurrentTenant(tenant);
      }
    } finally {
      setIsLoading(false);
    }
  }

  function switchTenant(slug: string) {
    const tenant = tenants.find(t => t.slug === slug);
    if (tenant) {
      setCurrentTenant(tenant);
      localStorage.setItem('currentTenant', slug);
      router.refresh();
    }
  }

  return (
    <TenantContext.Provider value={{ currentTenant, tenants, switchTenant, isLoading }}>
      {children}
    </TenantContext.Provider>
  );
}

export function useTenant() {
  const context = useContext(TenantContext);
  if (!context) throw new Error('useTenant must be used within TenantProvider');
  return context;
}
```

### API Client with Tenant Header

```typescript
// lib/api.ts
import { useTenant } from '@/contexts/TenantContext';

export function useApi() {
  const { currentTenant } = useTenant();

  async function fetchWithTenant(url: string, options: RequestInit = {}) {
    if (!currentTenant) throw new Error('No tenant selected');

    return fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'X-Tenant-ID': currentTenant.slug,
        'Content-Type': 'application/json',
      },
    });
  }

  return { fetchWithTenant };
}
```

## Condominium Example (Agente Portero)

### Schema for Condominiums

```sql
-- Tenants = Condominiums
CREATE TABLE condominiums (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  address TEXT,
  settings JSONB DEFAULT '{}'::jsonb,
  -- Settings example:
  -- {
  --   "timezone": "America/Mexico_City",
  --   "gate_api_url": "http://192.168.1.100/api",
  --   "cameras": [...],
  --   "notifications": { "whatsapp": true, "email": false }
  -- }
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Residents (belong to a condominium)
CREATE TABLE residents (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  condominium_id UUID REFERENCES condominiums(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id),  -- Optional: linked to auth
  name TEXT NOT NULL,
  unit TEXT NOT NULL,  -- "A-101", "B-205"
  phone TEXT,
  vehicles JSONB DEFAULT '[]'::jsonb,  -- [{ "plate": "ABC123", "model": "Toyota Corolla" }]
  authorized_visitors JSONB DEFAULT '[]'::jsonb,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_residents_condominium ON residents(condominium_id);

-- Access logs (tenant-scoped)
CREATE TABLE access_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  condominium_id UUID REFERENCES condominiums(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,  -- 'entry', 'exit', 'denied', 'visitor'
  resident_id UUID REFERENCES residents(id),
  visitor_name TEXT,
  vehicle_plate TEXT,
  authorized_by TEXT,  -- 'resident', 'guard', 'ai_agent'
  camera_snapshot_url TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_access_logs_condominium ON access_logs(condominium_id);
CREATE INDEX idx_access_logs_created ON access_logs(created_at DESC);
```

## Best Practices

### DO
- Always filter by `tenant_id` in queries
- Use RLS as second layer of defense
- Validate tenant access in middleware
- Log all cross-tenant access attempts
- Use UUIDs for tenant IDs (not sequential)

### DON'T
- Never trust client-provided tenant_id without verification
- Don't use URL paths for tenant selection in APIs (use headers)
- Don't cache data across tenants without proper isolation
- Don't expose internal tenant IDs to end users (use slugs)

## Testing Multi-Tenant

```python
# tests/test_tenant_isolation.py
import pytest

async def test_tenant_isolation():
    """Verify users can't access other tenant's data"""
    # Create two tenants
    tenant_a = await create_tenant("Condominio A")
    tenant_b = await create_tenant("Condominio B")

    # Create resource in tenant A
    resource = await create_resource(tenant_id=tenant_a.id, name="Private")

    # Try to access from tenant B context - should fail
    with pytest.raises(NotFoundError):
        await get_resource(id=resource.id, tenant_id=tenant_b.id)
```

---

*This skill provides the foundation for building secure multi-tenant SaaS applications.*
