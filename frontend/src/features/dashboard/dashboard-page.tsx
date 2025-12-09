import { useState, useCallback, useRef } from 'react'
import { Camera, Sparkles, RotateCcw, Upload } from 'lucide-react'
import { VideoFeed } from './components/video-feed'
import { ImageUpload } from './components/image-upload'
import { AnalysisPanel } from './components/analysis-panel'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
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
    <div className="animate-in fade-in container mx-auto max-w-7xl p-6 duration-500">
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-foreground text-3xl font-bold tracking-tight">Drishti IC</h1>
              <p className="text-muted-foreground">
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
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Left Section - Camera & Upload */}
          <div className="flex flex-col gap-6 lg:col-span-2">
            {/* Image Capture Tabs */}
            <Card className="border-border shadow-sm">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>IC Image Capture</CardTitle>
                    <CardDescription>Capture or upload up to 2 images for analysis</CardDescription>
                  </div>
                  {hasAnyImage && (
                    <Button variant="outline" size="sm" onClick={clearImages} className="gap-2">
                      <RotateCcw className="h-4 w-4" />
                      Clear All
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  {/* Camera Capture */}
                  <div className="space-y-4">
                    <div className="flex items-center gap-2">
                      <Camera className="h-5 w-5 text-blue-600" />
                      <span className="font-medium">Camera Capture</span>
                      {hasAnyImage && (
                        <Badge variant="secondary" className="bg-green-100 text-green-700">
                          Captured
                        </Badge>
                      )}
                    </div>
                    <VideoFeed onCapture={handleCapture} />
                  </div>

                  {/* File Upload */}
                  <div className="border-t pt-4">
                    <div className="mb-4 flex items-center gap-2">
                      <Upload className="h-5 w-5 text-blue-600" />
                      <span className="font-medium">File Upload</span>
                      {capturedImages.length > 0 && (
                        <Badge variant="secondary" className="bg-green-100 text-green-700">
                          {capturedImages.length} image{capturedImages.length > 1 ? 's' : ''}{' '}
                          selected
                        </Badge>
                      )}
                    </div>
                    <ImageUpload
                      onFileSelect={handleFileSelect}
                      fileInputRef={fileInputRef}
                      disabled={isAnalyzing}
                      title="Select up to 2 images"
                      multiple={true}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right Section - Analysis Panel */}
          <div className="lg:col-span-1">
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
    </div>
  )
}
