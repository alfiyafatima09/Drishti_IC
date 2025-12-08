import { TrendingUp, CheckCircle2, XCircle, Database } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { DashboardStats } from '@/types/api'

// ============================================================
// TYPES
// ============================================================

interface StatCardProps {
  label: string
  value: string | number
  icon: React.ElementType
  trend?: string
  color?: string
}

interface StatsPanelProps {
  stats?: DashboardStats | null
  isLoading?: boolean
}

// ============================================================
// COMPONENTS
// ============================================================

function StatCard({ label, value, icon: Icon, trend, color = 'text-zinc-400' }: StatCardProps) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs text-zinc-500">{label}</span>
        <Icon className={cn('h-4 w-4', color)} />
      </div>
      <div className="flex items-end justify-between">
        <span className="font-mono text-2xl font-bold text-zinc-100">{value}</span>
        {trend && (
          <span className="flex items-center gap-1 text-xs text-emerald-500">
            <TrendingUp className="h-3 w-3" />
            {trend}
          </span>
        )}
      </div>
    </div>
  )
}

export function StatsPanel({ stats }: StatsPanelProps) {
  // Default values when no stats provided
  const data: DashboardStats = stats ?? {
    total_scans: 0,
    scans_today: 0,
    scans_this_week: 0,
    pass_count: 0,
    fail_count: 0,
    unknown_count: 0,
    counterfeit_count: 0,
    pass_rate_percentage: 0,
    queue_size: 0,
    fake_registry_size: 0,
    database_ic_count: 0,
  }

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <StatCard
        label="Today's Scans"
        value={data.scans_today}
        icon={TrendingUp}
        color="text-blue-400"
      />
      <StatCard
        label="Pass Rate"
        value={`${data.pass_rate_percentage.toFixed(1)}%`}
        icon={CheckCircle2}
        color="text-emerald-400"
      />
      <StatCard label="Failed" value={data.fail_count} icon={XCircle} color="text-red-400" />
      <StatCard
        label="ICs in Database"
        value={data.database_ic_count.toLocaleString()}
        icon={Database}
        color="text-zinc-400"
      />
    </div>
  )
}
