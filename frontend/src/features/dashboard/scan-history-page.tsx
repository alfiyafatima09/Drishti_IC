import { useEffect, useState, useMemo } from 'react'
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  ShieldAlert,
  Search,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Activity,
  Users,
  Target,
  Filter,
} from 'lucide-react'
import { format } from 'date-fns'
import { API_BASE } from '@/lib/config'
import { cn } from '@/lib/utils'
import type { ScanListItem } from '@/types/api'

interface ScanListResponse {
  scans: ScanListItem[]
  total_count: number
  limit: number
  offset: number
}

interface Analytics {
  summary: {
    total_scans: number
    pass_count: number
    fail_count: number
    unknown_count: number
    counterfeit_count: number
    partial_count: number
    avg_confidence_score: number | null
    unique_manufacturers: number
    unique_batches: number
  }
  time_series: Array<{
    date: string
    pass_count: number
    fail_count: number
    total: number
  }>
  top_manufacturers: Array<{
    manufacturer: string
    count: number
    pass_rate: number
  }>
  recent_batches: Array<{
    batch_id: string
    count: number
    pass_rate: number
  }>
  confidence_distribution: Record<string, number>
}

const STATUS_CONFIG = {
  PASS: {
    icon: CheckCircle2,
    label: 'Pass',
    className: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  },
  FAIL: {
    icon: XCircle,
    label: 'Fail',
    className: 'bg-red-100 text-red-800 border-red-200',
  },
  PARTIAL: {
    icon: AlertTriangle,
    label: 'Partial',
    className: 'bg-amber-100 text-amber-800 border-amber-200',
  },
  UNKNOWN: {
    icon: HelpCircle,
    label: 'Unknown',
    className: 'bg-slate-100 text-slate-800 border-slate-200',
  },
  COUNTERFEIT: {
    icon: ShieldAlert,
    label: 'Counterfeit',
    className: 'bg-orange-100 text-orange-800 border-orange-200',
  },
}

