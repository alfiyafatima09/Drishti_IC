import { useState, useCallback, useRef, useEffect } from 'react'
import { FolderOpen, Upload, CheckCircle, XCircle, Clock, AlertCircle, Cpu, Building2, Sparkles, ShieldCheck, ShieldAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { API_BASE } from '@/lib/config'
import type { BatchScanResult, BatchProgress, BatchImageResult } from '@/types/api'

// ============================================================
// COMPONENT
// ============================================================

export default function BatchPage() {
  const [currentBatch, setCurrentBatch] = useState<BatchScanResult | null>(null)
  const [batchProgress, setBatchProgress] = useState<BatchProgress | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadMode, setUploadMode] = useState<'files' | 'folder'>('folder')
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [filterMode, setFilterMode] = useState<'all' | 'correct' | 'counterfeit'>('all')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const folderInputRef = useRef<HTMLInputElement>(null)

  // Poll for progress updates
  useEffect(() => {
    if (!currentBatch?.job_id) return

    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE}/batch-progress/${currentBatch.job_id}`)
        if (response.ok) {
          const progress: BatchProgress = await response.json()
          setBatchProgress(progress)

          // Stop polling when complete
          if (progress.status === 'completed' || progress.status === 'failed') {
            clearInterval(pollInterval)
          }
        }
      } catch (error) {
        console.error('Progress polling error:', error)
      }
    }, 2000) // Poll every 2 seconds

    return () => clearInterval(pollInterval)
  }, [currentBatch?.job_id])

  /**
   * Handle file selection
   */
  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || [])
    setSelectedFiles(files)
  }, [])

  /**
   * Handle folder selection
   */
  const handleFolderSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || [])
    setSelectedFiles(files)
  }, [])

  /**
   * Handle batch upload
   */
  const handleBatchUpload = useCallback(async () => {
    if (selectedFiles.length === 0) return

    setIsUploading(true)

    try {
      // Add 15 second delay to show loading state
      await new Promise(resolve => setTimeout(resolve, 15000))
      
      const formData = new FormData()

      selectedFiles.forEach((file) => {
        formData.append('files', file)
      })

      const response = await fetch(`${API_BASE}/batch-scan`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        console.error('Batch upload failed:', response.status)
        return
      }

      const result: BatchScanResult = await response.json()
      console.log('Batch upload result:', result)
      setCurrentBatch(result)
      setSelectedFiles([])

    } catch (error) {
      console.error('Batch upload error:', error)
    } finally {
      setIsUploading(false)
    }
  }, [selectedFiles])

  /**
   * Clear current batch
   */
  const clearBatch = useCallback(() => {
    setCurrentBatch(null)
    setBatchProgress(null)
    setSelectedFiles([])
  }, [])

  /**
   * Get status icon
   */
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'processing':
        return <Clock className="h-4 w-4 text-blue-500" />
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />
      default:
        return <AlertCircle className="h-4 w-4 text-gray-500" />
    }
  }

  /**
   * Get status color
   */
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'processing':
        return 'bg-blue-100 text-blue-800'
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  /**
   * Get filtered results based on filter mode
   */
  const getFilteredResults = useCallback((results: BatchImageResult[]): BatchImageResult[] => {
    switch (filterMode) {
      case 'correct':
        return results.filter(r => !r.result.is_counterfeit)
      case 'counterfeit':
        return results.filter(r => r.result.is_counterfeit)
      default:
        return results
    }
  }, [filterMode])

  /**
   * Render detailed result card like single scan analysis
   */
  const renderResultCard = (result: BatchImageResult, index: number) => {
    const isCounterfeit = result.result.is_counterfeit
    const partNumber = result.result.specs?.part_number || 'N/A'
    const manufacturer = result.result.specs?.manufacturer || 'Unknown'
    const pinCount = result.result.specs?.pin_count || 'N/A'
    const confidence = result.classification.confidence || result.result.confidence || 0
    const validationStatus = result.result.validation_status
    // image_path is in format: {job_id}/{filename}
    const imagePath = result.image_path

    return (
      <Card key={index} className="overflow-hidden border-slate-200 shadow-md hover:shadow-lg transition-shadow">
        {/* Image Preview */}
        <div className="aspect-video bg-slate-100 relative flex items-center justify-center overflow-hidden">
          <img
            src={`${API_BASE}/batch-images/${imagePath}`}
            alt={imagePath.split('/').pop() || imagePath}
            className="w-full h-full object-cover"
            onError={(e) => {
              e.currentTarget.style.display = 'none'
              const filename = imagePath.split('/').pop() || imagePath
              e.currentTarget.parentElement!.innerHTML = `<div class="flex items-center justify-center h-full text-sm text-slate-400">${filename}</div>`
            }}
          />
          {/* Status Badge Overlay */}
          <Badge
            className={`absolute top-2 right-2 ${
              isCounterfeit
                ? 'bg-red-600 hover:bg-red-700'
                : 'bg-emerald-600 hover:bg-emerald-700'
            } text-white`}
          >
            {isCounterfeit ? (
              <>
                <ShieldAlert className="mr-1 h-3 w-3" />
                Counterfeit
              </>
            ) : (
              <>
                <ShieldCheck className="mr-1 h-3 w-3" />
                Authentic
              </>
            )}
          </Badge>
          {/* Model Type Badge */}
          <Badge
            variant="secondary"
            className="absolute top-2 left-2 bg-slate-800/80 text-white backdrop-blur-sm"
          >
            {result.classification.model_type}
          </Badge>
        </div>

        <CardContent className="p-4 space-y-4">
          {/* Detected Information Grid - Like Analysis Panel */}
          <div className="grid grid-cols-2 gap-2">
            {/* Part Number */}
            <div className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-slate-50 p-2.5 shadow-sm">
              <span className="text-[9px] font-bold tracking-wider text-slate-500 uppercase">
                Part Number
              </span>
              <div className="truncate font-mono text-sm font-bold text-slate-900">
                {partNumber}
              </div>
            </div>

            {/* Manufacturer */}
            <div className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-slate-50 p-2.5 shadow-sm">
              <span className="text-[9px] font-bold tracking-wider text-slate-500 uppercase">
                Manufacturer
              </span>
              <div className="flex items-center gap-1 font-medium text-sm text-slate-900">
                <Building2 className="h-3 w-3 shrink-0 text-slate-400" />
                <span className="truncate">{manufacturer}</span>
              </div>
            </div>

            {/* Pins Detected */}
            <div className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-slate-50 p-2.5 shadow-sm">
              <span className="text-[9px] font-bold tracking-wider text-slate-500 uppercase">
                Pins Detected
              </span>
              <div className="flex items-center gap-1 font-bold text-sm text-slate-900">
                <Cpu className="h-3 w-3 text-slate-400" />
                <span>{pinCount}</span>
              </div>
            </div>

            {/* Confidence */}
            <div className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-slate-50 p-2.5 shadow-sm">
              <span className="text-[9px] font-bold tracking-wider text-slate-500 uppercase">
                Confidence
              </span>
              <div className="flex items-center gap-1 font-bold text-sm text-slate-900">
                <Sparkles className="h-3 w-3 text-blue-500" />
                <span>{(confidence * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>

          {/* Additional Info */}
          <div className="flex items-center justify-between text-xs text-slate-500 pt-2 border-t border-slate-100">
            <div className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              <span>{result.processing_time.toFixed(2)}s</span>
            </div>
            <Badge
              variant="outline"
              className={
                validationStatus === 'complete'
                  ? 'border-green-200 bg-green-50 text-green-700'
                  : 'border-amber-200 bg-amber-50 text-amber-700'
              }
            >
              {validationStatus}
            </Badge>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Batch IC Analysis</h1>
          <p className="text-muted-foreground">
            Upload folders or multiple images for intelligent batch processing
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => {
              setUploadMode('files')
              fileInputRef.current?.click()
            }}
            disabled={isUploading}
            variant="outline"
            className="flex items-center gap-2"
          >
            <Upload className="h-4 w-4" />
            Select Files
          </Button>
          <Button
            onClick={() => {
              setUploadMode('folder')
              folderInputRef.current?.click()
            }}
            disabled={isUploading}
            className="flex items-center gap-2"
          >
            <FolderOpen className="h-4 w-4" />
            Select Folder
          </Button>
        </div>
      </div>

      {/* File Input (Hidden) */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept="image/*,.zip"
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Folder Input (Hidden) */}
      <input
        ref={folderInputRef}
        type="file"
        {...({ webkitdirectory: '' } as any)}
        onChange={handleFolderSelect}
        className="hidden"
      />

      {/* File Selection */}
      {selectedFiles.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              {uploadMode === 'folder' ? 'Selected Folder' : 'Selected Files'} ({selectedFiles.length} images)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
              {selectedFiles.map((file) => (
                <div key={file.name} className="flex items-center gap-2 p-2 border rounded">
                  <div className="w-8 h-8 bg-gray-100 rounded flex items-center justify-center text-xs font-medium">
                    {file.name.split('.').pop()?.toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{file.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <Button
                onClick={handleBatchUpload}
                disabled={isUploading}
                className="flex-1"
              >
                {isUploading ? 'Uploading...' : 'Start Batch Analysis'}
              </Button>
              <Button variant="outline" onClick={() => setSelectedFiles([])}>
                Clear
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Current Batch Progress */}
      {currentBatch && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {batchProgress && getStatusIcon(batchProgress.status)}
              Batch Job: {currentBatch.job_id}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {batchProgress && (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Progress</span>
                  <Badge className={getStatusColor(batchProgress.status)}>
                    {batchProgress.status}
                  </Badge>
                </div>
                <Progress value={batchProgress.progress_percentage} className="w-full" />
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Processed</p>
                    <p className="font-medium">
                      {batchProgress.processed_images} / {batchProgress.total_images}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Progress</p>
                    <p className="font-medium">{batchProgress.progress_percentage.toFixed(1)}%</p>
                  </div>
                  {batchProgress.estimated_time_remaining && (
                    <div>
                      <p className="text-muted-foreground">ETA</p>
                      <p className="font-medium">
                        {Math.ceil(batchProgress.estimated_time_remaining / 60)}m remaining
                      </p>
                    </div>
                  )}
                  <div>
                    <p className="text-muted-foreground">Status</p>
                    <p className="font-medium capitalize">{batchProgress.status}</p>
                  </div>
                </div>
              </>
            )}

            {/* Results */}
            {batchProgress?.status === 'completed' && batchProgress.results && (
              <>
                <Separator />
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Results Summary</h3>

                  {/* Summary Stats */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-center">
                      <div className="text-2xl font-bold text-slate-900">{batchProgress.results.length}</div>
                      <div className="text-xs text-slate-500 uppercase tracking-wider">Total Processed</div>
                    </div>
                    <div className="rounded-xl border border-green-200 bg-green-50 p-3 text-center">
                      <div className="text-2xl font-bold text-green-700">
                        {batchProgress.results.filter(r => !r.result.is_counterfeit).length}
                      </div>
                      <div className="text-xs text-green-600 uppercase tracking-wider">Authentic</div>
                    </div>
                    <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-center">
                      <div className="text-2xl font-bold text-red-700">
                        {batchProgress.results.filter(r => r.result.is_counterfeit).length}
                      </div>
                      <div className="text-xs text-red-600 uppercase tracking-wider">Counterfeit</div>
                    </div>
                  </div>

                  {/* Filter Tabs */}
                  <div className="flex gap-2">
                    <Button 
                      variant={filterMode === 'all' ? 'default' : 'outline'} 
                      size="sm"
                      onClick={() => setFilterMode('all')}
                    >
                      All ({batchProgress.results.length})
                    </Button>
                    <Button 
                      variant={filterMode === 'correct' ? 'default' : 'outline'} 
                      size="sm"
                      onClick={() => setFilterMode('correct')}
                      className={filterMode === 'correct' ? 'bg-emerald-600 hover:bg-emerald-700' : ''}
                    >
                      <ShieldCheck className="mr-1 h-3 w-3" />
                      Authentic ({batchProgress.results.filter(r => !r.result.is_counterfeit).length})
                    </Button>
                    <Button 
                      variant={filterMode === 'counterfeit' ? 'default' : 'outline'} 
                      size="sm"
                      onClick={() => setFilterMode('counterfeit')}
                      className={filterMode === 'counterfeit' ? 'bg-red-600 hover:bg-red-700' : ''}
                    >
                      <ShieldAlert className="mr-1 h-3 w-3" />
                      Counterfeit ({batchProgress.results.filter(r => r.result.is_counterfeit).length})
                    </Button>
                  </div>

                  {/* Results Grid - Detailed Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {getFilteredResults(batchProgress.results).map((result, index) => 
                      renderResultCard(result, index)
                    )}
                  </div>

                  {/* Show message if no results match filter */}
                  {getFilteredResults(batchProgress.results).length === 0 && (
                    <div className="text-center py-8 text-slate-500">
                      <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p>No results match the current filter</p>
                    </div>
                  )}
                </div>
              </>
            )}

            <div className="flex gap-2">
              <Button onClick={clearBatch} variant="outline">
                Start New Batch
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Instructions */}
      {!currentBatch && selectedFiles.length === 0 && (
        <Card>
          <CardContent className="p-6">
            <div className="text-center space-y-4">
              <FolderOpen className="h-12 w-12 mx-auto text-muted-foreground" />
              <div>
                <h3 className="text-lg font-semibold">Batch Processing</h3>
                <p className="text-muted-foreground">
                  Process multiple IC images at once. Select individual files or choose an entire folder containing your chip photos.
                  Each image gets automatically analyzed using the most suitable AI model for fastest, most accurate results.
                </p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div className="space-y-2">
                  <h4 className="font-medium">📁 Upload Options</h4>
                  <p>Select individual image files or choose an entire folder with all your IC photos in one go.</p>
                </div>
                <div className="space-y-2">
                  <h4 className="font-medium">🎯 Smart Analysis</h4>
                  <p>Images are automatically sorted by type and sent to specialized models - no manual setup needed.</p>
                </div>
                <div className="space-y-2">
                  <h4 className="font-medium">⚡ GPU Acceleration</h4>
                  <p>Parallel processing with GPU support for quick turnaround, even with large batches.</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}