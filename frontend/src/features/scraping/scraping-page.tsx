import { useState, useEffect, useCallback, useMemo } from 'react'
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
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { API_BASE } from '@/lib/config'

type SyncStage = 'idle' | 'processing' | 'completed' | 'error' | 'cancelled'

interface QueueItem {
  part_number: string
  first_seen_at?: string
  last_scanned_at?: string
  scan_count?: number
  status?: string
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

  const [syncStage, setSyncStage] = useState<SyncStage>('idle')
  const [currentIC, setCurrentIC] = useState('')
  const [progress, setProgress] = useState(0)
  const [syncMessage, setSyncMessage] = useState('')
  const [pollTimer, setPollTimer] = useState<ReturnType<typeof setInterval> | null>(null)

  // Form states
  const [manualPart, setManualPart] = useState('')
  const [manualNote, setManualNote] = useState('')
  const [manualLoading, setManualLoading] = useState(false)
  const [manualError, setManualError] = useState<string | null>(null)

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

  const fetchQueue = useCallback(async () => {
    setQueueLoading(true)
    setQueueError(null)
    try {
      const resp = await fetch(`${API_BASE}/queue/list`)
      if (!resp.ok) throw new Error(`Queue list failed: ${resp.status}`)
      const data = await resp.json()
      setQueueItems(data.queue_items || [])
    } catch (err) {
      console.error(err)
      setQueueError('Failed to load queue. Please try again.')
    } finally {
      setQueueLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchQueue()
  }, [fetchQueue])

  useEffect(() => {
    const maxPage = Math.max(0, Math.ceil(queueItems.length / 8) - 1)
    if (queuePage > maxPage) {
      setQueuePage(maxPage)
    }
  }, [queueItems, queuePage])

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
      await fetchQueue()
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
      setQueueItems((items) => items.filter((i) => i.part_number !== partNumber))
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
          return false
        case 'PROCESSING':
          setSyncStage('processing')
          return true
        case 'COMPLETED':
          setSyncStage('completed')
          return false
        case 'ERROR':
          setSyncStage('error')
          return false
        case 'CANCELLED':
          setSyncStage('cancelled')
          return false
        default:
          return false
      }
    } catch (err) {
      console.error(err)
      setSyncStage('error')
      return false
    }
  }, [])

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
      const resp = await fetch(`${API_BASE}/sync/start`, { method: 'POST' })
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

  return (
    <div className="flex h-full flex-col gap-6 overflow-hidden bg-gradient-to-br from-blue-50 via-cyan-50 to-blue-100 p-6">
      {/* Header */}
      <div className="shrink-0">
        <div className="rounded-2xl border-2 border-blue-200 bg-white/80 p-6 shadow-lg backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="mb-2 bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-3xl font-black text-transparent">
                IC Data Management
              </h1>
              <p className="text-base font-semibold text-slate-700">
                Scrape datasheets, manage queue, and add ICs. This page extracts IC info from the
                internet via web scraping and parsing.
              </p>
            </div>
            <Globe className="h-12 w-12 text-cyan-600" />
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Left Column - Queue Table & Sync */}
          <div className="space-y-6 lg:col-span-2">
            {/* Sync Control */}
            <div className="rounded-2xl border-2 border-blue-300 bg-white p-6 shadow-xl">
              <div className="mb-6 flex items-center justify-between">
                <h2 className="text-xl font-bold text-slate-900">Internet Sync & Scraping</h2>
                <Badge className="bg-blue-500 font-bold text-white">
                  {queueItems.length} in Queue
                </Badge>
              </div>

              <div className="space-y-4">
                <p className="text-sm font-medium text-slate-600">
                  Connect to the internet to scrape IC datasheets and update the database
                  automatically.
                </p>

                <Button
                  onClick={handleStartSync}
                  disabled={syncStage === 'processing' || queueItems.length === 0}
                  className="h-14 w-full bg-gradient-to-r from-blue-600 to-cyan-600 text-base font-bold text-white shadow-xl hover:from-blue-700 hover:to-cyan-700"
                >
                  <Globe className="mr-2 h-5 w-5" />
                  Start Sync & Scrape Queue
                </Button>

                {isSyncActive && (
                  <Button
                    variant="outline"
                    onClick={handleCancelSync}
                    className="h-12 w-full border-red-300 font-semibold text-red-600 hover:bg-red-50"
                  >
                    Cancel Sync
                  </Button>
                )}

                {/* Sync Progress */}
                {syncStage !== 'idle' && (
                  <div className="space-y-3">
                    {/* Progress Bar */}
                    <div className="h-3 w-full overflow-hidden rounded-full bg-slate-200">
                      <div
                        className="h-full bg-gradient-to-r from-blue-600 to-cyan-600 transition-all duration-500"
                        style={{ width: `${progress}%` }}
                      />
                    </div>

                    {/* Current Status */}
                    <div className={cn('rounded-xl border-2 p-4', stageConfig[syncStage].color)}>
                      <p className="font-bold text-slate-900">{stageConfig[syncStage].label}</p>
                      {currentIC && (
                        <p className="mt-1 text-sm text-slate-600">Processing: {currentIC}</p>
                      )}
                      {syncMessage && <p className="mt-1 text-sm text-slate-500">{syncMessage}</p>}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Queue Table */}
            <div className="rounded-2xl border-2 border-blue-300 bg-white p-6 shadow-xl">
              <h2 className="mb-4 text-xl font-bold text-slate-900">Scraping Queue</h2>
              {queueError && (
                <div className="mb-3 rounded-lg border-2 border-red-300 bg-red-50 p-3 text-sm text-red-700">
                  {queueError}
                </div>
              )}

              {queueLoading ? (
                <div className="py-8 text-center text-slate-500">Loading queue...</div>
              ) : queueItems.length === 0 ? (
                <div className="py-12 text-center">
                  <Clock className="mx-auto mb-4 h-16 w-16 text-slate-300" />
                  <p className="font-medium text-slate-500">Queue is empty</p>
                  <p className="mt-1 text-sm text-slate-400">
                    ICs will be added here when scanned but not found in database
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-sm text-slate-600">
                    <span>
                      Showing {queuePage * 8 + 1}-{Math.min(queueItems.length, (queuePage + 1) * 8)}{' '}
                      of {queueItems.length}
                    </span>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="icon"
                        disabled={queuePage === 0}
                        onClick={() => setQueuePage((p) => Math.max(0, p - 1))}
                        className="h-9 w-9"
                      >
                        <ChevronLeft className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="icon"
                        disabled={(queuePage + 1) * 8 >= queueItems.length}
                        onClick={() => setQueuePage((p) => p + 1)}
                        className="h-9 w-9"
                      >
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b-2 border-blue-200">
                          <th className="px-4 py-3 text-left font-bold text-slate-700">
                            Part Number
                          </th>
                          <th className="px-4 py-3 text-left font-bold text-slate-700">
                            Added Date
                          </th>
                          <th className="px-4 py-3 text-left font-bold text-slate-700">Status</th>
                          <th className="px-4 py-3 text-right font-bold text-slate-700">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {queueItems.slice(queuePage * 8, (queuePage + 1) * 8).map((item) => (
                          <tr
                            key={item.part_number}
                            className="border-b border-slate-200 transition-colors hover:bg-blue-50"
                          >
                            <td className="px-4 py-3 font-mono font-bold text-blue-600">
                              {item.part_number}
                            </td>
                            <td className="px-4 py-3 text-sm text-slate-600">
                              {item.first_seen_at
                                ? new Date(item.first_seen_at).toLocaleString()
                                : '—'}
                            </td>
                            <td className="px-4 py-3">
                              <Badge className="border border-amber-300 bg-amber-100 font-semibold text-amber-700">
                                <Clock className="mr-1 h-3 w-3" />
                                {item.status || 'Pending'}
                              </Badge>
                            </td>
                            <td className="px-4 py-3 text-right">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => removeFromQueue(item.part_number)}
                                className="border-red-300 text-red-600 hover:bg-red-50"
                              >
                                <Trash2 className="mr-1 h-4 w-4" />
                                Remove
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right Column - Forms */}
          <div className="space-y-6">
            {/* Manual IC Entry Form */}
            <div className="rounded-2xl border-2 border-emerald-300 bg-white p-6 shadow-xl">
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500">
                  <Plus className="h-5 w-5 text-white" />
                </div>
                <h2 className="text-lg font-bold text-slate-900">Add IC Manually</h2>
              </div>

              <p className="mb-4 text-xs font-medium text-slate-500">
                If scraping fails, queue a part number to fetch online via sync.
              </p>

              <div className="space-y-3">
                <div>
                  <Label className="mb-1 text-sm font-bold text-slate-700">Part Number *</Label>
                  <Input
                    value={manualPart}
                    onChange={(e) => setManualPart(e.target.value)}
                    placeholder="e.g., LM555"
                    className="h-10 border-2 border-emerald-200 focus:border-emerald-400"
                  />
                </div>

                <div>
                  <Label className="mb-1 text-sm font-bold text-slate-700">Note (optional)</Label>
                  <Textarea
                    value={manualNote}
                    onChange={(e) => setManualNote(e.target.value)}
                    placeholder="Context for adding this IC"
                    rows={2}
                    className="border-2 border-emerald-200 focus:border-emerald-400"
                  />
                </div>

                {manualError && (
                  <div className="rounded-lg border-2 border-red-300 bg-red-50 p-3 text-sm text-red-700">
                    {manualError}
                  </div>
                )}

                <Button
                  onClick={addToQueue}
                  className="h-12 w-full bg-emerald-600 font-bold text-white shadow-lg hover:bg-emerald-700"
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
  )
}
