import { Shield, Hexagon } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

export function LoginHero() {
  return (
    <div className="relative hidden flex-col justify-between overflow-hidden border-r border-zinc-900 bg-zinc-950 p-8 lg:flex lg:w-1/2 lg:p-16">
      {/* Abstract Background - Geometric/Architectural */}
      <div className="absolute inset-0 overflow-hidden opacity-20">
        <div className="absolute top-0 left-0 h-full w-full bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-zinc-800 via-zinc-950 to-zinc-950" />
        <div className="absolute right-0 bottom-0 h-[500px] w-[500px] translate-x-1/3 translate-y-1/3 rounded-full border border-zinc-800" />
        <div className="absolute right-0 bottom-0 h-[400px] w-[400px] translate-x-1/3 translate-y-1/3 rounded-full border border-zinc-800" />
      </div>

      <div className="relative z-10 flex h-full flex-col justify-between">
        {/* Header */}
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900">
              <Shield className="h-4 w-4 text-zinc-100" />
            </div>
            <h1 className="text-xl font-medium tracking-wide text-zinc-100">Drishti IC</h1>
          </div>
        </div>

        {/* Main Content */}
        <div className="space-y-8">
          <Badge
            variant="outline"
            className="border-zinc-800 bg-zinc-900/50 px-3 py-1 text-[10px] font-light tracking-wider text-zinc-400 uppercase"
          >
            SIH 2025 • Team Win Diesel
          </Badge>

          <div className="space-y-6">
            <h2 className="text-4xl leading-tight font-light tracking-tight text-zinc-100 sm:text-5xl">
              Precision <br />
              <span className="font-medium text-zinc-400">Authentication.</span>
            </h2>
            <p className="max-w-sm text-base leading-relaxed font-light text-zinc-500">
              Advanced optical inspection for instant counterfeit detection. Pure software. Zero
              hardware dependencies.
            </p>
          </div>

          <div className="flex items-center gap-6 text-xs font-medium tracking-widest text-zinc-600 uppercase">
            <div className="flex items-center gap-2">
              <Hexagon className="h-3 w-3" />
              <span>AI Core</span>
            </div>
            <div className="flex items-center gap-2">
              <Hexagon className="h-3 w-3" />
              <span>OCR</span>
            </div>
            <div className="flex items-center gap-2">
              <Hexagon className="h-3 w-3" />
              <span>Datasheets</span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-6">
          <p className="text-[10px] tracking-widest text-zinc-700 uppercase">v1.0.0 • Stable</p>
        </div>
      </div>
    </div>
  )
}
