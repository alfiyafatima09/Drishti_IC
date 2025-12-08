import { useEffect } from 'react';
import { Camera, CameraOff, Wifi, WifiOff, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useCameraFeed, type CameraStatus } from '@/hooks/use-camera-feed';

interface VideoFeedProps {
  onCapture?: (imageUrl: string) => void;
}

const STATUS_CONFIG: Record<CameraStatus, { 
  label: string; 
  color: string; 
  dotColor: string;
  icon: typeof Wifi 
}> = {
  disconnected: { label: 'Disconnected', color: 'text-slate-500', dotColor: 'bg-slate-400', icon: WifiOff },
  connecting: { label: 'Connecting', color: 'text-amber-600', dotColor: 'bg-amber-500', icon: Wifi },
  connected: { label: 'Connected', color: 'text-emerald-600', dotColor: 'bg-emerald-500', icon: Wifi },
  error: { label: 'Error', color: 'text-red-600', dotColor: 'bg-red-500', icon: WifiOff },
};

export function VideoFeed({ onCapture }: VideoFeedProps) {
  const {
    status,
    isPhoneConnected,
    currentFrame,
    frameCount,
    connect,
    disconnect,
  } = useCameraFeed();

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

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

  const canCapture = isPhoneConnected && currentFrame;
  const statusInfo = STATUS_CONFIG[status];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center">
            <Camera className="w-5 h-5 text-slate-600" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Live Camera</h2>
            <p className="text-xs text-slate-500">Phone AOI Feed</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Status Indicator */}
          <div className="flex items-center gap-2">
            <span className={cn('w-2 h-2 rounded-full', statusInfo.dotColor, status === 'connecting' && 'animate-pulse')} />
            <span className={cn('text-xs font-medium', statusInfo.color)}>
              {isPhoneConnected ? 'Phone Connected' : statusInfo.label}
            </span>
          </div>

          {/* Frame Counter */}
          {isPhoneConnected && (
            <span className="text-xs font-mono text-slate-400 bg-slate-100 px-2 py-1 rounded">
              {frameCount.toLocaleString()} frames
            </span>
          )}
        </div>
      </div>

      {/* Video Container */}
      <div className="relative aspect-video rounded-lg overflow-hidden bg-slate-900 border border-slate-200">
        {currentFrame ? (
          <>
            <img
              src={currentFrame}
              alt="Camera feed"
              className="absolute inset-0 w-full h-full object-contain"
            />
            {/* Subtle scan overlay */}
            <div className="absolute inset-0 pointer-events-none">
              <div className="absolute top-3 left-3 w-8 h-8 border-l-2 border-t-2 border-cyan-400/60 rounded-tl" />
              <div className="absolute top-3 right-3 w-8 h-8 border-r-2 border-t-2 border-cyan-400/60 rounded-tr" />
              <div className="absolute bottom-3 left-3 w-8 h-8 border-l-2 border-b-2 border-cyan-400/60 rounded-bl" />
              <div className="absolute bottom-3 right-3 w-8 h-8 border-r-2 border-b-2 border-cyan-400/60 rounded-br" />
            </div>
          </>
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-900">
            {status === 'connecting' ? (
              <>
                <Loader2 className="w-10 h-10 text-slate-400 animate-spin mb-3" />
                <p className="text-sm text-slate-400">Connecting to server...</p>
              </>
            ) : status === 'connected' && !isPhoneConnected ? (
              <>
                <CameraOff className="w-10 h-10 text-slate-500 mb-3" />
                <p className="text-sm text-slate-300 mb-1">Waiting for phone camera</p>
                <p className="text-xs text-slate-500">
                  Open <code className="px-1.5 py-0.5 rounded bg-slate-800 text-cyan-400">/camera</code> on your phone
                </p>
              </>
            ) : (
              <>
                <WifiOff className="w-10 h-10 text-slate-500 mb-3" />
                <p className="text-sm text-slate-300 mb-3">Not connected</p>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={connect}
                  className="text-white border-slate-600 hover:bg-slate-800"
                >
                  Connect
                </Button>
              </>
            )}
          </div>
        )}
      </div>

      {/* Capture Controls */}
      <div className="flex items-center gap-3 mt-4">
        <Button
          size="lg"
          className={cn(
            "flex-1 h-12 font-semibold transition-all",
            canCapture 
              ? "bg-blue-600 hover:bg-blue-700 text-white shadow-sm" 
              : "bg-slate-100 text-slate-400 cursor-not-allowed"
          )}
          disabled={!canCapture}
          onClick={handleCaptureFromCamera}
        >
          <Camera className="w-5 h-5 mr-2" />
          {canCapture ? 'Capture Image' : 'Camera Not Connected'}
        </Button>

        <Button
          size="lg"
          className={cn(
            "h-12 px-4 border-2 shadow-md",
            status === 'connected' 
              ? "bg-emerald-100 border-emerald-400 hover:bg-emerald-200" 
              : "bg-slate-200 border-slate-500 hover:bg-slate-300"
          )}
          onClick={status === 'connected' ? disconnect : connect}
          title={status === 'connected' ? 'Disconnect' : 'Connect'}
        >
          {status === 'connected' ? (
            <Wifi className="w-5 h-5 text-emerald-700" />
          ) : (
            <WifiOff className="w-5 h-5 text-slate-700" />
          )}
        </Button>
      </div>
    </div>
  );
}
