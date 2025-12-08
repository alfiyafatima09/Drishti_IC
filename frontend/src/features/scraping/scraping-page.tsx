import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import {
  Globe,
  Download,
  CheckCircle2,
  XCircle,
  Clock,
  Trash2,
  AlertCircle,
  Plus,
  ChevronLeft,
  ChevronRight,
  Filter,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { API_BASE } from '@/lib/config'

type SyncStage = 'idle' | 'processing' | 'completed' | 'error' | 'cancelled'
type QueueStatusType = 'PENDING' | 'PROCESSING' | 'FAILED'

const STATUS_OPTIONS: { value: QueueStatusType; label: string; color: string }[] = [
  { value: 'PENDING', label: 'Pending', color: 'bg-amber-100 text-amber-700 border-amber-300' },
  { value: 'PROCESSING', label: 'Processing', color: 'bg-blue-100 text-blue-700 border-blue-300' },
  { value: 'FAILED', label: 'Failed', color: 'bg-red-100 text-red-700 border-red-300' },
]

interface QueueItem {
  part_number: string
  first_seen_at?: string
  last_scanned_at?: string
  scan_count?: number
  status?: string
  retry_count?: number
  error_message?: string
}

interface QueueListResult {
  queue_items: QueueItem[]
  total_count: number
  pending_count: number
  failed_count: number
  limit: number
  offset: number
}

interface SyncStatus {
  status: 'IDLE' | 'PROCESSING' | 'COMPLETED' | 'ERROR' | 'CANCELLED'
  progress_percentage?: number
  current_item?: string | null
  message?: string | null
}

export default function ScrapingPage() {
  const [queueItems, setQueueItems] = useState<QueueItem[]>([])
  const [queueLoading, setQueueLoading] = useState(false)
  const [queueError, setQueueError] = useState<string | null>(null)
  const [queuePage, setQueuePage] = useState(0)
  const [totalCount, setTotalCount] = useState(0)
  const [pendingCount, setPendingCount] = useState(0)
  const [failedCount, setFailedCount] = useState(0)

  // Fake registry count
  const [fakeCount, setFakeCount] = useState(0)
  const [transferLoading, setTransferLoading] = useState(false)
  const [transferMessage, setTransferMessage] = useState<string | null>(null)

  // Status filter (multi-select)
  const [selectedStatuses, setSelectedStatuses] = useState<QueueStatusType[]>([])
  const [syncLimit, setSyncLimit] = useState<string>('')

  const [syncStage, setSyncStage] = useState<SyncStage>('idle')
  const [currentIC, setCurrentIC] = useState('')
  const [progress, setProgress] = useState(0)
  const [syncMessage, setSyncMessage] = useState('')
  const [pollTimer, setPollTimer] = useState<ReturnType<typeof setInterval> | null>(null)

  // Auto-poll toggle
  const [autoPollEnabled, setAutoPollEnabled] = useState(false)
  const autoPollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Form states
  const [manualPart, setManualPart] = useState('')
  const [manualNote, setManualNote] = useState('')
  const [manualLoading, setManualLoading] = useState(false)
  const [manualError, setManualError] = useState<string | null>(null)

  const ITEMS_PER_PAGE = 8

  const stageConfig: Record<SyncStage, { label: string; color: string; icon: typeof Globe }> = {
    idle: { label: 'Ready to Sync', color: 'border-slate-300 bg-slate-50', icon: Globe },
    processing: {
      label: 'Scraping & Downloading',
      color: 'border-blue-400 bg-blue-50 animate-pulse',
      icon: Download,
    },
    completed: {
      label: 'Sync Completed',
      color: 'border-emerald-400 bg-emerald-50',
      icon: CheckCircle2,
    },
    error: { label: 'Sync Failed', color: 'border-red-400 bg-red-50', icon: XCircle },
    cancelled: {
      label: 'Sync Cancelled',
      color: 'border-amber-400 bg-amber-50',
      icon: AlertCircle,
    },
  }

  const fetchQueue = useCallback(
    async (page: number = 0) => {
      setQueueLoading(true)
      setQueueError(null)
      try {
        const params = new URLSearchParams()
        params.append('limit', ITEMS_PER_PAGE.toString())
        params.append('offset', (page * ITEMS_PER_PAGE).toString())

        // Add status filters
        selectedStatuses.forEach((status) => {
          params.append('status', status)
        })

        const resp = await fetch(`${API_BASE}/queue/list?${params.toString()}`)
        if (!resp.ok) throw new Error(`Queue list failed: ${resp.status}`)
        const data: QueueListResult = await resp.json()
        setQueueItems(data.queue_items || [])
        setTotalCount(data.total_count)
        setPendingCount(data.pending_count)
        setFailedCount(data.failed_count)
      } catch (err) {
        console.error(err)
        setQueueError('Failed to load queue. Please try again.')
      } finally {
        setQueueLoading(false)
      }
    },
    [selectedStatuses],
  )

  // Fetch fake registry count
  const fetchFakeCount = useCallback(async () => {
    try {
      const resp = await fetch(`${API_BASE}/fakes/list`)
      if (!resp.ok) throw new Error('Failed to fetch fakes')
      const data = await resp.json()
      setFakeCount(data.total_count || 0)
    } catch (err) {
      console.error('Failed to fetch fake count:', err)
    }
  }, [])

  // Transfer fakes to queue
  const transferFakesToQueue = async () => {
    if (fakeCount === 0) return

    const confirmed = window.confirm(
      `Transfer ${fakeCount} items from Fake Registry to Queue?\n\nThis will move all fake ICs to the scraping queue for retry.`,
    )
    if (!confirmed) return

    setTransferLoading(true)
    setTransferMessage(null)
    try {
      const resp = await fetch(`${API_BASE}/fakes/transfer-to-queue`, { method: 'POST' })
      if (!resp.ok) throw new Error('Transfer failed')
      const data = await resp.json()
      setTransferMessage(data.message)
      // Refresh both counts
      await Promise.all([fetchQueue(queuePage), fetchFakeCount()])
    } catch (err) {
      console.error('Transfer failed:', err)
      setTransferMessage('Failed to transfer items. Please try again.')
    } finally {
      setTransferLoading(false)
    }
  }

  useEffect(() => {
    fetchQueue(queuePage)
    fetchFakeCount()
  }, [fetchQueue, fetchFakeCount, queuePage])

  // Auto-poll effect - refresh queue every 5 seconds when enabled
  useEffect(() => {
    // Clear existing timer
    if (autoPollTimerRef.current) {
      clearInterval(autoPollTimerRef.current)
      autoPollTimerRef.current = null
    }

    if (!autoPollEnabled) {
      return // Don't start timer if disabled
    }

    // Start new timer - capture current page in closure
    const currentPage = queuePage
    const currentStatuses = selectedStatuses

    const poll = async () => {
      try {
        // Fetch queue
        const params = new URLSearchParams()
        params.append('limit', ITEMS_PER_PAGE.toString())
        params.append('offset', (currentPage * ITEMS_PER_PAGE).toString())
        currentStatuses.forEach((status) => params.append('status', status))

        const queueResp = await fetch(`${API_BASE}/queue/list?${params.toString()}`)
        if (queueResp.ok) {
          const data = await queueResp.json()
          setQueueItems(data.queue_items || [])
          setTotalCount(data.total_count)
          setPendingCount(data.pending_count)
          setFailedCount(data.failed_count)
        }

        // Fetch fake count
        const fakeResp = await fetch(`${API_BASE}/fakes/list`)
        if (fakeResp.ok) {
          const data = await fakeResp.json()
          setFakeCount(data.total_count || 0)
        }
      } catch (err) {
        console.error('Auto-poll error:', err)
      }
    }

    autoPollTimerRef.current = setInterval(poll, 5000)

    return () => {
      if (autoPollTimerRef.current) {
        clearInterval(autoPollTimerRef.current)
        autoPollTimerRef.current = null
      }
    }
  }, [autoPollEnabled, queuePage, selectedStatuses])

  // Reset to page 0 when filters change
  useEffect(() => {
    setQueuePage(0)
  }, [selectedStatuses])

  const toggleStatus = (status: QueueStatusType) => {
    setSelectedStatuses((prev) =>
      prev.includes(status) ? prev.filter((s) => s !== status) : [...prev, status],
    )
  }

  const clearFilters = () => {
    setSelectedStatuses([])
  }

  const addToQueue = async () => {
    if (!manualPart.trim()) return
    setManualLoading(true)
    setManualError(null)
    try {
      const resp = await fetch(`${API_BASE}/queue/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          part_numbers: [manualPart.trim()],
          source: 'manual_entry',
          note: manualNote || undefined,
        }),
      })
      if (!resp.ok) throw new Error(`Add failed: ${resp.status}`)
      await fetchQueue(queuePage)
      setManualPart('')
      setManualNote('')
    } catch (err) {
      console.error(err)
      setManualError('Unable to add IC to queue.')
    } finally {
      setManualLoading(false)
    }
  }

  const removeFromQueue = async (partNumber: string) => {
    const ok = window.confirm(`Remove ${partNumber} from queue?`)
    if (!ok) return
    try {
      const resp = await fetch(`${API_BASE}/queue/${encodeURIComponent(partNumber)}/remove`, {
        method: 'DELETE',
      })
      if (!resp.ok) throw new Error(`Remove failed: ${resp.status}`)
      await fetchQueue(queuePage)
    } catch (err) {
      console.error(err)
      setQueueError('Failed to remove item.')
    }
  }

  const pollStatus = useCallback(async () => {
    try {
      const resp = await fetch(`${API_BASE}/sync/status`)
      if (!resp.ok) throw new Error('Status failed')
      const data: SyncStatus = await resp.json()
      setSyncMessage(data.message || '')
      setCurrentIC(data.current_item || '')
      setProgress(data.progress_percentage ?? 0)

      switch (data.status) {
        case 'IDLE':
          setSyncStage('idle')
          fetchQueue(queuePage)
          fetchFakeCount()
          return false
        case 'PROCESSING':
          setSyncStage('processing')
          return true
        case 'COMPLETED':
          setSyncStage('completed')
          fetchQueue(queuePage)
          fetchFakeCount()
          return false
        case 'ERROR':
          setSyncStage('error')
          return false
        case 'CANCELLED':
          setSyncStage('cancelled')
          fetchQueue(queuePage)
          fetchFakeCount()
          return false
        default:
          return false
      }
    } catch (err) {
      console.error(err)
      setSyncStage('error')
      return false
    }
  }, [queuePage, fetchQueue, fetchFakeCount])

  const stopPolling = useCallback(() => {
    if (pollTimer) {
      clearInterval(pollTimer)
      setPollTimer(null)
    }
  }, [pollTimer])

  const startPolling = useCallback(() => {
    stopPolling()
    const timer = setInterval(async () => {
      const keepGoing = await pollStatus()
      if (!keepGoing) stopPolling()
    }, 5000)
    setPollTimer(timer)
  }, [pollStatus, stopPolling])

  const handleStartSync = async () => {
    try {
      setSyncStage('processing')
      setProgress(0)
      setSyncMessage('')

      // Build request body with filters
      const requestBody: {
        max_items?: number
        retry_failed: boolean
        status_filter?: string[]
      } = {
        retry_failed: true,
      }

      // Add max_items if specified
      if (syncLimit.trim()) {
        const limit = parseInt(syncLimit.trim(), 10)
        if (!isNaN(limit) && limit > 0) {
          requestBody.max_items = limit
        }
      }

      // Add status filter if any selected
      if (selectedStatuses.length > 0) {
        requestBody.status_filter = selectedStatuses
      }

      const resp = await fetch(`${API_BASE}/sync/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      })
      if (!resp.ok) throw new Error(`Sync start failed: ${resp.status}`)
      startPolling()
    } catch (err) {
      console.error(err)
      setSyncStage('error')
    }
  }

  const handleCancelSync = async () => {
    try {
      const resp = await fetch(`${API_BASE}/sync/cancel`, { method: 'POST' })
      if (!resp.ok) throw new Error(`Cancel failed: ${resp.status}`)
      await pollStatus()
      stopPolling()
    } catch (err) {
      console.error(err)
      setSyncStage('error')
    }
  }

  useEffect(() => {
    return () => {
      stopPolling()
    }
  }, [stopPolling])

  const isSyncActive = useMemo(() => ['processing'].includes(syncStage), [syncStage])
  const totalPages = Math.ceil(totalCount / ITEMS_PER_PAGE)

  const CurrentStageIcon = stageConfig[syncStage].icon

  return (
    <div className="h-screen w-full overflow-hidden bg-slate-50/50 p-4 animate-in fade-in duration-500 flex flex-col">
      {/* Header */}
      <div className="shrink-0 mb-4">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <h1 className="text-2xl font-black tracking-tight text-slate-900">
              IC Data Management
            </h1>
            <p className="text-sm font-medium text-slate-500">
              Manage scraping queue and manually add components.
            </p>
          </div>
          <div className="h-10 w-10 flex items-center justify-center rounded-xl bg-white shadow-sm border border-slate-200">
            <Globe className="h-5 w-5 text-blue-600" />
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-hidden min-h-0">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3 h-full">
          {/* Left Column - Queue Table & Sync */}
          <div className="flex flex-col gap-4 lg:col-span-2 min-h-0 h-full min-w-0">
            {/* Sync Control */}
            <div className="shrink-0 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-base font-bold text-slate-900">Internet Sync & Scraping</h2>
                <div className="flex items-center gap-2">
                  {/* Auto-poll toggle */}
                  <button
                    onClick={() => setAutoPollEnabled(!autoPollEnabled)}
                    className={cn(
                      'flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider transition-all shadow-sm',
                      autoPollEnabled
                        ? 'border-blue-200 bg-blue-50 text-blue-700'
                        : 'border-slate-200 bg-white text-slate-500 hover:bg-slate-50 hover:text-slate-700',
                    )}
                  >
                    <RefreshCw className={cn('h-3 w-3', autoPollEnabled && 'animate-spin')} />
                    {autoPollEnabled ? 'Auto ON' : 'Auto-refresh'}
                  </button>
                  <div className="flex gap-1.5">
                    <Badge className="bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100 shadow-none px-2 py-0.5 text-[10px]">
                      {pendingCount} Pending
                    </Badge>
                    <Badge className="bg-red-50 text-red-700 border-red-200 hover:bg-red-100 shadow-none px-2 py-0.5 text-[10px]">{failedCount} Failed</Badge>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                {/* Transfer Fakes to Queue - Compact */}
                {fakeCount > 0 && (
                  <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-slate-500" />
                      <span className="text-xs font-bold text-slate-700">
                        {fakeCount} items in Fake Registry
                      </span>
                    </div>
                    <Button
                      onClick={transferFakesToQueue}
                      disabled={transferLoading || syncStage === 'processing'}
                      variant="outline"
                      size="sm"
                      className="h-7 border-slate-200 text-slate-600 hover:bg-slate-100 font-bold text-xs"
                    >
                      {transferLoading ? 'Transferring...' : 'Transfer to Queue'}
                    </Button>
                  </div>
                )}

                {/* Sync Options */}
                <div className="flex items-end gap-3">
                  {/* Limit Input */}
                  <div className="w-24">
                    <Label className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-slate-500">Max Items</Label>
                    <Input
                      type="number"
                      value={syncLimit}
                      onChange={(e) => setSyncLimit(e.target.value)}
                      placeholder="All"
                      min="1"
                      className="h-9 rounded-lg border-slate-200 text-xs focus:border-blue-500 focus:ring-blue-500/20 font-bold"
                    />
                  </div>

                  {/* Status Filter Pills */}
                  <div className="flex-1">
                    <Label className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-slate-500">
                      Filter by Status
                    </Label>
                    <div className="flex flex-wrap gap-1.5">
                      {STATUS_OPTIONS.map((option) => (
                        <button
                          key={option.value}
                          onClick={() => toggleStatus(option.value)}
                          className={cn(
                            'rounded-md border px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider transition-all shadow-sm',
                            selectedStatuses.includes(option.value)
                              ? 'bg-blue-50 border-blue-200 text-blue-700'
                              : 'border-slate-200 bg-white text-slate-500 hover:bg-slate-50 hover:text-slate-900',
                          )}
                        >
                          {option.label}
                        </button>
                      ))}
                      {selectedStatuses.length > 0 && (
                        <button
                          onClick={clearFilters}
                          className="rounded-md px-2 py-1 text-[10px] font-bold text-red-600 hover:bg-red-50 transition-colors uppercase tracking-wider"
                        >
                          Clear
                        </button>
                      )}
                    </div>
                  </div>

                  <Button
                    onClick={handleStartSync}
                    disabled={syncStage === 'processing' || (pendingCount === 0 && failedCount === 0)}
                    className="h-9 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg shadow-sm text-xs px-4"
                  >
                    <Globe className="mr-2 h-3.5 w-3.5" />
                    {selectedStatuses.length > 0
                      ? `Sync Selected`
                      : 'Start Sync'}
                  </Button>
                </div>

                {isSyncActive && (
                  <Button
                    variant="outline"
                    onClick={handleCancelSync}
                    className="h-9 w-full border-slate-200 text-slate-600 hover:bg-red-50 hover:text-red-700 hover:border-red-200 font-bold rounded-lg text-xs"
                  >
                    Cancel Sync
                  </Button>
                )}

                {/* Sync Progress */}
                {syncStage !== 'idle' && (
                  <div className="space-y-3 pt-1">
                    {/* Progress Bar */}
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                      <div
                        className="h-full bg-blue-600 transition-all duration-500 rounded-full"
                        style={{ width: `${progress}%` }}
                      />
                    </div>

                    {/* Current Status */}
                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className={cn("h-6 w-6 rounded-md flex items-center justify-center",
                          syncStage === 'completed' ? 'bg-emerald-100 text-emerald-600' :
                            syncStage === 'error' ? 'bg-red-100 text-red-600' : 'bg-blue-100 text-blue-600'
                        )}>
                          <CurrentStageIcon className="h-3.5 w-3.5" />
                        </div>
                        <div>
                          <p className="text-xs font-bold text-slate-900">{stageConfig[syncStage].label}</p>
                          {currentIC && (
                            <p className="text-[10px] font-medium text-slate-500">Processing: {currentIC}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Queue Table */}
            <div className="flex-1 flex flex-col rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden min-h-0">
              <div className="flex shrink-0 items-center justify-between border-b border-slate-100 bg-white px-4 py-3">
                <h2 className="text-base font-bold text-slate-900">Scraping Queue</h2>
                {selectedStatuses.length > 0 && (
                  <div className="flex items-center gap-2 rounded-full bg-slate-50 px-2.5 py-1">
                    <Filter className="h-3 w-3 text-slate-400" />
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                      Filtered
                    </span>
                  </div>
                )}
              </div>

              {queueError && (
                <div className="m-3 rounded-lg border border-red-200 bg-red-50 p-3 text-xs font-medium text-red-800">
                  {queueError}
                </div>
              )}

              {queueLoading ? (
                <div className="flex-1 flex items-center justify-center p-8">
                  <div className="flex flex-col items-center gap-3">
                    <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-200 border-t-blue-600"></div>
                    <p className="text-xs font-medium text-slate-500">Loading...</p>
                  </div>
                </div>
              ) : queueItems.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-50 mb-3">
                    <Clock className="h-6 w-6 text-slate-300" />
                  </div>
                  <p className="text-sm font-bold text-slate-900">Queue is empty</p>
                  <p className="mt-1 text-xs text-slate-500">
                    Add parts manually or via scan
                  </p>
                </div>
              ) : (
                <div className="flex-1 flex flex-col min-h-0">
                  <div className="overflow-auto custom-scrollbar">
                    <table className="w-full text-left">
                      <thead className="bg-slate-50/80 backdrop-blur sticky top-0 z-10">
                        <tr>
                          <th className="px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200">
                            Part
                          </th>
                          <th className="px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200">
                            Date
                          </th>
                          <th className="px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200">Status</th>
                          <th className="px-4 py-2.5 text-[10px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200 text-center">Retries</th>
                          <th className="px-4 py-2.5 text-right text-[10px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-50">
                        {queueItems.map((item) => (
                          <tr
                            key={item.part_number}
                            className="bg-white hover:bg-slate-50 transition-colors group"
                          >
                            <td className="px-4 py-2.5">
                              <span className="font-bold text-sm text-slate-900 font-mono">{item.part_number}</span>
                            </td>
                            <td className="px-4 py-2.5 text-[10px] font-medium text-slate-500">
                              {item.first_seen_at
                                ? new Date(item.first_seen_at).toLocaleDateString()
                                : '—'}
                            </td>
                            <td className="px-4 py-2.5">
                              <Badge
                                className={cn(
                                  'border font-bold shadow-none px-2 py-0 text-[10px]',
                                  item.status === 'PENDING' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                                    item.status === 'PROCESSING' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                                      item.status === 'FAILED' ? 'bg-red-50 text-red-700 border-red-200' :
                                        'bg-slate-100 text-slate-700 border-slate-200'
                                )}
                              >
                                {item.status || 'Pending'}
                              </Badge>
                            </td>
                            <td className="px-4 py-2.5 text-xs font-bold text-slate-400 text-center">
                              {item.retry_count || 0}
                            </td>
                            <td className="px-4 py-2.5 text-right">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => removeFromQueue(item.part_number)}
                                className="h-6 w-6 p-0 text-slate-300 hover:text-red-600 hover:bg-red-50 rounded-full"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination Footer */}
                  <div className="flex shrink-0 items-center justify-between border-t border-slate-100 bg-white px-4 py-2 mt-auto">
                    <button
                      onClick={() => setQueuePage((p) => Math.max(0, p - 1))}
                      disabled={queuePage === 0}
                      className="flex items-center gap-1 rounded-lg px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-900 disabled:opacity-30"
                    >
                      <ChevronLeft size={12} />
                      Prev
                    </button>

                    <span className="text-[10px] font-bold text-slate-400">
                      Page {queuePage + 1}
                    </span>

                    <button
                      onClick={() => setQueuePage((p) => p + 1)}
                      disabled={queuePage >= totalPages - 1}
                      className="flex items-center gap-1 rounded-lg px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-900 disabled:opacity-30"
                    >
                      Next
                      <ChevronRight size={12} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right Column - Forms */}
          <div className="flex flex-col gap-4 lg:h-full min-w-0">
            {/* Manual IC Entry Form */}
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm h-full flex flex-col">
              <div className="mb-4 flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 text-blue-600 border border-blue-100">
                  <Plus className="h-4 w-4" />
                </div>
                <h2 className="text-base font-bold text-slate-900">Add Manually</h2>
              </div>

              <div className="rounded-lg bg-slate-50 border border-slate-100 p-3 mb-4">
                <p className="text-xs font-medium text-slate-500 leading-relaxed text-justify break-words">
                  Manually queue a part number. The system will attempt to fetch datasheets and details from online sources.
                </p>
              </div>

              <div className="space-y-4 flex-1">
                <div>
                  <Label className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-slate-500">Part Number *</Label>
                  <Input
                    value={manualPart}
                    onChange={(e) => setManualPart(e.target.value)}
                    placeholder="e.g., LM555"
                    className="h-10 rounded-lg border-slate-200 text-sm font-bold focus:border-blue-500 focus:ring-blue-500/20"
                  />
                </div>

                <div className="flex-1">
                  <Label className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-slate-500">Note (optional)</Label>
                  <Textarea
                    value={manualNote}
                    onChange={(e) => setManualNote(e.target.value)}
                    placeholder="Context for adding"
                    className="rounded-lg border-slate-200 resize-none focus:border-blue-500 focus:ring-blue-500/20 h-[100px] text-xs"
                  />
                </div>

                {manualError && (
                  <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-xs font-medium text-red-700">
                    {manualError}
                  </div>
                )}

                <div className="mt-auto">
                  <Button
                    onClick={addToQueue}
                    className="h-10 w-full bg-blue-600 font-bold text-white rounded-xl shadow-sm hover:bg-blue-700 transition-all text-xs"
                    disabled={!manualPart.trim() || manualLoading}
                  >
                    {manualLoading ? 'Adding...' : 'Add to Queue'}
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
