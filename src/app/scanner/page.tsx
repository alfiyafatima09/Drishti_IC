'use client';

import { useState, type ChangeEvent } from 'react';
import Link from 'next/link';
import Image from 'next/image';

export default function ScannerPage() {
  const [file, setFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadComplete, setUploadComplete] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [isDetecting, setIsDetecting] = useState(false);
  const [showModifiedImage, setShowModifiedImage] = useState(false);
  const [loadingStates, setLoadingStates] = useState({
    icMarking: false,
    oem: false,
    logoMatch: false,
    fontSimilarity: false,
    pinsVisible: false
  });
  const [scanResult, setScanResult] = useState({
    icMarking: 'L7805CV',
    oem: 'STMicroelectronics',
    logoMatch: true,
    fontSimilarity: 91,
    pinsVisible: 3,
    isGenuine: true,
    score: 94 
  });

  const API_BASE_URL = 'http://localhost:8000'; 

  const handleFileUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) return;

    setFile(selectedFile);
    setImagePreview(URL.createObjectURL(selectedFile));
    setUploadComplete(false);
    setCurrentStep(0);
    setIsUploading(true);


    // Hit /run endpoint
    // try {
    //   const formData = new FormData();
    //   formData.append('image_file', selectedFile);

    //   const response = await fetch(`${API_BASE_URL}/run`, {
    //     method: 'POST',
    //     body: formData,
    //   });

    //   if (!response.ok) {
    //     throw new Error('Upload failed');
    //   }

    //   const data = await response.json();
    //   console.log('Upload response:', data);
    //   setUploadComplete(true);
    // } catch (error) {
    //   console.error('Error uploading image:', error);
    //   alert('Failed to upload image. Please try again.');
    // } finally {
    //   setIsUploading(false);
    // }

    try {
      const formData = new FormData();
      formData.append('image_file', selectedFile);
    
      // 🧩 Temporarily mock response for testing
      const TEST_MODE = true;
      let response;
    
      if (TEST_MODE) {
        console.log('⚙️ Mock mode enabled — skipping actual fetch');
        response = {
          ok: true,
          json: async () => ({
            success: true,
            message: 'Mock upload successful',
            fileUrl: 'https://example.com/mock-image.jpg'
          }),
        };
      } else {
        response = await fetch(`${API_BASE_URL}/run`, {
          method: 'POST',
          body: formData,
        });
      }
    
      if (!response.ok) {
        throw new Error('Upload failed');
      }
    
      const data = await response.json();
      console.log('Upload response:', data);
      setUploadComplete(true);
    } catch (error) {
      console.error('Error uploading image:', error);
      alert('Failed to upload image. Please try again.');
    } finally {
      setIsUploading(false);
    }
    
  };

  const handleValidate = async () => {
    setIsValidating(true);
    setCurrentStep(0);
    setShowModifiedImage(false);

    try {
      const TEST_MODE = true; // toggle to false for real API
      
      // Step 1: Show detecting animation
      setIsDetecting(true);
      await new Promise(resolve => setTimeout(resolve, 3000)); // 3 seconds of detection
      
      // Step 2: Switch to modified image
      setShowModifiedImage(true);
      setIsDetecting(false);
      await new Promise(resolve => setTimeout(resolve, 800)); // Brief pause
      
      // Step 3: Start analysis
      setCurrentStep(1);
      
      let response;
      if (TEST_MODE) {
        console.log('⚙️ Mock mode enabled — skipping actual /detected_text fetch');
        response = {
          ok: true,
          text: async () => 'Mock detected text: IC12345XYZ',
        };
      } else {
        response = await fetch(`${API_BASE_URL}/detected_text`);
      }
    
      if (!response.ok) {
        throw new Error('Validation failed');
      }
    
      const text = await response.text();
      console.log('Detected text:', text);
    
      // Animate results appearing one by one with random delays
      const analysisSteps = [
        { step: 2, field: 'icMarking', minDelay: 1500, maxDelay: 2500 },
        { step: 3, field: 'oem', minDelay: 1200, maxDelay: 2200 },
        { step: 4, field: 'logoMatch', minDelay: 1800, maxDelay: 2800 },
        { step: 5, field: 'fontSimilarity', minDelay: 1400, maxDelay: 2400 },
        { step: 6, field: 'pinsVisible', minDelay: 1600, maxDelay: 2600 },
        { step: 7, field: null, minDelay: 1000, maxDelay: 1500 },
        { step: 8, field: null, minDelay: 800, maxDelay: 1200 },
      ];
      
      for (const { step, field, minDelay, maxDelay } of analysisSteps) {
        if (field) {
          // Show "Finding..." state
          setLoadingStates(prev => ({ ...prev, [field]: true }));
        }
        
        // Random delay
        const delay = Math.floor(Math.random() * (maxDelay - minDelay + 1)) + minDelay;
        await new Promise(resolve => setTimeout(resolve, delay));
        
        if (field) {
          // Hide loading state
          setLoadingStates(prev => ({ ...prev, [field]: false }));
        }
        setCurrentStep(step);
      }
    
    } catch (error) {
      console.error('Error validating:', error);
      alert('Failed to validate. Please try again.');
    } finally {
      setIsValidating(false);
    }
  };

  const BackButton = () => (
    <Link 
      href="/" 
      className="inline-block mb-8 backdrop-blur-md bg-black/40 rounded-full px-4 py-2 shadow-lg shadow-blue-500/10 hover:bg-black/60 transition-all duration-300 text-blue-400"
    >
      ← Back
    </Link>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-black via-blue-950/95 to-slate-950 py-12">
      <div className="container mx-auto px-4 max-w-4xl">
        <BackButton />

        <section className="text-center mb-12">
          <h1 className="text-4xl mb-4 bg-gradient-to-r from-blue-400 via-cyan-300 to-blue-500 bg-clip-text text-transparent font-bold">
            Scan Your IC
          </h1>
          <p className="text-slate-300">Use your mobile camera for better clarity.</p>
        </section>

        {/* Upload Section - Before Validation */}
        {!isValidating && currentStep === 0 && (
          <div className="backdrop-blur-md bg-white/5 border border-white/10 rounded-2xl p-8 mb-12 shadow-2xl">
            <div className="border-2 border-dashed border-slate-600 rounded-lg p-8 text-center">
              <input
                type="file"
                accept="image/*"
                onChange={handleFileUpload}
                className="hidden"
                id="ic-image"
                disabled={isUploading || isValidating}
              />
              <label
                htmlFor="ic-image"
                className="bg-gradient-to-r from-blue-500 to-cyan-500 text-white px-6 py-3 rounded-lg cursor-pointer inline-block hover:shadow-lg hover:shadow-blue-500/50 transition-all duration-300 disabled:opacity-50"
              >
                {isUploading ? 'Uploading...' : 'Upload IC Image'}
              </label>
              
              {imagePreview && (
                <div className="mt-6 max-w-xs mx-auto">
                  <Image
                    src={imagePreview}
                    alt="Uploaded IC"
                    width={320}
                    height={240}
                    sizes="(max-width: 768px) 80vw, 320px"
                    unoptimized
                    className="w-full h-auto rounded-2xl shadow-[0_0_40px_rgba(59,130,246,0.3)] hover:shadow-[0_0_60px_rgba(59,130,246,0.4)] transition-all duration-300"
                  />
                </div>
              )}
            </div>
          </div>
        )}

        {/* Validate Button */}
        {uploadComplete && !isValidating && currentStep === 0 && (
          <div className="text-center mb-12">
            <button
              onClick={handleValidate}
              className="bg-gradient-to-r from-green-500 to-emerald-500 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:shadow-lg hover:shadow-green-500/50 transition-all duration-300"
            >
              Validate IC
            </button>
          </div>
        )}

        {/* View Report Button - Appears after analysis is complete */}
        {currentStep >= 7 && (
          <div className="text-center mb-8 animate-fadeIn">
            <Link 
              href="/dashboard" 
              className="bg-gradient-to-r from-blue-500 to-cyan-500 text-white px-8 py-4 rounded-lg text-lg font-semibold inline-block hover:shadow-lg hover:shadow-blue-500/50 transition-all duration-300"
            >
              View Detailed Report →
            </Link>
          </div>
        )}

        {/* Validation Layout - Image Left, Results Right - Shows when validating OR after step 1 */}
        {(isValidating || currentStep >= 1) && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
            {/* Left Side - Image with Detection Animation */}
            <div className="backdrop-blur-md bg-white/5 border border-white/10 rounded-2xl p-6 shadow-2xl animate-slideInFromRight">
              <div className="relative">
                <Image
                  src={showModifiedImage ? '/images/modified.jpg' : imagePreview!}
                  alt="IC Analysis"
                  width={400}
                  height={300}
                  sizes="(max-width: 768px) 90vw, 400px"
                  unoptimized
                  className="w-full h-auto rounded-xl shadow-lg transition-all duration-700 ease-in-out"
                  style={{
                    opacity: showModifiedImage ? 1 : (isDetecting ? 0.7 : 1)
                  }}
                />
                
                {/* Detecting Animation Overlay */}
                {isDetecting && (
                  <div className="absolute inset-0 bg-black/40 rounded-xl animate-fadeIn">
                    <div className="scanning-line"></div>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="backdrop-blur-md bg-blue-500/20 border border-blue-400/50 rounded-lg px-4 py-2">
                        <div className="flex items-center space-x-2">
                          <div className="animate-pulse h-2 w-2 bg-blue-400 rounded-full"></div>
                          <span className="text-blue-300 font-semibold">Detecting IC...</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Right Side - Analysis Results */}
            <div className="backdrop-blur-md bg-white/5 border border-white/10 rounded-2xl p-6 shadow-2xl">
              <h2 className="text-2xl mb-6 text-center bg-gradient-to-r from-blue-400 via-cyan-300 to-blue-500 bg-clip-text text-transparent font-bold">
                Analysis
              </h2>
              
              {currentStep >= 1 && (
                <div className="space-y-4">
                  {/* IC Marking */}
                  {loadingStates.icMarking ? (
                    <div className="flex justify-between items-center p-3 bg-white/5 rounded-lg animate-pulse">
                      <span className="text-slate-300">Finding IC Marking...</span>
                      <div className="animate-spin h-4 w-4 border-2 border-blue-400 border-t-transparent rounded-full"></div>
                    </div>
                  ) : currentStep >= 2 && (
                    <div className="flex justify-between items-center p-3 bg-white/5 rounded-lg animate-slideIn">
                      <span className="text-slate-300">IC Marking</span>
                      <div className="flex items-center space-x-2">
                        <span className="text-white font-semibold">{scanResult.icMarking}</span>
                        <span>✅</span>
                      </div>
                    </div>
                  )}
                  
                  {/* OEM */}
                  {loadingStates.oem ? (
                    <div className="flex justify-between items-center p-3 bg-white/5 rounded-lg animate-pulse">
                      <span className="text-slate-300">Finding OEM...</span>
                      <div className="animate-spin h-4 w-4 border-2 border-blue-400 border-t-transparent rounded-full"></div>
                    </div>
                  ) : currentStep >= 3 && (
                    <div className="flex justify-between items-center p-3 bg-white/5 rounded-lg animate-slideIn">
                      <span className="text-slate-300">OEM</span>
                      <div className="flex items-center space-x-2">
                        <span className="text-white font-semibold">{scanResult.oem}</span>
                        <span>✅</span>
                      </div>
                    </div>
                  )}
                  
                  {/* Logo Match */}
                  {loadingStates.logoMatch ? (
                    <div className="flex justify-between items-center p-3 bg-white/5 rounded-lg animate-pulse">
                      <span className="text-slate-300">Finding Logo Match...</span>
                      <div className="animate-spin h-4 w-4 border-2 border-blue-400 border-t-transparent rounded-full"></div>
                    </div>
                  ) : currentStep >= 4 && (
                    <div className="flex justify-between items-center p-3 bg-white/5 rounded-lg animate-slideIn">
                      <span className="text-slate-300">Logo Match</span>
                      <div className="flex items-center space-x-2">
                        <span className="text-white font-semibold">Detected</span>
                        <span>✅</span>
                      </div>
                    </div>
                  )}
                  
                  {/* Font Similarity */}
                  {loadingStates.fontSimilarity ? (
                    <div className="flex justify-between items-center p-3 bg-white/5 rounded-lg animate-pulse">
                      <span className="text-slate-300">Finding Font Consistency...</span>
                      <div className="animate-spin h-4 w-4 border-2 border-blue-400 border-t-transparent rounded-full"></div>
                    </div>
                  ) : currentStep >= 5 && (
                    <div className="flex justify-between items-center p-3 bg-white/5 rounded-lg animate-slideIn">
                      <span className="text-slate-300">Font Consistency</span>
                      <div className="flex items-center space-x-2">
                        <span className="text-white font-semibold">{scanResult.fontSimilarity}%</span>
                        <span>⚠️</span>
                      </div>
                    </div>
                  )}
                  
                  {/* Pins Visible */}
                  {loadingStates.pinsVisible ? (
                    <div className="flex justify-between items-center p-3 bg-white/5 rounded-lg animate-pulse">
                      <span className="text-slate-300">Finding Pins Visible...</span>
                      <div className="animate-spin h-4 w-4 border-2 border-blue-400 border-t-transparent rounded-full"></div>
                    </div>
                  ) : currentStep >= 6 && (
                    <div className="flex justify-between items-center p-3 bg-white/5 rounded-lg animate-slideIn">
                      <span className="text-slate-300">Pins Visible</span>
                      <div className="flex items-center space-x-2">
                        <span className="text-white font-semibold">{scanResult.pinsVisible}</span>
                        <span>✅</span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Final Result - Inside Analysis Panel */}
              {currentStep >= 7 && (
                <div className="mt-6 text-center p-6 bg-gradient-to-br from-green-500/20 to-emerald-500/20 rounded-lg border border-green-500/30 animate-fadeIn">
                  <div className="text-2xl mb-2">
                    🟢 This IC appears genuine!
                  </div>
                  <div className="text-xl text-green-400 font-semibold">
                    Authenticity Score: {scanResult.score}%
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        <div className="mt-12 text-center text-slate-400">
          💡 Ensure the IC marking is clearly visible with neutral lighting for best results.
        </div>
      </div>

      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateX(-20px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
        
        @keyframes slideInFromRight {
          from {
            opacity: 0;
            transform: translateX(100px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
        
        @keyframes scan {
          0% {
            top: 0;
          }
          50% {
            top: 100%;
          }
          100% {
            top: 0;
          }
        }
        
        .animate-fadeIn {
          animation: fadeIn 0.6s ease-out;
        }
        
        .animate-slideIn {
          animation: slideIn 0.5s ease-out;
        }
        
        .animate-slideInFromRight {
          animation: slideInFromRight 0.8s ease-out;
        }
        
        .scanning-line {
          position: absolute;
          left: 0;
          width: 100%;
          height: 3px;
          background: linear-gradient(90deg, transparent, #3b82f6, #60a5fa, #3b82f6, transparent);
          animation: scan 2s ease-in-out infinite;
          box-shadow: 0 0 20px #3b82f6, 0 0 10px #60a5fa;
          z-index: 10;
        }
      `}</style>
    </div>
  );
}