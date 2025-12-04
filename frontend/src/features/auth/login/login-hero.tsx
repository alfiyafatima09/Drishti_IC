import { Shield, Hexagon } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

export function LoginHero() {
  return (
    <div className="bg-noise relative hidden flex-col justify-between overflow-hidden border-r-2 border-cyan-400 bg-gradient-to-br from-blue-600 via-cyan-600 to-blue-700 p-8 lg:flex lg:w-1/2 lg:p-16 shadow-2xl">
      {/* Abstract Background - Geometric/Architectural */}
      <div className="absolute inset-0 overflow-hidden opacity-20">
        <div className="absolute top-0 left-0 h-full w-full bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-cyan-500 via-blue-600 to-blue-700" />
        <div className="absolute right-0 bottom-0 h-[500px] w-[500px] translate-x-1/3 translate-y-1/3 rounded-full border-2 border-cyan-400/30" />
        <div className="absolute right-0 bottom-0 h-[400px] w-[400px] translate-x-1/3 translate-y-1/3 rounded-full border-2 border-cyan-400/30" />
      </div>

      <div className="relative z-10 flex h-full flex-col justify-between">
        {/* Header */}
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl border-2 border-cyan-300 bg-white shadow-xl">
              <Shield className="h-7 w-7 text-blue-600" />
            </div>
            <h1 className="text-2xl font-black tracking-tight text-white">Drishti IC</h1>
          </div>
        </div>

        {/* Main Content */}
        <div className="space-y-8">
          <Badge
            variant="outline"
            className="border-2 border-cyan-300 bg-white/20 backdrop-blur-sm px-4 py-2 text-xs font-bold tracking-wider text-white uppercase"
          >
            SIH 2025 • Bharat Electronics Limited
          </Badge>

          <div className="space-y-6">
            <h2 className="text-5xl leading-tight font-black tracking-tight text-white sm:text-6xl">
              Precision <br />
              <span className="font-black text-cyan-200">Authentication.</span>
            </h2>
            <p className="max-w-sm text-lg leading-relaxed font-semibold text-cyan-100">
              Advanced optical inspection for instant counterfeit detection. Pure software. Zero
              hardware dependencies.
            </p>
          </div>

          <div className="flex items-center gap-6 text-sm font-bold tracking-widest text-cyan-200 uppercase">
            <div className="flex items-center gap-2">
              <Hexagon className="h-4 w-4" />
              <span>OCR</span>
            </div>
            <div className="flex items-center gap-2">
              <Hexagon className="h-4 w-4" />
              <span>Datasheets</span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-6">
          <p className="text-xs tracking-widest text-cyan-300 uppercase font-bold">Smart India Hackathon</p>
        </div>
      </div>
    </div>
  )
}