export default function ScanHistoryPage() {
  const [scans, setScans] = useState<ScanListItem[]>([])
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [manufacturerFilter, setManufacturerFilter] = useState<string>('all')
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())

  const fetchData = async () => {
    try {
      setLoading(true)
      
      // Fetch scans with filters
      const params = new URLSearchParams({ limit: '100' })
      if (statusFilter !== 'all') params.append('status', statusFilter)
      if (manufacturerFilter !== 'all') params.append('manufacturer', manufacturerFilter)
      
      const [scansRes, analyticsRes] = await Promise.all([
        fetch(`${API_BASE}/scans/list?${params}`),
        fetch(`${API_BASE}/scans/analytics?days=30`)
      ])
      
      if (scansRes.ok) {
        const data: ScanListResponse = await scansRes.json()
        setScans(data.scans)
      }
      
      if (analyticsRes.ok) {
        const data: Analytics = await analyticsRes.json()
        setAnalytics(data)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [statusFilter, manufacturerFilter])

  const filteredScans = useMemo(() => {
    return scans.filter(
      (scan) =>
        (scan.part_number || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        (scan.message || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        (scan.batch_id || '').toLowerCase().includes(searchTerm.toLowerCase())
    )
  }, [scans, searchTerm])

  const toggleRowExpansion = (scanId: string) => {
    setExpandedRows((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(scanId)) {
        newSet.delete(scanId)
      } else {
        newSet.add(scanId)
      }
      return newSet
    })
  }

  const passRate = analytics?.summary.total_scans
    ? ((analytics.summary.pass_count / analytics.summary.total_scans) * 100).toFixed(1)
    : 0

  const recentTrend = useMemo(() => {
    if (!analytics?.time_series || analytics.time_series.length < 2) return 0
    const recent = analytics.time_series.slice(-7)
    const earlier = analytics.time_series.slice(-14, -7)
    const recentAvg = recent.reduce((sum, d) => sum + d.total, 0) / recent.length
    const earlierAvg = earlier.reduce((sum, d) => sum + d.total, 0) / earlier.length || 1
    return ((recentAvg - earlierAvg) / earlierAvg) * 100
  }, [analytics])

  const uniqueManufacturers = useMemo(() => {
    return Array.from(new Set(scans.map(s => s.manufacturer_detected).filter(Boolean)))
  }, [scans])

  return (
    <div className="animate-in fade-in flex h-screen w-full flex-col overflow-hidden bg-gradient-to-br from-slate-50 to-blue-50/30 p-6 duration-500">
      {/* Header */}
      <div className="mb-6 shrink-0">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h1 className="text-3xl font-black tracking-tight text-slate-900">
              Scan Analytics & History
            </h1>
            <p className="text-sm font-medium text-slate-500">
              Comprehensive insights and real-time audit trail
            </p>
          </div>
          <Button
            variant="outline"
            size="icon"
            className="h-10 w-10 rounded-xl border-slate-200 bg-white shadow-sm"
            onClick={fetchData}
          >
            <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
          </Button>
        </div>
      </div>

      {/* Analytics Cards */}
      {analytics && (
        <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4 shrink-0">
          <Card className="rounded-2xl border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold tracking-wider text-slate-500 uppercase">
                  Total Scans
                </p>
                <p className="mt-2 text-3xl font-black text-slate-900">
                  {analytics.summary.total_scans}
                </p>
                <div className="mt-2 flex items-center gap-1">
                  {recentTrend > 0 ? (
                    <TrendingUp className="h-3 w-3 text-emerald-600" />
                  ) : (
                    <TrendingDown className="h-3 w-3 text-red-600" />
                  )}
                  <span className={cn(
                    'text-xs font-bold',
                    recentTrend > 0 ? 'text-emerald-600' : 'text-red-600'
                  )}>
                    {Math.abs(recentTrend).toFixed(1)}% this week
                  </span>
                </div>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100">
                <Activity className="h-6 w-6 text-blue-600" />
              </div>
            </div>
          </Card>

          <Card className="rounded-2xl border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold tracking-wider text-slate-500 uppercase">
                  Pass Rate
                </p>
                <p className="mt-2 text-3xl font-black text-emerald-600">
                  {passRate}%
                </p>
                <p className="mt-2 text-xs text-slate-500">
                  {analytics.summary.pass_count} / {analytics.summary.total_scans} passed
                </p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-100">
                <CheckCircle2 className="h-6 w-6 text-emerald-600" />
              </div>
            </div>
          </Card>

          <Card className="rounded-2xl border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold tracking-wider text-slate-500 uppercase">
                  Avg Confidence
                </p>
                <p className="mt-2 text-3xl font-black text-slate-900">
                  {analytics.summary.avg_confidence_score?.toFixed(1) || 0}%
                </p>
                <p className="mt-2 text-xs text-slate-500">
                  Across all scans
                </p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-100">
                <Target className="h-6 w-6 text-amber-600" />
              </div>
            </div>
          </Card>

          <Card className="rounded-2xl border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold tracking-wider text-slate-500 uppercase">
                  Manufacturers
                </p>
                <p className="mt-2 text-3xl font-black text-slate-900">
                  {analytics.summary.unique_manufacturers}
                </p>
                <p className="mt-2 text-xs text-slate-500">
                  {analytics.summary.unique_batches} batches tracked
                </p>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-purple-100">
                <Users className="h-6 w-6 text-purple-600" />
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Filters & Search */}
      <div className="mb-4 flex flex-wrap items-center gap-3 shrink-0">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input
            placeholder="Search by part number, message, or batch..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="h-10 rounded-xl border-slate-200 bg-white pl-10 shadow-sm"
          />
        </div>

        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="h-10 w-[180px] rounded-xl border-slate-200 bg-white shadow-sm">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="PASS">Pass</SelectItem>
            <SelectItem value="FAIL">Fail</SelectItem>
            <SelectItem value="UNKNOWN">Unknown</SelectItem>
            <SelectItem value="COUNTERFEIT">Counterfeit</SelectItem>
            <SelectItem value="PARTIAL">Partial</SelectItem>
          </SelectContent>
        </Select>

        <Select value={manufacturerFilter} onValueChange={setManufacturerFilter}>
          <SelectTrigger className="h-10 w-[200px] rounded-xl border-slate-200 bg-white shadow-sm">
            <SelectValue placeholder="All Manufacturers" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Manufacturers</SelectItem>
            {uniqueManufacturers.map((mfg) => (
              <SelectItem key={mfg} value={mfg!}>
                {mfg}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {(statusFilter !== 'all' || manufacturerFilter !== 'all') && (
          <Button
            variant="ghost"
            size="sm"
            className="h-10 rounded-xl text-slate-600"
            onClick={() => {
              setStatusFilter('all')
              setManufacturerFilter('all')
            }}
          >
            <Filter className="mr-2 h-4 w-4" />
            Clear Filters
          </Button>
        )}

        <Badge variant="outline" className="h-10 rounded-xl bg-white px-4 shadow-sm">
          {filteredScans.length} results
        </Badge>
      </div>

      {/* Main Content - Split View */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 min-h-0">
        {/* Left Panel - Quick Stats */}
        {analytics && (
          <div className="lg:col-span-1 space-y-4 overflow-auto custom-scrollbar">
            {/* Top Manufacturers */}
            <Card className="rounded-2xl border-slate-200 bg-white p-4 shadow-sm">
              <h3 className="mb-3 text-sm font-bold text-slate-900">
                Top Manufacturers
              </h3>
              <div className="space-y-2">
                {analytics.top_manufacturers.slice(0, 5).map((mfg) => (
                  <div
                    key={mfg.manufacturer}
                    className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50 p-2"
                  >
                    <div className="flex-1">
                      <p className="text-xs font-bold text-slate-900">
                        {mfg.manufacturer}
                      </p>
                      <p className="text-[10px] text-slate-500">
                        {mfg.count} scans
                      </p>
                    </div>
                    <Badge
                      variant="outline"
                      className={cn(
                        'text-xs font-bold',
                        mfg.pass_rate >= 80
                          ? 'bg-emerald-100 text-emerald-700 border-emerald-200'
                          : mfg.pass_rate >= 60
                            ? 'bg-amber-100 text-amber-700 border-amber-200'
                            : 'bg-red-100 text-red-700 border-red-200'
                      )}
                    >
                      {mfg.pass_rate}%
                    </Badge>
                  </div>
                ))}
              </div>
            </Card>

            {/* Recent Batches */}
            {analytics.recent_batches.length > 0 && (
              <Card className="rounded-2xl border-slate-200 bg-white p-4 shadow-sm">
                <h3 className="mb-3 text-sm font-bold text-slate-900">
                  Recent Batches
                </h3>
                <div className="space-y-2">
                  {analytics.recent_batches.slice(0, 5).map((batch) => (
                    <div
                      key={batch.batch_id}
                      className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50 p-2"
                    >
                      <div className="flex-1">
                        <p className="text-xs font-bold font-mono text-slate-900">
                          {batch.batch_id}
                        </p>
                        <p className="text-[10px] text-slate-500">
                          {batch.count} scans
                        </p>
                      </div>
                      <Badge
                        variant="outline"
                        className={cn(
                          'text-xs font-bold',
                          batch.pass_rate >= 80
                            ? 'bg-emerald-100 text-emerald-700 border-emerald-200'
                            : 'bg-red-100 text-red-700 border-red-200'
                        )}
                      >
                        {batch.pass_rate}%
                      </Badge>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* Status Distribution */}
            <Card className="rounded-2xl border-slate-200 bg-white p-4 shadow-sm">
              <h3 className="mb-3 text-sm font-bold text-slate-900">
                Status Distribution
              </h3>
              <div className="space-y-2">
                {[
                  { label: 'Pass', count: analytics.summary.pass_count, colorClass: 'bg-emerald-500' },
                  { label: 'Fail', count: analytics.summary.fail_count, colorClass: 'bg-red-500' },
                  { label: 'Unknown', count: analytics.summary.unknown_count, colorClass: 'bg-slate-500' },
                  { label: 'Counterfeit', count: analytics.summary.counterfeit_count, colorClass: 'bg-orange-500' },
                ].map((item) => (
                  <div key={item.label} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-slate-600">{item.label}</span>
                      <span className="font-bold text-slate-900">{item.count}</span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                      <div
                        className={cn(
                          'h-full rounded-full transition-all',
                          item.colorClass
                        )}
                        style={{
                          width: `${(item.count / analytics.summary.total_scans) * 100}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}

        {/* Right Panel - Table */}
        <Card className="lg:col-span-2 flex flex-col overflow-hidden rounded-2xl border-slate-200 bg-white shadow-sm">
          <div className="custom-scrollbar flex-1 overflow-auto">
            <Table>
              <TableHeader className="sticky top-0 z-10 bg-slate-50">
                <TableRow className="border-slate-100">
                  <TableHead className="font-bold text-slate-500">Time</TableHead>
                  <TableHead className="font-bold text-slate-500">Part Number</TableHead>
                  <TableHead className="font-bold text-slate-500">Status</TableHead>
                  <TableHead className="font-bold text-slate-500">Action</TableHead>
                  <TableHead className="text-center font-bold text-slate-500">Confidence</TableHead>
                  <TableHead className="font-bold text-slate-500">Manufacturer</TableHead>
                  <TableHead className="font-bold text-slate-500">Message</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading && filteredScans.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="h-32 text-center">
                      <div className="flex flex-col items-center gap-3">
                        <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-200 border-t-blue-600" />
                        <p className="text-sm text-slate-500">Loading...</p>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : filteredScans.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="h-32 text-center text-slate-500">
                      No scans found.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredScans.map((scan) => {
                    const statusStyle = STATUS_CONFIG.hasOwnProperty(scan.status)
                      ? STATUS_CONFIG[scan.status as keyof typeof STATUS_CONFIG]
                      : STATUS_CONFIG.UNKNOWN
                    const StatusIcon = statusStyle.icon
                    const isExpanded = expandedRows.has(scan.scan_id)

                    return (
                      <>
                        <TableRow
                          key={scan.scan_id}
                          className="cursor-pointer border-slate-100 transition-colors hover:bg-blue-50/50"
                          onClick={() => toggleRowExpansion(scan.scan_id)}
                        >
                          <TableCell className="font-medium text-slate-600">
                            <div className="text-xs">
                              {scan.scanned_at
                                ? format(new Date(scan.scanned_at), 'HH:mm')
                                : '-'}
                            </div>
                            {scan.was_manual_override && (
                              <Badge variant="outline" className="mt-1 text-[9px] bg-amber-50 text-amber-700 border-amber-200">
                                OVERRIDE
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="font-mono text-sm font-bold text-slate-900">
                              {scan.part_number || '-'}
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant="outline"
                              className={cn(
                                'flex w-fit items-center gap-1 rounded-lg px-2 py-0.5 text-xs font-bold',
                                statusStyle.className
                              )}
                            >
                              <StatusIcon className="h-3 w-3" />
                              {statusStyle.label}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {scan.action_required !== 'NONE' ? (
                              <Badge
                                variant="outline"
                                className="flex w-fit items-center gap-1 rounded-lg bg-amber-50 border-amber-200 px-2 py-0.5 text-xs font-bold text-amber-700"
                              >
                                <Target className="h-3 w-3" />
                                {scan.action_required === 'SCAN_BOTTOM' ? 'Bottom Scan' : scan.action_required}
                              </Badge>
                            ) : (
                              <span className="text-xs text-slate-400">-</span>
                            )}
                          </TableCell>
                          <TableCell className="text-center">
                            {scan.confidence_score !== null ? (
                              <span
                                className={cn(
                                  'text-sm font-bold',
                                  scan.confidence_score > 80
                                    ? 'text-emerald-600'
                                    : scan.confidence_score > 50
                                      ? 'text-amber-600'
                                      : 'text-red-600'
                                )}
                              >
                                {scan.confidence_score.toFixed(0)}%
                              </span>
                            ) : (
                              '-'
                            )}
                          </TableCell>
                          <TableCell className="text-xs text-slate-700">
                            {scan.manufacturer_detected || '-'}
                          </TableCell>
                          <TableCell>
                            <p className="text-xs text-slate-600 line-clamp-2">
                              {scan.message || '-'}
                            </p>
                          </TableCell>
                        </TableRow>
                        {isExpanded && (
                          <TableRow key={`${scan.scan_id}-details`}>
                            <TableCell colSpan={7} className="bg-slate-50 p-6">
                              <div className="space-y-4">
                                {/* Message Section */}
                                {scan.message && (
                                  <div className="rounded-lg bg-blue-50 border border-blue-200 p-3">
                                    <span className="text-xs font-bold text-blue-700 uppercase">Message:</span>
                                    <p className="mt-1 text-sm text-blue-900">{scan.message}</p>
                                  </div>
                                )}

                                {/* Main Details Grid */}
                                <div className="grid grid-cols-4 gap-4 text-xs">
                                  <div>
                                    <span className="font-bold text-slate-500">Scan ID:</span>
                                    <p className="mt-1 font-mono text-slate-700 break-all">{scan.scan_id}</p>
                                  </div>
                                  
                                  {scan.part_number_detected && (
                                    <div>
                                      <span className="font-bold text-slate-500">Part # Detected:</span>
                                      <p className="mt-1 font-mono text-slate-700">{scan.part_number_detected}</p>
                                    </div>
                                  )}
                                  
                                  {scan.part_number_verified && (
                                    <div>
                                      <span className="font-bold text-slate-500">Part # Verified:</span>
                                      <p className="mt-1 font-mono text-slate-700">{scan.part_number_verified}</p>
                                    </div>
                                  )}
                                  
                                  {scan.detected_pins !== null && (
                                    <div>
                                      <span className="font-bold text-slate-500">Detected Pins:</span>
                                      <p className="mt-1 text-slate-700">{scan.detected_pins}</p>
                                    </div>
                                  )}
                                  
                                  {scan.expected_pins !== null && scan.expected_pins !== undefined && (
                                    <div>
                                      <span className="font-bold text-slate-500">Expected Pins:</span>
                                      <p className="mt-1 text-slate-700">{scan.expected_pins}</p>
                                    </div>
                                  )}
                                  
                                  {scan.batch_id && (
                                    <div>
                                      <span className="font-bold text-slate-500">Batch ID:</span>
                                      <p className="mt-1 font-mono text-slate-700">{scan.batch_id}</p>
                                    </div>
                                  )}
                                  
                                  {scan.batch_vender && (
                                    <div>
                                      <span className="font-bold text-slate-500">Batch Vendor:</span>
                                      <p className="mt-1 text-slate-700">{scan.batch_vender}</p>
                                    </div>
                                  )}
                                  
                                  <div>
                                    <span className="font-bold text-slate-500">Has Bottom Scan:</span>
                                    <p className="mt-1 text-slate-700">{scan.has_bottom_scan ? 'Yes' : 'No'}</p>
                                  </div>
                                  
                                  <div>
                                    <span className="font-bold text-slate-500">Scanned At:</span>
                                    <p className="mt-1 text-slate-700">
                                      {scan.scanned_at ? format(new Date(scan.scanned_at), 'MMM dd, yyyy HH:mm:ss') : '-'}
                                    </p>
                                  </div>
                                  
                                  {scan.completed_at && (
                                    <div>
                                      <span className="font-bold text-slate-500">Completed At:</span>
                                      <p className="mt-1 text-slate-700">
                                        {format(new Date(scan.completed_at), 'MMM dd, yyyy HH:mm:ss')}
                                      </p>
                                    </div>
                                  )}
                                </div>

                                {/* Part Number Candidates */}
                                {scan.part_number_candidates && scan.part_number_candidates.length > 0 && (
                                  <div>
                                    <span className="text-xs font-bold text-slate-500">Part Number Candidates:</span>
                                    <div className="mt-2 flex flex-wrap gap-2">
                                      {scan.part_number_candidates.map((c, i) => (
                                        <Badge key={i} variant="outline" className="text-xs font-mono">
                                          {c}
                                        </Badge>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </div>
                            </TableCell>
                          </TableRow>
                        )}
                      </>
                    )
                  })
                )}
              </TableBody>
            </Table>
          </div>
        </Card>
      </div>
    </div>
  )
}
