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
import { VerificationModal } from './verification-modal'

interface AnalysisPanelProps {
  capturedImages: string[]
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
  EXTRACTED: {
    icon: Sparkles,
    label: 'Extracted',
    variant: 'secondary',
    className: 'bg-blue-100 text-blue-700 hover:bg-blue-200',
  },
  NEED_BOTTOM_SCAN: {
    icon: AlertTriangle,
    label: 'Top Scan Only',
    variant: 'secondary',
    className: 'bg-amber-100 text-amber-700 hover:bg-amber-200',
  },
  MATCH_FOUND: {
    icon: CheckCircle2,
    label: 'Authentic',
    variant: 'default',
    className: 'bg-emerald-600 hover:bg-emerald-700',
  },
  PIN_MISMATCH: {
    icon: AlertTriangle,
    label: 'Pin Mismatch',
    variant: 'destructive',
  },
  MANUFACTURER_MISMATCH: {
    icon: AlertTriangle,
    label: 'Manufacturer Mismatch',
    variant: 'destructive',
  },
  NOT_IN_DATABASE: {
    icon: HelpCircle,
    label: 'Not in DB',
    variant: 'secondary',
  },
}

export function AnalysisPanel({
  capturedImages,
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
  const [showVerification, setShowVerification] = useState(false)

  useEffect(() => {
    const pn = scanResult?.part_number_detected || scanResult?.part_number || ''
    setOverridePart(pn)
    setLocalError(null)
  }, [scanResult?.scan_id, scanResult?.part_number_detected, scanResult?.part_number])

  const hasAnyImage = capturedImages.length > 0

  if (!hasAnyImage) {
    return (
      <Card className="h-full border-none shadow-xl shadow-slate-200/40 rounded-3xl bg-white ring-1 ring-slate-100/50">
        <CardContent className="flex h-full min-h-[400px] flex-col items-center justify-center p-8 text-center">
          <div className="mb-6 rounded-full bg-slate-50 p-6 ring-1 ring-slate-100">
            <Cpu className="h-10 w-10 text-slate-400" />
          </div>
          <h3 className="mb-2 text-xl font-semibold tracking-tight text-slate-900">
            No IC Captured
          </h3>
          <p className="text-slate-500 max-w-[280px] leading-relaxed">
            Capture from camera or upload images to begin analysis
          </p>
          <div className="mt-8 flex gap-2">
            {capturedImages.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {capturedImages.map((_, index) => (
                  <Badge
                    key={index}
                    variant="secondary"
                    className="bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition-colors px-3 py-1"
                  >
                    Image {index + 1} ✓
                  </Badge>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    )
  }

  // Handle status config more gracefully for new statuses
  const config = scanResult
    ? STATUS_CONFIG[scanResult.status as ScanStatus] || STATUS_CONFIG['UNKNOWN']
    : null
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

  const handleVerificationComplete = (result: ScanResult) => {
    onResultUpdate(result)
  }

  return (
    <>
      <VerificationModal
        isOpen={showVerification}
        onOpenChange={setShowVerification}
        scanResult={scanResult}
        onVerificationComplete={handleVerificationComplete}
      />

      <Card className="flex h-full flex-col overflow-hidden rounded-2xl border-slate-200 bg-white shadow-lg shadow-slate-200/50">
        <CardHeader className="border-b border-slate-100 bg-white pb-4">
          <div className="flex w-full items-center justify-between">
            <CardTitle className="text-xl font-bold text-slate-900">Analysis</CardTitle>
            {scanResult && config && (
              <Badge
                variant={config.variant}
                className={cn('px-2.5 py-0.5 font-bold', config.className)}
              >
                {StatusIcon && <StatusIcon className="mr-1.5 h-3.5 w-3.5" />}
                {config.label}
              </Badge>
            )}
          </div>
          <CardDescription className="text-slate-500">
            {scanResult ? 'Results and specifications' : 'Ready to analyze captured image'}
          </CardDescription>
        </CardHeader>

        <CardContent className="flex-1 space-y-6 overflow-y-auto">
          {/* Image Preview */}
          {capturedImages.length > 0 && (
            <div className="flex flex-col gap-4">
              {capturedImages.map((imageUrl, index) => (
                <div key={index} className="relative overflow-hidden rounded-2xl border border-slate-100 bg-slate-50 shadow-md shadow-slate-200/50 ring-1 ring-slate-50">
                  <img
                    src={imageUrl}
                    alt={`Captured IC ${index + 1}`}
                    className="w-full h-auto max-h-[350px] object-contain"
                  />
                  <Badge
                    className="absolute top-3 left-3 bg-white/90 text-slate-700 backdrop-blur border-slate-200 shadow-sm font-medium"
                    variant="secondary"
                  >
                    Image {index + 1}
                  </Badge>
                  {scanResult && index === 0 && (
                    <Badge
                      className="absolute top-3 right-3 bg-white/90 text-blue-700 backdrop-blur border-blue-100 shadow-sm font-bold"
                      variant="secondary"
                    >
                      {scanResult.confidence_score.toFixed(0)}% Match
                    </Badge>
                  )}
                </div>
              ))}
            </div>
          )}


          {/* Analyze Button */}
          {
            !scanResult && !isAnalyzing && (
              <Button
                onClick={onAnalyze}
                size="lg"
                className="w-full rounded-xl bg-blue-600 font-bold text-white shadow-md shadow-blue-600/20 transition-all hover:-translate-y-0.5 hover:bg-blue-700"
              >
                <Sparkles className="mr-2 h-4 w-4" />
                Analyze IC Image
              </Button>
            )
          }

          {/* Analyzing State */}
          {
            isAnalyzing && (
              <div className="text-muted-foreground flex flex-col items-center justify-center py-8 text-center">
                <Loader2 className="text-primary mb-4 h-8 w-8 animate-spin" />
                <p className="font-medium">Processing Image...</p>
                <p className="text-sm">Extracting component features</p>
              </div>
            )
          }

          {/* Results */}
          {
            scanResult && (
              <div className="animate-in fade-in slide-in-from-bottom-5 space-y-6 p-1">
                {/* Verification Ready State Trigger */}
                {(scanResult.status === 'EXTRACTED' || scanResult.status === 'NEED_BOTTOM_SCAN') && (
                  <div className="space-y-3 rounded-xl border border-slate-100 bg-slate-50 p-4">
                    <div className="flex items-center gap-3">
                      <div
                        className={cn(
                          'flex h-10 w-10 items-center justify-center rounded-full border',
                          'border-blue-200 bg-blue-100 text-blue-600',
                        )}
                      >
                        <Sparkles size={20} />
                      </div>
                      <div>
                        <h4 className="font-bold text-slate-900">Analysis Complete</h4>
                        <p className="text-xs text-slate-500">
                          Data extracted. Ready for validation.
                        </p>
                      </div>
                    </div>

                    <Button
                      onClick={() => setShowVerification(true)}
                      className="h-11 w-full rounded-xl bg-blue-600 font-bold text-white shadow-lg shadow-blue-500/20 transition-all hover:-translate-y-0.5 hover:bg-blue-700"
                    >
                      Ready for Validation
                      <CheckCircle2 className="ml-2 h-4 w-4" />
                    </Button>
                  </div>
                )}

                {/* Status Message */}
                <div
                  className={cn(
                    'rounded-xl border px-4 py-3 text-sm font-medium shadow-sm',
                    scanResult.message.includes('success') || scanResult.status === 'MATCH_FOUND'
                      ? 'border-emerald-100 bg-emerald-50 text-emerald-900'
                      : scanResult.status?.includes('FAIL') || scanResult.status === 'COUNTERFEIT'
                        ? 'border-red-100 bg-red-50 text-red-900'
                        : 'border-slate-200 bg-slate-50 text-slate-700',
                  )}
                >
                  <p>{scanResult.message}</p>
                </div>

                {/* Bottom Scan prompt */}
                {needsBottomScan && (
                  <div className="space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
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
                        className="bg-amber-600 text-white hover:bg-amber-700"
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
                  <h4 className="text-sm leading-none font-medium text-slate-900">
                    Detected Information
                  </h4>
                  <div className="grid grid-cols-2 gap-3">
                    {/* Part Number */}
                    <div className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-slate-50 p-3 shadow-sm transition-all hover:border-slate-300">
                      <span className="text-[10px] font-bold tracking-wider text-slate-500 uppercase">
                        Part Number
                      </span>
                      <div className="truncate font-mono text-base font-bold text-slate-900">
                        {scanResult.part_number_detected || scanResult.part_number || 'N/A'}
                      </div>
                    </div>

                    {/* Manufacturer */}
                    <div className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-slate-50 p-3 shadow-sm transition-all hover:border-slate-300">
                      <span className="text-[10px] font-bold tracking-wider text-slate-500 uppercase">
                        Manufacturer
                      </span>
                      <div className="flex items-center gap-1.5 font-medium text-slate-900">
                        <Building2 className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                        <span className="break-words">
                          {scanResult.manufacturer_detected || 'Unknown'}
                        </span>
                      </div>
                    </div>

                    {/* Pins */}
                    <div className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-slate-50 p-3 shadow-sm transition-all hover:border-slate-300">
                      <span className="text-[10px] font-bold tracking-wider text-slate-500 uppercase">
                        Pins Detected
                      </span>
                      <div className="flex items-center gap-1.5 font-bold text-slate-900">
                        <Cpu className="h-3.5 w-3.5 text-slate-400" />
                        <span>{scanResult.detected_pins}</span>
                      </div>
                    </div>

                    {/* Confidence */}
                    <div className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-slate-50 p-3 shadow-sm transition-all hover:border-slate-300">
                      <span className="text-[10px] font-bold tracking-wider text-slate-500 uppercase">
                        Confidence
                      </span>
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
                    <h4 className="text-sm leading-none font-medium">Specifications</h4>

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
                            <span className="font-medium">
                              {scanResult.ic_specification.package_type}
                            </span>
                          </div>
                        )}

                        {scanResult.ic_specification.pin_count && (
                          <div className="flex justify-between border-b pb-2">
                            <span className="text-muted-foreground">Spec Pins</span>
                            <span className="font-medium">
                              {scanResult.ic_specification.pin_count}
                            </span>
                          </div>
                        )}

                        {scanResult.ic_specification.voltage_min &&
                          scanResult.ic_specification.voltage_max && (
                            <div className="flex justify-between border-b pb-2">
                              <span className="text-muted-foreground">Voltage</span>
                              <span className="font-medium">
                                {scanResult.ic_specification.voltage_min}V -{' '}
                                {scanResult.ic_specification.voltage_max}V
                              </span>
                            </div>
                          )}

                        {scanResult.ic_specification.operating_temp_min &&
                          scanResult.ic_specification.operating_temp_max && (
                            <div className="flex justify-between border-b pb-2">
                              <span className="text-muted-foreground">Temp</span>
                              <span className="font-medium">
                                {scanResult.ic_specification.operating_temp_min}°C to{' '}
                                {scanResult.ic_specification.operating_temp_max}°C
                              </span>
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
                    <Edit3 className="text-muted-foreground h-4 w-4" />
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
                  <div className="bg-destructive/10 text-destructive rounded-md p-3 text-sm font-medium">
                    {localError}
                  </div>
                )}

                <div className="text-muted-foreground flex justify-between pt-2 text-xs">
                  <span>
                    Scan ID: <span className="font-mono">{scanResult.scan_id.slice(0, 8)}</span>
                  </span>
                  <span>{new Date(scanResult.scanned_at).toLocaleTimeString()}</span>
                </div>
              </div>
            )
          }
        </CardContent >
      </Card >
    </>
  )
}
