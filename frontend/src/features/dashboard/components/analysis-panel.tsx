import {
  Cpu,
} from 'lucide-react'
import { useState, useEffect } from 'react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import type { ScanResult } from '@/types/api'

interface AnalysisPanelProps {
  capturedImages: string[]
  scanResult: ScanResult | null
  isAnalyzing: boolean
  onAnalyze: () => void
  onResultUpdate: (result: ScanResult) => void
}


export function AnalysisPanel({
  capturedImages,
  scanResult,
  isAnalyzing,
  onAnalyze,
}: AnalysisPanelProps) {
  const [, setOverridePart] = useState('')
  const [, setLocalError] = useState<string | null>(null)

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

  // When images are present, show analysis interface
  return (
    <Card className="h-full border-none shadow-xl shadow-slate-200/40 rounded-3xl bg-white ring-1 ring-slate-100/50">
      <CardContent className="flex h-full flex-col p-6">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-slate-900 mb-2">IC Analysis</h3>
          <div className="flex flex-wrap gap-2 mb-4">
            {capturedImages.map((_, index) => (
              <Badge
                key={index}
                variant="secondary"
                className="bg-emerald-50 text-emerald-700 px-3 py-1"
              >
                Image {index + 1} ✓
              </Badge>
            ))}
          </div>
          
          {/* Display captured images */}
          {capturedImages.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-medium text-slate-700 mb-2">Captured Images</h4>
              <div className="grid grid-cols-1 gap-3 max-h-64 overflow-y-auto">
                {capturedImages.map((imageSrc, index) => (
                  <div key={index} className="relative border border-slate-200 rounded-lg p-2 bg-white">
                    <img
                      src={imageSrc}
                      alt={`Captured IC ${index + 1}`}
                      className="w-full h-32 object-contain rounded border border-slate-100"
                    />
                    <div className="absolute top-2 left-2 bg-black/70 text-white text-xs px-2 py-1 rounded">
                      Image {index + 1}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {scanResult && (
          <div className="flex-1 space-y-4">
            <div className="rounded-lg border bg-slate-50 p-4">
              <h4 className="font-medium text-slate-900 mb-3">Analysis Results</h4>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between items-center">
                  <span className="text-slate-600 font-medium">Part Number:</span>
                  <span className="font-semibold text-slate-900">
                    {scanResult.part_number || scanResult.part_number_detected || 'Not detected'}
                  </span>
                </div>
                
                <div className="flex justify-between items-center">
                  <span className="text-slate-600 font-medium">Status:</span>
                  <Badge variant={scanResult.status === 'EXTRACTED' ? 'default' : 'secondary'} className="text-xs">
                    {scanResult.status}
                  </Badge>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-slate-600 font-medium">Detected Pins:</span>
                  <span className="font-semibold text-slate-900">{scanResult.detected_pins || 0}</span>
                </div>

                {scanResult.manufacturer_detected && (
                  <div className="flex justify-between items-center">
                    <span className="text-slate-600 font-medium">Manufacturer:</span>
                    <span className="font-semibold text-slate-900">{scanResult.manufacturer_detected}</span>
                  </div>
                )}

                <div className="flex justify-between items-center">
                  <span className="text-slate-600 font-medium">Confidence:</span>
                  <span className="font-semibold text-slate-900">
                    {scanResult.confidence_score ? Math.round(scanResult.confidence_score) : 0}%
                  </span>
                </div>

                {scanResult.message && (
                  <div className="pt-2 border-t border-slate-200">
                    <span className="text-slate-600 font-medium block mb-1">Message:</span>
                    <span className="text-slate-800 text-xs">{scanResult.message}</span>
                  </div>
                )}

                {scanResult.ic_specification && (
                  <div className="pt-2 border-t border-slate-200">
                    <span className="text-slate-600 font-medium block mb-2">IC Specification:</span>
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Package:</span>
                        <span className="text-slate-800">{scanResult.ic_specification.package_type || 'Unknown'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Description:</span>
                        <span className="text-slate-800">{scanResult.ic_specification.description || 'N/A'}</span>
                      </div>
                    </div>
                  </div>
                )}

                {scanResult.match_details && (
                  <div className="pt-2 border-t border-slate-200">
                    <span className="text-slate-600 font-medium block mb-2">Match Details:</span>
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Part Match:</span>
                        <Badge variant={scanResult.match_details.part_number_match ? "default" : "secondary"} className="text-xs">
                          {scanResult.match_details.part_number_match ? "✓" : "✗"}
                        </Badge>
                      </div>
                      {scanResult.match_details.pin_count_match !== null && (
                        <div className="flex justify-between">
                          <span className="text-slate-500">Pin Match:</span>
                          <Badge variant={scanResult.match_details.pin_count_match ? "default" : "secondary"} className="text-xs">
                            {scanResult.match_details.pin_count_match ? "✓" : "✗"}
                          </Badge>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {!scanResult && !isAnalyzing && (
          <div className="flex-1 flex items-center justify-center">
            <button
              onClick={onAnalyze}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Analyze Images
            </button>
          </div>
        )}

        {isAnalyzing && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
              <p className="text-slate-600">Analyzing images...</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
