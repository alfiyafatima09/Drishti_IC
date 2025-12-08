import { 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  HelpCircle, 
  ShieldAlert,
  Cpu,
  Hash,
  Building2,
  Package,
  FileText,
  Zap,
  Thermometer,
  ExternalLink,
  Loader2,
  Upload,
  Edit3,
  Scan,
} from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import type { ScanResult, ScanStatus } from '@/types/api';
import { API_BASE } from '@/lib/config';

interface AnalysisPanelProps {
  capturedImage: string | null;
  scanResult: ScanResult | null;
  isAnalyzing: boolean;
  onAnalyze: () => void;
  onResultUpdate: (result: ScanResult) => void;
}

const STATUS_CONFIG: Record<ScanStatus, {
  icon: typeof CheckCircle2;
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
}> = {
  PASS: { icon: HelpCircle, label: 'Detection Complete', color: 'text-blue-600', bgColor: 'bg-blue-50', borderColor: 'border-blue-200' },
  FAIL: { icon: XCircle, label: 'Detection Failed', color: 'text-red-600', bgColor: 'bg-red-50', borderColor: 'border-red-200' },
  PARTIAL: { icon: AlertTriangle, label: 'Partial Detection', color: 'text-amber-600', bgColor: 'bg-amber-50', borderColor: 'border-amber-200' },
  UNKNOWN: { icon: HelpCircle, label: 'Unknown', color: 'text-slate-600', bgColor: 'bg-slate-50', borderColor: 'border-slate-200' },
  COUNTERFEIT: { icon: ShieldAlert, label: 'Detection Issue', color: 'text-red-700', bgColor: 'bg-red-50', borderColor: 'border-red-300' },
};

