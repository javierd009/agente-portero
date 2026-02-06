---
name: realtime-events
description: Implement real-time event streaming with WebSocket, SSE, and Supabase Realtime. Use for live notifications, dashboards, IoT events, and collaborative features.
license: MIT
---

# Real-Time Events Skill

## Purpose
Implement real-time event streaming for live updates, notifications, and collaborative features using WebSocket, Server-Sent Events (SSE), or Supabase Realtime.

## When to Use
- Live notifications (new visitor, gate opened, alert)
- Real-time dashboards
- IoT event streaming (camera events, sensor data)
- Collaborative features
- Live activity feeds

## Architecture Options

### Option 1: Supabase Realtime (Recommended for Supabase users)
```
┌──────────┐     ┌──────────────┐     ┌──────────┐
│  Client  │◄────│   Supabase   │◄────│  Backend │
│  (React) │     │   Realtime   │     │ (FastAPI)│
└──────────┘     └──────────────┘     └──────────┘
     ▲                                      │
     │         WebSocket connection         │
     └──────────────────────────────────────┘
```

### Option 2: Custom WebSocket (Full control)
```
┌──────────┐     ┌──────────────┐     ┌──────────┐
│  Client  │◄────│  WebSocket   │◄────│  Backend │
│  (React) │     │   Server     │     │ (FastAPI)│
└──────────┘     └──────────────┘     └──────────┘
```

### Option 3: Server-Sent Events (Simple, one-way)
```
┌──────────┐     ┌──────────────┐
│  Client  │◄────│   Backend    │
│  (React) │ SSE │  (FastAPI)   │
└──────────┘     └──────────────┘
```

## Supabase Realtime Implementation

### Database Setup

```sql
-- Events table for broadcasting
CREATE TABLE realtime_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,  -- 'visitor_arrived', 'gate_opened', 'alert'
  payload JSONB NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable realtime on this table
ALTER PUBLICATION supabase_realtime ADD TABLE realtime_events;

-- RLS: Only see events from your tenant
ALTER TABLE realtime_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY realtime_events_select ON realtime_events
  FOR SELECT
  USING (
    tenant_id IN (
      SELECT tenant_id FROM user_tenants
      WHERE user_id = auth.uid()
    )
  );
```

### Backend: Emit Events (FastAPI)

```python
# services/events.py
from supabase import create_client, Client
import os
import uuid
from datetime import datetime

supabase: Client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"]
)

async def emit_event(
    tenant_id: uuid.UUID,
    event_type: str,
    payload: dict
):
    """Emit real-time event to all connected clients of a tenant"""
    event = {
        "tenant_id": str(tenant_id),
        "event_type": event_type,
        "payload": payload,
        "created_at": datetime.utcnow().isoformat()
    }

    # Insert triggers Supabase Realtime broadcast
    supabase.table("realtime_events").insert(event).execute()

    return event

# Usage examples:
async def on_visitor_arrived(tenant_id: uuid.UUID, visitor: dict):
    await emit_event(
        tenant_id=tenant_id,
        event_type="visitor_arrived",
        payload={
            "visitor_name": visitor["name"],
            "vehicle_plate": visitor.get("plate"),
            "camera_snapshot": visitor.get("snapshot_url"),
            "timestamp": datetime.utcnow().isoformat()
        }
    )

async def on_gate_opened(tenant_id: uuid.UUID, gate_id: str, authorized_by: str):
    await emit_event(
        tenant_id=tenant_id,
        event_type="gate_opened",
        payload={
            "gate_id": gate_id,
            "authorized_by": authorized_by,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

async def on_alert(tenant_id: uuid.UUID, alert_type: str, message: str):
    await emit_event(
        tenant_id=tenant_id,
        event_type="alert",
        payload={
            "alert_type": alert_type,  # 'security', 'system', 'warning'
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

### Frontend: Subscribe to Events (Next.js)

```typescript
// hooks/useRealtimeEvents.ts
'use client';

import { useEffect, useCallback } from 'react';
import { createClient, RealtimeChannel } from '@supabase/supabase-js';
import { useTenant } from '@/contexts/TenantContext';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

