import { useEffect, useState } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Cell,
  Pie,
  PieChart,
} from 'recharts'
import {
  TrendingUp,
  TrendingDown,
  Cpu,
  ShieldCheck,
  ShieldAlert,
  Database,
  Activity,
} from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart'
import type { ChartConfig } from '@/components/ui/chart'
import { API_BASE } from '@/lib/config'

interface DashboardStats {
  total_scans: number
  authentic_count: number
  counterfeit_count: number
  unknown_count: number
}

// Hardcoded values for demo
const DEMO_AUTHENTIC = 8
const DEMO_COUNTERFEIT = 2
const TOTAL_IC_DATABASE = 257

// Chart configurations
const scanChartConfig = {
  scans: {
    label: 'Scans',
    color: 'hsl(var(--chart-1))',
  },
  authentic: {
    label: 'Authentic',
    color: '#10b981',
  },
  counterfeit: {
    label: 'Counterfeit',
    color: '#ef4444',
  },
} satisfies ChartConfig

const pieChartConfig = {
  authentic: {
    label: 'Authentic',
    color: '#10b981',
  },
  counterfeit: {
    label: 'Counterfeit',
    color: '#ef4444',
  },
  pending: {
    label: 'Pending',
    color: '#94a3b8',
  },
} satisfies ChartConfig

