import { useEffect, useRef, useState } from 'react';
import { Camera, CameraOff, Wifi, WifiOff, Loader2, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { useCameraFeed, type CameraStatus } from '@/hooks/use-camera-feed';
import { API_BASE } from '@/lib/config';
import type { ScanResult } from '@/types/api';

// ============================================================
// TYPES
// ============================================================

interface VideoFeedProps {
  /** Called when an image is captured (immediately for preview) */
  onCapture?: (scanId: string, imageUrl: string) => void;
  /** Called when scan result is received from backend */
  onScanResult?: (result: ScanResult) => void;
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

export function VideoFeed({ onCapture, onScanResult }: VideoFeedProps) {
  const {
    status,
    isPhoneConnected,
    currentFrame,
    frameCount,
    connect,
    disconnect,
    captureFrame,
    isCapturing: isCameraCapturing,
    lastScanResult,
  } = useCameraFeed();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);

  // Auto-connect to WebSocket on mount
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  // Notify parent when scan result changes
  useEffect(() => {
    if (lastScanResult && onScanResult) {
      onScanResult(lastScanResult);
    }
  }, [lastScanResult, onScanResult]);

  /**
   * Capture from live camera feed
   */
  const handleCaptureFromCamera = async () => {
    // Show preview immediately (optimistic UI)
    if (currentFrame && onCapture) {
      try {
        const response = await fetch(currentFrame);
        const blob = await response.blob();
        const imageUrl = URL.createObjectURL(blob);
        onCapture('pending', imageUrl);
      } catch (e) {
        console.error('[VideoFeed] Failed to create preview:', e);
      }
    }

    // Perform actual capture and scan
    const data = await captureFrame('TOP');
    if (data) {
      onCapture?.(data.result.scan_id, data.imageUrl);
      onScanResult?.(data.result);
    }
  };

  /**
   * Upload file for testing (when no camera connected)
   */
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    
    // Create preview immediately
    const imageUrl = URL.createObjectURL(file);
    onCapture?.('pending', imageUrl);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/scan`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        console.error('[VideoFeed] Scan failed:', response.status, await response.text());
        return;
      }

      const scanResult: ScanResult = await response.json();
      console.log('[VideoFeed] Scan result:', scanResult);

      onCapture?.(scanResult.scan_id, imageUrl);
      onScanResult?.(scanResult);
    } catch (error) {
      console.error('[VideoFeed] Upload error:', error);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const isCapturing = isCameraCapturing || isUploading;
  const StatusIcon = STATUS_CONFIG[status].icon;
  const canCapture = isPhoneConnected && currentFrame;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-zinc-900">
            <Camera className="w-5 h-5 text-zinc-400" />
          </div>
          <div>
            <h2 className="text-sm font-medium text-zinc-100">Live Camera Feed</h2>
            <p className="text-xs text-zinc-500">Phone AOI Simulator</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Connection Status */}
          <Badge
            variant="outline"
            className={cn(
              'gap-1.5 px-2.5 py-1 border-zinc-800 bg-zinc-900/50',
              status === 'connected' && isPhoneConnected && 'border-emerald-800 bg-emerald-950/30'
            )}
          >
            <span
              className={cn(
                'w-1.5 h-1.5 rounded-full',
                STATUS_CONFIG[status].color,
                status === 'connecting' && 'animate-pulse'
              )}
            />
            <span className="text-xs">
              {isPhoneConnected ? 'Phone Connected' : STATUS_CONFIG[status].label}
            </span>
          </Badge>

          {/* Frame Counter */}
          {isPhoneConnected && (
            <Badge variant="outline" className="px-2.5 py-1 border-zinc-800 bg-zinc-900/50 font-mono">
              {frameCount.toLocaleString()} frames
            </Badge>
          )}
        </div>
      </div>

      {/* Video Container - Fixed 16:9 aspect ratio */}
      <div className="relative aspect-video rounded-xl overflow-hidden bg-zinc-950 border border-zinc-800 shrink-0">
        {currentFrame ? (
          <img
            src={currentFrame}
            alt="Camera feed"
            className="absolute inset-0 w-full h-full object-contain"
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
            {status === 'connecting' ? (
              <>
                <Loader2 className="w-12 h-12 text-zinc-600 animate-spin" />
                <p className="text-sm text-zinc-500">Connecting to server...</p>
              </>
            ) : status === 'connected' && !isPhoneConnected ? (
              <>
                <CameraOff className="w-12 h-12 text-zinc-600" />
                <div className="text-center">
                  <p className="text-sm text-zinc-400">Waiting for phone camera</p>
                  <p className="text-xs text-zinc-600 mt-1">
                    Open <code className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">/camera</code> on your phone
                  </p>
                </div>
              </>
            ) : (
              <>
                <WifiOff className="w-12 h-12 text-zinc-600" />
                <div className="text-center">
                  <p className="text-sm text-zinc-400">Not connected to server</p>
                  <Button variant="outline" size="sm" onClick={connect} className="mt-3">
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
            <div className="absolute top-4 left-4 w-12 h-12 border-l-2 border-t-2 border-emerald-500/60" />
            <div className="absolute top-4 right-4 w-12 h-12 border-r-2 border-t-2 border-emerald-500/60" />
            <div className="absolute bottom-4 left-4 w-12 h-12 border-l-2 border-b-2 border-emerald-500/60" />
            <div className="absolute bottom-4 right-4 w-12 h-12 border-r-2 border-b-2 border-emerald-500/60" />

            {/* Center crosshair */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
              <div className="w-16 h-16 border border-emerald-500/30 rounded-lg" />
              <div className="absolute top-1/2 left-0 w-full h-px bg-emerald-500/20" />
              <div className="absolute top-0 left-1/2 w-px h-full bg-emerald-500/20" />
            </div>
          </div>
        )}

        {/* Capturing Overlay */}
        {isCapturing && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center backdrop-blur-sm">
            <div className="flex flex-col items-center gap-3 p-6 rounded-xl bg-zinc-900/90 border border-zinc-800">
              <Loader2 className="w-8 h-8 text-emerald-500 animate-spin" />
              <p className="text-sm text-zinc-300">Analyzing IC...</p>
            </div>
          </div>
        )}
      </div>

      {/* Capture Controls */}
      <div className="flex items-center gap-3 mt-4 shrink-0">
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileUpload}
          className="hidden"
        />

        {canCapture ? (
          <Button
            size="lg"
            className="flex-1 h-12 bg-emerald-600 hover:bg-emerald-700 text-white font-medium"
            disabled={isCapturing}
            onClick={handleCaptureFromCamera}
          >
            {isCapturing ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Camera className="w-5 h-5 mr-2" />
                Capture & Analyze
              </>
            )}
          </Button>
        ) : (
          <Button
            size="lg"
            className="flex-1 h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium"
            disabled={isCapturing}
            onClick={() => fileInputRef.current?.click()}
          >
            {isCapturing ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Upload className="w-5 h-5 mr-2" />
                Upload Image to Analyze
              </>
            )}
          </Button>
        )}

        <Button
          variant="outline"
          size="lg"
          className="h-12 px-4"
          onClick={status === 'connected' ? disconnect : connect}
          title={status === 'connected' ? 'Disconnect' : 'Connect'}
        >
          <StatusIcon className="w-5 h-5" />
        </Button>
      </div>
    </div>
  );
}
