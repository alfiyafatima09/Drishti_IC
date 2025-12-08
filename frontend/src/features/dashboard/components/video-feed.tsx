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
// CONSTANTS
// ============================================================

const STATUS_CONFIG: Record<
  CameraStatus,
  {
    label: string
    color: string
    icon: typeof Wifi
  }
> = {
  disconnected: { label: 'Disconnected', color: 'bg-zinc-500', icon: WifiOff },
  connecting: { label: 'Connecting...', color: 'bg-amber-500', icon: Wifi },
  connected: { label: 'Connected', color: 'bg-emerald-500', icon: Wifi },
  error: { label: 'Error', color: 'bg-red-500', icon: WifiOff },
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

  const StatusIcon = STATUS_CONFIG[status].icon
  const canCapture = isPhoneConnected && currentFrame

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="mb-4 flex shrink-0 items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-cyan-600 shadow-lg">
            <Camera className="h-6 w-6 text-white" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">Live Camera Feed</h2>
            <p className="text-sm font-medium text-blue-600">Phone AOI Simulator</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Connection Status */}
          <Badge
            className={cn(
              'gap-1.5 border-2 px-3 py-1.5 font-semibold',
              status === 'connected' && isPhoneConnected
                ? 'border-emerald-600 bg-emerald-500 text-white'
                : 'border-slate-300 bg-slate-100 text-slate-700',
            )}
          >
            <span
              className={cn(
                'h-2 w-2 rounded-full',
                status === 'connected' && isPhoneConnected ? 'bg-white' : 'bg-slate-400',
                status === 'connecting' && 'animate-pulse',
              )}
            />
            <span className="text-xs font-bold">
              {isPhoneConnected ? 'Connected' : STATUS_CONFIG[status].label}
            </span>
          </Badge>

          {/* Frame Counter */}
          {isPhoneConnected && (
            <Badge className="border-2 border-blue-600 bg-blue-500 px-3 py-1.5 font-mono font-bold text-white shadow-md">
              {frameCount.toLocaleString()} frames
            </Badge>
          )}
        </div>
      </div>

      {/* Video Container - Fixed 16:9 aspect ratio */}
      <div className="relative aspect-video shrink-0 overflow-hidden rounded-xl border-4 border-blue-400 bg-slate-900 shadow-2xl">
        {currentFrame ? (
          <img
            src={currentFrame}
            alt="Camera feed"
            className="absolute inset-0 h-full w-full object-contain"
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-gradient-to-br from-slate-800 to-slate-900">
            {status === 'connecting' ? (
              <>
                <Loader2 className="h-16 w-16 animate-spin text-blue-400" />
                <p className="text-base font-semibold text-white">Connecting to server...</p>
              </>
            ) : status === 'connected' && !isPhoneConnected ? (
              <>
                <CameraOff className="h-16 w-16 text-cyan-400" />
                <div className="text-center">
                  <p className="text-base font-semibold text-white">Waiting for phone camera</p>
                  <p className="mt-2 text-sm font-medium text-cyan-300">
                    Open{' '}
                    <code className="rounded bg-cyan-900 px-2 py-1 font-bold text-cyan-200">
                      /camera
                    </code>{' '}
                    on your phone
                  </p>
                </div>
              </>
            ) : (
              <>
                <WifiOff className="h-16 w-16 text-slate-400" />
                <div className="text-center">
                  <p className="text-base font-semibold text-white">Not connected to server</p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={connect}
                    className="mt-3 border-blue-500 bg-blue-600 font-bold text-white hover:bg-blue-700"
                  >
                    Connect
                  </Button>
                </div>
              </>
            )}
          </div>
        )}

        {/* Scanning Overlay */}
        {currentFrame && (
          <div className="pointer-events-none absolute inset-0">
            {/* Corner brackets */}
            <div className="absolute top-4 left-4 h-16 w-16 rounded-tl-lg border-t-4 border-l-4 border-cyan-400" />
            <div className="absolute top-4 right-4 h-16 w-16 rounded-tr-lg border-t-4 border-r-4 border-cyan-400" />
            <div className="absolute bottom-4 left-4 h-16 w-16 rounded-bl-lg border-b-4 border-l-4 border-cyan-400" />
            <div className="absolute right-4 bottom-4 h-16 w-16 rounded-br-lg border-r-4 border-b-4 border-cyan-400" />

            {/* Center crosshair */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
              <div className="h-20 w-20 rounded-lg border-2 border-cyan-400 shadow-lg shadow-cyan-500/50" />
              <div className="absolute top-1/2 left-0 h-0.5 w-full bg-cyan-400/40" />
              <div className="absolute top-0 left-1/2 h-full w-0.5 bg-cyan-400/40" />
            </div>
          </div>
        )}
      </div>

      {/* Capture Controls */}
      <div className="mt-4 flex shrink-0 items-center gap-3">
        <Button
          size="lg"
          className={cn(
            'h-14 flex-1 text-base font-bold text-white shadow-xl',
            canCapture
              ? 'bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 hover:from-emerald-600 hover:via-teal-600 hover:to-cyan-600'
              : 'cursor-not-allowed bg-slate-400',
          )}
          disabled={!canCapture}
          onClick={handleCaptureFromCamera}
        >
          <Camera className="mr-2 h-6 w-6" />
          {canCapture ? 'Capture from Camera' : 'Camera Not Connected'}
        </Button>

        <Button
          size="lg"
          className="h-14 border-2 border-blue-500 bg-white px-5 shadow-lg hover:bg-blue-50"
          onClick={status === 'connected' ? disconnect : connect}
          title={status === 'connected' ? 'Disconnect' : 'Connect'}
        >
          <StatusIcon
            className={cn('h-6 w-6', status === 'connected' ? 'text-blue-600' : 'text-slate-500')}
          />
        </Button>
      </div>
    </div>
  )
}
