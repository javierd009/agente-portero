---
name: audit-logging
description: Implement comprehensive audit logging for security, compliance, and debugging. Track all user actions, system events, and access patterns with tenant isolation.
license: MIT
---

# Audit Logging Skill

## Purpose
Implement comprehensive audit logging for security compliance, debugging, and activity tracking. Essential for multi-tenant SaaS where you need to track who did what, when, and from where.

## When to Use
- Security compliance (SOC2, HIPAA, GDPR)
- User activity tracking
- Access control monitoring
- Debugging production issues
- Forensic analysis after incidents
- Billing/usage tracking

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Application                           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ API     │  │ Auth    │  │ Access  │  │ System  │        │
│  │ Actions │  │ Events  │  │ Control │  │ Events  │        │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘        │
│       │            │            │            │              │
│       └────────────┴────────────┴────────────┘              │
│                          │                                   │
│                    ┌─────▼─────┐                            │
│                    │  Audit    │                            │
│                    │  Service  │                            │
│                    └─────┬─────┘                            │
└──────────────────────────┼───────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌────────┐  ┌─────────┐  ┌─────────┐
         │ Audit  │  │ Time-   │  │ Alert   │
         │ Table  │  │ Series  │  │ System  │
         └────────┘  │ (opt)   │  └─────────┘
                     └─────────┘
```

## Database Schema

### Core Audit Tables

```sql
-- Main audit log table
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,

  -- What happened
  action TEXT NOT NULL,  -- 'create', 'update', 'delete', 'login', 'access_granted'
  resource_type TEXT NOT NULL,  -- 'resident', 'gate', 'visitor', 'user'
  resource_id UUID,  -- ID of affected resource

  -- Who did it
  actor_id UUID REFERENCES auth.users(id),
  actor_type TEXT NOT NULL DEFAULT 'user',  -- 'user', 'system', 'api_key', 'ai_agent'
  actor_email TEXT,  -- Denormalized for quick access
  actor_role TEXT,  -- Role at time of action

  -- Context
  ip_address INET,
  user_agent TEXT,
  request_id UUID,  -- For correlating with other logs

  -- Details
  old_values JSONB,  -- Previous state (for updates/deletes)
  new_values JSONB,  -- New state (for creates/updates)
  metadata JSONB DEFAULT '{}'::jsonb,  -- Additional context

  -- Result
  status TEXT DEFAULT 'success' CHECK (status IN ('success', 'failure', 'partial')),
  error_message TEXT,

  -- Timing
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  duration_ms INTEGER  -- How long the action took
);

-- Indexes for common queries
CREATE INDEX idx_audit_tenant_created ON audit_logs(tenant_id, created_at DESC);
CREATE INDEX idx_audit_actor ON audit_logs(actor_id, created_at DESC);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_action ON audit_logs(action, created_at DESC);
CREATE INDEX idx_audit_status ON audit_logs(status) WHERE status != 'success';

-- Partitioning by month (for large-scale deployments)
-- CREATE TABLE audit_logs_2024_01 PARTITION OF audit_logs
--   FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Access logs (specific for physical access events)
CREATE TABLE access_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,

  -- Access event details
  event_type TEXT NOT NULL,  -- 'entry', 'exit', 'denied', 'visitor_entry'
  access_point TEXT NOT NULL,  -- 'main_gate', 'pedestrian_gate', 'parking'
  direction TEXT,  -- 'in', 'out'

  -- Who/What
  resident_id UUID REFERENCES residents(id),
  visitor_name TEXT,
  vehicle_plate TEXT,

  -- Authorization
  authorization_method TEXT,  -- 'auto_plate', 'manual_guard', 'ai_agent', 'resident_app'
  authorized_by UUID,  -- User who authorized (if manual)

  -- Evidence
  camera_snapshot_url TEXT,
  confidence_score FLOAT,  -- For AI-based authorization

  -- Metadata
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_access_tenant_created ON access_logs(tenant_id, created_at DESC);
CREATE INDEX idx_access_resident ON access_logs(resident_id);
CREATE INDEX idx_access_plate ON access_logs(vehicle_plate);
```

### Row Level Security

```sql
-- Enable RLS
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE access_logs ENABLE ROW LEVEL SECURITY;