export function AnalysisPanel({ capturedImage, scanResult, isAnalyzing, onAnalyze, onResultUpdate }: AnalysisPanelProps) {
  const bottomFileRef = useRef<HTMLInputElement>(null);
  const [bottomUploading, setBottomUploading] = useState(false);
  const [overridePart, setOverridePart] = useState('');
  const [overrideNote, setOverrideNote] = useState('');
  const [overrideLoading, setOverrideLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [showOverride, setShowOverride] = useState(false);

  useEffect(() => {
    if (scanResult?.part_number) {
      setOverridePart(scanResult.part_number);
    } else {
      setOverridePart('');
    }
    setLocalError(null);
    setShowOverride(false);
  }, [scanResult?.scan_id]);

  // Empty State
  if (!capturedImage) {
    return (
      <div className="h-full min-h-[400px] flex flex-col bg-white rounded-xl shadow-sm border border-slate-200">
        <div className="flex-1 flex flex-col items-center justify-center p-8">
          <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
            <Cpu className="w-8 h-8 text-slate-400" />
          </div>
          <p className="text-base font-medium text-slate-700 mb-1">No Image Selected</p>
          <p className="text-sm text-slate-400 text-center max-w-[200px]">
            Capture from camera or upload an image to start analysis
          </p>
        </div>
      </div>
    );
  }

  const config = scanResult ? STATUS_CONFIG[scanResult.status] : null;
  const StatusIcon = config?.icon;

  const needsBottomScan =
    scanResult &&
    (scanResult.detected_pins === 0 || scanResult.action_required === 'SCAN_BOTTOM');

  const handleBottomUpload = async (file: File) => {
    if (!scanResult) return;
    setLocalError(null);
    setBottomUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const resp = await fetch(`${API_BASE}/scan/${encodeURIComponent(scanResult.scan_id)}/bottom`, {
        method: 'POST',
        body: formData,
      });
      if (!resp.ok) throw new Error(`Bottom scan failed: ${resp.status}`);
      const data: ScanResult = await resp.json();
      onResultUpdate(data);
    } catch (err: any) {
      setLocalError('Failed to upload. Please try again.');
    } finally {
      setBottomUploading(false);
      if (bottomFileRef.current) bottomFileRef.current.value = '';
    }
  };

  const handleOverride = async () => {
    if (!scanResult || !overridePart.trim()) return;
    setLocalError(null);
    setOverrideLoading(true);
    try {
      const payload = {
        scan_id: scanResult.scan_id,
        manual_part_number: overridePart.trim(),
        operator_note: overrideNote.trim() || undefined,
      };
      const resp = await fetch(`${API_BASE}/scan/override`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error(`Override failed: ${resp.status}`);
      const data: ScanResult = await resp.json();
      onResultUpdate(data);
      setOverrideNote('');
      setShowOverride(false);
    } catch (err: any) {
      setLocalError('Failed to save override.');
    } finally {
      setOverrideLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      {/* Header */}
      <div className={cn(
        'px-5 py-4 border-b',
        config ? config.bgColor : 'bg-slate-50',
        config ? config.borderColor : 'border-slate-200'
      )}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={cn(
              'w-10 h-10 rounded-lg flex items-center justify-center',
              config ? config.bgColor : 'bg-white',
              config ? config.borderColor : 'border-slate-200',
              'border'
            )}>
              {StatusIcon ? (
                <StatusIcon className={cn('w-5 h-5', config?.color)} />
              ) : (
                <Scan className="w-5 h-5 text-slate-500" />
              )}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                {scanResult ? 'Detection Complete' : 'Ready to Analyze'}
              </h3>
              <p className={cn('text-xs font-medium', config ? config.color : 'text-slate-500')}>
                {scanResult ? config?.label : 'Image captured'}
              </p>
            </div>
          </div>
          {scanResult && (
            <div className={cn(
              'px-2.5 py-1 rounded-full text-xs font-semibold',
              config?.bgColor,
              config?.color
            )}>
              {scanResult.confidence_score.toFixed(0)}%
            </div>
          )}
        </div>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {/* Image Preview */}
        <div className="relative rounded-lg overflow-hidden border border-slate-200 bg-slate-100">
          <img src={capturedImage} alt="Captured IC" className="w-full aspect-video object-contain" />
          {scanResult && (
            <div className={cn(
              'absolute top-2 right-2 px-2 py-1 rounded text-xs font-medium',
              config?.bgColor, config?.color
            )}>
              {config?.label}
            </div>
          )}
        </div>

        {/* Analyze Button */}
        {!scanResult && !isAnalyzing && (
          <Button 
            onClick={onAnalyze} 
            size="lg" 
            className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-semibold shadow-sm"
          >
            <Scan className="w-5 h-5 mr-2" />
            Analyze Image
          </Button>
        )}

        {/* Analyzing State */}
        {isAnalyzing && (
          <div className="py-8 flex flex-col items-center justify-center bg-slate-50 rounded-lg border border-slate-200">
            <Loader2 className="w-10 h-10 text-blue-600 animate-spin mb-3" />
            <p className="text-sm font-medium text-slate-700">Analyzing IC...</p>
            <p className="text-xs text-slate-400 mt-1">This may take a moment</p>
          </div>
        )}

        {/* Results */}
        {scanResult && (
          <>
            {/* Verification Not Implemented Notice */}
            <div className="p-3 rounded-lg border-2 border-amber-300 bg-amber-50">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-amber-800">Verification Not Implemented</p>
                  <p className="text-xs text-amber-700 mt-1">
                    This is detection only. Actual IC verification against database is not yet implemented.
                  </p>
                </div>
              </div>
            </div>

            {/* Status Message */}
            <div className={cn('p-3 rounded-lg border', config?.bgColor, config?.borderColor)}>
              <p className="text-sm text-slate-700">{scanResult.message}</p>
            </div>

            {/* Bottom Scan Prompt */}
            {needsBottomScan && (
              <div className="p-4 rounded-lg border border-amber-200 bg-amber-50">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 shrink-0" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-amber-800 mb-2">Pins not detected</p>
                    <p className="text-xs text-amber-700 mb-3">Please upload a bottom-view image to count pins.</p>
                    <input
                      ref={bottomFileRef}
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) handleBottomUpload(file);
                      }}
                    />
                    <Button
                      size="sm"
                      disabled={bottomUploading}
                      onClick={() => bottomFileRef.current?.click()}
                      className="bg-amber-600 hover:bg-amber-700 text-white"
                    >
                      {bottomUploading ? (
                        <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Uploading...</>
                      ) : (
                        <><Upload className="w-4 h-4 mr-2" />Upload Bottom View</>
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Key Metrics */}
            <div className="grid grid-cols-2 gap-3">
              {/* Part Number */}
              <div className="col-span-2 p-4 rounded-lg bg-slate-50 border border-slate-200">
                <div className="flex items-center gap-2 mb-1">
                  <Hash className="w-4 h-4 text-slate-400" />
                  <span className="text-xs font-medium text-slate-500">Part Number</span>
                </div>
                <p className="text-lg font-semibold text-slate-900 font-mono break-all">
                  {scanResult.part_number || 'Not detected'}
                </p>
              </div>

              {/* Manufacturer */}
              {scanResult.manufacturer_detected && (
                <div className="col-span-2 p-3 rounded-lg bg-slate-50 border border-slate-200">
                  <div className="flex items-center gap-2 mb-1">
                    <Building2 className="w-4 h-4 text-slate-400" />
                    <span className="text-xs font-medium text-slate-500">Manufacturer</span>
                  </div>
                  <p className="text-sm font-medium text-slate-900">{scanResult.manufacturer_detected}</p>
                </div>
              )}

              {/* Pins */}
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                <div className="flex items-center gap-2 mb-1">
                  <Cpu className="w-4 h-4 text-slate-400" />
                  <span className="text-xs font-medium text-slate-500">Pins</span>
                </div>
                <p className="text-xl font-semibold text-slate-900 font-mono">{scanResult.detected_pins}</p>
              </div>

              {/* Confidence */}
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                <div className="flex items-center gap-2 mb-1">
                  <Zap className="w-4 h-4 text-slate-400" />
                  <span className="text-xs font-medium text-slate-500">Confidence</span>
                </div>
                <p className="text-xl font-semibold text-slate-900 font-mono">{scanResult.confidence_score.toFixed(0)}%</p>
              </div>
            </div>

            {/* IC Specifications */}
            {scanResult.ic_specification && (
              <div className="space-y-3">
                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Specifications</h4>
                
                <div className="space-y-2">
                  {scanResult.ic_specification.package_type && (
                    <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-200">
                      <div className="flex items-center gap-2">
                        <Package className="w-4 h-4 text-slate-400" />
                        <span className="text-xs text-slate-500">Package</span>
                      </div>
                      <span className="text-sm font-medium text-slate-900">{scanResult.ic_specification.package_type}</span>
                    </div>
                  )}

                  {scanResult.ic_specification.description && (
                    <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                      <div className="flex items-center gap-2 mb-1">
                        <FileText className="w-4 h-4 text-slate-400" />
                        <span className="text-xs text-slate-500">Description</span>
                      </div>
                      <p className="text-sm text-slate-700">{scanResult.ic_specification.description}</p>
                    </div>
                  )}

                  {scanResult.ic_specification.voltage_min && scanResult.ic_specification.voltage_max && (
                    <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-200">
                      <div className="flex items-center gap-2">
                        <Zap className="w-4 h-4 text-slate-400" />
                        <span className="text-xs text-slate-500">Voltage</span>
                      </div>
                      <span className="text-sm font-medium text-slate-900">
                        {scanResult.ic_specification.voltage_min}V - {scanResult.ic_specification.voltage_max}V
                      </span>
                    </div>
                  )}

                  {scanResult.ic_specification.operating_temp_min && scanResult.ic_specification.operating_temp_max && (
                    <div className="flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-200">
                      <div className="flex items-center gap-2">
                        <Thermometer className="w-4 h-4 text-slate-400" />
                        <span className="text-xs text-slate-500">Temp Range</span>
                      </div>
                      <span className="text-sm font-medium text-slate-900">
                        {scanResult.ic_specification.operating_temp_min}°C to {scanResult.ic_specification.operating_temp_max}°C
                      </span>
                    </div>
                  )}
                </div>

                {scanResult.ic_specification.datasheet_path && (
                  <a href={scanResult.ic_specification.datasheet_path} target="_blank" rel="noopener noreferrer" className="block">
                    <Button variant="outline" className="w-full" size="sm">
                      <FileText className="w-4 h-4 mr-2" />
                      View Datasheet
                      <ExternalLink className="w-4 h-4 ml-2" />
                    </Button>
                  </a>
                )}
              </div>
            )}

            {/* Manual Override Toggle */}
            <button
              onClick={() => setShowOverride(!showOverride)}
              className="w-full flex items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-200 hover:bg-slate-100 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Edit3 className="w-4 h-4 text-slate-500" />
                <span className="text-sm font-medium text-slate-700">Manual Override</span>
              </div>
              <svg className={cn("w-4 h-4 text-slate-400 transition-transform", showOverride && "rotate-180")} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {/* Override Form */}
            {showOverride && (
              <div className="p-4 rounded-lg border border-slate-200 bg-slate-50 space-y-3">
                <Input
                  placeholder="Correct part number"
                  value={overridePart}
                  onChange={(e) => setOverridePart(e.target.value)}
                  className="bg-white"
                />
                <Textarea
                  placeholder="Note (optional)"
                  value={overrideNote}
                  onChange={(e) => setOverrideNote(e.target.value)}
                  rows={2}
                  className="bg-white resize-none"
                />
                <Button
                  size="sm"
                  disabled={overrideLoading || !overridePart.trim()}
                  onClick={handleOverride}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                >
                  {overrideLoading ? (
                    <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Saving...</>
                  ) : (
                    'Save Override'
                  )}
                </Button>
              </div>
            )}

            {/* Error Message */}
            {localError && (
              <div className="p-3 rounded-lg border border-red-200 bg-red-50 text-sm text-red-700">
                {localError}
              </div>
            )}

            {/* Metadata */}
            <div className="pt-3 border-t border-slate-200">
              <div className="flex justify-between text-xs text-slate-400">
                <span>ID: {scanResult.scan_id.slice(0, 8)}</span>
                <span>{new Date(scanResult.scanned_at).toLocaleString()}</span>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
