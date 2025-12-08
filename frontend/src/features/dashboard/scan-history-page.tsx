import { useEffect, useState, useRef } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  ShieldAlert,
  Search,
  RefreshCw,
} from 'lucide-react'
import { format } from 'date-fns'
import { API_BASE, getWsUrl } from '@/lib/config'
import { cn } from '@/lib/utils'

// Types matching backend ScanListItem / ScanResult
interface ScanItem {
  scan_id: string
  part_number: string | null
  status: 'PASS' | 'FAIL' | 'PARTIAL' | 'UNKNOWN' | 'COUNTERFEIT'
  confidence_score: number
  detected_pins: number
  scanned_at: string
}

interface ScanListResponse {
  scans: ScanItem[]
  total_count: number
  limit: number
  offset: number
}

const STATUS_CONFIG: Record<
  string,
  {
    icon: any
    label: string
    className: string
    variant: 'default' | 'destructive' | 'outline' | 'secondary'
  }
> = {
  PASS: {
    icon: CheckCircle2,
    label: 'Verified',
    className: 'bg-emerald-100 text-emerald-800 hover:bg-emerald-100 border-emerald-200',
    variant: 'default',
  },
  FAIL: {
    icon: XCircle,
    label: 'Failed',
    className: 'bg-red-100 text-red-800 hover:bg-red-100 border-red-200',
    variant: 'destructive',
  },
  PARTIAL: {
    icon: AlertTriangle,
    label: 'Partial',
    className: 'bg-amber-100 text-amber-800 hover:bg-amber-100 border-amber-200',
    variant: 'secondary',
  },
  UNKNOWN: {
    icon: HelpCircle,
    label: 'Unknown',
    className: 'bg-slate-100 text-slate-800 hover:bg-slate-100 border-slate-200',
    variant: 'secondary',
  },
  COUNTERFEIT: {
    icon: ShieldAlert,
    label: 'Counterfeit',
    className: 'bg-orange-100 text-orange-800 hover:bg-orange-100 border-orange-200',
    variant: 'destructive',
  },
}

export default function ScanHistoryPage() {
  const [scans, setScans] = useState<ScanItem[]>([])
  const [loading, setLoading] = useState(true)
  const [, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const wsRef = useRef<WebSocket | null>(null)

  // Initial Fetch
  const fetchScans = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/scans/list?limit=100`)
      if (!res.ok) throw new Error('Failed to fetch scans')
      const data: ScanListResponse = await res.json()
      setScans(data.scans)
    } catch (err) {
      console.error(err)
      setError('Failed to load scan history')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchScans()

    // WebSocket Connection
    const wsUrl = getWsUrl() + '/ws/scans'
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('Connected to Scan History WebSocket')
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        if (message.type === 'scan_created' || message.type === 'scan_updated') {
          const newScan = message.data
          setScans((prev) => {
            // Remove existing if present (update case) then add to top
            const filtered = prev.filter((s) => s.scan_id !== newScan.scan_id)
            return [newScan, ...filtered]
          })
        }
      } catch (e) {
        console.error('WebSocket message parse error', e)
      }
    }

    ws.onerror = (e) => {
      console.error('WebSocket error', e)
    }

    return () => {
      if (ws.readyState === 1) ws.close()
    }
  }, [])

  const filteredScans = scans.filter(
    (scan) =>
      (scan.part_number || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      scan.status.toLowerCase().includes(searchTerm.toLowerCase()),
  )

  return (
    <div className="animate-in fade-in flex h-screen w-full flex-col overflow-hidden bg-slate-50/50 p-6 duration-500">
      {/* Header */}
      <div className="mb-6 shrink-0">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h1 className="text-2xl font-black tracking-tight text-slate-900">Scan History</h1>
            <p className="text-sm font-medium text-slate-500">
              Real-time audit log of all component verifications
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input
                placeholder="Search part number..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="h-10 w-64 rounded-xl border-slate-200 bg-white pl-10 focus:ring-blue-500/20"
              />
            </div>
            <Button
              variant="outline"
              size="icon"
              className="h-10 w-10 rounded-xl border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              onClick={fetchScans}
            >
              <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
            </Button>
          </div>
        </div>
      </div>

      {/* Content */}
      <Card className="flex flex-1 flex-col overflow-hidden rounded-2xl border-slate-200 bg-white shadow-sm">
        <div className="custom-scrollbar flex-1 overflow-auto">
          <Table>
            <TableHeader className="sticky top-0 z-10 bg-slate-50">
              <TableRow className="border-slate-100 hover:bg-slate-50">
                <TableHead className="w-[15%] font-bold text-slate-500">Timestamp</TableHead>
                <TableHead className="w-[15%] font-bold text-slate-500">Part Number</TableHead>
                <TableHead className="w-[10%] font-bold text-slate-500">Status</TableHead>
                <TableHead className="w-[10%] text-center font-bold text-slate-500">
                  Confidence
                </TableHead>
                <TableHead className="w-[10%] text-center font-bold text-slate-500">Pins</TableHead>
                <TableHead className="w-[40%] pl-8 text-left font-bold text-slate-500">
                  Scan ID
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading && scans.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-24 text-center text-slate-500">
                    Loading history...
                  </TableCell>
                </TableRow>
              ) : filteredScans.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-32 text-center text-slate-500">
                    No scans found.
                  </TableCell>
                </TableRow>
              ) : (
                filteredScans.map((scan) => {
                  const statusStyle = STATUS_CONFIG[scan.status] || STATUS_CONFIG.UNKNOWN
                  const StatusIcon = statusStyle.icon

                  return (
                    <TableRow
                      key={scan.scan_id}
                      className="group border-slate-100 transition-colors hover:bg-blue-50/50"
                    >
                      <TableCell className="font-medium text-slate-600">
                        {scan.scanned_at
                          ? format(new Date(scan.scanned_at), 'dd MMM HH:mm:ss')
                          : '-'}
                      </TableCell>
                      <TableCell>
                        <div className="font-mono font-bold break-words text-slate-900">
                          {scan.part_number || (
                            <span className="text-slate-400 italic">Not Detected</span>
                          )}
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
                        <span
                          className={cn(
                            'font-bold',
                            scan.confidence_score > 80
                              ? 'text-emerald-600'
                              : scan.confidence_score > 50
                                ? 'text-amber-600'
                                : 'text-red-600',
                          )}
                        >
                          {scan.confidence_score.toFixed(1)}%
                        </span>
                      </TableCell>
                      <TableCell className="text-center font-medium text-slate-600">
                        {scan.detected_pins}
                      </TableCell>
                      <TableCell className="pl-8 text-left font-mono text-xs break-all text-slate-500">
                        {scan.scan_id}
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </div>
      </Card>
    </div>
  )
}
