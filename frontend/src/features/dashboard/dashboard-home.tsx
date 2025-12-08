export default function DashboardHome() {
  return (
    <div className="animate-in fade-in flex h-screen w-full flex-col overflow-hidden bg-slate-50/50 p-6 duration-500">
      {/* Header */}
      <div className="mb-6 shrink-0">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h1 className="text-2xl font-black tracking-tight text-slate-900">Dashboard</h1>
            <p className="text-sm font-medium text-slate-500">Overview and statistics</p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex flex-1 flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-white/50 p-6 text-center">
        <div className="mb-4 rounded-full bg-blue-50 p-6 text-blue-600">
          {/* Placeholder chart/graph icon */}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="48"
            height="48"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect width="18" height="18" x="3" y="3" rx="2" />
            <path d="M3 9h18" />
            <path d="M3 15h18" />
            <path d="M9 3v18" />
          </svg>
        </div>
        <h3 className="mb-1 text-lg font-bold text-slate-900">Dashboard Empty State</h3>
        <p className="max-w-sm text-slate-500">
          This page is ready for your dashboard widgets, charts, and analytics.
        </p>
      </div>
    </div>
  )
}
