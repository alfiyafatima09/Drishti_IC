import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  ShieldAlert,
  Cpu,
  Building2,
  FileText,
  ExternalLink,
  Sparkles,
  Loader2,
  Upload,
  Edit3,
} from 'lucide-react'
import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import type { ScanResult, ScanStatus } from '@/types/api'
import { API_BASE } from '@/lib/config'

interface AnalysisPanelProps {
  capturedImage: string | null
  scanResult: ScanResult | null
  isAnalyzing: boolean
  onAnalyze: () => void
  onResultUpdate: (result: ScanResult) => void
}

const STATUS_CONFIG: Record<
  ScanStatus,
  {
    icon: typeof CheckCircle2
    label: string
    variant: 'default' | 'destructive' | 'secondary' | 'outline'
    className?: string
  }
> = {
  PASS: {
    icon: CheckCircle2,
    label: 'Verified',
    variant: 'default',
    className: 'bg-emerald-600 hover:bg-emerald-700',
  },
  FAIL: {
    icon: XCircle,
    label: 'Failed',
    variant: 'destructive',
  },
  PARTIAL: {
    icon: AlertTriangle,
    label: 'Partial',
    variant: 'secondary',
    className: 'text-amber-600 bg-amber-100',
  },
  UNKNOWN: {
    icon: HelpCircle,
    label: 'Unknown',
    variant: 'secondary',
  },
  COUNTERFEIT: {
    icon: ShieldAlert,
    label: 'Counterfeit',
    variant: 'destructive',
  },
}

