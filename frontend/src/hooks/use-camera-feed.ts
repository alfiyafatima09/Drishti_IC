import { useState, useEffect, useRef, useCallback } from 'react';
import { getWsUrl, API_BASE } from '@/lib/config';
import type { ScanResult, CaptureType, CaptureResponse } from '@/types/api';

// Re-export types for convenience
export type { ScanResult, CaptureType };

export type CameraStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface CaptureResult {
  result: ScanResult;
  imageUrl: string;
}

export interface UseCameraFeedReturn {
  // Connection state
  status: CameraStatus;
  isPhoneConnected: boolean;
  
  // Frame state
  currentFrame: string | null;
  frameCount: number;
  
  // Actions
  connect: () => void;
  disconnect: () => void;
  captureFrame: (type: CaptureType, scanId?: string) => Promise<CaptureResult | null>;
  
  // Capture state
  isCapturing: boolean;
  lastScanResult: ScanResult | null;
  capturedImage: string | null;
}

export function useCameraFeed(): UseCameraFeedReturn {
  // Connection state
  const [status, setStatus] = useState<CameraStatus>('disconnected');
  const [isPhoneConnected, setIsPhoneConnected] = useState(false);
  
  // Frame state
  const [currentFrame, setCurrentFrame] = useState<string | null>(null);
  const [frameCount, setFrameCount] = useState(0);
  
  // Capture state
  const [isCapturing, setIsCapturing] = useState(false);
  const [lastScanResult, setLastScanResult] = useState<ScanResult | null>(null);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  
  // Refs for cleanup
  const wsRef = useRef<WebSocket | null>(null);
  const frameUrlRef = useRef<string | null>(null);
  const capturedImageRef = useRef<string | null>(null);

  /**
   * Connect to the WebSocket camera feed
   */
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus('connecting');
    
    const wsUrl = `${getWsUrl()}/api/v1/camera/feed`;
    console.log('[Camera] Connecting to WebSocket:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[Camera] WebSocket connected');
      setStatus('connected');
      // Identify as desktop client
      ws.send(JSON.stringify({ type: 'identify', client: 'desktop' }));
    };

    ws.onmessage = (event) => {
      if (event.data instanceof Blob) {
        // Binary frame data from phone camera
        if (frameUrlRef.current) {
          URL.revokeObjectURL(frameUrlRef.current);
        }
        
        const url = URL.createObjectURL(event.data);
        frameUrlRef.current = url;
        setCurrentFrame(url);
        setFrameCount((prev) => prev + 1);
      } else {
        // JSON message (events from server)
        try {
          const data = JSON.parse(event.data);
          console.log('[Camera] WebSocket event:', data);
          
          if (data.event === 'CAMERA_CONNECTED') {
            setIsPhoneConnected(true);
          } else if (data.event === 'CAMERA_DISCONNECTED') {
            setIsPhoneConnected(false);
            setCurrentFrame(null);
          }
        } catch (e) {
          console.error('[Camera] Failed to parse WebSocket message:', e);
        }
      }
    };

    ws.onclose = () => {
      console.log('[Camera] WebSocket disconnected');
      setStatus('disconnected');
      setIsPhoneConnected(false);
      wsRef.current = null;
    };

    ws.onerror = (error) => {
      console.error('[Camera] WebSocket error:', error);
      setStatus('error');
    };
  }, []);

  /**
   * Disconnect from the WebSocket
   */
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStatus('disconnected');
    setIsPhoneConnected(false);
    setCurrentFrame(null);
  }, []);

  /**
   * Capture current frame and send for analysis
   */
  const captureFrame = useCallback(async (
    type: CaptureType, 
    scanId?: string
  ): Promise<CaptureResult | null> => {
    if (!isPhoneConnected || !currentFrame) {
      console.error('[Camera] Cannot capture: phone not connected or no frame available');
      return null;
    }

    setIsCapturing(true);

    try {
      // 1. Create a copy of the current frame
      const frameResponse = await fetch(currentFrame);
      const frameBlob = await frameResponse.blob();
      
      // 2. Create persistent URL for captured image preview
      if (capturedImageRef.current) {
        URL.revokeObjectURL(capturedImageRef.current);
      }
      const capturedUrl = URL.createObjectURL(frameBlob);
      capturedImageRef.current = capturedUrl;
      setCapturedImage(capturedUrl);

      // 3. Call capture endpoint to notify backend
      const captureResponse = await fetch(`${API_BASE}/camera/capture`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          capture_type: type,
          scan_id: scanId,
        }),
      });

      if (!captureResponse.ok) {
        const errorText = await captureResponse.text();
        throw new Error(`Capture failed: ${errorText}`);
      }

      const captureData: CaptureResponse = await captureResponse.json();
      console.log('[Camera] Capture response:', captureData);

      // 4. Send image to scan endpoint
      const formData = new FormData();
      formData.append('file', frameBlob, 'capture.jpg');

      const scanUrl = type === 'BOTTOM' && scanId 
        ? `${API_BASE}/scan/${scanId}/bottom`
        : `${API_BASE}/scan`;

      const scanResponse = await fetch(scanUrl, {
        method: 'POST',
        body: formData,
      });

      if (!scanResponse.ok) {
        const errorText = await scanResponse.text();
        throw new Error(`Scan failed: ${errorText}`);
      }

      const scanResult: ScanResult = await scanResponse.json();
      console.log('[Camera] Scan result:', scanResult);
      
      setLastScanResult(scanResult);
      
      return { result: scanResult, imageUrl: capturedUrl };

    } catch (error) {
      console.error('[Camera] Capture/scan error:', error);
      return null;
    } finally {
      setIsCapturing(false);
    }
  }, [isPhoneConnected, currentFrame]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (frameUrlRef.current) {
        URL.revokeObjectURL(frameUrlRef.current);
      }
      if (capturedImageRef.current) {
        URL.revokeObjectURL(capturedImageRef.current);
      }
    };
  }, []);

  return {
    status,
    isPhoneConnected,
    currentFrame,
    frameCount,
    connect,
    disconnect,
    captureFrame,
    isCapturing,
    lastScanResult,
    capturedImage,
  };
}
