import { useEffect, useState } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { CheckCircle2, XCircle, AlertCircle, RefreshCw, History } from 'lucide-react'
import { format } from 'date-fns'
import { API_BASE } from '@/lib/config'
import { cn } from '@/lib/utils'
import type { SyncHistoryResult, SyncHistoryItem } from '@/types/api'

const STATUS_CONFIG = {
  COMPLETED: {
    icon: CheckCircle2,
    label: 'Completed',
    className: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  },
  ERROR: {
    icon: XCircle,
    label: 'Error',
    className: 'bg-red-100 text-red-800 border-red-200',
  },
  CANCELLED: {
    icon: AlertCircle,
    label: 'Cancelled',
    className: 'bg-amber-100 text-amber-800 border-amber-200',
  },
} as const

interface SyncHistoryPanelProps {
  limit?: number
  compact?: boolean
}

export function SyncHistoryPanel({ limit = 10, compact = false }: SyncHistoryPanelProps) {
  const [history, setHistory] = useState<SyncHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchHistory = async () => {
    try {
      setLoading(true)
      setError(null)
      const res = await fetch(`${API_BASE}/sync/history?limit=${limit}`)
      if (!res.ok) throw new Error('Failed to fetch sync history')
      const data: SyncHistoryResult = await res.json()
      setHistory(data.sync_jobs)
    } catch (err) {
      console.error(err)
      setError('Failed to load sync history')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHistory()
  }, [limit])

  const calculateDuration = (started: string, completed: string) => {
    const start = new Date(started)
    const end = new Date(completed)
    const diffMs = end.getTime() - start.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffSecs = Math.floor((diffMs % 60000) / 1000)
    
    if (diffMins > 0) {
      return `${diffMins}m ${diffSecs}s`
    }
    return `${diffSecs}s`
  }

  if (loading && history.length === 0) {
    return (
      <div className="flex h-32 items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-200 border-t-blue-600"></div>
          <p className="text-xs font-medium text-slate-500">Loading history...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-medium text-red-800">
        {error}
      </div>
    )
  }

  if (history.length === 0) {
    return (
      <div className="flex h-32 flex-col items-center justify-center text-center">
        <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-slate-50">
          <History className="h-6 w-6 text-slate-300" />
        </div>
        <p className="text-sm font-bold text-slate-900">No sync history</p>
        <p className="mt-1 text-xs text-slate-500">Run your first sync to see results here</p>
      </div>
    )
  }

  if (compact) {
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold text-slate-900">Recent Syncs</h3>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchHistory}
            className="h-7 w-7 rounded-lg p-0 text-slate-400 hover:text-slate-600"
          >
            <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
          </Button>
        </div>
        <div className="space-y-2">
          {history.slice(0, 5).map((job) => {
            const statusStyle = STATUS_CONFIG[job.status]
            const StatusIcon = statusStyle.icon
            
            return (
              <div
                key={job.job_id}
                className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50/50 p-3 transition-colors hover:bg-slate-100"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={cn(
                      'flex h-8 w-8 items-center justify-center rounded-lg',
                      statusStyle.className,
                    )}
                  >
                    <StatusIcon className="h-4 w-4" />
                  </div>
                  <div className="space-y-0.5">
                    <p className="text-xs font-bold text-slate-900">
                      {format(new Date(job.started_at), 'MMM dd, HH:mm')}
                    </p>
                    <p className="text-[10px] font-medium text-slate-500">
                      {job.success_count}/{job.total_items} successful
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge
                    variant="outline"
                    className={cn('text-[10px] font-bold', statusStyle.className)}
                  >
                    {statusStyle.label}
                  </Badge>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <History className="h-5 w-5 text-blue-600" />
          <h2 className="text-base font-bold text-slate-900">Sync History</h2>
          <Badge variant="outline" className="bg-slate-50 text-xs font-bold text-slate-600">
            {history.length} jobs
          </Badge>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchHistory}
          className="h-8 rounded-lg border-slate-200 text-xs font-bold"
        >
          <RefreshCw className={cn('mr-2 h-3.5 w-3.5', loading && 'animate-spin')} />
          Refresh
        </Button>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        <Table>
          <TableHeader className="bg-slate-50">
            <TableRow className="border-slate-100">
              <TableHead className="font-bold text-slate-500">Started</TableHead>
              <TableHead className="font-bold text-slate-500">Status</TableHead>
              <TableHead className="text-center font-bold text-slate-500">Items</TableHead>
              <TableHead className="text-center font-bold text-slate-500">Success</TableHead>
              <TableHead className="text-center font-bold text-slate-500">Failed</TableHead>
              <TableHead className="text-center font-bold text-slate-500">Fake</TableHead>
              <TableHead className="text-right font-bold text-slate-500">Duration</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {history.map((job) => {
              const statusStyle = STATUS_CONFIG[job.status]
              const StatusIcon = statusStyle.icon
              const duration = calculateDuration(job.started_at, job.completed_at)

              return (
                <TableRow
                  key={job.job_id}
                  className="border-slate-100 transition-colors hover:bg-blue-50/50"
                >
                  <TableCell className="font-medium text-slate-600">
                    <div className="space-y-0.5">
                      <div className="text-sm font-bold">
                        {format(new Date(job.started_at), 'MMM dd, yyyy')}
                      </div>
                      <div className="text-xs text-slate-500">
                        {format(new Date(job.started_at), 'HH:mm:ss')}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={cn(
                        'flex w-fit items-center gap-1.5 rounded-lg border px-2.5 py-0.5 font-bold',
                        statusStyle.className,
                      )}
                    >
                      <StatusIcon className="h-3.5 w-3.5" />
                      {statusStyle.label}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center">
                    <span className="font-bold text-slate-900">{job.total_items}</span>
                  </TableCell>
                  <TableCell className="text-center">
                    <span className="font-bold text-emerald-600">{job.success_count}</span>
                  </TableCell>
                  <TableCell className="text-center">
                    <span
                      className={cn(
                        'font-bold',
                        job.failed_count > 0 ? 'text-red-600' : 'text-slate-400',
                      )}
                    >
                      {job.failed_count}
                    </span>
                  </TableCell>
                  <TableCell className="text-center">
                    <span
                      className={cn(
                        'font-bold',
                        job.fake_count > 0 ? 'text-orange-600' : 'text-slate-400',
                      )}
                    >
                      {job.fake_count}
                    </span>
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm font-medium text-slate-600">
                    {duration}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
