import { AccessLogsToday } from '@/features/dashboard/components/AccessLogsToday'

export default function DashboardPage() {
  return (
    <div className="min-h-screen p-8">
      <h1 className="text-3xl font-bold">Dashboard</h1>
      <p className="mt-2 text-gray-600">Resumen operativo del condominio</p>

      <AccessLogsToday />
    </div>
  )
}
