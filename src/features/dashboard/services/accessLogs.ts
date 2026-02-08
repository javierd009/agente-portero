import { createClient } from '@/lib/supabase/client'
import type { AccessLog } from '../types/access-log'

function startOfTodayISO(): string {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  return d.toISOString()
}

export async function fetchAccessLogsToday(limit = 50): Promise<AccessLog[]> {
  const supabase = createClient()

  const { data, error } = await supabase
    .from('access_logs')
    .select(
      'id, condominium_id, event_type, access_point, direction, resident_id, visitor_id, visitor_name, vehicle_plate, authorization_method, camera_snapshot_url, confidence_score, metadata, created_at'
    )
    .gte('created_at', startOfTodayISO())
    .order('created_at', { ascending: false })
    .limit(limit)

  if (error) throw error
  return (data ?? []) as AccessLog[]
}
