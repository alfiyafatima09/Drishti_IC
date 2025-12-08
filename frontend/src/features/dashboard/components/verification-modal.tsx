import { useState, useEffect, useRef } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import {
  Loader2,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  ShieldAlert,
  Cpu,
  Building2,
  Zap,
} from 'lucide-react'
import type { ScanResult } from '@/types/api'
import { cn } from '@/lib/utils'

interface VerificationModalProps {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  scanResult: ScanResult | null
  onVerificationComplete: (result: any) => void
}

interface VerificationCheck {
  id: string
  label: string
  icon: any
  status: 'pending' | 'loading' | 'match' | 'mismatch'
  detectedValue: string | number
  expectedValue: string | number | null
}

export function VerificationModal({
  isOpen,
  onOpenChange,
  scanResult,
}: VerificationModalProps) {
  const [status, setStatus] = useState<'idle' | 'verifying' | 'complete'>('idle')
  const [checks, setChecks] = useState<VerificationCheck[]>([])
  const [verdict, setVerdict] = useState<'authentic' | 'counterfeit' | null>(null)

  const verifiedIdsRef = useRef<Set<string>>(new Set())

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen && scanResult) {
      // Prevent loop: If we just finished verifying this scan ID, don't restart
      // The parent updates scanResult with the verification result, which triggers this effect again
      if (verifiedIdsRef.current.has(scanResult.scan_id)) {
        return
      }

      // If status is already complete (e.g. re-opening modal for same result), don't restart
      if (status === 'complete' && verdict !== null) {
        return
      }

      setStatus('idle')
      setVerdict(null)
      setChecks([
        {
          id: 'part_number',
          label: 'Part Number',
          icon: Cpu,
          status: 'pending',
          detectedValue: scanResult.part_number_detected || scanResult.part_number || 'Unknown',
          expectedValue: null,
        },
        {
          id: 'manufacturer',
          label: 'Manufacturer',
          icon: Building2,
          status: 'pending',
          detectedValue: scanResult.manufacturer_detected || 'Unknown',
          expectedValue: null,
        },
        {
          id: 'pin_count',
          label: 'Pin Count',
          icon: Zap,
          status: 'pending',
          detectedValue: scanResult.detected_pins,
          expectedValue: null,
        },
      ])

      // Auto-start verification
      // startVerification(scanResult.scan_id)
    }
  }, [isOpen, scanResult?.scan_id, status, verdict]) // Only depend on scan_id, not the whole object


  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="overflow-hidden rounded-3xl border-0 bg-white p-0 shadow-2xl sm:max-w-md">
        {/* Header */}
        <div className="border-b border-slate-100 bg-slate-50 px-6 py-6 text-center">
          <DialogTitle className="text-xl font-black tracking-tight text-slate-900">
            Validating Component
          </DialogTitle>
          <DialogDescription className="mt-1 font-medium text-slate-500">
            Comparing extracted features against Golden Record
          </DialogDescription>
        </div>

        <div className="space-y-6 p-6">
          {/* Progress Table */}
          <div className="space-y-3">
            {checks.map((check) => (
              <div
                key={check.id}
                className={cn(
                  'flex items-center justify-between rounded-2xl border p-3 transition-all duration-300',
                  check.status === 'pending'
                    ? 'border-transparent bg-transparent opacity-50'
                    : check.status === 'loading'
                      ? 'scale-[1.02] border-blue-200 bg-blue-50/50 shadow-sm'
                      : check.status === 'match'
                        ? 'border-emerald-100 bg-emerald-50/50'
                        : 'border-red-100 bg-red-50/50',
                )}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={cn(
                      'flex h-10 w-10 items-center justify-center rounded-xl transition-colors',
                      check.status === 'match'
                        ? 'bg-emerald-100 text-emerald-600'
                        : check.status === 'mismatch'
                          ? 'bg-red-100 text-red-600'
                          : 'bg-slate-100 text-slate-400',
                    )}
                  >
                    <check.icon size={18} />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-slate-900">{check.label}</p>
                    <p className="text-xs font-medium text-slate-500">
                      Found: {check.detectedValue}
                    </p>
                  </div>
                </div>

                {/* Status Icon */}
                <div className="pr-2">
                  {check.status === 'pending' && (
                    <div className="h-2 w-2 rounded-full bg-slate-200" />
                  )}
                  {check.status === 'loading' && (
                    <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
                  )}
                  {check.status === 'match' && (
                    <div className="flex flex-col items-end">
                      <CheckCircle2 className="h-6 w-6 text-emerald-500" />
                      <span className="text-[10px] font-bold text-emerald-600">MATCH</span>
                    </div>
                  )}
                  {check.status === 'mismatch' && (
                    <div className="flex flex-col items-end">
                      <XCircle className="h-6 w-6 text-red-500" />
                      <span className="text-[10px] font-bold text-red-600">
                        Expected: {check.expectedValue}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          <Separator className="bg-slate-100" />

          {/* Final Verdict Area */}
          <div className="flex min-h-[100px] flex-col items-center justify-center">
            {verdict === null ? (
              <div className="animate-pulse space-y-2 text-center">
                <p className="text-sm font-bold tracking-widest text-slate-400 uppercase">
                  Analyzing...
                </p>
              </div>
            ) : (
              <div
                className={cn(
                  'animate-in zoom-in spin-in-3 flex flex-col items-center space-y-2 text-center duration-500',
                  verdict === 'authentic' ? 'text-emerald-600' : 'text-red-600',
                )}
              >
                {verdict === 'authentic' ? (
                  <>
                    <ShieldCheck className="h-16 w-16 drop-shadow-xl" strokeWidth={1.5} />
                    <div>
                      <h3 className="text-2xl font-black tracking-tight">AUTHENTIC</h3>
                      <p className="text-sm font-medium text-emerald-600/80">
                        Matched Golden Record
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <ShieldAlert className="h-16 w-16 drop-shadow-xl" strokeWidth={1.5} />
                    <div>
                      <h3 className="text-2xl font-black tracking-tight">POTENTIAL COUNTERFEIT</h3>
                      <p className="text-sm font-medium text-red-600/80">Specifications Mismatch</p>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex justify-center border-t border-slate-100 bg-slate-50 p-6">
          <Button
            size="lg"
            variant={
              verdict === 'authentic'
                ? 'default'
                : verdict === 'counterfeit'
                  ? 'destructive'
                  : 'secondary'
            }
            className={cn(
              'w-full rounded-xl font-bold shadow-lg transition-all',
              verdict === 'authentic'
                ? 'bg-emerald-600 shadow-emerald-200 hover:bg-emerald-700'
                : verdict === 'counterfeit'
                  ? 'bg-red-600 shadow-red-200 hover:bg-red-700'
                  : 'cursor-not-allowed opacity-50',
            )}
            onClick={() => onOpenChange(false)}
            disabled={!status || status !== 'complete'}
          >
            {status === 'complete' ? 'Done' : 'Verifying...'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