-- Audit logs: Only admins can read
CREATE POLICY audit_logs_select ON audit_logs
  FOR SELECT
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_tenants
      WHERE user_id = auth.uid()
      AND role IN ('owner', 'admin')
    )
  );

-- No one can modify audit logs (append-only)
CREATE POLICY audit_logs_insert ON audit_logs
  FOR INSERT
  WITH CHECK (true);  -- Allow inserts from service role

-- Access logs: Admins and guards can read
CREATE POLICY access_logs_select ON access_logs
  FOR SELECT
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_tenants
      WHERE user_id = auth.uid()
      AND role IN ('owner', 'admin', 'guard')
    )
  );
```

## Backend Implementation (FastAPI)

### Audit Service

```python
# services/audit.py
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
from sqlmodel import Session
from models.audit import AuditLog
from contextlib import asynccontextmanager

class AuditService:
    def __init__(self, session: Session):
        self.session = session

    async def log(
        self,
        tenant_id: uuid.UUID,
        action: str,
        resource_type: str,
        resource_id: Optional[uuid.UUID] = None,
        actor_id: Optional[uuid.UUID] = None,
        actor_type: str = "user",
        actor_email: Optional[str] = None,
        actor_role: Optional[str] = None,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[uuid.UUID] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> AuditLog:
        """Create an audit log entry"""

        log_entry = AuditLog(
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_email=actor_email,
            actor_role=actor_role,
            old_values=old_values,
            new_values=new_values,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            status=status,
            error_message=error_message,
            duration_ms=duration_ms
        )

        self.session.add(log_entry)
        self.session.commit()
        return log_entry

# Singleton instance
_audit_service: Optional[AuditService] = None

def get_audit_service(session: Session) -> AuditService:
    global _audit_service
    if not _audit_service:
        _audit_service = AuditService(session)
    return _audit_service
```

### Audit Middleware

```python
# middleware/audit.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import uuid

class AuditMiddleware(BaseHTTPMiddleware):
    """Automatically log all API requests"""

    # Paths to skip logging
    SKIP_PATHS = {"/health", "/metrics", "/docs", "/openapi.json"}

    # Methods that typically modify data
    WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(self, request: Request, call_next):
        # Skip certain paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        # Generate request ID for correlation
        request_id = uuid.uuid4()
        request.state.request_id = request_id

        # Start timing
        start_time = time.time()

        # Get response
        response = await call_next(request)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Log write operations
        if request.method in self.WRITE_METHODS:
            await self._log_request(request, response, request_id, duration_ms)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = str(request_id)

        return response

    async def _log_request(
        self,
        request: Request,
        response: Response,
        request_id: uuid.UUID,
        duration_ms: int
    ):
        # Extract context
        tenant_id = getattr(request.state, "tenant_id", None)
        user_id = getattr(request.state, "user_id", None)
        user_email = getattr(request.state, "user_email", None)
        user_role = getattr(request.state, "user_role", None)

        if not tenant_id:
            return  # Skip if no tenant context

        # Determine action and resource from path
        action = self._get_action(request.method)
        resource_type, resource_id = self._parse_path(request.url.path)

        # Get audit service
        audit = get_audit_service(request.state.db)

        await audit.log(
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_id=user_id,
            actor_email=user_email,
            actor_role=user_role,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            request_id=request_id,
            status="success" if response.status_code < 400 else "failure",
            duration_ms=duration_ms
        )

    def _get_action(self, method: str) -> str:
        return {
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete"
        }.get(method, "unknown")

    def _parse_path(self, path: str) -> tuple:
        """Extract resource type and ID from path like /api/v1/residents/123"""
        parts = path.strip("/").split("/")
        resource_type = parts[-2] if len(parts) >= 2 else parts[-1]
        resource_id = None

        # Try to parse last part as UUID
        try:
            resource_id = uuid.UUID(parts[-1])
        except (ValueError, IndexError):
            pass

        return resource_type, resource_id
```

### Audit Decorator for Specific Actions

```python
# decorators/audit.py
from functools import wraps
from typing import Callable, Optional
import uuid

def audit_action(
    action: str,
    resource_type: str,
    get_resource_id: Optional[Callable] = None,
    get_old_values: Optional[Callable] = None
):
    """Decorator to automatically audit specific actions"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get context from kwargs
            tenant_ctx = kwargs.get("tenant_ctx")
            db = kwargs.get("db")

            # Get old values before action (for updates/deletes)
            old_values = None
            if get_old_values:
                old_values = await get_old_values(*args, **kwargs)

            # Execute the actual function
            try:
                result = await func(*args, **kwargs)
                status = "success"
                error = None
            except Exception as e:
                status = "failure"
                error = str(e)
                raise

            finally:
                # Log the action
                if tenant_ctx and db:
                    resource_id = None
                    if get_resource_id:
                        resource_id = get_resource_id(result if status == "success" else None, *args, **kwargs)

                    audit = get_audit_service(db)
                    await audit.log(
                        tenant_id=tenant_ctx.tenant_id,
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        actor_id=tenant_ctx.user_id,
                        actor_role=tenant_ctx.user_role,
                        old_values=old_values,
                        new_values=result.dict() if hasattr(result, "dict") else None,
                        status=status,
                        error_message=error
                    )

            return result
        return wrapper
    return decorator

# Usage example
@router.post("/residents")
@audit_action(
    action="create",
    resource_type="resident",
    get_resource_id=lambda result, *args, **kwargs: result.id if result else None
)
async def create_resident(
    data: ResidentCreate,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db)
):
    resident = await resident_service.create(data, tenant_ctx.tenant_id)
    return resident
```

### Access Log Service (Physical Access)

```python
# services/access_log.py
from typing import Optional
import uuid
from datetime import datetime

class AccessLogService:
    def __init__(self, session: Session):
        self.session = session

    async def log_entry(
        self,
        tenant_id: uuid.UUID,
        access_point: str,
        event_type: str = "entry",
        resident_id: Optional[uuid.UUID] = None,
        visitor_name: Optional[str] = None,
        vehicle_plate: Optional[str] = None,
        authorization_method: str = "manual_guard",
        authorized_by: Optional[uuid.UUID] = None,
        camera_snapshot_url: Optional[str] = None,
        confidence_score: Optional[float] = None,
        metadata: Optional[dict] = None
    ):
        """Log a physical access event"""

        log = AccessLog(
            tenant_id=tenant_id,
            event_type=event_type,
            access_point=access_point,
            direction="in" if event_type in ("entry", "visitor_entry") else "out",
            resident_id=resident_id,
            visitor_name=visitor_name,
            vehicle_plate=vehicle_plate,
            authorization_method=authorization_method,
            authorized_by=authorized_by,
            camera_snapshot_url=camera_snapshot_url,
            confidence_score=confidence_score,
            metadata=metadata or {}
        )

        self.session.add(log)
        self.session.commit()
        return log

# Usage in Agente Portero
async def on_gate_access_granted(
    tenant_id: uuid.UUID,
    plate: str,
    resident: Resident,
    snapshot_url: str,
    confidence: float
):
    access_log = get_access_log_service(db)

    await access_log.log_entry(
        tenant_id=tenant_id,
        access_point="main_gate",
        event_type="entry",
        resident_id=resident.id,
        vehicle_plate=plate,
        authorization_method="auto_plate",
        camera_snapshot_url=snapshot_url,
        confidence_score=confidence,
        metadata={
            "resident_name": resident.name,
            "unit": resident.unit,
            "vehicle_model": resident.vehicles[0].get("model") if resident.vehicles else None
        }
    )
```

## Frontend: Audit Log Viewer

### Audit Log Table Component

```typescript
// features/audit/components/AuditLogTable.tsx
'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';

interface AuditLog {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  actor_email: string;
  actor_role: string;
  status: 'success' | 'failure' | 'partial';
  created_at: string;
  metadata: Record<string, any>;
}

export function AuditLogTable() {
  const [filters, setFilters] = useState({
    action: '',
    resource_type: '',
    actor_email: '',
    status: '',
    from_date: '',
    to_date: ''
  });

  const { data: logs, isLoading } = useQuery({
    queryKey: ['audit-logs', filters],
    queryFn: () => fetchAuditLogs(filters)
  });

  const getStatusBadge = (status: string) => {
    const variants = {
      success: 'bg-green-100 text-green-800',
      failure: 'bg-red-100 text-red-800',
      partial: 'bg-yellow-100 text-yellow-800'
    };
    return <Badge className={variants[status] || ''}>{status}</Badge>;
  };

  const getActionBadge = (action: string) => {
    const variants = {
      create: 'bg-blue-100 text-blue-800',
      update: 'bg-purple-100 text-purple-800',
      delete: 'bg-red-100 text-red-800',
      login: 'bg-green-100 text-green-800'
    };
    return <Badge className={variants[action] || 'bg-gray-100'}>{action}</Badge>;
  };

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-4 flex-wrap">
        <Input
          placeholder="Filter by email..."
          value={filters.actor_email}
          onChange={(e) => setFilters({ ...filters, actor_email: e.target.value })}
          className="w-48"
        />
        <Select
          value={filters.action}
          onValueChange={(v) => setFilters({ ...filters, action: v })}
        >
          <option value="">All actions</option>
          <option value="create">Create</option>
          <option value="update">Update</option>
          <option value="delete">Delete</option>
          <option value="login">Login</option>
        </Select>
        <Select
          value={filters.status}
          onValueChange={(v) => setFilters({ ...filters, status: v })}
        >
          <option value="">All statuses</option>
          <option value="success">Success</option>
          <option value="failure">Failure</option>
        </Select>
      </div>

      {/* Table */}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Timestamp</TableHead>
            <TableHead>Action</TableHead>
            <TableHead>Resource</TableHead>
            <TableHead>Actor</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Details</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {logs?.map((log: AuditLog) => (
            <TableRow key={log.id}>
              <TableCell className="text-sm text-gray-500">
                {format(new Date(log.created_at), 'yyyy-MM-dd HH:mm:ss')}
              </TableCell>
              <TableCell>{getActionBadge(log.action)}</TableCell>
              <TableCell>
                <span className="font-medium">{log.resource_type}</span>
                {log.resource_id && (
                  <span className="text-xs text-gray-400 ml-1">
                    ({log.resource_id.slice(0, 8)}...)
                  </span>
                )}
              </TableCell>
              <TableCell>
                <div className="text-sm">{log.actor_email}</div>
                <div className="text-xs text-gray-400">{log.actor_role}</div>
              </TableCell>
              <TableCell>{getStatusBadge(log.status)}</TableCell>
              <TableCell>
                <button
                  onClick={() => showDetails(log)}
                  className="text-blue-500 hover:underline text-sm"
                >
                  View
                </button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
```

## Querying Audit Logs

### Common Queries

```sql
-- Recent activity for a tenant
SELECT * FROM audit_logs
WHERE tenant_id = $1
ORDER BY created_at DESC
LIMIT 100;

-- Failed actions (potential security issues)
SELECT * FROM audit_logs
WHERE tenant_id = $1 AND status = 'failure'
ORDER BY created_at DESC;

-- User activity timeline
SELECT * FROM audit_logs
WHERE actor_id = $1
ORDER BY created_at DESC;

-- Changes to a specific resource
SELECT * FROM audit_logs
WHERE resource_type = 'resident' AND resource_id = $1
ORDER BY created_at;

-- Access patterns for security analysis
SELECT
  DATE_TRUNC('hour', created_at) as hour,
  action,
  COUNT(*) as count
FROM audit_logs
WHERE tenant_id = $1
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY 1, 2
ORDER BY 1;
```

## Best Practices

### DO
- Log all write operations automatically
- Include before/after values for updates
- Use request IDs for correlation
- Index by tenant_id and created_at
- Implement log retention policies
- Make logs append-only (no updates/deletes)

### DON'T
- Don't log passwords or sensitive tokens
- Don't log in hot paths synchronously (use async)
- Don't skip logging on errors
- Don't allow users to delete their own audit logs
- Don't log too much detail (balance vs storage)

## Retention Policy

```sql
-- Delete logs older than 90 days (run as cron job)
DELETE FROM audit_logs
WHERE created_at < NOW() - INTERVAL '90 days';

-- Or archive to cold storage first
INSERT INTO audit_logs_archive
SELECT * FROM audit_logs
WHERE created_at < NOW() - INTERVAL '90 days';

DELETE FROM audit_logs
WHERE created_at < NOW() - INTERVAL '90 days';
```

---

*This skill provides comprehensive audit logging for security, compliance, and operational visibility.*
