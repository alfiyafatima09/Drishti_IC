
import React from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Sparkles, ArrowRight } from 'lucide-react';

interface NewModelPopupProps {
    isOpen: boolean;
    onConfirm: () => void;
    onCancel: () => void;
    topImage: string | null;
    bottomImage: string | null;
}

export function NewModelPopup({ isOpen, onConfirm, onCancel, topImage, bottomImage }: NewModelPopupProps) {
    return (
        <Dialog open={isOpen} onOpenChange={(open) => !open && onCancel()}>
            <DialogContent className="sm:max-w-md bg-white border-slate-200 text-slate-900 p-0 overflow-hidden shadow-xl rounded-xl">
                {/* Accent Bar */}
                <div className="absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r from-blue-400 to-blue-600" />

                {/* Header Content */}
                <div className="p-6 pb-2">
                    <div className="flex items-center gap-2.5 mb-2">
                        <div className="p-2 rounded-lg bg-blue-50 text-blue-600 shadow-sm border border-blue-100">
                            <Sparkles className="w-5 h-5" />
                        </div>
                        <DialogTitle className="text-xl font-bold text-slate-900 tracking-tight">
                            Enhanced OpenCV Analysis
                        </DialogTitle>
                    </div>
                    <DialogDescription className="text-slate-500 text-base leading-relaxed">
                        We have observed that for this specific type of IC, <span className="font-medium text-blue-600">OpenCV</span> detection is superior to standard AI models. It provides significantly better accuracy for pin counting and dimension measurements.
                    </DialogDescription>
                </div>

                {/* Images Preview - Light & Clean */}
                <div className="mx-6 px-4 py-6 flex gap-6 justify-center bg-slate-50/80 rounded-xl border border-slate-100/80">
                    {topImage && (
                        <div className="relative group">
                            <div className="relative w-32 h-32 rounded-lg overflow-hidden border border-slate-200 bg-white shadow-sm group-hover:shadow-md transition-shadow duration-300">
                                <img src={topImage} alt="Top View" className="w-full h-full object-contain p-1" />
                                <div className="absolute bottom-0 left-0 right-0 bg-white/90 border-t border-slate-100 py-1.5 text-[10px] text-center font-semibold text-slate-600 uppercase tracking-wider backdrop-blur-sm">
                                    Top View
                                </div>
                            </div>
                        </div>
                    )}

                    {bottomImage && (
                        <div className="relative group">
                            <div className="relative w-32 h-32 rounded-lg overflow-hidden border border-slate-200 bg-white shadow-sm group-hover:shadow-md transition-shadow duration-300">
                                <img src={bottomImage} alt="Bottom View" className="w-full h-full object-contain p-1" />
                                <div className="absolute bottom-0 left-0 right-0 bg-white/90 border-t border-slate-100 py-1.5 text-[10px] text-center font-semibold text-slate-600 uppercase tracking-wider backdrop-blur-sm">
                                    Bottom View
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                <DialogFooter className="p-6 pt-6 bg-white">
                    <Button
                        onClick={onConfirm}
                        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold shadow-md shadow-blue-500/20 border-0 transition-all active:scale-95 h-11 text-base"
                    >
                        Continue Analysis with OpenCV
                        <ArrowRight className="w-4 h-4 ml-2" />
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
