import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
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
  X,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { API_BASE } from '@/lib/config';

type SyncStage = 'idle' | 'processing' | 'completed' | 'error' | 'cancelled';
type QueueStatusType = 'PENDING' | 'PROCESSING' | 'FAILED';

const STATUS_OPTIONS: { value: QueueStatusType; label: string; color: string }[] = [
  { value: 'PENDING', label: 'Pending', color: 'bg-amber-100 text-amber-700 border-amber-300' },
  { value: 'PROCESSING', label: 'Processing', color: 'bg-blue-100 text-blue-700 border-blue-300' },
  { value: 'FAILED', label: 'Failed', color: 'bg-red-100 text-red-700 border-red-300' },
];

interface QueueItem {
  part_number: string;
  first_seen_at?: string;
  last_scanned_at?: string;
  scan_count?: number;
  status?: string;
  retry_count?: number;
  error_message?: string;
}

interface QueueListResult {
  queue_items: QueueItem[];
  total_count: number;
  pending_count: number;
  failed_count: number;
  limit: number;
  offset: number;
}

interface SyncStatus {
  status: 'IDLE' | 'PROCESSING' | 'COMPLETED' | 'ERROR' | 'CANCELLED'
  progress_percentage?: number
  current_item?: string | null
  message?: string | null
}

