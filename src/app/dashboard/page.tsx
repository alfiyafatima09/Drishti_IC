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
    icName: '74HC595N',
    oem: 'Texas Instruments',
    date: '13 Oct 2025',
    verdict: 'Genuine',
    overallScore: 94
  }

  return (
    <div className="min-h-screen py-12">
      <div className="container mx-auto px-4">
        <motion.section 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-8 mb-12"
        >
          <div className="grid md:grid-cols-2 gap-8 items-center">
            <div>
              <Image
                src="/sample-ic.jpg"
                alt="Scanned IC"
                width={400}
                height={300}
                className="rounded-lg"
              />
            </div>
            <div>
              <h1 className="font-orbitron text-3xl mb-6">{scanResult.icName}</h1>
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-text/80">OEM</span>
                  <span>{scanResult.oem}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text/80">Date Scanned</span>
                  <span>{scanResult.date}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text/80">Verdict</span>
                  <span className="text-green-400">🟢 {scanResult.verdict}</span>
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
          <h2 className="font-orbitron text-2xl mb-8">Confidence Breakdown</h2>
          
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
          <h2 className="font-orbitron text-2xl mb-6">Recent Scans</h2>
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
                  <td className="py-4">74HC595N</td>
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