export default function DashboardHome() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch(`${API_BASE}/scans/list?limit=500`)
        if (res.ok) {
          const data = await res.json()
          const totalScans = data.total_count || (data.scans || []).length
          // Use hardcoded values for authentic/counterfeit, but real total scans
          setStats({
            total_scans: totalScans,
            authentic_count: DEMO_AUTHENTIC,
            counterfeit_count: DEMO_COUNTERFEIT,
            unknown_count: totalScans - DEMO_AUTHENTIC - DEMO_COUNTERFEIT,
          })
        }
      } catch (error) {
        console.error('Failed to fetch stats:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchStats()
  }, [])

  // Generate chart data based on stats
  const weeklyData = [
    {
      day: 'Mon',
      scans: Math.floor((stats?.total_scans || 0) * 0.12),
      authentic: Math.floor(DEMO_AUTHENTIC * 0.15),
    },
    {
      day: 'Tue',
      scans: Math.floor((stats?.total_scans || 0) * 0.18),
      authentic: Math.floor(DEMO_AUTHENTIC * 0.2),
    },
    {
      day: 'Wed',
      scans: Math.floor((stats?.total_scans || 0) * 0.15),
      authentic: Math.floor(DEMO_AUTHENTIC * 0.12),
    },
    {
      day: 'Thu',
      scans: Math.floor((stats?.total_scans || 0) * 0.22),
      authentic: Math.floor(DEMO_AUTHENTIC * 0.25),
    },
    {
      day: 'Fri',
      scans: Math.floor((stats?.total_scans || 0) * 0.2),
      authentic: Math.floor(DEMO_AUTHENTIC * 0.18),
    },
    {
      day: 'Sat',
      scans: Math.floor((stats?.total_scans || 0) * 0.08),
      authentic: Math.floor(DEMO_AUTHENTIC * 0.06),
    },
    {
      day: 'Sun',
      scans: Math.floor((stats?.total_scans || 0) * 0.05),
      authentic: Math.floor(DEMO_AUTHENTIC * 0.04),
    },
  ]

  const pieData = [
    { name: 'Authentic', value: DEMO_AUTHENTIC, fill: '#10b981' },
    { name: 'Counterfeit', value: DEMO_COUNTERFEIT, fill: '#ef4444' },
    { name: 'Pending', value: stats?.unknown_count || 0, fill: '#94a3b8' },
  ]

  const barData = [
    { month: 'Oct', authentic: 45, counterfeit: 3 },
    { month: 'Nov', authentic: 62, counterfeit: 5 },
    { month: 'Dec', authentic: DEMO_AUTHENTIC, counterfeit: DEMO_COUNTERFEIT },
  ]

  const authenticRate = Math.round((DEMO_AUTHENTIC / (DEMO_AUTHENTIC + DEMO_COUNTERFEIT)) * 100)

  return (
    <div className="@container/main flex h-full w-full flex-col overflow-auto p-4 lg:p-6">
      {/* Stats Cards Row */}
      <div className="mb-6 grid grid-cols-2 gap-4 @xl/main:grid-cols-4">
        <Card className="rounded-2xl">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs">Total Scans</CardDescription>
            <CardTitle className="text-2xl font-bold tabular-nums">
              {loading ? '—' : stats?.total_scans || 0}
            </CardTitle>
          </CardHeader>
          <CardFooter className="pt-0">
            <div className="text-muted-foreground flex items-center gap-1 text-xs">
              <Cpu className="h-3.5 w-3.5" />
              <span>All time inspections</span>
            </div>
          </CardFooter>
        </Card>

        <Card className="rounded-2xl">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs">Authentic</CardDescription>
            <CardTitle className="text-2xl font-bold text-emerald-600 tabular-nums">
              {loading ? '—' : DEMO_AUTHENTIC}
            </CardTitle>
          </CardHeader>
          <CardFooter className="pt-0">
            <Badge
              variant="outline"
              className="gap-1 border-emerald-200 bg-emerald-50 text-emerald-700"
            >
              <ShieldCheck className="h-3 w-3" />
              Verified ICs
            </Badge>
          </CardFooter>
        </Card>

        <Card className="rounded-2xl">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs">Counterfeit</CardDescription>
            <CardTitle className="text-2xl font-bold text-red-600 tabular-nums">
              {loading ? '—' : DEMO_COUNTERFEIT}
            </CardTitle>
          </CardHeader>
          <CardFooter className="pt-0">
            <Badge variant="outline" className="gap-1 border-red-200 bg-red-50 text-red-700">
              <ShieldAlert className="h-3 w-3" />
              Detected fakes
            </Badge>
          </CardFooter>
        </Card>

        <Card className="rounded-2xl">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs">IC Database</CardDescription>
            <CardTitle className="text-2xl font-bold text-blue-600 tabular-nums">
              {loading ? '—' : TOTAL_IC_DATABASE}
            </CardTitle>
          </CardHeader>
          <CardFooter className="pt-0">
            <Badge variant="outline" className="gap-1 border-blue-200 bg-blue-50 text-blue-700">
              <Database className="h-3 w-3" />
              Datasheets
            </Badge>
          </CardFooter>
        </Card>
      </div>

      {/* Charts Grid */}
      <div className="grid flex-1 grid-cols-1 gap-4 @3xl/main:grid-cols-3">
        {/* Area Chart - Scan Activity */}
        <Card className="rounded-2xl @3xl/main:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Scan Activity</CardTitle>
            <CardDescription>Weekly inspection volume</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={scanChartConfig} className="h-[200px] w-full">
              <AreaChart data={weeklyData} margin={{ left: 0, right: 0 }}>
                <defs>
                  <linearGradient id="fillScans" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.1} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} strokeDasharray="3 3" />
                <XAxis
                  dataKey="day"
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  fontSize={12}
                />
                <ChartTooltip content={<ChartTooltipContent indicator="line" />} />
                <Area
                  dataKey="scans"
                  type="monotone"
                  fill="url(#fillScans)"
                  stroke="#06b6d4"
                  strokeWidth={2}
                />
              </AreaChart>
            </ChartContainer>
          </CardContent>
        </Card>

        {/* Pie Chart - Detection Distribution */}
        <Card className="rounded-2xl">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Detection Results</CardTitle>
            <CardDescription>Distribution by status</CardDescription>
          </CardHeader>
          <CardContent className="flex items-center justify-center">
            <ChartContainer config={pieChartConfig} className="h-[180px] w-[180px]">
              <PieChart>
                <ChartTooltip content={<ChartTooltipContent />} />
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={70}
                  strokeWidth={2}
                  stroke="hsl(var(--background))"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
              </PieChart>
            </ChartContainer>
          </CardContent>
          <CardFooter className="flex-col gap-2 text-sm">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5">
                <div className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
                <span className="text-muted-foreground text-xs">Authentic</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="h-2.5 w-2.5 rounded-full bg-red-500" />
                <span className="text-muted-foreground text-xs">Counterfeit</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="h-2.5 w-2.5 rounded-full bg-slate-400" />
                <span className="text-muted-foreground text-xs">Pending</span>
              </div>
            </div>
          </CardFooter>
        </Card>

        {/* Bar Chart - Monthly Comparison */}
        <Card className="rounded-2xl @3xl/main:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Monthly Comparison</CardTitle>
            <CardDescription>Authentic vs Counterfeit ICs</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer config={scanChartConfig} className="h-[180px] w-full">
              <BarChart data={barData} margin={{ left: 0, right: 0 }}>
                <CartesianGrid vertical={false} strokeDasharray="3 3" />
                <XAxis
                  dataKey="month"
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  fontSize={12}
                />
                <YAxis tickLine={false} axisLine={false} fontSize={12} width={30} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="authentic" fill="#10b981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="counterfeit" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>

        {/* System Health Card */}
        <Card className="rounded-2xl">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">System Health</CardTitle>
            <CardDescription>Real-time status</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
                <span className="text-sm">AI Model</span>
              </div>
              <Badge variant="secondary" className="bg-emerald-100 text-xs text-emerald-700">
                Active
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
                <span className="text-sm">OCR Engine</span>
              </div>
              <Badge variant="secondary" className="bg-emerald-100 text-xs text-emerald-700">
                Ready
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
                <span className="text-sm">Database</span>
              </div>
              <Badge variant="secondary" className="bg-emerald-100 text-xs text-emerald-700">
                Connected
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-blue-500" />
                <span className="text-sm">Detection</span>
              </div>
              <span className="text-sm font-semibold text-blue-600">95%</span>
            </div>
          </CardContent>
          <CardFooter>
            <div className="w-full rounded-lg bg-gradient-to-r from-cyan-50 to-blue-50 p-2.5 text-center">
              <span className="text-xs font-medium text-slate-700">SIH 2025 • BEL</span>
            </div>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}
