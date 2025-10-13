'use client';

import { useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import Image from 'next/image'

export default function ScannerPage() {
  const [file, setFile] = useState<File | null>(null)
  const [extractedText, setExtractedText] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  interface ScanResult {
    icMarking: string;
    oem: string;
    logoMatch: boolean;
    fontSimilarity: number;
    pinsVisible: number;
    isGenuine: boolean;
    score: number;
  }

  const [scanResult, setScanResult] = useState<ScanResult | null>(null)

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      setFile(file)
      processImage(file)
    }
  }

  const processImage = async (file: File) => {
    setIsProcessing(true)
    await new Promise(resolve => setTimeout(resolve, 2000))
    setExtractedText('74HC595N')
    
    setScanResult({
      icMarking: '74HC595N',
      oem: 'Texas Instruments',
      logoMatch: true,
      fontSimilarity: 91,
      pinsVisible: 16,
      isGenuine: true,
      score: 94
    })
    setIsProcessing(false)
  }

  return (
    <div className="min-h-screen py-12">
      <div className="container mx-auto px-4">
        <section className="text-center mb-12">
          <h1 className="font-orbitron text-4xl mb-4">Scan Your IC</h1>
          <p className="text-text/80">Use your mobile camera for better clarity.</p>
        </section>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card max-w-2xl mx-auto p-8 mb-12"
        >
          <div className="border-2 border-dashed border-text/20 rounded-lg p-8 text-center">
            <input
              type="file"
              accept="image/*"
              onChange={handleFileUpload}
              className="hidden"
              id="ic-image"
            />
            <label
              htmlFor="ic-image"
              className="btn-secondary cursor-pointer inline-block"
            >
              Upload IC Image
            </label>
            {file && (
              <div className="mt-4">
            <Image
              src="/images/landing-page-2.jpg"
              alt="Drishti IC Scanning"
              width={370}
              height={650}
              className="rounded-2xl shadow-[0_0_40px_rgba(59,130,246,0.3)] hover:shadow-[0_0_60px_rgba(59,130,246,0.4)] transition-all duration-300"
              priority
            />
              </div>
            )}
          </div>
        </motion.div>

        {isProcessing && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center mb-8"
          >
            <div className="inline-block glass-card px-6 py-3">
              <span className="animate-pulse">⏳ Extracting markings...</span>
            </div>
          </motion.div>
        )}

        {scanResult && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass-card max-w-2xl mx-auto p-8"
          >
            <h2 className="font-orbitron text-2xl mb-6 text-center">
              Verification Results
            </h2>
            
            <div className="space-y-4 mb-8">
              {[
                { label: 'IC Marking', value: scanResult.icMarking, status: '✅' },
                { label: 'OEM', value: scanResult.oem, status: '✅' },
                { label: 'Logo Match', value: 'Detected', status: '✅' },
                { label: 'Font Consistency', value: '91%', status: '⚠️' },
                { label: 'Pins Visible', value: '16', status: '✅' },
              ].map(item => (
                <div key={item.label} className="flex justify-between items-center">
                  <span className="text-text/80">{item.label}</span>
                  <div>
                    <span className="mr-2">{item.value}</span>
                    <span>{item.status}</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="text-center p-6 bg-background/50 rounded-lg mb-8">
              <div className="text-2xl mb-2">
                🟢 This IC appears genuine!
              </div>
              <div className="text-xl text-highlight">
                Authenticity Score: {scanResult.score}%
              </div>
            </div>

            <div className="text-center">
              <Link href="/dashboard" className="btn-primary">
                View Detailed Dashboard →
              </Link>
            </div>
          </motion.div>
        )}

        {/* Tip Bar */}
        <div className="mt-12 text-center text-text/60">
          💡 Ensure the IC marking is clearly visible with neutral lighting for best results.
        </div>
      </div>
    </div>
  )
}