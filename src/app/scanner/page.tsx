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
  const [scanResult, setScanResult] = useState({
    icMarking: 'LM358',
    oem: 'Texas Instruments',
    logoMatch: true,
    fontSimilarity: 91,
    pinsVisible: 16,
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

    // try {
    //   // Hit /detected_text endpoint
    //   const response = await fetch(`${API_BASE_URL}/detected_text`);
      
    //   if (!response.ok) {
    //     throw new Error('Validation failed');
    //   }

    //   const text = await response.text();
    //   console.log('Detected text:', text);

    //   // Animate results appearing one by one
    //   const steps = [1, 2, 3, 4, 5, 6, 7];
    //   for (let i = 0; i < steps.length; i++) {
    //     await new Promise(resolve => setTimeout(resolve, 5000));
    //     setCurrentStep(steps[i]);
    //   }
    // } catch (error) {
    //   console.error('Error validating:', error);
    //   alert('Failed to validate. Please try again.');
    // } finally {
    //   setIsValidating(false);
    // }

    try {
      const TEST_MODE = true; // toggle to false for real API
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
    
      // Simulate result animation (unchanged)
      const steps = [1, 2, 3, 4, 5, 6, 7];
      for (let i = 0; i < steps.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        setCurrentStep(steps[i]);
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

        {/* Upload Section */}
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
                {imagePreview && (
                  <Image
                    src={imagePreview}
                    alt="Uploaded IC"
                    width={320}
                    height={240}
                    sizes="(max-width: 768px) 80vw, 320px"
                    unoptimized
                    className="w-full h-auto rounded-2xl shadow-[0_0_40px_rgba(59,130,246,0.3)] hover:shadow-[0_0_60px_rgba(59,130,246,0.4)] transition-all duration-300"
                  />
                )}
              </div>
            )}
          </div>
        </div>

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

        {/* Loading Screen */}
        {isValidating && currentStep === 0 && (
          <div className="text-center mb-8">
            <div className="backdrop-blur-md bg-white/5 border border-white/10 rounded-2xl px-6 py-4 inline-block">
              <div className="flex items-center space-x-3">
                <div className="animate-spin h-5 w-5 border-2 border-blue-400 border-t-transparent rounded-full"></div>
                <span className="text-slate-300">Analyzing IC markings...</span>
              </div>
            </div>
          </div>
        )}

        {/* Results Section - Appearing One by One */}
        {currentStep > 0 && (
          <div className="backdrop-blur-md bg-white/5 border border-white/10 rounded-2xl p-8 shadow-2xl">
            <h2 className="text-2xl mb-8 text-center bg-gradient-to-r from-blue-400 via-cyan-300 to-blue-500 bg-clip-text text-transparent font-bold">
              Verification Results
            </h2>
            
            <div className="space-y-4 mb-8">
              {currentStep >= 1 && (
                <div className="flex justify-between items-center p-3 bg-white/5 rounded-lg animate-fadeIn">
                  <span className="text-slate-300">IC Marking</span>
                  <div className="flex items-center space-x-2">
                    <span className="text-white font-semibold">{scanResult.icMarking}</span>
                    <span>✅</span>
                  </div>
                </div>
              )}
              
              {currentStep >= 2 && (
                <div className="flex justify-between items-center p-3 bg-white/5 rounded-lg animate-fadeIn">
                  <span className="text-slate-300">OEM</span>
                  <div className="flex items-center space-x-2">
                    <span className="text-white font-semibold">{scanResult.oem}</span>
                    <span>✅</span>
                  </div>
                </div>
              )}
              
              {currentStep >= 3 && (
                <div className="flex justify-between items-center p-3 bg-white/5 rounded-lg animate-fadeIn">
                  <span className="text-slate-300">Logo Match</span>
                  <div className="flex items-center space-x-2">
                    <span className="text-white font-semibold">Detected</span>
                    <span>✅</span>
                  </div>
                </div>
              )}
              
              {currentStep >= 4 && (
                <div className="flex justify-between items-center p-3 bg-white/5 rounded-lg animate-fadeIn">
                  <span className="text-slate-300">Font Consistency</span>
                  <div className="flex items-center space-x-2">
                    <span className="text-white font-semibold">{scanResult.fontSimilarity}%</span>
                    <span>⚠️</span>
                  </div>
                </div>
              )}
              
              {currentStep >= 5 && (
                <div className="flex justify-between items-center p-3 bg-white/5 rounded-lg animate-fadeIn">
                  <span className="text-slate-300">Pins Visible</span>
                  <div className="flex items-center space-x-2">
                    <span className="text-white font-semibold">{scanResult.pinsVisible}</span>
                    <span>✅</span>
                  </div>
                </div>
              )}
            </div>

            {currentStep >= 6 && (
              <div className="text-center p-6 bg-gradient-to-br from-green-500/20 to-emerald-500/20 rounded-lg mb-8 border border-green-500/30 animate-fadeIn">
                <div className="text-2xl mb-2">
                  🟢 This IC appears genuine!
                </div>
                <div className="text-xl text-green-400 font-semibold">
                  Authenticity Score: {scanResult.score}%
                </div>
              </div>
            )}

            {currentStep >= 7 && (
              <div className="text-center animate-fadeIn">
                <Link 
                  href="/dashboard" 
                  className="bg-gradient-to-r from-blue-500 to-cyan-500 text-white px-8 py-3 rounded-lg inline-block hover:shadow-lg hover:shadow-blue-500/50 transition-all duration-300"
                >
                  View Detailed Dashboard →
                </Link>
              </div>
            )}
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
        .animate-fadeIn {
          animation: fadeIn 0.5s ease-out;
        }
      `}</style>
    </div>
  );
}