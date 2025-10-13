"use client";

import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { useState } from "react";

export default function Home() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gradient-to-br from-black via-blue-950/95 to-slate-950">
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-black/70 via-blue-950/80 to-slate-950" />

        <nav className="fixed top-4 right-4 z-50 md:left-1/2 md:right-auto md:transform md:-translate-x-1/2 md:w-[400px]">
          <div className="md:hidden">
            <motion.button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="backdrop-blur-md bg-black/40 rounded-full p-3 shadow-lg shadow-blue-500/10"
            >
              <div className="w-6 h-5 flex flex-col justify-between">
                <motion.div
                  animate={
                    isMenuOpen ? { rotate: 45, y: 9 } : { rotate: 0, y: 0 }
                  }
                  className="w-full h-0.5 bg-cyan-400 rounded-full origin-left"
                />
                <motion.div
                  animate={isMenuOpen ? { opacity: 0 } : { opacity: 1 }}
                  className="w-full h-0.5 bg-cyan-400 rounded-full"
                />
                <motion.div
                  animate={
                    isMenuOpen ? { rotate: -45, y: -9 } : { rotate: 0, y: 0 }
                  }
                  className="w-full h-0.5 bg-cyan-400 rounded-full origin-left"
                />
              </div>
            </motion.button>

            {/* Mobile Menu Dropdown */}
            <AnimatePresence>
              {isMenuOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="absolute right-0 mt-2 w-48 backdrop-blur-md bg-black/90 rounded-2xl shadow-lg shadow-blue-500/10 overflow-hidden"
                >
                  <ul className="py-2">
                    <motion.li>
                      <Link
                        href="/"
                        onClick={() => setIsMenuOpen(false)}
                        className="block px-4 py-3 text-cyan-400 text-sm font-medium hover:bg-white/5"
                      >
                        Home
                      </Link>
                    </motion.li>
                    <motion.li>
                      <Link
                        href="/scanner"
                        onClick={() => setIsMenuOpen(false)}
                        className="block px-4 py-3 text-gray-300 text-sm font-medium hover:bg-white/5 hover:text-cyan-400"
                      >
                        Scan
                      </Link>
                    </motion.li>
                    <motion.li>
                      <Link
                        href="#features"
                        onClick={() => setIsMenuOpen(false)}
                        className="block px-4 py-3 text-gray-300 text-sm font-medium hover:bg-white/5 hover:text-cyan-400"
                      >
                        About
                      </Link>
                    </motion.li>
                    <motion.li>
                      <Link
                        href="/login"
                        onClick={() => setIsMenuOpen(false)}
                        className="block px-4 py-3 text-gray-300 text-sm font-medium hover:bg-white/5 hover:text-cyan-400"
                      >
                        Login
                      </Link>
                    </motion.li>
                  </ul>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Desktop Menu */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="hidden md:block backdrop-blur-md bg-black/40 rounded-full px-3 py-2 shadow-lg shadow-blue-500/10"
          >
            <ul className="flex items-center justify-between px-10 py-3">
              <motion.li>
                <Link
                  href="/"
                  className="relative group text-cyan-400 text-md font-medium transition-colors"
                >
                  Home
                  <div className="absolute -bottom-1 left-0 w-full h-0.5 bg-cyan-400 scale-100" />
                </Link>
              </motion.li>
              <motion.li>
                <Link
                  href="/scanner"
                  className="text-gray-300 text-md font-medium hover:text-cyan-400 transition-colors"
                >
                  Scan
                </Link>
              </motion.li>
              <motion.li>
                <Link
                  href="#features"
                  className="text-gray-300 text-md font-medium hover:text-cyan-400 transition-colors"
                >
                  About
                </Link>
              </motion.li>
              <motion.li>
                <Link
                  href="/login"
                  className="text-gray-300 text-md font-medium hover:text-cyan-400 transition-colors"
                >
                  Login
                </Link>
              </motion.li>
            </ul>
          </motion.div>
        </nav>

        {/* <div className="absolute bottom-0 right-8 z-10 hidden lg:block mr-30">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8 }}
            whileHover={{ scale: 1.02, rotate: -1 }}
            className="relative"
          >
            <Image
              src="/images/landing-page-2.jpg"
              alt="Drishti IC Scanning"
              width={600}
              height={350}
              className="rounded-2xl shadow-[0_0_40px_rgba(59,130,246,0.3)] hover:shadow-[0_0_60px_rgba(59,130,246,0.4)] transition-all duration-300"
              priority
            />
            <div className="absolute inset-0 bg-gradient-to-t from-blue-600/30 via-blue-400/20 to-transparent blur-3xl -z-10 scale-110" />
          </motion.div>
        </div> */}

{/* <div className="absolute bottom-0 right-8 z-10 hidden lg:block mr-30">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8 }}
            whileHover={{ scale: 1.02, rotate: -1 }}
            className="relative"
          >
            <Image
              src="/images/landing-page-2.jpg"
              alt="Drishti IC Scanning"
              width={370}
              height={650}
              className="rounded-2xl shadow-[0_0_40px_rgba(59,130,246,0.3)] hover:shadow-[0_0_60px_rgba(59,130,246,0.4)] transition-all duration-300"
              priority
            />
            <div className="absolute inset-0 bg-gradient-to-t from-blue-600/30 via-blue-400/20 to-transparent blur-3xl -z-10 scale-110" />
          </motion.div>
        </div> */}

        <div className="absolute top-1/2 right-8 z-10 hidden lg:block mr-30 transform -translate-y-1/2">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8 }}
            whileHover={{ scale: 1.02, rotate: -1 }}
            className="relative"
          >
            <Image
              src="/images/langing-page.png"
              alt="Drishti IC Scanning"
              width={600}
              height={350}
              className="rounded-2xl shadow-[0_0_40px_rgba(59,130,246,0.3)] hover:shadow-[0_0_60px_rgba(59,130,246,0.4)] transition-all duration-300"
              priority
            />
            <div className="absolute inset-0 bg-gradient-to-t from-blue-600/30 via-blue-400/20 to-transparent blur-3xl -z-10 scale-110" />
          </motion.div>
        </div>

        <div className="absolute inset-0 overflow-hidden">
          {[...Array(20)].map((_, i) => {
            const left = (i * 17 + 13) % 100;
            const top = (i * 23 + 7) % 100;
            const duration = 3 + ((i * 13) % 3);
            const delay = (i * 7) % 2;

            return (
              <motion.div
                key={i}
                className="absolute w-1 h-1 bg-blue-400/30 rounded-full"
                style={{
                  left: `${left}%`,
                  top: `${top}%`,
                }}
                animate={{
                  y: [0, -30, 0],
                  opacity: [0.2, 0.5, 0.2],
                }}
                transition={{
                  duration: duration,
                  repeat: Infinity,
                  delay: delay,
                }}
              />
            );
          })}
        </div>

        <div className="container mx-auto px-8 lg:px-16 z-10">
          <div className="flex flex-col lg:flex-row items-center justify-between gap-16 lg:gap-24">
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8 }}
              className="text-center lg:text-left lg:pl-8 flex-1 max-w-2xl"
            >
              <motion.h1
                className="text-5xl md:text-7xl lg:text-8xl font-bold mb-6 bg-gradient-to-r from-blue-400 via-cyan-300 to-blue-500 bg-clip-text text-transparent"
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                transition={{ duration: 0.5 }}
              >
                Drishti IC
              </motion.h1>

              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3, duration: 0.8 }}
                className="text-xl md:text-2xl lg:text-3xl mb-4 text-blue-100 font-semibold"
              >
                Verify Integrated Circuits in Seconds
              </motion.p>

              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5, duration: 0.8 }}
                className="text-base md:text-lg lg:text-xl mb-12 text-slate-300 max-w-2xl mx-auto lg:mx-0"
              >
                A complete solution to automatically capture, extract, and
                verify IC markings against OEM standards, ensuring every
                component on your production line is genuine.
              </motion.p>

              <motion.button
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.7, duration: 0.5 }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="px-8 py-4 bg-gradient-to-r from-blue-600 to-cyan-500 text-white text-lg font-semibold rounded-full shadow-2xl shadow-blue-500/50 hover:shadow-blue-500/70 transition-all duration-300"
              >
                Get Started →
              </motion.button>
            </motion.div>
          </div>
        </div>

        <motion.div
          animate={{ y: [0, 10, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="absolute bottom-8 left-1/2 transform -translate-x-1/2"
        >
          <div className="w-6 h-10 border-2 border-blue-400/50 rounded-full flex items-start justify-center p-2">
            <div className="w-1 h-2 bg-blue-400 rounded-full" />
          </div>
        </motion.div>
      </section>

      <section className="py-24 relative">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-blue-950/30 to-transparent" />
        <div className="container mx-auto px-4 relative z-10">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-3xl md:text-4xl font-bold text-center mb-16 text-blue-100"
          >
            Trusted Across Leading OEMs
          </motion.h2>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {[
              "Texas Instruments",
              "STMicroelectronics",
              "NXP Semiconductors",
              "Analog Devices",
              "Infineon Technologies",
              "Microchip",
            ].map((oem, index) => (
              <motion.div
                key={oem}
                initial={{ opacity: 0, scale: 0.8 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                whileHover={{ scale: 1.05, y: -5 }}
                className="backdrop-blur-xl bg-white/5 border border-blue-400/20 rounded-2xl p-8 flex items-center justify-center hover:border-blue-400/50 hover:shadow-lg hover:shadow-blue-500/20 transition-all duration-300"
              >
                <span className="text-lg font-semibold text-blue-100 text-center">
                  {oem === "STMicroelectronics" ? (
                    <>
                      <span className="hidden md:block">
                        STMicroelectronics
                      </span>
                      <span className="block md:hidden">STM</span>
                    </>
                  ) : (
                    oem
                  )}
                </span>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section id="features" className="py-24 relative scroll-mt-20">
        <div className="container mx-auto px-4">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-3xl md:text-4xl font-bold text-center mb-16 text-blue-100"
          >
            Core Features
          </motion.h2>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8 max-w-7xl mx-auto">
            {[
              {
                number: "01",
                color: "from-cyan-400 to-blue-500",
                title: "OCR Marking Extraction",
                description:
                  "Detects text markings on ICs using advanced Vision AI and machine learning algorithms.",
              },
              {
                number: "02",
                color: "from-blue-400 to-purple-500",
                title: "OEM Datasheet Validation",
                description:
                  "Automatically cross-checks IC details with official OEM documentation for accuracy.",
              },
              {
                number: "03",
                color: "from-purple-400 to-pink-500",
                title: "Logo & Font Recognition",
                description:
                  "Matches IC logos and font styles using computer vision to verify authenticity.",
              },
              {
                number: "04",
                color: "from-pink-400 to-cyan-500",
                title: "Real-Time Dashboard",
                description:
                  "View detailed analysis, confidence levels, historical data, and verification reports.",
              },
            ].map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                whileHover={{ y: -10 }}
                className="backdrop-blur-xl bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border border-blue-400/20 rounded-2xl p-8 hover:border-blue-400/50 hover:shadow-xl hover:shadow-blue-500/20 transition-all duration-300 relative overflow-hidden group"
              >
                <div className="mb-6 relative">
                  <div
                    className={`inline-flex items-center justify-center w-16 h-16 rounded-xl bg-gradient-to-br ${feature.color} shadow-lg`}
                  >
                    <span className="text-2xl font-bold text-white">
                      {feature.number}
                    </span>
                  </div>
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{
                      duration: 8,
                      repeat: Infinity,
                      ease: "linear",
                    }}
                    className="absolute inset-0 w-16 h-16"
                  >
                    <div
                      className={`w-full h-full rounded-xl border-2 border-dashed ${
                        feature.color.includes("cyan")
                          ? "border-cyan-400/30"
                          : feature.color.includes("purple")
                          ? "border-purple-400/30"
                          : feature.color.includes("pink")
                          ? "border-pink-400/30"
                          : "border-blue-400/30"
                      }`}
                    />
                  </motion.div>
                </div>

                <h3 className="text-xl font-bold mb-4 text-blue-100 relative z-10">
                  {feature.title}
                </h3>
                <p className="text-slate-300 leading-relaxed relative z-10">
                  {feature.description}
                </p>

                <motion.div
                  initial={{ width: 0 }}
                  whileHover={{ width: "100%" }}
                  className={`absolute bottom-0 left-0 h-1 bg-gradient-to-r ${feature.color}`}
                />
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Why Drishti IC Section */}
      <section className="py-24 relative">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-blue-900/20 to-transparent" />
        <div className="container mx-auto px-4 relative z-10">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-3xl md:text-4xl font-bold text-center mb-16 text-blue-100"
          >
            Why Drishti IC?
          </motion.h2>

          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            {[
              {
                pattern: "M20,20 L80,80 M80,20 L20,80",
                title: "Smart Hybrid Verification",
                description:
                  "Combines OCR with advanced image analysis for superior accuracy and reliability",
                accent: "cyan",
              },
              {
                pattern: "M50,20 L80,50 L50,80 L20,50 Z",
                title: "Cloud + Mobile Ready",
                description:
                  "Works directly in your browser, no software installation or downloads needed",
                accent: "blue",
              },
              {
                pattern:
                  "M30,30 h40 v40 h-40 Z M45,45 m-8,0 a8,8 0 1,0 16,0 a8,8 0 1,0 -16,0",
                title: "Automated Reporting",
                description:
                  "Generates instant authenticity reports with full traceability and compliance data",
                accent: "purple",
              },
            ].map((item, index) => (
              <motion.div
                key={item.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.15 }}
                className="text-center group"
              >
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  className="inline-flex items-center justify-center w-20 h-20 mb-6 rounded-2xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 border border-blue-400/30 relative overflow-hidden"
                >
                  {/* Animated SVG pattern */}
                  <svg className="w-12 h-12" viewBox="0 0 100 100">
                    <motion.path
                      d={item.pattern}
                      fill="none"
                      stroke={
                        item.accent === "cyan"
                          ? "#22d3ee"
                          : item.accent === "blue"
                          ? "#3b82f6"
                          : "#a855f7"
                      }
                      strokeWidth="4"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      initial={{ pathLength: 0 }}
                      whileInView={{ pathLength: 1 }}
                      viewport={{ once: true }}
                      transition={{
                        duration: 2,
                        ease: "easeInOut",
                        delay: index * 0.2,
                      }}
                    />
                  </svg>

                  {/* Rotating ring */}
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{
                      duration: 10,
                      repeat: Infinity,
                      ease: "linear",
                    }}
                    className="absolute inset-0 rounded-2xl"
                    style={{
                      background: `conic-gradient(from 0deg, transparent 270deg, ${
                        item.accent === "cyan"
                          ? "#22d3ee"
                          : item.accent === "blue"
                          ? "#3b82f6"
                          : "#a855f7"
                      }40 360deg)`,
                    }}
                  />
                </motion.div>
                <h3 className="text-2xl font-bold mb-4 text-blue-100">
                  {item.title}
                </h3>
                <p className="text-slate-300 leading-relaxed">
                  {item.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-32 relative">
        <div className="absolute inset-0 bg-gradient-to-t from-blue-950/50 to-transparent" />
        <div className="container mx-auto px-4 text-center relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <h2 className="text-4xl md:text-5xl font-bold mb-6 text-blue-100">
              Ready to verify your first IC?
            </h2>
            <p className="text-xl text-slate-300 mb-10 max-w-2xl mx-auto">
              Join the future of IC authentication through automated
              verification.
            </p>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="px-10 py-5 bg-gradient-to-r from-blue-600 to-cyan-500 text-white text-xl font-semibold rounded-full shadow-2xl shadow-blue-500/50 hover:shadow-blue-500/70 transition-all duration-300"
            >
              Scan Now
            </motion.button>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 border-t border-blue-400/10">
        <div className="container mx-auto px-4 text-center text-slate-400">
          <p>© 2025 Drishti IC. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
