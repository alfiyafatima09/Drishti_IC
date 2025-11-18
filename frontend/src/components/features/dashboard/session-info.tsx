/**
 * Session Info Component
 * Displays current streaming session information
 */

'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface SessionInfoProps {
  isStreaming: boolean;
  sessionId: string | null;
  analysis?: any;
}

export function SessionInfo({ isStreaming, sessionId, analysis }: SessionInfoProps) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Session Info</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <p className="text-sm text-muted-foreground">Status</p>
            <p className="font-medium flex items-center gap-2">
              <span
                className={`inline-flex h-2 w-2 rounded-full ${
                  isStreaming ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
                }`}
              />
              {isStreaming ? 'Receiving stream' : 'Not connected'}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Session ID</p>
            <p className="font-mono text-xs break-all">{sessionId ?? '—'}</p>
          </div>
        </CardContent>
      </Card>

      {analysis && (
        <Card>
          <CardHeader>
            <CardTitle>Real-time Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-muted p-3 rounded overflow-auto max-h-64">
              {JSON.stringify(analysis, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

