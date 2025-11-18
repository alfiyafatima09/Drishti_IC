/**
 * Video Feed Component
 * Displays live video stream from mobile device
 */

/* eslint-disable @next/next/no-img-element */
'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface VideoFeedProps {
  isStreaming: boolean;
  frameSrc: string | null;
}

export function VideoFeed({ isStreaming, frameSrc }: VideoFeedProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Video Feed</CardTitle>
        <CardDescription>Live video stream from mobile device</CardDescription>
      </CardHeader>
      <CardContent>
        {isStreaming && frameSrc ? (
          <div className="relative aspect-video bg-black rounded-lg overflow-hidden flex items-center justify-center">
            <img src={frameSrc} alt="Live IC feed" className="w-full h-full object-contain" />
          </div>
        ) : (
          <div className="aspect-video bg-muted rounded-lg flex items-center justify-center text-center p-6">
            <div>
              <p className="text-muted-foreground">No active stream detected.</p>
              <p className="text-xs text-muted-foreground">
                Start streaming from the mobile page or click connect to try again.
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

