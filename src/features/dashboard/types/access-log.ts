export type AccessLog = {
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
  camera_snapshot_url: string | null
  confidence_score: number | null
  metadata: Record<string, unknown> | null
  created_at: string
}
