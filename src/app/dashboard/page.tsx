"use client";
import Image from 'next/image'
import Link from 'next/link'
import { motion } from 'framer-motion'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts'

const confidenceData = [
  { name: 'OEM Match', value: 99 },
  { name: 'Logo Match', value: 96 },
  { name: 'Font Match', value: 91 },
  { name: 'Pin Layout', value: 93 },
  { name: 'Text Consistency', value: 88 }
]

const COLORS = ['#38BDF8', '#FF6B35']

export default function Dashboard() {
  const scanResult = {
    icName: 'L7805CV',
    oem: 'STMicroelectronics',
    date: '13 Oct 2025',
    verdict: 'Genuine',
    overallScore: 94,

      
    logoMatch: true,
    fontSimilarity: 91,
    pinsVisible: 3,
    isGenuine: true,
    score: 94 
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-black via-blue-950/95 to-slate-950 py-12">
      <div className="container mx-auto px-4">
        <motion.section 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-4 sm:p-8 mb-12"
        >
          <div className="grid md:grid-cols-2 gap-8 items-center">
            <div className="mx-auto md:mx-0">
              <Image
                src="/images/modified.jpg"
                alt="Scanned IC"
                width={400}
                height={300}
                className="rounded-lg w-full max-w-[300px] md:max-w-[400px] lg:ml-20"
              />
            </div>
            <div>
              <h1 className="text-3xl mb-4 bg-gradient-to-r from-blue-400 via-cyan-300 to-blue-500 bg-clip-text text-transparent font-bold">{scanResult.icName}</h1>
              
              <div className="mb-4 p-3 bg-white/5 rounded-lg">
                <span className="text-text/80 block mb-1 text-sm">Extracted Text from Image:</span>
                <div className="text-white font-mono text-sm space-y-1">
                  <div>LM358</div>
                  <div>18M</div>
                  <div>GMIC20KG4</div>
                </div>
              </div>
              
              <div className="bg-white/5 rounded-lg p-4 space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-text/80 font-medium">IC Part Number:</span>
                  <span className="text-white font-semibold">{scanResult.icName}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-text/80 font-medium">Manufacturer:</span>
                  <div className="flex items-center space-x-3">
                    <span className="text-white">{scanResult.oem}</span>
                    <a 
                      href="https://www.st.com/resource/en/datasheet/l78.pdf" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="group relative inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-500/20 to-cyan-500/20 hover:from-blue-500/40 hover:to-cyan-500/40 border border-blue-400/30 hover:border-blue-400/60 rounded-lg text-blue-400 hover:text-blue-300 text-sm font-semibold transition-all duration-300 hover:shadow-lg hover:shadow-blue-500/30 hover:scale-105"
                    >
                      <span>View Details</span>
                      <svg 
                        className="w-4 h-4 group-hover:translate-x-1 transition-transform duration-300" 
                        fill="none" 
                        stroke="currentColor" 
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </a>
                  </div>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-text/80 font-medium">Scan Date:</span>
                  <span className="text-white">{scanResult.date}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-text/80 font-medium">Authenticity:</span>
                  <span className="text-green-400 font-semibold">🟢 {scanResult.verdict}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-text/80 font-medium">Confidence Score:</span>
                  <span className="text-blue-400 font-bold text-lg">{scanResult.overallScore}%</span>
                </div>
              </div>
            </div>
          </div>
        </motion.section>

        <motion.section 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass-card p-8 mb-12"
        >
          <h2 className="text-2xl mb-8 text-blue-100 font-bold">Confidence Breakdown</h2>
          
          <div className="grid md:grid-cols-2 gap-8">
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={confidenceData}
                  layout="vertical"
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" domain={[0, 100]} />
                  <YAxis dataKey="name" type="category" />
                  <Tooltip />
                  <Bar dataKey="value" fill="#38BDF8" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={[
                      { name: 'Genuine', value: scanResult.overallScore },
                      { name: 'Risk', value: 100 - scanResult.overallScore }
                    ]}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    fill="#8884d8"
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {confidenceData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <div className="text-center mt-4">
                <div className="text-2xl font-orbitron">
                  Overall Authenticity
                </div>
                <div className="text-highlight text-4xl font-bold">
                  {scanResult.overallScore}%
                </div>
              </div>
            </div>
          </div>
        </motion.section>

        <motion.section 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="glass-card p-8 mb-12"
        >
          <h2 className="text-2xl mb-6 text-blue-100 font-bold">Recent Scans</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-text/10">
                  <th className="text-left py-4">Date</th>
                  <th className="text-left py-4">IC Name</th>
                  <th className="text-left py-4">Verdict</th>
                  <th className="text-left py-4">Confidence</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-text/10">
                  <td className="py-4">13 Oct 2025</td>
                  <td className="py-4">LM358</td>
                  <td className="py-4 text-green-400">Genuine</td>
                  <td className="py-4">94%</td>
                </tr>
                <tr className="border-b border-text/10">
                  <td className="py-4">12 Oct 2025</td>
                  <td className="py-4">LM358N</td>
                  <td className="py-4 text-yellow-400">Suspect</td>
                  <td className="py-4">82%</td>
                </tr>
              </tbody>
            </table>
          </div>
        </motion.section>

        <div className="flex justify-center gap-4">
          <Link href="/scanner" className="btn-primary">
            Scan Another IC
          </Link>
          <Link href="/" className="btn-secondary">
            Back to Home
          </Link>
        </div>
      </div>
    </div>
  )
}