const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ApiOptions extends RequestInit {
  tenantId?: string
}

export async function api<T>(
  endpoint: string,
  options: ApiOptions = {}
): Promise<T> {
  const { tenantId, ...fetchOptions } = options

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  if (tenantId) {
    (headers as Record<string, string>)['X-Tenant-ID'] = tenantId
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...fetchOptions,
    headers,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || `API Error: ${response.status}`)
  }

  // Handle 204 No Content responses (e.g., DELETE)
  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}

// Typed API functions
export const apiClient = {
  // Agents
  getAgents: (tenantId: string) =>
    api<Agent[]>('/api/v1/agents/', { tenantId }),

  createAgent: (tenantId: string, data: AgentCreate) =>
    api<Agent>('/api/v1/agents/', {
      method: 'POST',
      body: JSON.stringify(data),
      tenantId,
    }),

  // Residents
  getResidents: (tenantId: string, params?: { unit?: string }) => {
    const query = params?.unit ? `?unit=${params.unit}` : ''
    return api<Resident[]>(`/api/v1/access/residents${query}`, { tenantId })
  },

  createResident: (tenantId: string, data: ResidentCreate) =>
    api<Resident>('/api/v1/access/residents', {
      method: 'POST',
      body: JSON.stringify(data),
      tenantId,
    }),

  // Access Logs
  getAccessLogs: (tenantId: string, params?: { limit?: number }) => {
    const query = params?.limit ? `?limit=${params.limit}` : ''
    return api<AccessLog[]>(`/api/v1/access/logs${query}`, { tenantId })
  },

  // Visitors
  getVisitors: (tenantId: string) =>
    api<Visitor[]>('/api/v1/visitors/', { tenantId }),

  createVisitor: (tenantId: string, data: VisitorCreate) =>
    api<Visitor>('/api/v1/visitors/', {
      method: 'POST',
      body: JSON.stringify(data),
      tenantId,
    }),

  // Camera Events
  getCameraEvents: (tenantId: string, params?: { limit?: number }) => {
    const query = params?.limit ? `?limit=${params.limit}` : ''
    return api<CameraEvent[]>(`/api/v1/camera-events/${query}`, { tenantId })
  },

  getRecentPlates: (tenantId: string) =>
    api<{ plates: PlateDetection[] }>('/api/v1/camera-events/plates/recent', { tenantId }),

  // Notifications
  getNotifications: (tenantId: string) =>
    api<Notification[]>('/api/v1/notifications/', { tenantId }),

  // Reports
  getReports: (tenantId: string, params?: { status?: string; report_type?: string; limit?: number }) => {
    const query = new URLSearchParams()
    if (params?.status) query.append('status', params.status)
    if (params?.report_type) query.append('report_type', params.report_type)
    if (params?.limit) query.append('limit', params.limit.toString())
    const queryString = query.toString() ? `?${query.toString()}` : ''
    return api<Report[]>(`/api/v1/reports/${queryString}`, { tenantId })
  },

  createReport: (tenantId: string, data: ReportCreate) =>
    api<Report>('/api/v1/reports/', {
      method: 'POST',
      body: JSON.stringify(data),
      tenantId,
    }),

  updateReport: (tenantId: string, reportId: string, data: ReportUpdate) =>
    api<Report>(`/api/v1/reports/${reportId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
      tenantId,
    }),

  getReportStats: (tenantId: string) =>
    api<ReportStats>('/api/v1/reports/stats/summary', { tenantId }),

  // Cameras (VMS)
  getCameras: (tenantId: string) =>
    api<Camera[]>('/api/v1/cameras/', { tenantId }),

  createCamera: (tenantId: string, data: CameraCreate) =>
    api<Camera>('/api/v1/cameras/', {
      method: 'POST',
      body: JSON.stringify(data),
      tenantId,
    }),

  updateCamera: (tenantId: string, cameraId: string, data: CameraUpdate) =>
    api<Camera>(`/api/v1/cameras/${cameraId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
      tenantId,
    }),

  deleteCamera: (tenantId: string, cameraId: string) =>
    api<void>(`/api/v1/cameras/${cameraId}`, {
      method: 'DELETE',
      tenantId,
    }),

  testCameraConnection: (tenantId: string, cameraId: string) =>
    api<CameraTestResult>(`/api/v1/cameras/${cameraId}/test`, {
      method: 'POST',
      tenantId,
    }),

  getCameraSnapshot: (tenantId: string, cameraId: string) =>
    api<CameraSnapshot>(`/api/v1/cameras/${cameraId}/snapshot`, { tenantId }),

  // Condominiums
  getCondominium: (condominiumId: string) =>
    api<Condominium>(`/api/v1/condominiums/${condominiumId}`),

  updateCondominium: (condominiumId: string, data: CondominiumUpdate) =>
    api<Condominium>(`/api/v1/condominiums/${condominiumId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
}

// Vision Service - Calls go through backend proxy to avoid HTTPS/HTTP mixed content issues
export const visionService = {
  // Test camera connection via vision-service (through backend proxy)
  testCamera: async (visionServiceUrl: string, camera: { host: string; port: number; username: string; password: string }) => {
    const params = new URLSearchParams({
      vision_url: visionServiceUrl,
      host: camera.host,
      port: camera.port.toString(),
      username: camera.username,
      password: camera.password,
    })
    const response = await fetch(`${API_URL}/api/v1/cameras/vision-service/test-camera?${params}`, {
      method: 'POST',
    })
    return response.json() as Promise<VisionTestResult>
  },

  // Get snapshot via vision-service (through backend proxy)
  getSnapshot: async (visionServiceUrl: string, channelId: string = '1') => {
    const params = new URLSearchParams({
      vision_url: visionServiceUrl,
      channel_id: channelId,
    })
    const response = await fetch(`${API_URL}/api/v1/cameras/vision-service/snapshot?${params}`)
    return response.json() as Promise<VisionSnapshotResult>
  },

  // Health check (through backend proxy to avoid mixed content)
  healthCheck: async (visionServiceUrl: string) => {
    try {
      const params = new URLSearchParams({ vision_url: visionServiceUrl })
      const response = await fetch(`${API_URL}/api/v1/cameras/vision-service/health?${params}`, {
        method: 'GET',
        signal: AbortSignal.timeout(10000),
      })
      if (response.ok) {
        const data = await response.json()
        return data.status === 'healthy'
      }
      return false
    } catch (error) {
      console.error('Vision Service health check failed:', error)
      return false
    }
  },

  // List cameras from vision-service
  listCameras: async (visionServiceUrl: string) => {
    const response = await fetch(`${visionServiceUrl}/cameras`)
    return response.json() as Promise<{ cameras: VisionCamera[] }>
  },
}

// Types
export interface Agent {
  id: string
  condominium_id: string
  name: string
  extension: string
  prompt: string
  voice_id: string | null
  language: string
  is_active: boolean
  settings: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface AgentCreate {
  condominium_id: string
  name: string
  extension: string
  prompt?: string
  voice_id?: string
  language?: string
}

export interface Resident {
  id: string
  condominium_id: string
  user_id: string | null
  name: string
  unit: string
  phone: string | null
  email: string | null
  whatsapp: string | null
  authorized_visitors: string[]
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ResidentCreate {
  condominium_id: string
  name: string
  unit: string
  phone?: string
  email?: string
  whatsapp?: string
}

export interface AccessLog {
  id: string
  condominium_id: string
  event_type: string
  access_point: string
  direction: string | null
  resident_id: string | null
  visitor_id: string | null
  visitor_name: string | null
  vehicle_plate: string | null
  authorization_method: string
  authorized_by: string | null
  camera_snapshot_url: string | null
  confidence_score: number | null
  metadata: Record<string, unknown>
  created_at: string
}

export interface Visitor {
  id: string
  condominium_id: string
  resident_id: string | null
  name: string
  id_number: string | null
  phone: string | null
  vehicle_plate: string | null
  reason: string | null
  authorized_by: string | null
  entry_time: string | null
  exit_time: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface VisitorCreate {
  condominium_id: string
  resident_id?: string
  name: string
  id_number?: string
  phone?: string
  vehicle_plate?: string
  reason?: string
  authorized_by?: string
}

export interface CameraEvent {
  id: string
  condominium_id: string
  camera_id: string
  event_type: string
  plate_number: string | null
  plate_confidence: number | null
  snapshot_url: string | null
  processed: boolean
  created_at: string
}

export interface PlateDetection {
  plate: string
  timestamp: string
  camera_id: string
}

export interface Notification {
  id: string
  condominium_id: string
  resident_id: string | null
  channel: string
  recipient: string
  notification_type: string
  title: string
  message: string
  status: string
  sent_at: string | null
  delivered_at: string | null
  created_at: string
}

export interface Report {
  id: string
  condominium_id: string
  resident_id: string | null
  report_type: string  // 'maintenance', 'security', 'noise', 'cleaning', 'other'
  title: string
  description: string
  location: string | null
  urgency: string  // 'low', 'normal', 'high', 'urgent'
  status: string  // 'pending', 'in_progress', 'resolved', 'closed'
  source: string  // 'web', 'whatsapp', 'voice', 'email'
  photo_urls: Record<string, unknown>
  assigned_to: string | null
  resolved_at: string | null
  resolution_notes: string | null
  extra_data: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface ReportCreate {
  condominium_id: string
  resident_id?: string
  report_type: string
  title: string
  description: string
  location?: string
  urgency?: string
  source?: string
}

export interface ReportUpdate {
  status?: string
  assigned_to?: string
  resolution_notes?: string
}

export interface ReportStats {
  total: number
  by_status: Record<string, number>
  by_type: Record<string, number>
  by_urgency: Record<string, number>
  pending: number
  in_progress: number
  resolved: number
}

// Camera types (VMS)
export interface Camera {
  id: string
  condominium_id: string
  name: string
  location: string | null
  camera_type: string
  has_ptz: boolean
  has_anpr: boolean
  has_face: boolean
  is_active: boolean
  is_online: boolean
  last_seen: string | null
  created_at: string
}

export interface CameraCreate {
  condominium_id: string
  name: string
  location?: string
  host: string
  port?: number
  username: string
  password: string
  camera_type?: string
  has_ptz?: boolean
  has_anpr?: boolean
  has_face?: boolean
}

export interface CameraUpdate {
  name?: string
  location?: string
  host?: string
  port?: number
  username?: string
  password?: string
  is_active?: boolean
  has_ptz?: boolean
  has_anpr?: boolean
  has_face?: boolean
}

export interface CameraTestResult {
  camera_id: string
  is_online: boolean
  device_info: Record<string, unknown> | null
}

export interface CameraSnapshot {
  camera_id: string
  image: string  // base64 data URL
  timestamp: string
}

// Condominium types
export interface CondominiumSettings {
  vision_service_url?: string
  voice_service_url?: string
  go2rtc_url?: string
  hikvision?: {
    host?: string
    port?: number
    username?: string
  }
}

export interface Condominium {
  id: string
  name: string
  slug: string
  address: string | null
  timezone: string
  settings: CondominiumSettings
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CondominiumUpdate {
  name?: string
  address?: string
  timezone?: string
  settings?: CondominiumSettings
  is_active?: boolean
}

// Vision Service types (edge computing)
export interface VisionTestResult {
  host: string
  port: number
  is_online: boolean
  device_info: {
    name?: string
    model?: string
    serial?: string
    firmware?: string
  } | null
  error: string | null
}

export interface VisionSnapshotResult {
  camera_id: string
  image: string  // base64 data URL
  success: boolean
  error?: string
}

export interface VisionCamera {
  id: string
  name: string
  enabled: boolean
}
