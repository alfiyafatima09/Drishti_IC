import { useState, useCallback, useRef } from 'react';
import { VideoFeed } from './components/video-feed';
import { ImageUpload } from './components/image-upload';
import { AnalysisPanel } from './components/analysis-panel';
import { API_BASE } from '@/lib/config';
import type { ScanResult } from '@/types/api';
import logo from '@/assets/logo_nobg.png';

export default function DashboardPage() {
  const [currentScanResult, setCurrentScanResult] = useState<ScanResult | null>(null);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleCapture = useCallback((imageUrl: string) => {
    setCapturedImage(imageUrl);
    setCurrentScanResult(null);
  }, []);

  const handleFileSelect = useCallback((file: File) => {
    const imageUrl = URL.createObjectURL(file);
    setCapturedImage(imageUrl);
    setCurrentScanResult(null);
  }, []);

  const handleAnalyze = useCallback(async () => {
    if (!capturedImage || isAnalyzing) return;

    setIsAnalyzing(true);

    try {
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
      setCurrentScanResult(scanResult);
    } catch (error) {
      console.error('[Dashboard] Analysis error:', error);
    } finally {
      setIsAnalyzing(false);
    }
  }, [capturedImage, isAnalyzing]);

  return (
    <div className="h-full w-full bg-slate-50 overflow-auto">
      <div className="max-w-[1800px] mx-auto p-4 md:p-6 lg:p-8">
        
        {/* Header - Compact */}
        <header className="mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white rounded-xl p-4 md:p-5 shadow-sm border border-slate-200">
            <div className="flex items-center gap-4">
              <img 
                src={logo} 
                alt="Drishti IC" 
                className="w-16 h-16 object-contain"
              />
              <div>
                <h1 className="text-xl md:text-2xl font-bold text-slate-900">IC Inspection</h1>
                <p className="text-sm text-slate-500">Capture or upload an IC image to analyze</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center px-3 py-1.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-2 animate-pulse"></span>
                System Ready
              </span>
            </div>
          </div>
        </header>

        {/* Main Grid */}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
          
          {/* Left Column - Camera & Upload */}
          <div className="xl:col-span-7 2xl:col-span-8 space-y-6">
            
            {/* Camera Feed Card */}
            <section className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
              <div className="p-4 md:p-5">
                <VideoFeed onCapture={handleCapture} />
              </div>
            </section>

            {/* Upload Card */}
            <section>
              <ImageUpload 
                onFileSelect={handleFileSelect} 
                fileInputRef={fileInputRef} 
                disabled={isAnalyzing} 
              />
            </section>
          </div>

          {/* Right Column - Analysis */}
          <div className="xl:col-span-5 2xl:col-span-4">
            <div className="sticky top-6">
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
      </div>
    </div>
  );
}
