/* eslint-disable @next/next/no-img-element */
'use client';

import { useEffect, useState, useRef } from 'react';
import { Container } from '@/components/layout/container';
import { PageHeader } from '@/components/layout/page-header';
import { VideoFeed } from '@/components/features/dashboard/video-feed';
import { SessionInfo } from '@/components/features/dashboard/session-info';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Play, Square, RefreshCw, AlertCircle } from 'lucide-react';
import { ApiService } from '@/services/api.service';
import { WS_BASE_URL } from '@/lib/config';
import { WebSocketClient } from '@/lib/websocket';
import { useToast } from '@/hooks/use-toast';

type ActiveSessionResponse = {
  active: boolean;
  session_id?: string;
  viewer_ws_path?: string;
  started_at?: string | null;
};

export default function DashboardPage() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [frameSrc, setFrameSrc] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const wsRef = useRef<WebSocketClient | null>(null);
  const { toast } = useToast();

  const connectToStream = async (silent = false) => {
    try {
      setIsConnecting(true);
      if (!silent) {
        setError(null);
      }

      if (wsRef.current) {
        wsRef.current.disconnect();
        wsRef.current = null;
      }

      const active = await ApiService.videoSession.getActiveSession();

      if (!active.active || !active.session_id || !active.viewer_ws_path) {
        if (!silent) {
          setError('No active mobile stream. Start streaming from /mobile.');
          toast({
            title: 'No Active Stream',
            description: 'Start the camera from the mobile page to stream.',
            variant: 'destructive',
          });
        }
        setIsStreaming(false);
        setSessionId(null);
        return;
      }

      const wsUrl = `${WS_BASE_URL}${active.viewer_ws_path}`;
      const ws = new WebSocketClient(wsUrl);
      wsRef.current = ws;

      ws.on('connected', () => {
        setIsStreaming(true);
        setSessionId(active.session_id!);
        setError(null);
        toast({
          title: 'Connected to Stream',
          description: 'Receiving live feed from mobile device',
        });
      });

      ws.on('frame', (data: string) => {
        setFrameSrc(`data:image/jpeg;base64,${data}`);
      });

      ws.on('analysis', (data: any) => {
        setAnalysis(data);
      });

      ws.on('session_completed', () => {
        setIsStreaming(false);
        setSessionId(null);
        setFrameSrc(null);
        setAnalysis(null);
        setError('Stream ended by mobile device');
        toast({
          title: 'Stream Ended',
          description: 'Mobile device stopped streaming',
          variant: 'destructive',
        });
        ws.disconnect();
      });

      ws.on('error', (data: { message: string }) => {
        setError(data.message);
        toast({
          title: 'Stream Error',
          description: data.message,
          variant: 'destructive',
        });
      });

      await ws.connect();
    } catch (err: any) {
      const message = err.message || 'Failed to connect to live stream';
      setError(message);
      toast({
        title: 'Connection Failed',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setIsConnecting(false);
    }
  };

  const disconnectStream = () => {
    if (wsRef.current) {
      wsRef.current.disconnect();
      wsRef.current = null;
    }
    setIsStreaming(false);
    setSessionId(null);
    setFrameSrc(null);
    setAnalysis(null);
    setError(null);
    toast({
      title: 'Disconnected',
      description: 'Dashboard disconnected from the stream',
    });
  };

  useEffect(() => {
    // Attempt to connect on load
    connectToStream(true);

    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const headerActions = (
    <>
      {!isStreaming ? (
        <Button onClick={() => connectToStream()} className="gap-2" disabled={isConnecting}>
          <Play className="h-4 w-4" />
          {isConnecting ? 'Connecting...' : 'Connect to Live Stream'}
        </Button>
      ) : (
        <Button onClick={disconnectStream} variant="destructive" className="gap-2">
          <Square className="h-4 w-4" />
          Disconnect
        </Button>
      )}
      <Button variant="outline" onClick={() => connectToStream()} disabled={isConnecting}>
        <RefreshCw className="h-4 w-4" />
      </Button>
    </>
  );

  return (
    <Container size="xl">
      <PageHeader
        title="Dashboard"
        description="Real-time IC verification monitoring"
        actions={headerActions}
      />

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <VideoFeed isStreaming={isStreaming} frameSrc={frameSrc} />
        </div>

        <SessionInfo
          isStreaming={isStreaming}
          sessionId={sessionId}
          analysis={analysis}
        />
      </div>
    </Container>
  );
}
