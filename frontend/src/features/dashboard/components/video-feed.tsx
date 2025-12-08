import { useEffect } from 'react'
import { Camera, CameraOff, Wifi, WifiOff, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { useCameraFeed, type CameraStatus } from '@/hooks/use-camera-feed'

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
          <Badge variant={status === 'connected' ? (isPhoneConnected ? 'default' : 'secondary') : 'destructive'}>
            <span
              className={cn(
                'mr-1.5 h-1.5 w-1.5 rounded-full',
                status === 'connected' && isPhoneConnected ? 'bg-emerald-400' : 'bg-current',
                status === 'connecting' && 'animate-pulse'
              )}
            />
            {isPhoneConnected ? 'Ready' : status === 'connected' ? 'Server Connected' : 'Disconnected'}
          </Badge>

          {isPhoneConnected && (
            <Badge variant="outline" className="font-mono">
              {frameCount} frames
            </Badge>
          )}
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={status === 'connected' ? disconnect : connect}
          title={status === 'connected' ? 'Disconnect' : 'Connect'}
          className={cn(status === 'connected' && "text-destructive hover:text-destructive")}
        >
          {status === 'connected' ? <WifiOff className="h-4 w-4 mr-2" /> : <Wifi className="h-4 w-4 mr-2" />}
          {status === 'connected' ? 'Disconnect' : 'Connect'}
        </Button>
      </div>

      {/* Video Container */}
      <div className="relative aspect-video w-full overflow-hidden rounded-lg border bg-muted shadow-inner">
        {currentFrame ? (
          <img
            src={currentFrame}
            alt="Camera feed"
            className="absolute inset-0 h-full w-full object-contain"
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 text-muted-foreground">
            {status === 'connecting' ? (
              <div className="flex flex-col items-center gap-2">
                <Loader2 className="h-8 w-8 animate-spin" />
                <p className="text-sm">Connecting...</p>
              </div>
            ) : status === 'connected' && !isPhoneConnected ? (
              <div className="flex flex-col items-center gap-2 text-center p-4">
                <CameraOff className="h-8 w-8 opacity-50" />
                <p className="text-sm font-medium">Waiting for camera source</p>
                <div className="text-xs bg-background/50 px-2 py-1 rounded border">
                  Open <code className="font-mono font-bold">/camera</code> on device
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <WifiOff className="h-8 w-8 opacity-50" />
                <p className="text-sm">Server disconnected</p>
              </div>
            )}
          </div>
        )}

        {/* Scanning Overlay (minimal) */}
        {currentFrame && (
          <div className="pointer-events-none absolute inset-0">
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-48 w-48 border border-primary/30 rounded-lg">
              <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 h-4 w-0.5 bg-primary/50"></div>
              <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 h-4 w-0.5 bg-primary/50"></div>
              <div className="absolute left-0 top-1/2 -translate-x-1/2 -translate-y-1/2 h-0.5 w-4 bg-primary/50"></div>
              <div className="absolute right-0 top-1/2 translate-x-1/2 -translate-y-1/2 h-0.5 w-4 bg-primary/50"></div>
            </div>
          </div>
        )}
      </div>

      {/* Capture Action */}
      <Button
        size="lg"
        className="w-full"
        disabled={!canCapture}
        onClick={handleCaptureFromCamera}
      >
        <Camera className="mr-2 h-4 w-4" />
        {canCapture ? 'Capture Frame' : 'Waiting for Video...'}
      </Button>
    </div>
  )
}