type EventType = 'visitor_arrived' | 'gate_opened' | 'alert' | '*';

interface RealtimeEvent {
  id: string;
  tenant_id: string;
  event_type: string;
  payload: Record<string, any>;
  created_at: string;
}

export function useRealtimeEvents(
  eventTypes: EventType[],
  onEvent: (event: RealtimeEvent) => void
) {
  const { currentTenant } = useTenant();

  useEffect(() => {
    if (!currentTenant) return;

    // Subscribe to INSERT events on realtime_events table
    const channel: RealtimeChannel = supabase
      .channel(`tenant-${currentTenant.id}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'realtime_events',
          filter: `tenant_id=eq.${currentTenant.id}`
        },
        (payload) => {
          const event = payload.new as RealtimeEvent;

          // Filter by event type if not subscribing to all
          if (eventTypes.includes('*') || eventTypes.includes(event.event_type as EventType)) {
            onEvent(event);
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [currentTenant, eventTypes, onEvent]);
}

// Usage in component
export function NotificationCenter() {
  const [notifications, setNotifications] = useState<RealtimeEvent[]>([]);

  useRealtimeEvents(['visitor_arrived', 'alert'], (event) => {
    setNotifications(prev => [event, ...prev].slice(0, 50));

    // Show toast notification
    toast({
      title: getEventTitle(event.event_type),
      description: event.payload.message || JSON.stringify(event.payload),
    });
  });

  return (
    <div className="notifications">
      {notifications.map(n => (
        <NotificationCard key={n.id} event={n} />
      ))}
    </div>
  );
}
```

## Custom WebSocket Implementation

### Backend: WebSocket Server (FastAPI)

```python
# api/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
import json
import uuid

router = APIRouter()

# Connection manager
class ConnectionManager:
    def __init__(self):
        # tenant_id -> set of WebSocket connections
        self.connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, tenant_id: str):
        await websocket.accept()
        if tenant_id not in self.connections:
            self.connections[tenant_id] = set()
        self.connections[tenant_id].add(websocket)

    def disconnect(self, websocket: WebSocket, tenant_id: str):
        if tenant_id in self.connections:
            self.connections[tenant_id].discard(websocket)

    async def broadcast_to_tenant(self, tenant_id: str, message: dict):
        if tenant_id in self.connections:
            dead_connections = set()
            for connection in self.connections[tenant_id]:
                try:
                    await connection.send_json(message)
                except:
                    dead_connections.add(connection)

            # Clean up dead connections
            self.connections[tenant_id] -= dead_connections

manager = ConnectionManager()

@router.websocket("/ws/{tenant_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    tenant_id: str,
    token: str  # Auth token as query param
):
    # Verify token and tenant access
    user = await verify_token(token)
    if not user or not await has_tenant_access(user.id, tenant_id):
        await websocket.close(code=4003)
        return

    await manager.connect(websocket, tenant_id)

    try:
        while True:
            # Keep connection alive, handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle client messages (e.g., acknowledgments)
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, tenant_id)

# Function to broadcast from anywhere in the app
async def broadcast_event(tenant_id: str, event_type: str, payload: dict):
    await manager.broadcast_to_tenant(tenant_id, {
        "type": event_type,
        "payload": payload,
        "timestamp": datetime.utcnow().isoformat()
    })
```

### Frontend: WebSocket Client

```typescript
// hooks/useWebSocket.ts
'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import { useTenant } from '@/contexts/TenantContext';

interface WebSocketMessage {
  type: string;
  payload: Record<string, any>;
  timestamp: string;
}

export function useWebSocket(onMessage: (msg: WebSocketMessage) => void) {
  const { currentTenant } = useTenant();
  const ws = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const reconnectTimeout = useRef<NodeJS.Timeout>();

  const connect = useCallback(() => {
    if (!currentTenant) return;

    const token = localStorage.getItem('access_token');
    const url = `${process.env.NEXT_PUBLIC_WS_URL}/ws/${currentTenant.id}?token=${token}`;

    ws.current = new WebSocket(url);

    ws.current.onopen = () => {
      setIsConnected(true);
      console.log('WebSocket connected');
    };

    ws.current.onmessage = (event) => {
      const message = JSON.parse(event.data) as WebSocketMessage;
      onMessage(message);
    };

    ws.current.onclose = () => {
      setIsConnected(false);
      // Reconnect after 3 seconds
      reconnectTimeout.current = setTimeout(connect, 3000);
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      ws.current?.close();
    };
  }, [currentTenant, onMessage]);

  useEffect(() => {
    connect();

    // Ping every 30 seconds to keep connection alive
    const pingInterval = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);

    return () => {
      clearInterval(pingInterval);
      clearTimeout(reconnectTimeout.current);
      ws.current?.close();
    };
  }, [connect]);

  return { isConnected };
}
```

## Server-Sent Events (SSE) Implementation

### Backend: SSE Endpoint (FastAPI)

```python
# api/sse.py
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import asyncio
import json

router = APIRouter()

# Event queue per tenant
event_queues: Dict[str, asyncio.Queue] = {}

async def event_generator(tenant_id: str, request: Request):
    """Generate SSE events for a tenant"""
    queue = event_queues.setdefault(tenant_id, asyncio.Queue())

    try:
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                break

            try:
                # Wait for event with timeout
                event = await asyncio.wait_for(queue.get(), timeout=30)
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                # Send keepalive
                yield f": keepalive\n\n"

    except asyncio.CancelledError:
        pass

@router.get("/events/{tenant_id}")
async def sse_events(tenant_id: str, request: Request):
    # Verify tenant access here

    return StreamingResponse(
        event_generator(tenant_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

# Emit event to SSE clients
async def emit_sse_event(tenant_id: str, event_type: str, payload: dict):
    if tenant_id in event_queues:
        await event_queues[tenant_id].put({
            "type": event_type,
            "payload": payload
        })
```

### Frontend: SSE Client

```typescript
// hooks/useSSE.ts
export function useSSE(onMessage: (msg: any) => void) {
  const { currentTenant } = useTenant();

  useEffect(() => {
    if (!currentTenant) return;

    const eventSource = new EventSource(
      `/api/events/${currentTenant.id}`
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };

    eventSource.onerror = () => {
      eventSource.close();
      // Reconnect after delay
      setTimeout(() => {
        // Recreate EventSource
      }, 3000);
    };

    return () => eventSource.close();
  }, [currentTenant, onMessage]);
}
```

## IoT Event Pattern (Agente Portero)

### Camera Event Flow

```
┌─────────┐     ┌──────────┐     ┌─────────┐     ┌──────────┐
│ Camera  │────►│  Vision  │────►│ Backend │────►│ Dashboard│
│(Hikvision)   │  Service  │     │(FastAPI)│     │ (React)  │
└─────────┘     └──────────┘     └─────────┘     └──────────┘
   ISAPI          YOLO+OCR        emit_event    Realtime sub
```

```python
# vision_service/handlers.py
async def on_plate_detected(tenant_id: str, plate: str, confidence: float, image_url: str):
    """Called when vision service detects a license plate"""

    # 1. Lookup resident by plate
    resident = await lookup_resident_by_plate(tenant_id, plate)

    if resident:
        # 2. Auto-authorize known resident
        await emit_event(tenant_id, "resident_arrived", {
            "resident_id": str(resident.id),
            "resident_name": resident.name,
            "unit": resident.unit,
            "plate": plate,
            "image_url": image_url,
            "auto_authorized": True
        })

        # 3. Open gate automatically
        await open_gate(tenant_id)

    else:
        # 4. Unknown vehicle - alert guards
        await emit_event(tenant_id, "unknown_vehicle", {
            "plate": plate,
            "confidence": confidence,
            "image_url": image_url,
            "requires_verification": True
        })
```

## Best Practices

### DO
- Use tenant isolation for all event channels
- Implement reconnection logic on frontend
- Send keepalive messages to detect dead connections
- Clean up subscriptions on component unmount
- Rate limit event emission

### DON'T
- Don't broadcast sensitive data without filtering
- Don't keep connections open without heartbeat
- Don't emit events synchronously in request handlers
- Don't store events indefinitely (use TTL)

---

*This skill enables real-time features for live dashboards, notifications, and IoT event streaming.*
