import { useEffect } from 'react'
import { Camera, CameraOff, Wifi, WifiOff, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useCameraFeed, type CameraStatus } from '@/hooks/use-camera-feed'

interface VideoFeedProps {
  onCapture?: (imageUrl: string) => void
}

const STATUS_CONFIG: Record<
  CameraStatus,
  {
    label: string
    color: string
    dotColor: string
    icon: typeof Wifi
  }
> = {
  disconnected: {
    label: 'Disconnected',
    color: 'text-slate-500',
    dotColor: 'bg-slate-400',
    icon: WifiOff,
  },
  connecting: {
    label: 'Connecting',
    color: 'text-amber-600',
    dotColor: 'bg-amber-500',
    icon: Wifi,
  },
  connected: {
    label: 'Connected',
    color: 'text-emerald-600',
    dotColor: 'bg-emerald-500',
    icon: Wifi,
  },
  error: { label: 'Error', color: 'text-red-600', dotColor: 'bg-red-500', icon: WifiOff },
}

export function VideoFeed({ onCapture }: VideoFeedProps) {
  const { status, isPhoneConnected, currentFrame, frameCount, connect, disconnect } =
    useCameraFeed()

  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

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
  const statusInfo = STATUS_CONFIG[status]

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100">
            <Camera className="h-5 w-5 text-slate-600" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Live Camera</h2>
            <p className="text-xs text-slate-500">Phone AOI Feed</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Status Indicator */}
          <div className="flex items-center gap-2">
            <span
              className={cn(
                'h-2 w-2 rounded-full',
                statusInfo.dotColor,
                status === 'connecting' && 'animate-pulse',
              )}
            />
            <span className={cn('text-xs font-medium', statusInfo.color)}>
              {isPhoneConnected ? 'Phone Connected' : statusInfo.label}
            </span>
          </div>

          {/* Frame Counter */}
          {isPhoneConnected && (
            <span className="rounded bg-slate-100 px-2 py-1 font-mono text-xs text-slate-400">
              {frameCount.toLocaleString()} frames
            </span>
          )}
        </div>
      </div>

      {/* Video Container */}
      <div className="relative aspect-video overflow-hidden rounded-lg border border-slate-200 bg-slate-900">
        {currentFrame ? (
          <>
            <img
              src={currentFrame}
              alt="Camera feed"
              className="absolute inset-0 h-full w-full object-contain"
            />
            {/* Subtle scan overlay */}
            <div className="pointer-events-none absolute inset-0">
              <div className="absolute top-3 left-3 h-8 w-8 rounded-tl border-t-2 border-l-2 border-cyan-400/60" />
              <div className="absolute top-3 right-3 h-8 w-8 rounded-tr border-t-2 border-r-2 border-cyan-400/60" />
              <div className="absolute bottom-3 left-3 h-8 w-8 rounded-bl border-b-2 border-l-2 border-cyan-400/60" />
              <div className="absolute right-3 bottom-3 h-8 w-8 rounded-br border-r-2 border-b-2 border-cyan-400/60" />
            </div>
          </>
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-900">
            {status === 'connecting' ? (
              <>
                <Loader2 className="mb-3 h-10 w-10 animate-spin text-slate-400" />
                <p className="text-sm text-slate-400">Connecting to server...</p>
              </>
            ) : status === 'connected' && !isPhoneConnected ? (
              <>
                <CameraOff className="mb-3 h-10 w-10 text-slate-500" />
                <p className="mb-1 text-sm text-slate-300">Waiting for phone camera</p>
                <p className="text-xs text-slate-500">
                  Open{' '}
                  <code className="rounded bg-slate-800 px-1.5 py-0.5 text-cyan-400">/camera</code>{' '}
                  on your phone
                </p>
              </>
            ) : (
              <>
                <WifiOff className="mb-3 h-10 w-10 text-slate-500" />
                <p className="mb-3 text-sm text-slate-300">Not connected</p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={connect}
                  className="border-slate-600 text-white hover:bg-slate-800"
                >
                  Connect
                </Button>
              </>
            )}
          </div>
        )}
      </div>

      {/* Capture Controls */}
      <div className="mt-4 flex items-center gap-3">
        <Button
          size="lg"
          className={cn(
            'h-12 flex-1 font-semibold transition-all',
            canCapture
              ? 'bg-blue-600 text-white shadow-sm hover:bg-blue-700'
              : 'cursor-not-allowed bg-slate-100 text-slate-400',
          )}
          disabled={!canCapture}
          onClick={handleCaptureFromCamera}
        >
          <Camera className="mr-2 h-5 w-5" />
          {canCapture ? 'Capture Image' : 'Camera Not Connected'}
        </Button>

        <Button
          size="lg"
          className={cn(
            'h-12 border-2 px-4 shadow-md',
            status === 'connected'
              ? 'border-emerald-400 bg-emerald-100 hover:bg-emerald-200'
              : 'border-slate-500 bg-slate-200 hover:bg-slate-300',
          )}
          onClick={status === 'connected' ? disconnect : connect}
          title={status === 'connected' ? 'Disconnect' : 'Connect'}
        >
          {status === 'connected' ? (
            <Wifi className="h-5 w-5 text-emerald-700" />
          ) : (
            <WifiOff className="h-5 w-5 text-slate-700" />
          )}
        </Button>
      </div>
    </div>
  )
}
