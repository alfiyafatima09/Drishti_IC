import { useState, useCallback, useRef } from 'react';
import { VideoFeed } from './components/video-feed';
import { ImageUpload } from './components/image-upload';
import { AnalysisPanel } from './components/analysis-panel';
import { API_BASE } from '@/lib/config';
import type { ScanResult } from '@/types/api';

// ============================================================
// COMPONENT
// ============================================================

export default function DashboardPage() {
  const [currentScanResult, setCurrentScanResult] = useState<ScanResult | null>(null);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  /**
   * Handle camera capture - just show image, don't analyze yet
   */
  const handleCapture = useCallback((imageUrl: string) => {
    console.log('[Dashboard] Image captured');
    setCapturedImage(imageUrl);
    setCurrentScanResult(null);
  }, []);

  /**
   * Handle file upload - just show image, don't analyze yet
   */
  const handleFileSelect = useCallback((file: File) => {
    console.log('[Dashboard] File selected');
    const imageUrl = URL.createObjectURL(file);
    setCapturedImage(imageUrl);
    setCurrentScanResult(null);
  }, []);

  /**
   * Analyze the captured/uploaded image
   */
  const handleAnalyze = useCallback(async () => {
    if (!capturedImage || isAnalyzing) return;

    setIsAnalyzing(true);

    try {
      // Convert image URL to File
      const response = await fetch(capturedImage);
      const blob = await response.blob();
      const file = new File([blob], 'ic-image.jpg', { type: 'image/jpeg' });

      const formData = new FormData();
      formData.append('file', file);

      const apiResponse = await fetch(`${API_BASE}/scan`, {
        method: 'POST',
        body: formData,
      });

      if (!apiResponse.ok) {
        console.error('[Dashboard] Scan failed:', apiResponse.status);
        return;
      }

      const scanResult: ScanResult = await apiResponse.json();
      console.log('[Dashboard] Scan result:', scanResult);
      setCurrentScanResult(scanResult);
    } catch (error) {
      console.error('[Dashboard] Analysis error:', error);
    } finally {
      setIsAnalyzing(false);
    }
  }, [capturedImage, isAnalyzing]);

  return (
    <div className="flex flex-col h-full gap-6 p-6 overflow-hidden bg-gradient-to-br from-blue-50 via-cyan-50 to-blue-100">
      {/* Header */}
      <div className="shrink-0">
        <div className="flex items-center justify-between bg-white/80 backdrop-blur-sm rounded-2xl p-6 shadow-lg border-2 border-blue-200">
          <div>
            <h1 className="text-4xl font-black bg-gradient-to-r from-blue-600 via-cyan-600 to-blue-700 bg-clip-text text-transparent mb-2">
              Drishti IC
            </h1>
            <p className="text-base font-semibold text-slate-700">Intelligent Integrated Circuit Inspection System</p>
          </div>
          <div className="px-6 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 shadow-lg">
            <p className="text-sm text-white font-bold">AOI Technology</p>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-0 overflow-hidden">
        {/* Left Section - Camera & Upload */}
        <div className="lg:col-span-2 flex flex-col gap-6 overflow-hidden">
          {/* Video Feed */}
          <div className="flex-1 min-h-0 bg-white rounded-2xl shadow-2xl border-2 border-blue-300 p-6">
            <VideoFeed onCapture={handleCapture} />
          </div>

          {/* Upload Section */}
          <div className="shrink-0">
            <ImageUpload onFileSelect={handleFileSelect} fileInputRef={fileInputRef} disabled={isAnalyzing} />
          </div>
        </div>

        {/* Right Section - Analysis Panel */}
        <div className="overflow-hidden">
          <AnalysisPanel
            capturedImage={capturedImage}
            scanResult={currentScanResult}
            isAnalyzing={isAnalyzing}
            onAnalyze={handleAnalyze}
            onResultUpdate={setCurrentScanResult}
          />
        </div>
      </div>
    </div>
  );
}
