import { useState, useCallback } from 'react';
import { VideoFeed } from './components/video-feed';
import { ResultsPanel } from './components/results-panel';
import { StatsPanel } from './components/stats-panel';
import type { ScanResult, DashboardStats } from '@/types/api';

// ============================================================
// COMPONENT
// ============================================================

export default function DashboardPage() {
  // Scan state
  const [currentScanResult, setCurrentScanResult] = useState<ScanResult | null>(null);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [_pendingScanId, setPendingScanId] = useState<string | null>(null);

  // Stats state (placeholder - will be fetched from API)
  const [stats] = useState<DashboardStats | null>(null);

  /**
   * Called when an image is captured (for immediate preview)
   */
  const handleCapture = useCallback((scanId: string, imageUrl: string) => {
    console.log('[Dashboard] Captured:', scanId);
    setPendingScanId(scanId);
    setCapturedImage(imageUrl);
    
    // Clear previous result when new capture starts
    if (scanId === 'pending') {
      setCurrentScanResult(null);
    }
  }, []);

  /**
   * Called when scan result is received from backend
   */
  const handleScanResult = useCallback((result: ScanResult) => {
    console.log('[Dashboard] Scan result:', result);
    setCurrentScanResult(result);
    setPendingScanId(result.scan_id);
  }, []);

  /**
   * Called when user wants to scan bottom of IC
   */
  const handleScanBottom = useCallback((scanId: string) => {
    console.log('[Dashboard] Scan bottom requested:', scanId);
    // This will be handled by the VideoFeed component
    // TODO: Implement bottom scan flow
  }, []);

  return (
    <div className="flex flex-col h-full gap-4 p-4 overflow-hidden">
      {/* Stats Row */}
      <div className="shrink-0">
        <StatsPanel stats={stats} />
      </div>

      {/* Main Content - Video Feed and Results */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 min-h-0 overflow-hidden">
        {/* Video Feed - Takes 2/3 on large screens */}
        <div className="lg:col-span-2 overflow-hidden">
          <div className="h-full p-4 rounded-xl border border-zinc-800 bg-zinc-900/30">
            <VideoFeed
              onCapture={handleCapture}
              onScanResult={handleScanResult}
            />
          </div>
        </div>

        {/* Results Panel - Takes 1/3 on large screens */}
        <div className="overflow-hidden">
          <div className="h-full p-4 rounded-xl border border-zinc-800 bg-zinc-900/30 overflow-y-auto">
            <ResultsPanel
              scanResult={currentScanResult}
              capturedImage={capturedImage}
              onScanBottom={handleScanBottom}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
