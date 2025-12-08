import { useState, useCallback, useRef } from 'react'

import { VideoFeed } from './components/video-feed'
import { ImageUpload } from './components/image-upload'
import { AnalysisPanel } from './components/analysis-panel'
import { API_BASE } from '@/lib/config'
import type { ScanResult } from '@/types/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'

// ============================================================
// COMPONENT
// ============================================================

export default function DashboardPage() {
  const [currentScanResult, setCurrentScanResult] = useState<ScanResult | null>(null)
  const [capturedImage, setCapturedImage] = useState<string | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  /**
   * Handle camera capture - just show image, don't analyze yet
   */
  const handleCapture = useCallback((imageUrl: string) => {
    console.log('[Dashboard] Image captured')
    setCapturedImage(imageUrl)
    setCurrentScanResult(null)
  }, [])

  /**
   * Handle file upload - just show image, don't analyze yet
   */
  const handleFileSelect = useCallback((file: File) => {
    console.log('[Dashboard] File selected')
    const imageUrl = URL.createObjectURL(file)
    setCapturedImage(imageUrl)
    setCurrentScanResult(null)
  }, [])

  /**
   * Analyze the captured/uploaded image
   */
  const handleAnalyze = useCallback(async () => {
    if (!capturedImage || isAnalyzing) return

    setIsAnalyzing(true)

    try {
      // Convert image URL to File
      const response = await fetch(capturedImage)
      const blob = await response.blob()
      const file = new File([blob], 'ic-image.jpg', { type: 'image/jpeg' })

      const formData = new FormData()
      formData.append('file', file)

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
  }, [capturedImage, isAnalyzing])

  return (
    <div className="container mx-auto p-6 max-w-7xl animate-in fade-in duration-500">
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-foreground">Drishti IC</h1>
              <p className="text-muted-foreground">
                Intelligent Integrated Circuit Inspection System
              </p>
            </div>
            <div className="hidden md:block">
              <span className="inline-flex items-center rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary ring-1 ring-inset ring-primary/20">
                AOI Enabled
              </span>
            </div>
          </div>
          <Separator />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Section - Camera & Upload */}
          <div className="flex flex-col gap-6 lg:col-span-2">
            <Card className="border-border shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle>Live Feed</CardTitle>
                <CardDescription>Real-time camera view from inspection unit</CardDescription>
              </CardHeader>
              <CardContent>
                <VideoFeed onCapture={handleCapture} />
              </CardContent>
            </Card>

            <Card className="border-border shadow-sm">
              <CardHeader className="pb-3">
                <CardTitle>Manual Upload</CardTitle>
                <CardDescription>Upload high-resolution images for analysis</CardDescription>
              </CardHeader>
              <CardContent>
                <ImageUpload
                  onFileSelect={handleFileSelect}
                  fileInputRef={fileInputRef}
                  disabled={isAnalyzing}
                />
              </CardContent>
            </Card>
          </div>

          {/* Right Section - Analysis Panel */}
          <div className="lg:col-span-1">
            <AnalysisPanel
              capturedImage={capturedImage}
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