export function AnalysisPanel({
  capturedImage,
  scanResult,
  isAnalyzing,
  onAnalyze,
  onResultUpdate,
}: AnalysisPanelProps) {
  const bottomFileRef = useRef<HTMLInputElement>(null)
  const [bottomUploading, setBottomUploading] = useState(false)
  const [overridePart, setOverridePart] = useState('')
  const [overrideNote, setOverrideNote] = useState('')
  const [overrideLoading, setOverrideLoading] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)

  useEffect(() => {
    const pn = scanResult?.part_number_detected || scanResult?.part_number || ''
    setOverridePart(pn)
    setLocalError(null)
  }, [scanResult?.scan_id, scanResult?.part_number_detected, scanResult?.part_number])

  if (!capturedImage) {
    return (
      <Card className="h-full border-dashed shadow-none bg-muted/30">
        <CardContent className="flex flex-col items-center justify-center h-full min-h-[400px] text-muted-foreground p-6 text-center">
          <Cpu className="h-12 w-12 mb-4 opacity-20" />
          <h3 className="text-lg font-semibold mb-2">No IC Captured</h3>
          <p className="text-sm">Capture from camera or upload an image to begin analysis</p>
        </CardContent>
      </Card>
    )
  }

  const config = scanResult ? STATUS_CONFIG[scanResult.status] : null
  const StatusIcon = config?.icon

  const needsBottomScan =
    scanResult && (scanResult.detected_pins === 0 || scanResult.action_required === 'SCAN_BOTTOM')

  const handleBottomUpload = async (file: File) => {
    if (!scanResult) return
    setLocalError(null)
    setBottomUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const resp = await fetch(
        `${API_BASE}/scan/${encodeURIComponent(scanResult.scan_id)}/bottom`,
        {
          method: 'POST',
          body: formData,
        },
      )
      if (!resp.ok) {
        throw new Error(`Bottom scan failed: ${resp.status}`)
      }
      const data: ScanResult = await resp.json()
      onResultUpdate(data)
    } catch (err) {
      console.error('Bottom scan error:', err)
      setLocalError('Failed to upload bottom scan. Please try again.')
    } finally {
      setBottomUploading(false)
      if (bottomFileRef.current) bottomFileRef.current.value = ''
    }
  }

  const handleOverride = async () => {
    if (!scanResult || !overridePart.trim()) return
    setLocalError(null)
    setOverrideLoading(true)
    try {
      const payload = {
        scan_id: scanResult.scan_id,
        manual_part_number: overridePart.trim(),
        operator_note: overrideNote.trim() || undefined,
      }
      const resp = await fetch(`${API_BASE}/scan/override`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!resp.ok) {
        throw new Error(`Override failed: ${resp.status}`)
      }
      const data: ScanResult = await resp.json()
      onResultUpdate(data)
      setOverrideNote('')
    } catch (err) {
      console.error('Override error:', err)
      setLocalError('Failed to override part number. Please try again.')
    } finally {
      setOverrideLoading(false)
    }
  }

  return (
    <Card className="flex h-full flex-col overflow-hidden rounded-2xl border-slate-200 bg-white shadow-lg shadow-slate-200/50">
      <CardHeader className="border-b border-slate-100 bg-white pb-4">
        <div className="flex items-center justify-between w-full">
          <CardTitle className="text-xl font-bold text-slate-900">Analysis</CardTitle>
          {scanResult && config && (
            <Badge variant={config.variant} className={cn("px-2.5 py-0.5 font-bold", config.className)}>
              {StatusIcon && <StatusIcon className="mr-1.5 h-3.5 w-3.5" />}
              {config.label}
            </Badge>
          )}
        </div>
        <CardDescription className="text-slate-500">
          {scanResult ? 'Results and specifications' : 'Ready to analyze captured image'}
        </CardDescription>
      </CardHeader>

      <CardContent className="flex-1 overflow-y-auto space-y-6">
        {/* Image Preview */}
        <div className="relative rounded-lg overflow-hidden border bg-muted">
          <img
            src={capturedImage}
            alt="Captured IC"
            className="aspect-video w-full object-contain"
          />
          {scanResult && (
            <Badge className="absolute top-2 right-2 backdrop-blur-md bg-background/80 text-foreground hover:bg-background/90" variant="outline">
              Confidence: {scanResult.confidence_score.toFixed(0)}%
            </Badge>
          )}
        </div>

        {/* Analyze Button */}
        {!scanResult && !isAnalyzing && (
          <Button
            onClick={onAnalyze}
            size="lg"
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl shadow-md shadow-blue-600/20 transition-all hover:-translate-y-0.5"
          >
            <Sparkles className="mr-2 h-4 w-4" />
            Analyze IC Image
          </Button>
        )}

        {/* Analyzing State */}
        {isAnalyzing && (
          <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground">
            <Loader2 className="mb-4 h-8 w-8 animate-spin text-primary" />
            <p className="font-medium">Processing Image...</p>
            <p className="text-sm">Extracting component features</p>
          </div>
        )}

        {/* Results */}
        {scanResult && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-5 p-1">
            {/* Status Message */}
            <div className={cn("px-4 py-3 rounded-xl border text-sm font-medium shadow-sm",
              scanResult.status === 'PASS' ? "bg-emerald-50 text-emerald-900 border-emerald-100" :
                scanResult.status === 'FAIL' ? "bg-red-50 text-red-900 border-red-100" :
                  "bg-slate-50 text-slate-700 border-slate-200"
            )}>
              <p>{scanResult.message}</p>
            </div>

            {/* Bottom Scan prompt */}
            {needsBottomScan && (
              <div className="space-y-3 p-4 rounded-lg border border-amber-200 bg-amber-50">
                <div className="flex items-center gap-2 font-medium text-amber-800">
                  <AlertTriangle className="h-4 w-4" />
                  <span>Pins hidden. Bottom view required.</span>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    ref={bottomFileRef}
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={(e) => {
                      const file = e.target.files?.[0]
                      if (file) handleBottomUpload(file)
                    }}
                  />
                  <Button
                    variant="default"
                    size="sm"
                    className="bg-amber-600 hover:bg-amber-700 text-white"
                    disabled={bottomUploading}
                    onClick={() => bottomFileRef.current?.click()}
                  >
                    {bottomUploading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Uploading
                      </>
                    ) : (
                      <>
                        <Upload className="mr-2 h-4 w-4" />
                        Upload Bottom
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}

            {/* Parameters List - Compact */}
            <div className="space-y-4">
              <h4 className="text-sm font-medium leading-none text-slate-900">Detected Information</h4>
              <div className="grid grid-cols-2 gap-3">

                {/* Part Number */}
                <div className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-slate-50 p-3 shadow-sm transition-all hover:border-slate-300">
                  <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500">Part Number</span>
                  <div className="font-mono text-base font-bold text-slate-900 truncate">
                    {scanResult.part_number_detected || scanResult.part_number || 'N/A'}
                  </div>
                </div>

                {/* Manufacturer */}
                <div className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-slate-50 p-3 shadow-sm transition-all hover:border-slate-300">
                  <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500">Manufacturer</span>
                  <div className="flex items-center gap-1.5 font-medium text-slate-900">
                    <Building2 className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                    <span className="break-words">{scanResult.manufacturer_detected || 'Unknown'}</span>
                  </div>
                </div>

                {/* Pins */}
                <div className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-slate-50 p-3 shadow-sm transition-all hover:border-slate-300">
                  <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500">Pins Detected</span>
                  <div className="flex items-center gap-1.5 font-bold text-slate-900">
                    <Cpu className="h-3.5 w-3.5 text-slate-400" />
                    <span>{scanResult.detected_pins}</span>
                  </div>
                </div>

                {/* Confidence */}
                <div className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-slate-50 p-3 shadow-sm transition-all hover:border-slate-300">
                  <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500">Confidence</span>
                  <div className="flex items-center gap-1.5 font-bold text-slate-900">
                    <Sparkles className="h-3.5 w-3.5 text-blue-500" />
                    <span>{scanResult.confidence_score.toFixed(1)}%</span>
                  </div>
                </div>

              </div>
            </div>

            <Separator />

            {/* IC Specifications */}
            {scanResult.ic_specification && (
              <div className="space-y-4">
                <h4 className="text-sm font-medium leading-none">Specifications</h4>

                <div className="grid gap-4 text-sm">
                  {scanResult.ic_specification.description && (
                    <p className="text-muted-foreground leading-relaxed">
                      {scanResult.ic_specification.description}
                    </p>
                  )}

                  <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                    {scanResult.ic_specification.package_type && (
                      <div className="flex justify-between border-b pb-2">
                        <span className="text-muted-foreground">Package</span>
                        <span className="font-medium">{scanResult.ic_specification.package_type}</span>
                      </div>
                    )}

                    {scanResult.ic_specification.pin_count && (
                      <div className="flex justify-between border-b pb-2">
                        <span className="text-muted-foreground">Spec Pins</span>
                        <span className="font-medium">{scanResult.ic_specification.pin_count}</span>
                      </div>
                    )}

                    {(scanResult.ic_specification.voltage_min && scanResult.ic_specification.voltage_max) && (
                      <div className="flex justify-between border-b pb-2">
                        <span className="text-muted-foreground">Voltage</span>
                        <span className="font-medium">{scanResult.ic_specification.voltage_min}V - {scanResult.ic_specification.voltage_max}V</span>
                      </div>
                    )}

                    {(scanResult.ic_specification.operating_temp_min && scanResult.ic_specification.operating_temp_max) && (
                      <div className="flex justify-between border-b pb-2">
                        <span className="text-muted-foreground">Temp</span>
                        <span className="font-medium">{scanResult.ic_specification.operating_temp_min}°C to {scanResult.ic_specification.operating_temp_max}°C</span>
                      </div>
                    )}
                  </div>
                </div>

                {scanResult.ic_specification.datasheet_path && (
                  <Button variant="outline" className="w-full" asChild>
                    <a
                      href={scanResult.ic_specification.datasheet_path}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <FileText className="mr-2 h-4 w-4" />
                      View Datasheet
                      <ExternalLink className="ml-2 h-4 w-4" />
                    </a>
                  </Button>
                )}
              </div>
            )}

            <Separator />

            {/* Manual Override */}
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Edit3 className="h-4 w-4 text-muted-foreground" />
                <span>Manual Override</span>
              </div>
              <div className="space-y-3">
                <Input
                  placeholder="Part Number"
                  value={overridePart}
                  onChange={(e) => setOverridePart(e.target.value)}
                />
                <Textarea
                  placeholder="Notes (optional)"
                  value={overrideNote}
                  onChange={(e) => setOverrideNote(e.target.value)}
                  className="min-h-[60px]"
                />
                <Button
                  disabled={overrideLoading || !overridePart.trim()}
                  onClick={handleOverride}
                  className="w-full"
                  variant="secondary"
                >
                  {overrideLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    'Save Override'
                  )}
                </Button>
              </div>
            </div>

            {localError && (
              <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive font-medium">
                {localError}
              </div>
            )}

            <div className="text-xs text-muted-foreground flex justify-between pt-2">
              <span>Scan ID: <span className="font-mono">{scanResult.scan_id.slice(0, 8)}</span></span>
              <span>{new Date(scanResult.scanned_at).toLocaleTimeString()}</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
