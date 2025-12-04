import { useEffect } from 'react';
import { Camera, CameraOff, Wifi, WifiOff, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { useCameraFeed, type CameraStatus } from '@/hooks/use-camera-feed';

// ============================================================
// TYPES
// ============================================================

interface VideoFeedProps {
  /** Called when an image is captured */
  onCapture?: (imageUrl: string) => void;
}

// ============================================================
// CONSTANTS
// ============================================================

const STATUS_CONFIG: Record<CameraStatus, { 
  label: string; 
  color: string; 
  icon: typeof Wifi 
}> = {
  disconnected: { label: 'Disconnected', color: 'bg-zinc-500', icon: WifiOff },
  connecting: { label: 'Connecting...', color: 'bg-amber-500', icon: Wifi },
  connected: { label: 'Connected', color: 'bg-emerald-500', icon: Wifi },
  error: { label: 'Error', color: 'bg-red-500', icon: WifiOff },
};

// ============================================================
// COMPONENT
// ============================================================

export function VideoFeed({ onCapture }: VideoFeedProps) {
  const {
    status,
    isPhoneConnected,
    currentFrame,
    frameCount,
    connect,
    disconnect,
  } = useCameraFeed();

  // Auto-connect to WebSocket on mount
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  /**
   * Capture from live camera feed - just capture the image
   */
  const handleCaptureFromCamera = async () => {
    if (currentFrame && onCapture) {
      try {
        const response = await fetch(currentFrame);
        const blob = await response.blob();
        const imageUrl = URL.createObjectURL(blob);
        onCapture(imageUrl);
      } catch (e) {
        console.error('[VideoFeed] Failed to create preview:', e);
      }
    }
  };

  const StatusIcon = STATUS_CONFIG[status].icon;
  const canCapture = isPhoneConnected && currentFrame;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-600 shadow-lg">
            <Camera className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">Live Camera Feed</h2>
            <p className="text-sm text-blue-600 font-medium">Phone AOI Simulator</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Connection Status */}
          <Badge
            className={cn(
              'gap-1.5 px-3 py-1.5 border-2 font-semibold',
              status === 'connected' && isPhoneConnected 
                ? 'bg-emerald-500 border-emerald-600 text-white' 
                : 'bg-slate-100 border-slate-300 text-slate-700'
            )}
          >
            <span
              className={cn(
                'w-2 h-2 rounded-full',
                status === 'connected' && isPhoneConnected ? 'bg-white' : 'bg-slate-400',
                status === 'connecting' && 'animate-pulse'
              )}
            />
            <span className="text-xs font-bold">
              {isPhoneConnected ? 'Connected' : STATUS_CONFIG[status].label}
            </span>
          </Badge>

          {/* Frame Counter */}
          {isPhoneConnected && (
            <Badge className="px-3 py-1.5 bg-blue-500 border-2 border-blue-600 text-white font-mono font-bold shadow-md">
              {frameCount.toLocaleString()} frames
            </Badge>
          )}
        </div>
      </div>

      {/* Video Container - Fixed 16:9 aspect ratio */}
      <div className="relative aspect-video rounded-xl overflow-hidden bg-slate-900 border-4 border-blue-400 shrink-0 shadow-2xl">
        {currentFrame ? (
          <img
            src={currentFrame}
            alt="Camera feed"
            className="absolute inset-0 w-full h-full object-contain"
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-gradient-to-br from-slate-800 to-slate-900">
            {status === 'connecting' ? (
              <>
                <Loader2 className="w-16 h-16 text-blue-400 animate-spin" />
                <p className="text-base font-semibold text-white">Connecting to server...</p>
              </>
            ) : status === 'connected' && !isPhoneConnected ? (
              <>
                <CameraOff className="w-16 h-16 text-cyan-400" />
                <div className="text-center">
                  <p className="text-base font-semibold text-white">Waiting for phone camera</p>
                  <p className="text-sm text-cyan-300 mt-2 font-medium">
                    Open <code className="px-2 py-1 rounded bg-cyan-900 text-cyan-200 font-bold">/camera</code> on your phone
                  </p>
                </div>
              </>
            ) : (
              <>
                <WifiOff className="w-16 h-16 text-slate-400" />
                <div className="text-center">
                  <p className="text-base font-semibold text-white">Not connected to server</p>
                  <Button variant="outline" size="sm" onClick={connect} className="mt-3 bg-blue-600 text-white border-blue-500 hover:bg-blue-700 font-bold">
                    Connect
                  </Button>
                </div>
              </>
            )}
          </div>
        )}

        {/* Scanning Overlay */}
        {currentFrame && (
          <div className="absolute inset-0 pointer-events-none">
            {/* Corner brackets */}
            <div className="absolute top-4 left-4 w-16 h-16 border-l-4 border-t-4 border-cyan-400 rounded-tl-lg" />
            <div className="absolute top-4 right-4 w-16 h-16 border-r-4 border-t-4 border-cyan-400 rounded-tr-lg" />
            <div className="absolute bottom-4 left-4 w-16 h-16 border-l-4 border-b-4 border-cyan-400 rounded-bl-lg" />
            <div className="absolute bottom-4 right-4 w-16 h-16 border-r-4 border-b-4 border-cyan-400 rounded-br-lg" />

            {/* Center crosshair */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
              <div className="w-20 h-20 border-2 border-cyan-400 rounded-lg shadow-lg shadow-cyan-500/50" />
              <div className="absolute top-1/2 left-0 w-full h-0.5 bg-cyan-400/40" />
              <div className="absolute top-0 left-1/2 w-0.5 h-full bg-cyan-400/40" />
            </div>
          </div>
        )}

      </div>

      {/* Capture Controls */}
      <div className="flex items-center gap-3 mt-4 shrink-0">
        <Button
          size="lg"
          className={cn(
            "flex-1 h-14 text-white font-bold shadow-xl text-base",
            canCapture 
              ? "bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 hover:from-emerald-600 hover:via-teal-600 hover:to-cyan-600" 
              : "bg-slate-400 cursor-not-allowed"
          )}
          disabled={!canCapture}
          onClick={handleCaptureFromCamera}
        >
          <Camera className="w-6 h-6 mr-2" />
          {canCapture ? 'Capture from Camera' : 'Camera Not Connected'}
        </Button>

        <Button
          size="lg"
          className="h-14 px-5 border-2 border-blue-500 hover:bg-blue-50 shadow-lg bg-white"
          onClick={status === 'connected' ? disconnect : connect}
          title={status === 'connected' ? 'Disconnect' : 'Connect'}
        >
          <StatusIcon className={cn("w-6 h-6", status === 'connected' ? 'text-blue-600' : 'text-slate-500')} />
        </Button>
      </div>
    </div>
  );
}
