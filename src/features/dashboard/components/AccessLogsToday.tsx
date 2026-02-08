'use client'

import * as React from 'react'
import { fetchAccessLogsToday } from '../services/accessLogs'
import type { AccessLog } from '../types/access-log'

function formatTime(ts: string) {
  const d = new Date(ts)
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function AccessLogsToday() {
  const [items, setItems] = React.useState<AccessLog[]>([])
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        setLoading(true)
        const data = await fetchAccessLogsToday(50)
        if (!cancelled) setItems(data)
      } catch (e: any) {
        if (!cancelled) setError(e?.message ?? 'Error cargando bitácora')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="mt-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Bitácora (hoy)</h2>
        <button
          className="rounded-md border px-3 py-1 text-sm"
          onClick={async () => {
            setError(null)
            setLoading(true)
            try {
              const data = await fetchAccessLogsToday(50)
              setItems(data)
            } catch (e: any) {
              setError(e?.message ?? 'Error refrescando bitácora')
            } finally {
              setLoading(false)
            }
          }}
        >
          Refrescar
        </button>
      </div>

      {loading && <p className="mt-3 text-sm text-gray-600">Cargando…</p>}
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      <div className="mt-4 overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b text-left">
              <th className="py-2 pr-3">Hora</th>
              <th className="py-2 pr-3">Evento</th>
              <th className="py-2 pr-3">Punto</th>
              <th className="py-2 pr-3">Visitante</th>
              <th className="py-2 pr-3">Placa</th>
              <th className="py-2 pr-3">Método</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.id} className="border-b">
                <td className="py-2 pr-3 whitespace-nowrap">{formatTime(it.created_at)}</td>
                <td className="py-2 pr-3">{it.event_type}</td>
                <td className="py-2 pr-3">{it.access_point}</td>
                <td className="py-2 pr-3">{it.visitor_name ?? '-'}</td>
                <td className="py-2 pr-3">{it.vehicle_plate ?? '-'}</td>
                <td className="py-2 pr-3">{it.authorization_method}</td>
              </tr>
            ))}
            {!loading && items.length === 0 && (
              <tr>
                <td className="py-3 text-gray-600" colSpan={6}>
                  Sin eventos hoy.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
