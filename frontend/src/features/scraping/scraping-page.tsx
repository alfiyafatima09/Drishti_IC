import { useState, useEffect, useCallback, useMemo } from 'react';
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
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { API_BASE } from '@/lib/config';

type SyncStage = 'idle' | 'processing' | 'completed' | 'error' | 'cancelled';

interface QueueItem {
  part_number: string;
  first_seen_at?: string;
  last_scanned_at?: string;
  scan_count?: number;
  status?: string;
}

interface SyncStatus {
  status: 'IDLE' | 'PROCESSING' | 'COMPLETED' | 'ERROR' | 'CANCELLED';
  progress_percentage?: number;
  current_item?: string | null;
  message?: string | null;
}

export default function ScrapingPage() {
  const [queueItems, setQueueItems] = useState<QueueItem[]>([]);
  const [queueLoading, setQueueLoading] = useState(false);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [queuePage, setQueuePage] = useState(0);

  const [syncStage, setSyncStage] = useState<SyncStage>('idle');
  const [currentIC, setCurrentIC] = useState('');
  const [progress, setProgress] = useState(0);
  const [syncMessage, setSyncMessage] = useState('');
  const [pollTimer, setPollTimer] = useState<ReturnType<typeof setInterval> | null>(null);
  
  // Form states
  const [manualPart, setManualPart] = useState('');
  const [manualNote, setManualNote] = useState('');
  const [manualLoading, setManualLoading] = useState(false);
  const [manualError, setManualError] = useState<string | null>(null);

  const stageConfig: Record<SyncStage, { label: string; color: string; icon: typeof Globe }> = {
    idle: { label: 'Ready to Sync', color: 'border-slate-300 bg-slate-50', icon: Globe },
    processing: { label: 'Scraping & Downloading', color: 'border-blue-400 bg-blue-50 animate-pulse', icon: Download },
    completed: { label: 'Sync Completed', color: 'border-emerald-400 bg-emerald-50', icon: CheckCircle2 },
    error: { label: 'Sync Failed', color: 'border-red-400 bg-red-50', icon: XCircle },
    cancelled: { label: 'Sync Cancelled', color: 'border-amber-400 bg-amber-50', icon: AlertCircle },
  };

  const fetchQueue = useCallback(async () => {
    setQueueLoading(true);
    setQueueError(null);
    try {
      const resp = await fetch(`${API_BASE}/queue/list`);
      if (!resp.ok) throw new Error(`Queue list failed: ${resp.status}`);
      const data = await resp.json();
      setQueueItems(data.queue_items || []);
    } catch (err) {
      console.error(err);
      setQueueError('Failed to load queue. Please try again.');
    } finally {
      setQueueLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  useEffect(() => {
    const maxPage = Math.max(0, Math.ceil(queueItems.length / 8) - 1);
    if (queuePage > maxPage) {
      setQueuePage(maxPage);
    }
  }, [queueItems, queuePage]);

  const addToQueue = async () => {
    if (!manualPart.trim()) return;
    setManualLoading(true);
    setManualError(null);
    try {
      const resp = await fetch(`${API_BASE}/queue/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ part_numbers: [manualPart.trim()], source: 'manual_entry', note: manualNote || undefined }),
      });
      if (!resp.ok) throw new Error(`Add failed: ${resp.status}`);
      await fetchQueue();
      setManualPart('');
      setManualNote('');
    } catch (err) {
      console.error(err);
      setManualError('Unable to add IC to queue.');
    } finally {
      setManualLoading(false);
    }
  };

  const removeFromQueue = async (partNumber: string) => {
    const ok = window.confirm(`Remove ${partNumber} from queue?`);
    if (!ok) return;
    try {
      const resp = await fetch(`${API_BASE}/queue/${encodeURIComponent(partNumber)}/remove`, { method: 'DELETE' });
      if (!resp.ok) throw new Error(`Remove failed: ${resp.status}`);
      setQueueItems(items => items.filter(i => i.part_number !== partNumber));
    } catch (err) {
      console.error(err);
      setQueueError('Failed to remove item.');
    }
  };

  const pollStatus = useCallback(async () => {
    try {
      const resp = await fetch(`${API_BASE}/sync/status`);
      if (!resp.ok) throw new Error('Status failed');
      const data: SyncStatus = await resp.json();
      setSyncMessage(data.message || '');
      setCurrentIC(data.current_item || '');
      setProgress(data.progress_percentage ?? 0);

      switch (data.status) {
        case 'IDLE':
          setSyncStage('idle');
          return false;
        case 'PROCESSING':
          setSyncStage('processing');
          return true;
        case 'COMPLETED':
          setSyncStage('completed');
          return false;
        case 'ERROR':
          setSyncStage('error');
          return false;
        case 'CANCELLED':
          setSyncStage('cancelled');
          return false;
        default:
          return false;
      }
    } catch (err) {
      console.error(err);
      setSyncStage('error');
      return false;
    }
  }, []);

  const stopPolling = useCallback(() => {
    if (pollTimer) {
      clearInterval(pollTimer);
      setPollTimer(null);
    }
  }, [pollTimer]);

  const startPolling = useCallback(() => {
    stopPolling();
    const timer = setInterval(async () => {
      const keepGoing = await pollStatus();
      if (!keepGoing) stopPolling();
    }, 5000);
    setPollTimer(timer);
  }, [pollStatus, stopPolling]);

  const handleStartSync = async () => {
    try {
      setSyncStage('processing');
      setProgress(0);
      setSyncMessage('');
      const resp = await fetch(`${API_BASE}/sync/start`, { method: 'POST' });
      if (!resp.ok) throw new Error(`Sync start failed: ${resp.status}`);
      startPolling();
    } catch (err) {
      console.error(err);
      setSyncStage('error');
    }
  };

  const handleCancelSync = async () => {
    try {
      const resp = await fetch(`${API_BASE}/sync/cancel`, { method: 'POST' });
      if (!resp.ok) throw new Error(`Cancel failed: ${resp.status}`);
      await pollStatus();
      stopPolling();
    } catch (err) {
      console.error(err);
      setSyncStage('error');
    }
  };

  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  const isSyncActive = useMemo(() => ['processing'].includes(syncStage), [syncStage]);

  return (
    <div className="flex flex-col h-full gap-6 p-6 overflow-hidden bg-gradient-to-br from-blue-50 via-cyan-50 to-blue-100">
      {/* Header */}
      <div className="shrink-0">
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 shadow-lg border-2 border-blue-200">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-black bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent mb-2">
                IC Data Management
              </h1>
              <p className="text-base font-semibold text-slate-700">
                Scrape datasheets, manage queue, and add ICs. This page extracts IC info from the internet via web scraping and parsing.
              </p>
            </div>
            <Globe className="w-12 h-12 text-cyan-600" />
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Queue Table & Sync */}
          <div className="lg:col-span-2 space-y-6">
            {/* Sync Control */}
            <div className="bg-white rounded-2xl shadow-xl border-2 border-blue-300 p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-slate-900">Internet Sync & Scraping</h2>
                <Badge className="bg-blue-500 text-white font-bold">
                  {queueItems.length} in Queue
                </Badge>
              </div>

              <div className="space-y-4">
                <p className="text-sm text-slate-600 font-medium">
                  Connect to the internet to scrape IC datasheets and update the database automatically.
                </p>

                <Button
                  onClick={handleStartSync}
                  disabled={syncStage === 'processing' || queueItems.length === 0}
                  className="w-full h-14 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white font-bold text-base shadow-xl"
                >
                  <Globe className="w-5 h-5 mr-2" />
                  Start Sync & Scrape Queue
                </Button>

                {isSyncActive && (
                  <Button
                    variant="outline"
                    onClick={handleCancelSync}
                    className="w-full h-12 border-red-300 text-red-600 hover:bg-red-50 font-semibold"
                  >
                    Cancel Sync
                  </Button>
                )}

                {/* Sync Progress */}
                {syncStage !== 'idle' && (
                  <div className="space-y-3">
                    {/* Progress Bar */}
                    <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-blue-600 to-cyan-600 transition-all duration-500"
                        style={{ width: `${progress}%` }}
                      />
                    </div>

                    {/* Current Status */}
                    <div className={cn('p-4 rounded-xl border-2', stageConfig[syncStage].color)}>
                      <p className="font-bold text-slate-900">{stageConfig[syncStage].label}</p>
                      {currentIC && <p className="text-sm text-slate-600 mt-1">Processing: {currentIC}</p>}
                      {syncMessage && <p className="text-sm text-slate-500 mt-1">{syncMessage}</p>}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Queue Table */}
            <div className="bg-white rounded-2xl shadow-xl border-2 border-blue-300 p-6">
              <h2 className="text-xl font-bold text-slate-900 mb-4">Scraping Queue</h2>
              {queueError && (
                <div className="mb-3 p-3 rounded-lg border-2 border-red-300 bg-red-50 text-sm text-red-700">
                  {queueError}
                </div>
              )}
              
              {queueLoading ? (
                <div className="py-8 text-center text-slate-500">Loading queue...</div>
              ) : queueItems.length === 0 ? (
                <div className="text-center py-12">
                  <Clock className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                  <p className="text-slate-500 font-medium">Queue is empty</p>
                  <p className="text-sm text-slate-400 mt-1">ICs will be added here when scanned but not found in database</p>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-sm text-slate-600">
                    <span>
                      Showing {queuePage * 8 + 1}-{Math.min(queueItems.length, (queuePage + 1) * 8)} of {queueItems.length}
                    </span>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="icon"
                        disabled={queuePage === 0}
                        onClick={() => setQueuePage((p) => Math.max(0, p - 1))}
                        className="h-9 w-9"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="icon"
                        disabled={(queuePage + 1) * 8 >= queueItems.length}
                        onClick={() => setQueuePage((p) => p + 1)}
                        className="h-9 w-9"
                      >
                        <ChevronRight className="w-4 h-4" />
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
                          <th className="text-right py-3 px-4 font-bold text-slate-700">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {queueItems.slice(queuePage * 8, (queuePage + 1) * 8).map((item) => (
                          <tr key={item.part_number} className="border-b border-slate-200 hover:bg-blue-50 transition-colors">
                            <td className="py-3 px-4 font-mono font-bold text-blue-600">{item.part_number}</td>
                            <td className="py-3 px-4 text-slate-600 text-sm">
                              {item.first_seen_at ? new Date(item.first_seen_at).toLocaleString() : '—'}
                            </td>
                            <td className="py-3 px-4">
                              <Badge className="bg-amber-100 text-amber-700 border border-amber-300 font-semibold">
                                <Clock className="w-3 h-3 mr-1" />
                                {item.status || 'Pending'}
                              </Badge>
                            </td>
                            <td className="py-3 px-4 text-right">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => removeFromQueue(item.part_number)}
                                className="border-red-300 text-red-600 hover:bg-red-50"
                              >
                                <Trash2 className="w-4 h-4 mr-1" />
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
            <div className="bg-white rounded-2xl shadow-xl border-2 border-emerald-300 p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-emerald-500 flex items-center justify-center">
                  <Plus className="w-5 h-5 text-white" />
                </div>
                <h2 className="text-lg font-bold text-slate-900">Add IC Manually</h2>
              </div>

              <p className="text-xs text-slate-500 mb-4 font-medium">
                If scraping fails, queue a part number to fetch online via sync.
              </p>

              <div className="space-y-3">
                <div>
                  <Label className="text-sm font-bold text-slate-700 mb-1">Part Number *</Label>
                  <Input
                    value={manualPart}
                    onChange={(e) => setManualPart(e.target.value)}
                    placeholder="e.g., LM555"
                    className="h-10 border-2 border-emerald-200 focus:border-emerald-400"
                  />
                </div>

                <div>
                  <Label className="text-sm font-bold text-slate-700 mb-1">Note (optional)</Label>
                  <Textarea
                    value={manualNote}
                    onChange={(e) => setManualNote(e.target.value)}
                    placeholder="Context for adding this IC"
                    rows={2}
                    className="border-2 border-emerald-200 focus:border-emerald-400"
                  />
                </div>

                {manualError && (
                  <div className="p-3 rounded-lg border-2 border-red-300 bg-red-50 text-sm text-red-700">
                    {manualError}
                  </div>
                )}

                <Button
                  onClick={addToQueue}
                  className="w-full h-12 bg-emerald-600 hover:bg-emerald-700 text-white font-bold shadow-lg"
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
  );
}


