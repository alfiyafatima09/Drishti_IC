import { 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  HelpCircle, 
  ShieldAlert,
  Cpu,
  Hash,
  Building2,
  Clock,
  FileText,
  RotateCcw,
  Loader2
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { ScanResult, ScanStatus } from '@/types/api';

interface ResultsPanelProps {
  scanResult: ScanResult | null;
  capturedImage: string | null;
  onScanBottom?: (scanId: string) => void;
}

const STATUS_CONFIG: Record<ScanStatus, {
  icon: typeof CheckCircle2;
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
  description: string;
}> = {
  PASS: {
    icon: CheckCircle2,
    label: 'Verified',
    color: 'text-emerald-500',
    bgColor: 'bg-emerald-500/10',
    borderColor: 'border-emerald-500/20',
    description: 'IC verified successfully',
  },
  FAIL: {
    icon: XCircle,
    label: 'Failed',
    color: 'text-red-500',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/20',
    description: 'Verification failed',
  },
  PARTIAL: {
    icon: AlertTriangle,
    label: 'Partial',
    color: 'text-amber-500',
    bgColor: 'bg-amber-500/10',
    borderColor: 'border-amber-500/20',
    description: 'Additional scan required',
  },
  UNKNOWN: {
    icon: HelpCircle,
    label: 'Unknown',
    color: 'text-zinc-500',
    bgColor: 'bg-zinc-500/10',
    borderColor: 'border-zinc-500/20',
    description: 'IC not in database',
  },
  COUNTERFEIT: {
    icon: ShieldAlert,
    label: 'Counterfeit',
    color: 'text-red-600',
    bgColor: 'bg-red-600/10',
    borderColor: 'border-red-600/30',
    description: 'Known counterfeit detected',
  },
};

export function ResultsPanel({ scanResult, capturedImage, onScanBottom }: ResultsPanelProps) {
  // Show captured image with "Analyzing..." state if we have image but no result yet
  if (!scanResult && capturedImage) {
    return (
      <div className="flex flex-col h-full overflow-hidden">
        <div className="flex items-center gap-3 mb-4 shrink-0">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-blue-500/10">
            <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />
          </div>
          <div>
            <h2 className="text-sm font-medium text-zinc-100">Analyzing...</h2>
            <p className="text-xs text-zinc-500">Processing captured image</p>
          </div>
        </div>

        {/* Show captured image while analyzing */}
        <div className="mb-4 rounded-lg overflow-hidden border border-zinc-800 bg-zinc-950 shrink-0">
          <div className="px-3 py-2 border-b border-zinc-800 bg-zinc-900/50">
            <span className="text-xs text-zinc-500">Captured Image</span>
          </div>
          <div className="relative aspect-video">
            <img
              src={capturedImage}
              alt="Captured IC"
              className="w-full h-full object-contain"
            />
            <div className="absolute inset-0 bg-blue-500/5 flex items-center justify-center">
              <div className="px-3 py-1.5 rounded-full bg-blue-500/20 border border-blue-500/30">
                <span className="text-xs text-blue-400 flex items-center gap-2">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Analyzing...
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex-1 flex flex-col items-center justify-center rounded-xl border border-dashed border-zinc-800 bg-zinc-950/50">
          <p className="text-sm text-zinc-500 text-center">
            Waiting for analysis results...
          </p>
        </div>
      </div>
    );
  }

  if (!scanResult) {
    return (
      <div className="flex flex-col h-full overflow-hidden">
        <div className="flex items-center gap-3 mb-4 shrink-0">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-zinc-900">
            <FileText className="w-5 h-5 text-zinc-400" />
          </div>
          <div>
            <h2 className="text-sm font-medium text-zinc-100">Scan Results</h2>
            <p className="text-xs text-zinc-500">IC verification status</p>
          </div>
        </div>

        <div className="flex-1 flex flex-col items-center justify-center rounded-xl border border-dashed border-zinc-800 bg-zinc-950/50">
          <Cpu className="w-16 h-16 text-zinc-800 mb-4" />
          <p className="text-sm text-zinc-500 text-center">
            No scan results yet
          </p>
          <p className="text-xs text-zinc-600 mt-1 text-center max-w-[200px]">
            Capture an IC image to see verification results
          </p>
        </div>
      </div>
    );
  }

  const config = STATUS_CONFIG[scanResult.status];
  const StatusIcon = config.icon;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 shrink-0">
        <div className="flex items-center gap-3">
          <div className={cn('flex items-center justify-center w-10 h-10 rounded-lg', config.bgColor)}>
            <StatusIcon className={cn('w-5 h-5', config.color)} />
          </div>
          <div>
            <h2 className="text-sm font-medium text-zinc-100">Scan Results</h2>
            <p className={cn('text-xs', config.color)}>{config.label}</p>
          </div>
        </div>
        <Badge
          variant="outline"
          className={cn('text-xs', config.borderColor, config.color)}
        >
          {scanResult.confidence_score.toFixed(1)}% confidence
        </Badge>
      </div>

      {/* Scrollable content area */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {/* Captured Image Preview */}
        {capturedImage && (
          <div className="mb-4 rounded-lg overflow-hidden border border-zinc-800 bg-zinc-950">
            <div className="px-3 py-2 border-b border-zinc-800 bg-zinc-900/50">
              <span className="text-xs text-zinc-500">Captured Image</span>
            </div>
            <div className="relative aspect-video">
              <img
                src={capturedImage}
                alt="Captured IC"
                className="w-full h-full object-contain"
              />
              {/* Status overlay badge */}
              <div className={cn(
                'absolute top-2 right-2 px-2 py-1 rounded-md text-xs font-medium',
                config.bgColor,
                config.color
              )}>
                {config.label}
              </div>
            </div>
          </div>
        )}

      {/* Status Card */}
      <Card className={cn('mb-4 border', config.borderColor, config.bgColor)}>
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <StatusIcon className={cn('w-6 h-6 mt-0.5', config.color)} />
            <div className="flex-1">
              <p className={cn('font-medium', config.color)}>{config.label}</p>
              <p className="text-sm text-zinc-400 mt-1">{scanResult.message}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Action Required */}
      {scanResult.action_required === 'SCAN_BOTTOM' && onScanBottom && (
        <Button
          size="lg"
          className="mb-4 w-full h-12 bg-amber-600 hover:bg-amber-700 text-white"
          onClick={() => onScanBottom(scanResult.scan_id)}
        >
          <RotateCcw className="w-5 h-5 mr-2" />
          Flip & Scan Bottom
        </Button>
      )}

      {/* Details */}
      <div className="space-y-3">
        {/* Part Number */}
        <div className="p-3 rounded-lg bg-zinc-900/50 border border-zinc-800">
          <div className="flex items-center gap-2 text-xs text-zinc-500 mb-1">
            <Hash className="w-3.5 h-3.5" />
            Part Number
          </div>
          <p className="text-lg font-mono font-medium text-zinc-100">
            {scanResult.part_number || 'Unknown'}
          </p>
          {scanResult.ocr_text && scanResult.ocr_text !== scanResult.part_number && (
            <p className="text-xs text-zinc-500 mt-1">
              OCR: {scanResult.ocr_text}
            </p>
          )}
        </div>

        {/* Manufacturer */}
        {scanResult.manufacturer_detected && (
          <div className="p-3 rounded-lg bg-zinc-900/50 border border-zinc-800">
            <div className="flex items-center gap-2 text-xs text-zinc-500 mb-1">
              <Building2 className="w-3.5 h-3.5" />
              Manufacturer
            </div>
            <p className="text-sm font-medium text-zinc-100">
              {scanResult.manufacturer_detected}
            </p>
          </div>
        )}

        {/* Pin Count */}
        <div className="p-3 rounded-lg bg-zinc-900/50 border border-zinc-800">
          <div className="flex items-center gap-2 text-xs text-zinc-500 mb-1">
            <Cpu className="w-3.5 h-3.5" />
            Detected Pins
          </div>
          <p className="text-2xl font-mono font-bold text-zinc-100">
            {scanResult.detected_pins}
          </p>
        </div>

        {/* Timestamp */}
        <div className="p-3 rounded-lg bg-zinc-900/50 border border-zinc-800">
          <div className="flex items-center gap-2 text-xs text-zinc-500 mb-1">
            <Clock className="w-3.5 h-3.5" />
            Scanned At
          </div>
          <p className="text-sm text-zinc-300">
            {new Date(scanResult.scanned_at).toLocaleString()}
          </p>
        </div>

        {/* Queued Notice */}
        {scanResult.queued_for_sync && (
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
            <p className="text-xs text-amber-400">
              This IC has been added to the sync queue for online lookup.
            </p>
          </div>
        )}
      </div>
      </div>{/* End scrollable content area */}

      {/* Scan ID Footer */}
      <div className="mt-4 pt-3 border-t border-zinc-800 shrink-0">
        <p className="text-xs text-zinc-600 font-mono truncate">
          Scan ID: {scanResult.scan_id}
        </p>
      </div>
    </div>
  );
}

