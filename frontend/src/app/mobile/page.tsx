'use client';

import { useEffect, useRef, useState } from 'react';
import { apiRequest } from '@/api/client';
import { API_ENDPOINTS, WS_BASE_URL } from '@/lib/config';
import { WebSocketClient } from '@/lib/websocket';
import { useToast } from '@/hooks/use-toast';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Video, Square, Loader2, AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

export default function MobilePage() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cameraAvailable, setCameraAvailable] = useState<boolean | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const wsRef = useRef<WebSocketClient | null>(null);
  const { toast } = useToast();

  const frameIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Check camera availability on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const checkCamera = async () => {
        const nav = navigator as any;
        const hasModernAPI = nav.mediaDevices && typeof nav.mediaDevices.getUserMedia === 'function';
        const hasLegacyAPI = typeof nav.getUserMedia === 'function' ||
                           typeof nav.webkitGetUserMedia === 'function' ||
                           typeof nav.mozGetUserMedia === 'function' ||
                           typeof nav.msGetUserMedia === 'function';

        const apiExists = hasModernAPI || hasLegacyAPI;
        let actuallyAvailable = false;

        // Try a quick camera access test (this will fail on HTTP for security)
        if (apiExists) {
          try {
            // Request camera access with minimal constraints for testing
            const testStream = await navigator.mediaDevices.getUserMedia({
              video: { width: 1, height: 1 },
              audio: false
            });
            // If we get here, camera is accessible
            actuallyAvailable = true;
            // Clean up the test stream
            testStream.getTracks().forEach(track => track.stop());
          } catch (error: any) {
            // Camera exists but access failed (likely HTTPS/security requirement)
            console.log('Camera API exists but access failed:', error.name, error.message);
            // We'll still show it as available - the real error will come when user tries to start
            actuallyAvailable = true;
          }
        }

        setCameraAvailable(actuallyAvailable);

        // Debug info
        console.log('Camera API check:', {
          apiExists,
          hasModernAPI,
          hasLegacyAPI,
          actuallyAvailable,
          protocol: window.location.protocol,
          hostname: window.location.hostname,
          isLocalhost: window.location.hostname === 'localhost' || window.location.hostname.startsWith('127.'),
          userAgent: navigator.userAgent.substring(0, 100) + '...'
        });

        // Show warning for HTTP + non-localhost
        if (actuallyAvailable && window.location.protocol === 'http:' &&
            window.location.hostname !== 'localhost' && !window.location.hostname.startsWith('127.')) {
          console.warn('⚠️  Camera access may require HTTPS. For mobile testing, use: make frontend-ngrok');
        }
      };
      checkCamera();
    }
  }, []);

  const stopCamera = () => {
    if (frameIntervalRef.current) {
      clearInterval(frameIntervalRef.current);
      frameIntervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.disconnect();
      wsRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsStreaming(false);
    setSessionId(null);
    toast({
      title: 'Stream Stopped',
      description: 'Camera stream disconnected',
    });
  };

  const startCamera = async () => {
    try {
      setError(null);
      
      // Check if getUserMedia is available
      if (typeof window === 'undefined') {
        throw new Error('Camera access requires a browser environment.');
      }
      
      // Get getUserMedia with comprehensive browser compatibility
      const nav = navigator as any;
      let getUserMedia: (constraints: MediaStreamConstraints) => Promise<MediaStream>;
      
      // Check for modern API first (Safari 11+, Chrome, Firefox)
      if (nav.mediaDevices && typeof nav.mediaDevices.getUserMedia === 'function') {
        getUserMedia = nav.mediaDevices.getUserMedia.bind(nav.mediaDevices);
      }
      // Legacy API (older Safari, etc.)
      else if (typeof nav.getUserMedia === 'function') {
        getUserMedia = (constraints: MediaStreamConstraints) => {
          return new Promise((resolve, reject) => {
            nav.getUserMedia(constraints, resolve, reject);
          });
        };
      }
      // WebKit prefix (very old Safari)
      else if (typeof nav.webkitGetUserMedia === 'function') {
        getUserMedia = (constraints: MediaStreamConstraints) => {
          return new Promise((resolve, reject) => {
            nav.webkitGetUserMedia(constraints, resolve, reject);
          });
        };
      }
      // Mozilla prefix (very old Firefox)
      else if (typeof nav.mozGetUserMedia === 'function') {
        getUserMedia = (constraints: MediaStreamConstraints) => {
          return new Promise((resolve, reject) => {
            nav.mozGetUserMedia(constraints, resolve, reject);
          });
        };
      }
      // MS prefix (old IE/Edge)
      else if (typeof nav.msGetUserMedia === 'function') {
        getUserMedia = (constraints: MediaStreamConstraints) => {
          return new Promise((resolve, reject) => {
            nav.msGetUserMedia(constraints, resolve, reject);
          });
        };
      }
      // If none available, provide helpful error
      else {
        const browserInfo = {
          userAgent: navigator.userAgent,
          hasMediaDevices: !!nav.mediaDevices,
          hasGetUserMedia: typeof nav.getUserMedia === 'function',
          hasWebkitGetUserMedia: typeof nav.webkitGetUserMedia === 'function',
          protocol: window.location.protocol,
          hostname: window.location.hostname,
        };
        
        console.error('Camera API not found. Browser info:', browserInfo);
        
        let errorMsg = 'Camera access is not available. ';

        if (browserInfo.protocol === 'http:' && browserInfo.hostname !== 'localhost' && !browserInfo.hostname.startsWith('127.')) {
          errorMsg += 'For security reasons, most browsers require HTTPS for camera access when not on localhost. ';
          errorMsg += 'Try accessing via localhost, or use ngrok for HTTPS tunnel: `make frontend-ngrok`. ';
        } else {
          errorMsg += 'Please ensure you are using a modern browser (Safari, Chrome, Firefox) and have granted camera permissions. ';
          if (browserInfo.protocol === 'http:') {
            errorMsg += 'If using Safari, you may need to enable "Allow Camera Access on Insecure Sites" in Safari settings.';
          }
        }

        throw new Error(errorMsg);
      }
      
      // Request camera access with Safari-compatible constraints
      const constraints: MediaStreamConstraints = {
        video: {
          facingMode: 'environment', // Use back camera on mobile
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      };
      
      // For older Safari, try simpler constraints if facingMode fails
      let stream: MediaStream;
      try {
        stream = await getUserMedia(constraints);
      } catch (err: any) {
        // If facingMode fails, try without it (Safari compatibility)
        if (err.name === 'OverconstrainedError' || err.name === 'ConstraintNotSatisfiedError') {
          const fallbackConstraints: MediaStreamConstraints = {
            video: true,
            audio: false,
          };
          stream = await getUserMedia(fallbackConstraints);
        } else {
          throw err;
        }
      }

      streamRef.current = stream;
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }

      // Start video session
      const response = await apiRequest<{
        session_id: string;
        stream_url: string;
        ingest_ws_path: string;
      }>(
        API_ENDPOINTS.videoSessionStart,
        { method: 'POST' }
      );

      setSessionId(response.session_id);
      setIsStreaming(true);

      // Connect WebSocket for sending frames
      const wsUrl = `${WS_BASE_URL}${response.ingest_ws_path}`;
      console.log('📡 API Base URL:', API_ENDPOINTS.videoSessionStart);
      console.log('📡 WebSocket URL:', wsUrl);
      console.log('📡 Current window location:', window.location.href);
      
      const ws = new WebSocketClient(wsUrl);
      wsRef.current = ws;

          ws.on('connected', () => {
            console.log('📡 WebSocket connected to backend');
            setWsConnected(true);
            setError(null);
            toast({
              title: 'Connected',
              description: 'Streaming to dashboard',
            });
          });

          ws.on('error', (data: { message: string }) => {
            console.error('📡 WebSocket error:', data.message);
            setWsConnected(false);
            const errorMsg = `Connection failed: ${data.message}. Make sure backend is running on the same network.`;
            setError(errorMsg);
            toast({
              title: 'Connection Error',
              description: errorMsg,
              variant: 'destructive',
            });
          });

          ws.on('disconnected', () => {
            console.log('📡 WebSocket disconnected from backend');
            setWsConnected(false);
            toast({
              title: 'Disconnected',
              description: 'Lost connection to dashboard',
              variant: 'destructive',
            });
          });

      await ws.connect();

      // Send frames periodically
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const sendFrame = () => {
        if (videoRef.current && ctx && ws.isConnected()) {
          canvas.width = videoRef.current.videoWidth;
          canvas.height = videoRef.current.videoHeight;
          ctx.drawImage(videoRef.current, 0, 0);
          const frameData = canvas.toDataURL('image/jpeg', 0.8).split(',')[1];
          ws.send({ type: 'frame', data: frameData });
        }
      };

      frameIntervalRef.current = setInterval(sendFrame, 100); // 10 FPS

    } catch (err: any) {
      setError(err.message || 'Failed to start camera');
      toast({
        title: 'Camera Error',
        description: err.message || 'Failed to access camera',
        variant: 'destructive',
      });
    }
  };

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  return (
    <div className="container mx-auto p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Mobile Camera</h1>
          <p className="text-muted-foreground">Stream IC images to dashboard</p>
        </div>
        {!isStreaming ? (
          <Button onClick={startCamera} className="gap-2">
            <Video className="h-4 w-4" />
            Start Camera
          </Button>
        ) : (
          <Button onClick={stopCamera} variant="destructive" className="gap-2">
            <Square className="h-4 w-4" />
            Stop Camera
          </Button>
        )}
      </div>

      {/* Browser Extension Warning */}
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          <strong>Important:</strong> If you see CORS errors about external URLs (like dudley-eds-88977.herokuapp.com),
          they&apos;re from browser extensions, not our app. Disable workplace/company extensions for testing.
          <br />
          <em>Tip: Try Incognito/Private mode to test without extensions.</em>
        </AlertDescription>
      </Alert>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
            <CardHeader>
              <CardTitle>Camera Preview</CardTitle>
              <CardDescription>
                {isStreaming
                  ? `Streaming to dashboard - point camera at IC component ${wsConnected ? '🟢 Connected' : '🔴 Connecting...'}`
                  : 'Start camera to begin streaming'}
              </CardDescription>
            </CardHeader>
        <CardContent>
          <div className="relative aspect-video bg-black rounded-lg overflow-hidden">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-contain"
            />
            {!isStreaming && (
              <div className="absolute inset-0 flex items-center justify-center text-white">
                <div className="text-center">
                  <Video className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>Camera not active</p>
                </div>
              </div>
            )}
            {isStreaming && !videoRef.current?.srcObject && (
              <div className="absolute inset-0 flex items-center justify-center text-white">
                <div className="text-center">
                  <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2" />
                  <p>Initializing camera...</p>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {isStreaming && sessionId && (
        <Card>
          <CardHeader>
            <CardTitle>Stream Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 bg-green-600 rounded-full animate-pulse" />
                <span className="text-sm">Streaming active</span>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Session ID</p>
                <p className="font-mono text-xs">{sessionId}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

