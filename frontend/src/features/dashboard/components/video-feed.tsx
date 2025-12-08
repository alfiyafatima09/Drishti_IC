import { useEffect } from 'react'
import { Camera, CameraOff, Wifi, WifiOff, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { useCameraFeed } from '@/hooks/use-camera-feed'

// ============================================================
// TYPES
// ============================================================

interface VideoFeedProps {
  /** Called when an image is captured */
  onCapture?: (imageUrl: string) => void
}

// ============================================================
// COMPONENT
// ============================================================

export function VideoFeed({ onCapture }: VideoFeedProps) {
  const { status, isPhoneConnected, currentFrame, frameCount, connect, disconnect } =
    useCameraFeed()

  // Auto-connect to WebSocket on mount
  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  /**
   * Capture from live camera feed - just capture the image
   */
  const handleCaptureFromCamera = async () => {
    if (currentFrame && onCapture) {
      try {
        const response = await fetch(currentFrame)
        const blob = await response.blob()
        const imageUrl = URL.createObjectURL(blob)
        onCapture(imageUrl)
      } catch (e) {
        console.error('[VideoFeed] Failed to create preview:', e)
      }
    }
  }

  const canCapture = isPhoneConnected && currentFrame

  return (
    <div className="flex h-full flex-col gap-4">
      {/* Controls Bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge
            variant={
              status === 'connected' ? (isPhoneConnected ? 'default' : 'secondary') : 'destructive'
            }
            className="rounded-md"
          >
            <span
              className={cn(
                'mr-2 h-2 w-2 rounded-full',
                status === 'connected' && isPhoneConnected ? 'bg-emerald-400' : 'bg-current',
                status === 'connecting' && 'animate-pulse',
              )}
            />
            {isPhoneConnected
              ? 'Ready'
              : status === 'connected'
                ? 'Server Connected'
                : 'Disconnected'}
          </Badge>

          {isPhoneConnected && (
            <Badge variant="outline" className="border-slate-200 bg-white font-mono text-slate-600">
              {frameCount} frames
            </Badge>
          )}
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={status === 'connected' ? disconnect : connect}
          title={status === 'connected' ? 'Disconnect' : 'Connect'}
          className={cn(
            'border-slate-200 hover:bg-slate-50',
            status === 'connected' &&
              'border-red-100 text-red-600 hover:bg-red-50 hover:text-red-700',
          )}
        >
          {status === 'connected' ? (
            <WifiOff className="mr-2 h-4 w-4" />
          ) : (
            <Wifi className="mr-2 h-4 w-4" />
          )}
          {status === 'connected' ? 'Disconnect' : 'Connect'}
        </Button>
      </div>

      {/* Video Container */}
      <div className="relative aspect-video w-full overflow-hidden rounded-xl border border-slate-200 bg-slate-950 shadow-inner">
        {currentFrame ? (
          <img
            src={currentFrame}
            alt="Camera feed"
            className="absolute inset-0 h-full w-full object-contain"
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 text-slate-400">
            {status === 'connecting' ? (
              <div className="flex flex-col items-center gap-2">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
                <p className="text-sm font-medium text-slate-300">Connecting...</p>
              </div>
            ) : status === 'connected' && !isPhoneConnected ? (
              <div className="flex flex-col items-center gap-2 p-4 text-center">
                <CameraOff className="h-10 w-10 opacity-30" />
                <p className="text-sm font-medium text-slate-300">Waiting for camera source</p>
                <div className="mt-2 rounded-full border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-slate-400">
                  Open <code className="font-mono text-blue-400">/camera</code> on device
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <WifiOff className="h-10 w-10 opacity-30" />
                <p className="text-sm font-medium text-slate-400">Server disconnected</p>
              </div>
            )}
          </div>
        )}

        {/* Scanning Overlay (minimal) */}
        {currentFrame && (
          <div className="pointer-events-none absolute inset-0">
            <div className="absolute top-1/2 left-1/2 h-48 w-48 -translate-x-1/2 -translate-y-1/2 rounded-xl border border-white/20 shadow-[0_0_15px_rgba(0,0,0,0.3)]">
              <div className="absolute top-0 left-1/2 h-4 w-0.5 -translate-x-1/2 -translate-y-1/2 bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.8)]"></div>
              <div className="absolute bottom-0 left-1/2 h-4 w-0.5 -translate-x-1/2 translate-y-1/2 bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.8)]"></div>
              <div className="absolute top-1/2 left-0 h-0.5 w-4 -translate-x-1/2 -translate-y-1/2 bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.8)]"></div>
              <div className="absolute top-1/2 right-0 h-0.5 w-4 translate-x-1/2 -translate-y-1/2 bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.8)]"></div>
            </div>
          </div>
        )}
      </div>

      {/* Capture Action */}
      <Button
        size="lg"
        className="w-full rounded-xl bg-blue-600 font-bold text-white shadow-md shadow-blue-600/20 transition-all hover:-translate-y-0.5 hover:bg-blue-700"
        disabled={!canCapture}
        onClick={handleCaptureFromCamera}
      >
        <Camera className="mr-2 h-4 w-4" />
        {canCapture ? 'Capture Frame' : 'Waiting for Video...'}
      </Button>
    </div>
  )
}
