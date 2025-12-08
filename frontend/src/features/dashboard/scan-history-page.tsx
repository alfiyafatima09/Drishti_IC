
export default function ScanHistoryPage() {
    return (
        <div className="flex h-full flex-col gap-6 overflow-hidden bg-gradient-to-br from-blue-50 via-cyan-50 to-blue-100 p-6">
            {/* Header */}
            <div className="shrink-0">
                <div className="flex items-center justify-between rounded-2xl border-2 border-blue-200 bg-white/80 p-6 shadow-lg backdrop-blur-sm">
                    <div>
                        <h1 className="mb-2 bg-gradient-to-r from-blue-600 via-cyan-600 to-blue-700 bg-clip-text text-4xl font-black text-transparent">
                            Scan History
                        </h1>
                        <p className="text-base font-semibold text-slate-700">
                            View past IC scan results
                        </p>
                    </div>
                </div>
            </div>

            <div className="flex-1 rounded-2xl border-2 border-blue-200 bg-white/80 p-6 shadow-lg backdrop-blur-sm">
                <div className="flex h-full items-center justify-center text-slate-500">
                    <p>Scan history feature coming soon...</p>
                </div>
            </div>
        </div>
    )
}
