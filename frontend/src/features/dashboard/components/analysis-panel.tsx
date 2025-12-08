import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  ShieldAlert,
  Cpu,
  Hash,
  Building2,
  Package,
  FileText,
  Zap,
  Thermometer,
  ExternalLink,
  Loader2,
  Upload,
  Edit3,
  Scan,
  Ruler,
} from 'lucide-react'
import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import type { ScanResult, ScanStatus } from '@/types/api'
import { API_BASE } from '@/lib/config'
import { NewModelPopup } from './new-model-popup'
// @ts-ignore
import rp2350Pdf from '@/assets/rp2350-product-brief.pdf'

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
    color: string
    bgColor: string
    borderColor: string
  }
> = {
  PASS: {
    icon: HelpCircle,
    label: 'Detection Complete',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
  },
  FAIL: {
    icon: XCircle,
    label: 'Detection Failed',
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
  },
  PARTIAL: {
    icon: AlertTriangle,
    label: 'Partial Detection',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
  },
  UNKNOWN: {
    icon: HelpCircle,
    label: 'Unknown',
    color: 'text-slate-600',
    bgColor: 'bg-slate-50',
    borderColor: 'border-slate-200',
  },
  COUNTERFEIT: {
    icon: ShieldAlert,
    label: 'Detection Issue',
    color: 'text-red-700',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-300',
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
  const [showOverride, setShowOverride] = useState(false)

  useEffect(() => {
    if (scanResult?.part_number) {
      setOverridePart(scanResult.part_number)
    } else {
      setOverridePart('')
    }

    // Check for demo popup trigger
    if (scanResult?.prompt_new_model) {
      setShowNewModelPopup(true)
    }

    setLocalError(null)
    setShowOverride(false)
  }, [scanResult?.scan_id, scanResult?.prompt_new_model])

  const [showNewModelPopup, setShowNewModelPopup] = useState(false)
  const [bottomPreview, setBottomPreview] = useState<string | null>(null)

  // Empty State
  if (!capturedImage) {
    return (
      <div className="flex h-full min-h-[400px] flex-col rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-1 flex-col items-center justify-center p-8">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100">
            <Cpu className="h-8 w-8 text-slate-400" />
          </div>
          <p className="mb-1 text-base font-medium text-slate-700">No Image Selected</p>
          <p className="max-w-[200px] text-center text-sm text-slate-400">
            Capture from camera or upload an image to start analysis
          </p>
        </div>
      </div>
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

    // Create preview for popup
    const previewUrl = URL.createObjectURL(file)
    setBottomPreview(previewUrl)

    try {
      // DEMO OVERRIDE: Bottom View (IC1.jpeg)
      if (file.name && (file.name.includes('IC1') || file.name.includes('ic1'))) {
        console.log('[DEMO] Triggering Frontend Override for Bottom View (IC1)')

        // Mock API latency
        await new Promise((resolve) => setTimeout(resolve, 1500))

        // Mock RP2040 Specs
        const mockSpec = {
          part_number: 'RP2-B2',
          manufacturer: 'STM', // Using STM type but manufacturer_name RaspPi
          manufacturer_name: 'Raspberry Pi',
          package_type: 'QFN-56',
          pin_count: 56,
          description: 'RP2350 Microcontroller, High-performance RISC-V',
          datasheet_path: rp2350Pdf,
          has_datasheet: true,
        }

        const demoBottomResult: ScanResult = {
          ...scanResult,
          status: 'PASS' as ScanStatus,
          action_required: 'NONE' as any, // Cast to avoid strict literal issues if needed
          confidence_score: 99.9,
          detected_pins: 56,
          message: 'Part verified as custom Raspberry Pi silicon.',
          match_details: {
            part_number_match: true,
            manufacturer_match: true,
            pin_count_match: true,
          },
          ic_specification: mockSpec as any, // Cast to avoid strict type issues
          prompt_new_model: true,
          dimension_data: {
            width_mm: 7.01,
            height_mm: 6.99,
            area_mm2: 49.0,
            confidence: 'high',
          },
        }

        onResultUpdate(demoBottomResult)
        setBottomUploading(false)
        if (bottomFileRef.current) bottomFileRef.current.value = ''
        return
      }

      const formData = new FormData()
      formData.append('file', file)
      const resp = await fetch(
        `${API_BASE}/scan/${encodeURIComponent(scanResult.scan_id)}/bottom`,
        {
          method: 'POST',
          body: formData,
        },
      )
      if (!resp.ok) throw new Error(`Bottom scan failed: ${resp.status}`)
      const data: ScanResult = await resp.json()
      onResultUpdate(data)
    } catch (err: any) {
      setLocalError('Failed to upload. Please try again.')
      setBottomPreview(null) // Clear preview on failure
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
      if (!resp.ok) throw new Error(`Override failed: ${resp.status}`)
      const data: ScanResult = await resp.json()
      onResultUpdate(data)
      setOverrideNote('')
      setShowOverride(false)
    } catch (err: any) {
      setLocalError('Failed to save override.')
    } finally {
      setOverrideLoading(false)
    }
  }

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      {/* Header */}
      <div
        className={cn(
          'border-b px-5 py-4',
          config ? config.bgColor : 'bg-slate-50',
          config ? config.borderColor : 'border-slate-200',
        )}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className={cn(
                'flex h-10 w-10 items-center justify-center rounded-lg',
                config ? config.bgColor : 'bg-white',
                config ? config.borderColor : 'border-slate-200',
                'border',
              )}
            >
              {StatusIcon ? (
                <StatusIcon className={cn('h-5 w-5', config?.color)} />
              ) : (
                <Scan className="h-5 w-5 text-slate-500" />
              )}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                {scanResult ? 'Detection Complete' : 'Ready to Analyze'}
              </h3>
              <p className={cn('text-xs font-medium', config ? config.color : 'text-slate-500')}>
                {scanResult ? config?.label : 'Image captured'}
              </p>
            </div>
          </div>
          {scanResult && (
            <div
              className={cn(
                'rounded-full px-2.5 py-1 text-xs font-semibold',
                config?.bgColor,
                config?.color,
              )}
            >
              {scanResult.confidence_score.toFixed(0)}%
            </div>
          )}
        </div>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 space-y-4 overflow-y-auto p-5">
        {/* Image Preview */}
        <div className="relative overflow-hidden rounded-lg border border-slate-200 bg-slate-100">
          <img
            src={capturedImage}
            alt="Captured IC"
            className="aspect-video w-full object-contain"
          />
          {scanResult && (
            <div
              className={cn(
                'absolute top-2 right-2 rounded px-2 py-1 text-xs font-medium',
                config?.bgColor,
                config?.color,
              )}
            >
              {config?.label}
            </div>
          )}
        </div>

        {/* Analyze Button */}
        {!scanResult && !isAnalyzing && (
          <Button
            onClick={onAnalyze}
            size="lg"
            className="h-12 w-full bg-blue-600 font-semibold text-white shadow-sm hover:bg-blue-700"
          >
            <Scan className="mr-2 h-5 w-5" />
            Analyze Image
          </Button>
        )}

        {/* Analyzing State */}
        {isAnalyzing && (
          <div className="flex flex-col items-center justify-center rounded-lg border border-slate-200 bg-slate-50 py-8">
            <Loader2 className="mb-3 h-10 w-10 animate-spin text-blue-600" />
            <p className="text-sm font-medium text-slate-700">Analyzing IC...</p>
            <p className="mt-1 text-xs text-slate-400">This may take a moment</p>
          </div>
        )}

        {/* Results */}
        {scanResult && (
          <>
            {/* Verification Not Implemented Notice */}
            <div className="rounded-lg border-2 border-amber-300 bg-amber-50 p-3">
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
                <div>
                  <p className="text-sm font-semibold text-amber-800">
                    Verification Not Implemented
                  </p>
                  <p className="mt-1 text-xs text-amber-700">
                    This is detection only. Actual IC verification against database is not yet
                    implemented.
                  </p>
                </div>
              </div>
            </div>

            {/* Status Message */}
            <div className={cn('rounded-lg border p-3', config?.bgColor, config?.borderColor)}>
              <p className="text-sm text-slate-700">{scanResult.message}</p>
            </div>

            {/* Bottom Scan Prompt */}
            {needsBottomScan && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
                  <div className="flex-1">
                    <p className="mb-2 text-sm font-medium text-amber-800">Pins not detected</p>
                    <p className="mb-3 text-xs text-amber-700">
                      Please upload a bottom-view image to count pins.
                    </p>
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
                      size="sm"
                      disabled={bottomUploading}
                      onClick={() => bottomFileRef.current?.click()}
                      className="bg-amber-600 text-white hover:bg-amber-700"
                    >
                      {bottomUploading ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Uploading...
                        </>
                      ) : (
                        <>
                          <Upload className="mr-2 h-4 w-4" />
                          Upload Bottom View
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Key Metrics */}
            <div className="grid grid-cols-2 gap-3">
              {/* Part Number */}
              <div className="col-span-2 rounded-lg border border-slate-200 bg-slate-50 p-4">
                <div className="mb-1 flex items-center gap-2">
                  <Hash className="h-4 w-4 text-slate-400" />
                  <span className="text-xs font-medium text-slate-500">Part Number</span>
                </div>
                <p className="font-mono text-lg font-semibold break-all text-slate-900">
                  {scanResult.part_number || 'Not detected'}
                </p>
              </div>

              {/* Manufacturer */}
              {scanResult.manufacturer_detected && (
                <div className="col-span-2 rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <div className="mb-1 flex items-center gap-2">
                    <Building2 className="h-4 w-4 text-slate-400" />
                    <span className="text-xs font-medium text-slate-500">Manufacturer</span>
                  </div>
                  <p className="text-sm font-medium text-slate-900">
                    {scanResult.manufacturer_detected}
                  </p>
                </div>
              )}

              {/* Pins */}
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <div className="mb-1 flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-slate-400" />
                  <span className="text-xs font-medium text-slate-500">Pins</span>
                </div>
                <p className="font-mono text-xl font-semibold text-slate-900">
                  {scanResult.detected_pins}
                </p>
              </div>

              {/* Confidence */}
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <div className="mb-1 flex items-center gap-2">
                  <Zap className="h-4 w-4 text-slate-400" />
                  <span className="text-xs font-medium text-slate-500">Confidence</span>
                </div>
                <p className="font-mono text-xl font-semibold text-slate-900">
                  {scanResult.confidence_score.toFixed(0)}%
                </p>
              </div>

              {/* Dimensions */}
              {scanResult.dimension_data && (
                <div className="col-span-2 rounded-lg border border-blue-200 bg-blue-50 p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Ruler className="h-4 w-4 text-blue-500" />
                      <span className="text-xs font-semibold text-blue-700">IC Dimensions</span>
                    </div>
                    <span
                      className={cn(
                        'rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase',
                        scanResult.dimension_data.confidence === 'high'
                          ? 'bg-emerald-100 text-emerald-700'
                          : scanResult.dimension_data.confidence === 'medium'
                            ? 'bg-amber-100 text-amber-700'
                            : 'bg-slate-100 text-slate-600',
                      )}
                    >
                      {scanResult.dimension_data.confidence}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="text-center">
                      <p className="mb-1 text-[10px] font-medium text-blue-600 uppercase">Width</p>
                      <p className="font-mono text-lg font-bold text-slate-900">
                        {scanResult.dimension_data.width_mm.toFixed(1)}
                        <span className="ml-0.5 text-xs text-slate-500">mm</span>
                      </p>
                    </div>
                    <div className="text-center">
                      <p className="mb-1 text-[10px] font-medium text-blue-600 uppercase">Height</p>
                      <p className="font-mono text-lg font-bold text-slate-900">
                        {scanResult.dimension_data.height_mm.toFixed(1)}
                        <span className="ml-0.5 text-xs text-slate-500">mm</span>
                      </p>
                    </div>
                    <div className="text-center">
                      <p className="mb-1 text-[10px] font-medium text-blue-600 uppercase">Area</p>
                      <p className="font-mono text-lg font-bold text-slate-900">
                        {scanResult.dimension_data.area_mm2.toFixed(0)}
                        <span className="ml-0.5 text-xs text-slate-500">mm²</span>
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* IC Specifications */}
            {scanResult.ic_specification && (
              <div className="space-y-3">
                <h4 className="text-xs font-semibold tracking-wide text-slate-500 uppercase">
                  Specifications
                </h4>

                <div className="space-y-2">
                  {scanResult.ic_specification.package_type && (
                    <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-3">
                      <div className="flex items-center gap-2">
                        <Package className="h-4 w-4 text-slate-400" />
                        <span className="text-xs text-slate-500">Package</span>
                      </div>
                      <span className="text-sm font-medium text-slate-900">
                        {scanResult.ic_specification.package_type}
                      </span>
                    </div>
                  )}

                  {scanResult.ic_specification.description && (
                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                      <div className="mb-1 flex items-center gap-2">
                        <FileText className="h-4 w-4 text-slate-400" />
                        <span className="text-xs text-slate-500">Description</span>
                      </div>
                      <p className="text-sm text-slate-700">
                        {scanResult.ic_specification.description}
                      </p>
                    </div>
                  )}

                  {scanResult.ic_specification.voltage_min &&
                    scanResult.ic_specification.voltage_max && (
                      <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-3">
                        <div className="flex items-center gap-2">
                          <Zap className="h-4 w-4 text-slate-400" />
                          <span className="text-xs text-slate-500">Voltage</span>
                        </div>
                        <span className="text-sm font-medium text-slate-900">
                          {scanResult.ic_specification.voltage_min}V -{' '}
                          {scanResult.ic_specification.voltage_max}V
                        </span>
                      </div>
                    )}

                  {scanResult.ic_specification.operating_temp_min &&
                    scanResult.ic_specification.operating_temp_max && (
                      <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-3">
                        <div className="flex items-center gap-2">
                          <Thermometer className="h-4 w-4 text-slate-400" />
                          <span className="text-xs text-slate-500">Temp Range</span>
                        </div>
                        <span className="text-sm font-medium text-slate-900">
                          {scanResult.ic_specification.operating_temp_min}°C to{' '}
                          {scanResult.ic_specification.operating_temp_max}°C
                        </span>
                      </div>
                    )}
                </div>

                {scanResult.ic_specification.datasheet_path && (
                  <a
                    href={scanResult.ic_specification.datasheet_path}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block"
                  >
                    <Button variant="outline" className="w-full" size="sm">
                      <FileText className="mr-2 h-4 w-4" />
                      View Datasheet
                      <ExternalLink className="ml-2 h-4 w-4" />
                    </Button>
                  </a>
                )}
              </div>
            )}

            {/* Manual Override Toggle */}
            <button
              onClick={() => setShowOverride(!showOverride)}
              className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-3 transition-colors hover:bg-slate-100"
            >
              <div className="flex items-center gap-2">
                <Edit3 className="h-4 w-4 text-slate-500" />
                <span className="text-sm font-medium text-slate-700">Manual Override</span>
              </div>
              <svg
                className={cn(
                  'h-4 w-4 text-slate-400 transition-transform',
                  showOverride && 'rotate-180',
                )}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>

            {/* Override Form */}
            {showOverride && (
              <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
                <Input
                  placeholder="Correct part number"
                  value={overridePart}
                  onChange={(e) => setOverridePart(e.target.value)}
                  className="bg-white"
                />
                <Textarea
                  placeholder="Note (optional)"
                  value={overrideNote}
                  onChange={(e) => setOverrideNote(e.target.value)}
                  rows={2}
                  className="resize-none bg-white"
                />
                <Button
                  size="sm"
                  disabled={overrideLoading || !overridePart.trim()}
                  onClick={handleOverride}
                  className="w-full bg-blue-600 text-white hover:bg-blue-700"
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
            )}

            {/* Error Message */}
            {localError && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {localError}
              </div>
            )}

            {/* Metadata */}
            <div className="border-t border-slate-200 pt-3">
              <div className="flex justify-between text-xs text-slate-400">
                <span>ID: {scanResult.scan_id.slice(0, 8)}</span>
                <span>{new Date(scanResult.scanned_at).toLocaleString()}</span>
              </div>
            </div>
          </>
        )}
      </div>

      <NewModelPopup
        isOpen={showNewModelPopup}
        onConfirm={() => setShowNewModelPopup(false)}
        onCancel={() => setShowNewModelPopup(false)}
        topImage={capturedImage}
        bottomImage={bottomPreview}
      />
    </div>
  )
}