export default function ScrapingPage() {
  const [queueItems, setQueueItems] = useState<QueueItem[]>([]);
  const [queueLoading, setQueueLoading] = useState(false);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [queuePage, setQueuePage] = useState(0);
  const [totalCount, setTotalCount] = useState(0);
  const [pendingCount, setPendingCount] = useState(0);
  const [failedCount, setFailedCount] = useState(0);

  // Fake registry count
  const [fakeCount, setFakeCount] = useState(0);
  const [transferLoading, setTransferLoading] = useState(false);
  const [transferMessage, setTransferMessage] = useState<string | null>(null);

  // Status filter (multi-select)
  const [selectedStatuses, setSelectedStatuses] = useState<QueueStatusType[]>([]);
  const [syncLimit, setSyncLimit] = useState<string>('');

  const [syncStage, setSyncStage] = useState<SyncStage>('idle');
  const [currentIC, setCurrentIC] = useState('');
  const [progress, setProgress] = useState(0);
  const [syncMessage, setSyncMessage] = useState('');
  const [pollTimer, setPollTimer] = useState<ReturnType<typeof setInterval> | null>(null);
  
  // Auto-poll toggle
  const [autoPollEnabled, setAutoPollEnabled] = useState(false);
  const autoPollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  
  // Form states
  const [manualPart, setManualPart] = useState('');
  const [manualNote, setManualNote] = useState('');
  const [manualLoading, setManualLoading] = useState(false);
  const [manualError, setManualError] = useState<string | null>(null);

  const ITEMS_PER_PAGE = 8;

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

  const fetchQueue = useCallback(async (page: number = 0) => {
    setQueueLoading(true);
    setQueueError(null);
    try {
      const params = new URLSearchParams();
      params.append('limit', ITEMS_PER_PAGE.toString());
      params.append('offset', (page * ITEMS_PER_PAGE).toString());
      
      // Add status filters
      selectedStatuses.forEach(status => {
        params.append('status', status);
      });

      const resp = await fetch(`${API_BASE}/queue/list?${params.toString()}`);
      if (!resp.ok) throw new Error(`Queue list failed: ${resp.status}`);
      const data: QueueListResult = await resp.json();
      setQueueItems(data.queue_items || []);
      setTotalCount(data.total_count);
      setPendingCount(data.pending_count);
      setFailedCount(data.failed_count);
    } catch (err) {
      console.error(err)
      setQueueError('Failed to load queue. Please try again.')
    } finally {
      setQueueLoading(false)
    }
  }, [selectedStatuses]);

  // Fetch fake registry count
  const fetchFakeCount = useCallback(async () => {
    try {
      const resp = await fetch(`${API_BASE}/fakes/list`);
      if (!resp.ok) throw new Error('Failed to fetch fakes');
      const data = await resp.json();
      setFakeCount(data.total_count || 0);
    } catch (err) {
      console.error('Failed to fetch fake count:', err);
    }
  }, []);

  // Transfer fakes to queue
  const transferFakesToQueue = async () => {
    if (fakeCount === 0) return;
    
    const confirmed = window.confirm(
      `Transfer ${fakeCount} items from Fake Registry to Queue?\n\nThis will move all fake ICs to the scraping queue for retry.`
    );
    if (!confirmed) return;

    setTransferLoading(true);
    setTransferMessage(null);
    try {
      const resp = await fetch(`${API_BASE}/fakes/transfer-to-queue`, { method: 'POST' });
      if (!resp.ok) throw new Error('Transfer failed');
      const data = await resp.json();
      setTransferMessage(data.message);
      // Refresh both counts
      await Promise.all([fetchQueue(queuePage), fetchFakeCount()]);
    } catch (err) {
      console.error('Transfer failed:', err);
      setTransferMessage('Failed to transfer items. Please try again.');
    } finally {
      setTransferLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue(queuePage);
    fetchFakeCount();
  }, [fetchQueue, fetchFakeCount, queuePage]);

  // Auto-poll effect - refresh queue every 5 seconds when enabled
  useEffect(() => {
    // Clear existing timer
    if (autoPollTimerRef.current) {
      clearInterval(autoPollTimerRef.current);
      autoPollTimerRef.current = null;
    }
    
    if (!autoPollEnabled) {
      return; // Don't start timer if disabled
    }
    
    // Start new timer - capture current page in closure
    const currentPage = queuePage;
    const currentStatuses = selectedStatuses;
    
    const poll = async () => {
      try {
        // Fetch queue
        const params = new URLSearchParams();
        params.append('limit', ITEMS_PER_PAGE.toString());
        params.append('offset', (currentPage * ITEMS_PER_PAGE).toString());
        currentStatuses.forEach(status => params.append('status', status));
        
        const queueResp = await fetch(`${API_BASE}/queue/list?${params.toString()}`);
        if (queueResp.ok) {
          const data = await queueResp.json();
          setQueueItems(data.queue_items || []);
          setTotalCount(data.total_count);
          setPendingCount(data.pending_count);
          setFailedCount(data.failed_count);
        }
        
        // Fetch fake count
        const fakeResp = await fetch(`${API_BASE}/fakes/list`);
        if (fakeResp.ok) {
          const data = await fakeResp.json();
          setFakeCount(data.total_count || 0);
        }
      } catch (err) {
        console.error('Auto-poll error:', err);
      }
    };
    
    autoPollTimerRef.current = setInterval(poll, 5000);
    
    return () => {
      if (autoPollTimerRef.current) {
        clearInterval(autoPollTimerRef.current);
        autoPollTimerRef.current = null;
      }
    };
  }, [autoPollEnabled, queuePage, selectedStatuses]);

  // Reset to page 0 when filters change
  useEffect(() => {
    setQueuePage(0);
  }, [selectedStatuses]);

  const toggleStatus = (status: QueueStatusType) => {
    setSelectedStatuses(prev => 
      prev.includes(status) 
        ? prev.filter(s => s !== status)
        : [...prev, status]
    );
  };

  const clearFilters = () => {
    setSelectedStatuses([]);
  };

  const addToQueue = async () => {
    if (!manualPart.trim()) return
    setManualLoading(true)
    setManualError(null)
    try {
      const resp = await fetch(`${API_BASE}/queue/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ part_numbers: [manualPart.trim()], source: 'manual_entry', note: manualNote || undefined }),
      });
      if (!resp.ok) throw new Error(`Add failed: ${resp.status}`);
      await fetchQueue(queuePage);
      setManualPart('');
      setManualNote('');
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
      const resp = await fetch(`${API_BASE}/queue/${encodeURIComponent(partNumber)}/remove`, { method: 'DELETE' });
      if (!resp.ok) throw new Error(`Remove failed: ${resp.status}`);
      await fetchQueue(queuePage);
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
          setSyncStage('idle');
          fetchQueue(queuePage);
          fetchFakeCount();
          return false;
        case 'PROCESSING':
          setSyncStage('processing')
          return true
        case 'COMPLETED':
          setSyncStage('completed');
          fetchQueue(queuePage);
          fetchFakeCount();
          return false;
        case 'ERROR':
          setSyncStage('error')
          return false
        case 'CANCELLED':
          setSyncStage('cancelled');
          fetchQueue(queuePage);
          fetchFakeCount();
          return false;
        default:
          return false
      }
    } catch (err) {
      console.error(err)
      setSyncStage('error')
      return false
    }
  }, [queuePage, fetchQueue, fetchFakeCount]);

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
      setSyncStage('processing');
      setProgress(0);
      setSyncMessage('');
      
      // Build request body with filters
      const requestBody: {
        max_items?: number;
        retry_failed: boolean;
        status_filter?: string[];
      } = {
        retry_failed: true,
      };
      
      // Add max_items if specified
      if (syncLimit.trim()) {
        const limit = parseInt(syncLimit.trim(), 10);
        if (!isNaN(limit) && limit > 0) {
          requestBody.max_items = limit;
        }
      }
      
      // Add status filter if any selected
      if (selectedStatuses.length > 0) {
        requestBody.status_filter = selectedStatuses;
      }

      const resp = await fetch(`${API_BASE}/sync/start`, { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      });
      if (!resp.ok) throw new Error(`Sync start failed: ${resp.status}`);
      startPolling();
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

  const isSyncActive = useMemo(() => ['processing'].includes(syncStage), [syncStage]);
  const totalPages = Math.ceil(totalCount / ITEMS_PER_PAGE);

  const getStatusBadgeColor = (status: string) => {
    const option = STATUS_OPTIONS.find(o => o.value === status);
    return option?.color || 'bg-gray-100 text-gray-700 border-gray-300';
  };

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
            <div className="bg-white rounded-2xl shadow-xl border-2 border-blue-300 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-slate-900">Internet Sync & Scraping</h2>
                <div className="flex items-center gap-3">
                  {/* Auto-poll toggle */}
                  <button
                    onClick={() => setAutoPollEnabled(!autoPollEnabled)}
                    className={cn(
                      'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all',
                      autoPollEnabled
                        ? 'bg-green-100 text-green-700 border-green-300 ring-2 ring-green-400 ring-offset-1'
                        : 'bg-gray-100 text-gray-500 border-gray-200 hover:bg-gray-200'
                    )}
                  >
                    <RefreshCw className={cn('w-3 h-3', autoPollEnabled && 'animate-spin')} />
                    {autoPollEnabled ? 'Auto-refresh ON' : 'Auto-refresh'}
                  </button>
                  <Badge className="bg-amber-500 text-white font-bold">
                    {pendingCount} Pending
                  </Badge>
                  <Badge className="bg-red-500 text-white font-bold">
                    {failedCount} Failed
                  </Badge>
                  <Badge className="bg-purple-500 text-white font-bold">
                    {fakeCount} Fake
                  </Badge>
                </div>
              </div>

              <div className="space-y-4">
                <p className="text-sm text-slate-600 font-medium">
                  Connect to the internet to scrape IC datasheets and update the database automatically.
                </p>

                {/* Transfer Fakes to Queue */}
                {fakeCount > 0 && (
                  <div className="p-3 rounded-xl border-2 border-purple-200 bg-purple-50">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="w-5 h-5 text-purple-600" />
                        <div>
                          <p className="text-sm font-semibold text-purple-900">
                            {fakeCount} ICs in Fake Registry
                          </p>
                          <p className="text-xs text-purple-600">
                            Transfer to queue to retry scraping
                          </p>
                        </div>
                      </div>
                      <Button
                        onClick={transferFakesToQueue}
                        disabled={transferLoading || syncStage === 'processing'}
                        variant="outline"
                        size="sm"
                        className="border-purple-400 text-purple-700 hover:bg-purple-100"
                      >
                        {transferLoading ? (
                          <>
                            <RefreshCw className="w-4 h-4 mr-1 animate-spin" />
                            Transferring...
                          </>
                        ) : (
                          <>
                            <RefreshCw className="w-4 h-4 mr-1" />
                            Transfer to Queue
                          </>
                        )}
                      </Button>
                    </div>
                    {transferMessage && (
                      <p className="text-xs text-purple-700 mt-2 font-medium">{transferMessage}</p>
                    )}
                  </div>
                )}

                {/* Sync Options */}
                <div className="flex flex-wrap gap-3 items-end">
                  {/* Limit Input */}
                  <div className="w-32">
                    <Label className="text-xs font-semibold text-slate-600 mb-1">Max Items</Label>
                    <Input
                      type="number"
                      value={syncLimit}
                      onChange={(e) => setSyncLimit(e.target.value)}
                      placeholder="All"
                      min="1"
                      className="h-9 text-sm"
                    />
                  </div>

                  {/* Status Filter Pills */}
                  <div className="flex-1">
                    <Label className="text-xs font-semibold text-slate-600 mb-1">Filter by Status</Label>
                    <div className="flex flex-wrap gap-2">
                      {STATUS_OPTIONS.map(option => (
                        <button
                          key={option.value}
                          onClick={() => toggleStatus(option.value)}
                          className={cn(
                            'px-3 py-1.5 rounded-full text-xs font-semibold border transition-all',
                            selectedStatuses.includes(option.value)
                              ? option.color + ' ring-2 ring-offset-1 ring-blue-400'
                              : 'bg-gray-100 text-gray-500 border-gray-200 hover:bg-gray-200'
                          )}
                        >
                          {option.label}
                        </button>
                      ))}
                      {selectedStatuses.length > 0 && (
                        <button
                          onClick={clearFilters}
                          className="px-2 py-1.5 rounded-full text-xs font-semibold text-red-600 hover:bg-red-50"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                <Button
                  onClick={handleStartSync}
                  disabled={syncStage === 'processing' || (pendingCount === 0 && failedCount === 0)}
                  className="w-full h-14 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white font-bold text-base shadow-xl"
                >
                  <Globe className="w-5 h-5 mr-2" />
                  {selectedStatuses.length > 0 
                    ? `Sync ${selectedStatuses.join(' & ')} Items`
                    : 'Start Sync & Scrape Queue'
                  }
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
            <div className="bg-white rounded-2xl shadow-xl border-2 border-blue-300 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-slate-900">Scraping Queue</h2>
                {selectedStatuses.length > 0 && (
                  <div className="flex items-center gap-2">
                    <Filter className="w-4 h-4 text-blue-600" />
                    <span className="text-sm text-blue-600 font-medium">
                      Filtering: {selectedStatuses.join(', ')}
                    </span>
                  </div>
                )}
              </div>
              
              {queueError && (
                <div className="mb-3 rounded-lg border-2 border-red-300 bg-red-50 p-3 text-sm text-red-700">
                  {queueError}
                </div>
              )}

              {queueLoading ? (
                <div className="py-8 text-center text-slate-500">Loading queue...</div>
              ) : queueItems.length === 0 ? (
                <div className="text-center py-12">
                  <Clock className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                  <p className="text-slate-500 font-medium">
                    {selectedStatuses.length > 0 ? 'No items match the filter' : 'Queue is empty'}
                  </p>
                  <p className="text-sm text-slate-400 mt-1">
                    {selectedStatuses.length > 0 
                      ? 'Try adjusting your status filter'
                      : 'ICs will be added here when scanned but not found in database'
                    }
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-sm text-slate-600">
                    <span>
                      Showing {queuePage * ITEMS_PER_PAGE + 1}-{Math.min(totalCount, (queuePage + 1) * ITEMS_PER_PAGE)} of {totalCount}
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
                      <span className="text-xs text-slate-500">
                        Page {queuePage + 1} of {totalPages || 1}
                      </span>
                      <Button
                        variant="outline"
                        size="icon"
                        disabled={queuePage >= totalPages - 1}
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
                          <th className="text-left py-3 px-4 font-bold text-slate-700">Part Number</th>
                          <th className="text-left py-3 px-4 font-bold text-slate-700">Added Date</th>
                          <th className="text-left py-3 px-4 font-bold text-slate-700">Status</th>
                          <th className="text-left py-3 px-4 font-bold text-slate-700">Retries</th>
                          <th className="text-right py-3 px-4 font-bold text-slate-700">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {queueItems.map((item) => (
                          <tr key={item.part_number} className="border-b border-slate-200 hover:bg-blue-50 transition-colors">
                            <td className="py-3 px-4 font-mono font-bold text-blue-600">{item.part_number}</td>
                            <td className="py-3 px-4 text-slate-600 text-sm">
                              {item.first_seen_at ? new Date(item.first_seen_at).toLocaleString() : '—'}
                            </td>
                            <td className="py-3 px-4">
                              <Badge className={cn('font-semibold border', getStatusBadgeColor(item.status || 'PENDING'))}>
                                {item.status === 'PROCESSING' && <Download className="w-3 h-3 mr-1 animate-pulse" />}
                                {item.status === 'FAILED' && <XCircle className="w-3 h-3 mr-1" />}
                                {item.status === 'PENDING' && <Clock className="w-3 h-3 mr-1" />}
                                {item.status || 'Pending'}
                              </Badge>
                            </td>
                            <td className="py-3 px-4 text-slate-600 text-sm">
                              {item.retry_count || 0}
                            </td>
                            <td className="py-3 px-4 text-right">
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
