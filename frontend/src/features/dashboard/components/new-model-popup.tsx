import React from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Sparkles, ArrowRight } from 'lucide-react'

interface NewModelPopupProps {
  isOpen: boolean
  onConfirm: () => void
  onCancel: () => void
  topImage: string | null
  bottomImage: string | null
}

export function NewModelPopup({
  isOpen,
  onConfirm,
  onCancel,
  topImage,
  bottomImage,
}: NewModelPopupProps) {
  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onCancel()}>
      <DialogContent className="overflow-hidden rounded-xl border-slate-200 bg-white p-0 text-slate-900 shadow-xl sm:max-w-md">
        {/* Accent Bar */}
        <div className="absolute top-0 left-0 h-1.5 w-full bg-gradient-to-r from-blue-400 to-blue-600" />

        {/* Header Content */}
        <div className="p-6 pb-2">
          <div className="mb-2 flex items-center gap-2.5">
            <div className="rounded-lg border border-blue-100 bg-blue-50 p-2 text-blue-600 shadow-sm">
              <Sparkles className="h-5 w-5" />
            </div>
            <DialogTitle className="text-xl font-bold tracking-tight text-slate-900">
              Enhanced OpenCV Analysis
            </DialogTitle>
          </div>
          <DialogDescription className="text-base leading-relaxed text-slate-500">
            We have observed that for this specific type of IC,{' '}
            <span className="font-medium text-blue-600">OpenCV</span> detection is superior to
            standard AI models. It provides significantly better accuracy for pin counting and
            dimension measurements.
          </DialogDescription>
        </div>

        {/* Images Preview - Light & Clean */}
        <div className="mx-6 flex justify-center gap-6 rounded-xl border border-slate-100/80 bg-slate-50/80 px-4 py-6">
          {topImage && (
            <div className="group relative">
              <div className="relative h-32 w-32 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm transition-shadow duration-300 group-hover:shadow-md">
                <img src={topImage} alt="Top View" className="h-full w-full object-contain p-1" />
                <div className="absolute right-0 bottom-0 left-0 border-t border-slate-100 bg-white/90 py-1.5 text-center text-[10px] font-semibold tracking-wider text-slate-600 uppercase backdrop-blur-sm">
                  Top View
                </div>
              </div>
            </div>
          )}

          {bottomImage && (
            <div className="group relative">
              <div className="relative h-32 w-32 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm transition-shadow duration-300 group-hover:shadow-md">
                <img
                  src={bottomImage}
                  alt="Bottom View"
                  className="h-full w-full object-contain p-1"
                />
                <div className="absolute right-0 bottom-0 left-0 border-t border-slate-100 bg-white/90 py-1.5 text-center text-[10px] font-semibold tracking-wider text-slate-600 uppercase backdrop-blur-sm">
                  Bottom View
                </div>
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="bg-white p-6 pt-6">
          <Button
            onClick={onConfirm}
            className="h-11 w-full border-0 bg-blue-600 text-base font-semibold text-white shadow-md shadow-blue-500/20 transition-all hover:bg-blue-700 active:scale-95"
          >
            Continue Analysis with OpenCV
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
