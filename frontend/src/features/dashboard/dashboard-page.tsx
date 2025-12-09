import { useState, useCallback, useRef } from 'react'
import { Camera, Sparkles, RotateCcw } from 'lucide-react'
import { VideoFeed } from './components/video-feed'
import { ImageUpload } from './components/image-upload'
import { AnalysisPanel } from './components/analysis-panel'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { API_BASE } from '@/lib/config'
import type { ScanResult } from '@/types/api'

// ============================================================
// COMPONENT
// ============================================================

export default function DashboardPage() {
  const [currentScanResult, setCurrentScanResult] = useState<ScanResult | null>(null)
  const [capturedImages, setCapturedImages] = useState<string[]>([])
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  /**
   * Handle camera capture - just show image, don't analyze yet
   */
  const handleCapture = useCallback((imageUrl: string) => {
    console.log('[Dashboard] Image captured')
    setCapturedImages((prev) => [...prev, imageUrl])
    setCurrentScanResult(null)
  }, [])

  /**
   * Handle file upload - just show image, don't analyze yet
   */
  const handleFileSelect = useCallback((files: File | File[]) => {
    const fileArray = Array.isArray(files) ? files : [files]

    const newImageUrls = fileArray.map((file) => {
      console.log('[Dashboard] File selected')
      return URL.createObjectURL(file)
    })

    setCapturedImages((prev) => [...prev, ...newImageUrls])
    setCurrentScanResult(null)
  }, [])

  /**
   * Clear images
   */
  const clearImages = useCallback(() => {
    setCapturedImages([])
    setCurrentScanResult(null)
  }, [])

  /**
   * Analyze the captured/uploaded images
   */
  const handleAnalyze = useCallback(async () => {
    if (capturedImages.length === 0) return

    setIsAnalyzing(true)

    try {
      const formData = new FormData()

      // Add first image as 'file'
      if (capturedImages[0]) {
        const firstResponse = await fetch(capturedImages[0])
        const firstBlob = await firstResponse.blob()
        const firstFile = new File([firstBlob], 'ic-1.jpg', { type: 'image/jpeg' })
        formData.append('file', firstFile)
      }

      // Add second image as 'bottom_file' if available
      if (capturedImages[1]) {
        const secondResponse = await fetch(capturedImages[1])
        const secondBlob = await secondResponse.blob()
        const secondFile = new File([secondBlob], 'ic-2.jpg', { type: 'image/jpeg' })
        formData.append('bottom_file', secondFile)
      }

      const apiResponse = await fetch(`${API_BASE}/scan`, {
        method: 'POST',
        body: formData,
      })

      if (!apiResponse.ok) {
        console.error('[Dashboard] Scan failed:', apiResponse.status)
        return
      }

      const scanResult: ScanResult = await apiResponse.json()
      console.log('[Dashboard] Scan result:', scanResult)
      setCurrentScanResult(scanResult)
    } catch (error) {
      console.error('[Dashboard] Analysis error:', error)
    } finally {
      setIsAnalyzing(false)
    }
  }, [capturedImages])

  const hasAnyImage = capturedImages.length > 0
  const hasBothImages = capturedImages.length >= 2

  return (
    <div className="h-[calc(100vh-1rem)] w-full p-4 overflow-hidden flex flex-col gap-4">
      {/* Header - Compact */}
      <div className="flex shrink-0 items-center justify-between px-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Drishti IC</h1>
          <p className="text-xs text-muted-foreground">
            Intelligent Integrated Circuit Inspection System
          </p>
        </div>
        <div className="flex items-center gap-2">
          {hasBothImages && (
            <Badge variant="secondary" className="border-green-200 bg-green-100 text-green-700">
              <Sparkles className="mr-1 h-3 w-3" />
              Dual View Ready
            </Badge>
          )}
          <span className="bg-primary/10 text-primary ring-primary/20 inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset">
            AOI Enabled
          </span>
        </div>
      </div>

      <Separator />

      {/* Main Content Grid - Full Height */}
      <div className="grid flex-1 grid-cols-12 gap-4 min-h-0">
        {/* Left Section - Available Space */}
        <div className="col-span-12 lg:col-span-9 flex flex-col min-h-0">
          <Card className="flex-1 flex flex-col border-none shadow-xl shadow-slate-200/40 rounded-3xl overflow-hidden bg-white ring-1 ring-slate-100">
            <CardHeader className="py-4 px-6 shrink-0 border-b border-slate-50 bg-white">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
                    <Camera className="h-5 w-5" />
                  </div>
                  <span className="font-semibold text-slate-900 tracking-tight">Acquire Image</span>
                </div>
                {hasAnyImage && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearImages}
                    className="h-8 gap-1.5 text-slate-500 hover:bg-red-50 hover:text-red-600 rounded-full px-3"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    Reset
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="flex-1 p-0 overflow-y-auto">
              <div className="flex flex-col lg:flex-row h-full">
                {/* Video Feed Area - Large */}
                <div className="flex-1 p-6 flex flex-col border-b lg:border-b-0 lg:border-r border-slate-50 min-h-[400px]">
                  <div className="flex items-center justify-between mb-4">
                    <span className="font-medium text-sm text-slate-500">Live Feed</span>
                    {hasAnyImage && (
                      <Badge variant="secondary" className="bg-emerald-50 text-emerald-700 border-none px-2.5 py-0.5 font-medium">
                        {capturedImages.length} Captured
                      </Badge>
                    )}
                  </div>
                  <div className="flex-1 bg-slate-50/50 rounded-2xl border border-dashed border-slate-200 flex flex-col justify-center overflow-hidden ring-4 ring-slate-50">
                    <VideoFeed onCapture={handleCapture} />
                  </div>
                </div>

                {/* Upload Area - Sidebar style */}
                <div className="w-full lg:w-80 shrink-0 p-6 bg-slate-50/50 flex flex-col gap-6">
                  <div>
                    <span className="font-semibold text-sm text-slate-900 block mb-3">Manual Upload</span>
                    <ImageUpload
                      onFileSelect={handleFileSelect}
                      fileInputRef={fileInputRef}
                      disabled={isAnalyzing}
                      title=""
                      multiple={true}
                    />
                  </div>

                  <div className="flex-1"></div> {/* Spacer */}

                  <div className="rounded-2xl border-none bg-white p-5 shadow-lg shadow-slate-200/50 ring-1 ring-slate-100">
                    <h4 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
                      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-100 text-[10px] text-blue-700 font-bold">i</span>
                      Capture Instructions
                    </h4>
                    <ul className="text-xs/relaxed text-slate-600 space-y-2.5 list-none">
                      <li className="flex gap-2">
                        <span className="text-blue-500">•</span>
                        <span>Position IC in the center of the frame</span>
                      </li>
                      <li className="flex gap-2">
                        <span className="text-blue-500">•</span>
                        <span>Ensure good lighting (avoid glare)</span>
                      </li>
                      <li className="flex gap-2">
                        <span className="text-blue-500">•</span>
                        <span>Capture <strong>Top view</strong> first</span>
                      </li>
                      <li className="flex gap-2">
                        <span className="text-blue-500">•</span>
                        <span>For full analysis, capture <strong>Bottom view</strong> second</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Section - Analysis */}
        <div className="col-span-12 lg:col-span-3 h-full min-h-0">
          <AnalysisPanel
            capturedImages={capturedImages}
            scanResult={currentScanResult}
            isAnalyzing={isAnalyzing}
            onAnalyze={handleAnalyze}
            onResultUpdate={setCurrentScanResult}
          />
        </div>
      </div>
    </div>
  )
}
