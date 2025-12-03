import { useState, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'

const messages = [
    "Drishti IC: Precision Authentication",
    "AI Core: Advanced optical inspection",
    "OCR: Instant counterfeit detection",
    "Datasheets: Pure software solution",
    "Zero hardware dependencies",
    "SIH 2025 • Team Win Diesel"
]

export function RotatingTooltip() {
    const [index, setIndex] = useState(0)

    useEffect(() => {
        const timer = setInterval(() => {
            setIndex((prev) => (prev + 1) % messages.length)
        }, 3000)

        return () => clearInterval(timer)
    }, [])

    return (
        <div className="flex h-8 items-center justify-center overflow-hidden">
            <AnimatePresence mode="wait">
                <motion.p
                    key={index}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.5 }}
                    className="text-center text-[10px] font-medium tracking-widest text-zinc-400 uppercase dark:text-zinc-600"
                >
                    {messages[index]}
                </motion.p>
            </AnimatePresence>
        </div>
    )
}
