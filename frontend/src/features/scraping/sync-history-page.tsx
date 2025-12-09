import { History, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { SyncHistoryPanel } from './components/sync-history-panel'
import { useNavigate } from 'react-router-dom'

export default function SyncHistoryPage() {
  const navigate = useNavigate()

  return (
    <div className="animate-in fade-in flex h-screen w-full flex-col overflow-hidden bg-slate-50/50 p-6 duration-500">
      {/* Header */}
      <div className="mb-6 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate(-1)}
              className="h-10 w-10 rounded-xl text-slate-600 hover:bg-white"
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div className="space-y-1">
              <h1 className="text-2xl font-black tracking-tight text-slate-900">
                Sync Job History
              </h1>
              <p className="text-sm font-medium text-slate-500">
                Review past datasheet synchronization jobs and their results
              </p>
            </div>
          </div>

          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white shadow-sm">
            <History className="h-5 w-5 text-blue-600" />
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <SyncHistoryPanel limit={50} />
      </div>
    </div>
  )
}
