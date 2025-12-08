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
  Ruler,
  Zap,
  Thermometer,
  ExternalLink,
  Sparkles,
  Loader2,
  Upload,
  Edit3,
} from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
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
  badgeColor: string;
}> = {
  PASS: { icon: CheckCircle2, label: 'Verified', color: 'text-emerald-600', bgColor: 'bg-emerald-50', badgeColor: 'bg-emerald-500' },
  FAIL: { icon: XCircle, label: 'Failed', color: 'text-red-600', bgColor: 'bg-red-50', badgeColor: 'bg-red-500' },
  PARTIAL: { icon: AlertTriangle, label: 'Partial', color: 'text-amber-600', bgColor: 'bg-amber-50', badgeColor: 'bg-amber-500' },
  UNKNOWN: { icon: HelpCircle, label: 'Unknown', color: 'text-slate-600', bgColor: 'bg-slate-50', badgeColor: 'bg-slate-500' },
  COUNTERFEIT: { icon: ShieldAlert, label: 'Counterfeit', color: 'text-red-700', bgColor: 'bg-red-100', badgeColor: 'bg-red-600' },
};

export function AnalysisPanel({ capturedImage, scanResult, isAnalyzing, onAnalyze, onResultUpdate }: AnalysisPanelProps) {
  const bottomFileRef = useRef<HTMLInputElement>(null);
  const [bottomUploading, setBottomUploading] = useState(false);
  const [overridePart, setOverridePart] = useState('');
  const [overrideNote, setOverrideNote] = useState('');
  const [overrideLoading, setOverrideLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    const pn = scanResult?.part_number_detected || scanResult?.part_number || '';
    setOverridePart(pn);
    setLocalError(null);
  }, [scanResult?.scan_id, scanResult?.part_number_detected, scanResult?.part_number]);

  if (!capturedImage) {
    return (
      <div className="h-full flex flex-col bg-white rounded-2xl shadow-2xl border-2 border-blue-300 p-6">
        <div className="flex-1 flex flex-col items-center justify-center">
          <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mb-4 shadow-xl">
            <Cpu className="w-12 h-12 text-white" />
          </div>
          <p className="text-lg font-bold text-slate-900 mb-2">No IC Captured</p>
          <p className="text-sm text-blue-600 font-medium text-center max-w-[220px]">
            Capture from camera or upload an image to begin analysis
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
      if (!resp.ok) {
        throw new Error(`Bottom scan failed: ${resp.status}`);
      }
      const data: ScanResult = await resp.json();
      onResultUpdate(data);
    } catch (err: any) {
      console.error('Bottom scan error:', err);
      setLocalError('Failed to upload bottom scan. Please try again.');
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
      if (!resp.ok) {
        throw new Error(`Override failed: ${resp.status}`);
      }
      const data: ScanResult = await resp.json();
      onResultUpdate(data);
      setOverrideNote('');
    } catch (err: any) {
      console.error('Override error:', err);
      setLocalError('Failed to override part number. Please try again.');
    } finally {
      setOverrideLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-white rounded-2xl shadow-2xl border-2 border-blue-300 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 bg-gradient-to-r from-blue-100 via-cyan-100 to-blue-100 border-b-2 border-blue-300">
        <div className="flex items-center gap-3">
          <div className={cn('flex items-center justify-center w-10 h-10 rounded-lg', config ? config.bgColor : 'bg-blue-50')}>
            {StatusIcon ? <StatusIcon className={cn('w-5 h-5', config?.color)} /> : <Sparkles className="w-5 h-5 text-blue-500" />}
          </div>
          <div className="flex-1">
            <h3 className="text-base font-bold text-slate-900">
              {scanResult ? 'Analysis Complete' : 'Captured Image'}
            </h3>
            <p className={cn('text-sm font-semibold', config ? config.color : 'text-blue-600')}>
              {scanResult ? config?.label : 'Ready for analysis'}
            </p>
          </div>
          {scanResult && (
            <Badge className={cn('text-xs font-semibold text-white', config?.badgeColor)}>
              {scanResult.confidence_score.toFixed(0)}%
            </Badge>
          )}
        </div>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {/* Image Preview */}
        <div className="relative rounded-lg overflow-hidden border-2 border-slate-400 bg-slate-100 shadow-md">
          <img src={capturedImage} alt="Captured IC" className="w-full aspect-video object-contain" />
          {scanResult && (
            <div className={cn('absolute top-3 right-3 px-3 py-1.5 rounded-full text-xs font-semibold backdrop-blur-sm shadow-lg border-2 border-white/50', config?.bgColor, config?.color)}>
              {config?.label}
            </div>
          )}
        </div>

        {/* Analyze Button */}
        {!scanResult && !isAnalyzing && (
          <Button onClick={onAnalyze} size="lg" className="w-full h-16 bg-gradient-to-r from-blue-600 via-cyan-600 to-blue-700 hover:from-blue-700 hover:via-cyan-700 hover:to-blue-800 text-white font-black text-lg shadow-2xl animate-pulse">
            <Sparkles className="w-6 h-6 mr-2" />
            Analyze IC Image
          </Button>
        )}

        {/* Analyzing State */}
        {isAnalyzing && (
          <div className="py-10 flex flex-col items-center justify-center bg-gradient-to-br from-blue-50 to-cyan-50 rounded-xl border-2 border-blue-400 shadow-xl">
            <Loader2 className="w-16 h-16 text-blue-600 animate-spin mb-4" />
            <p className="text-lg font-black text-blue-700">Analyzing IC...</p>
            <p className="text-sm text-cyan-600 font-semibold mt-2">Extracting parameters</p>
          </div>
        )}

        {/* Results */}
        {scanResult && (
          <>
            {/* Status Card */}
            <div className={cn('p-4 rounded-lg border-2 shadow-md', config?.bgColor)}>
              <div className="flex items-start gap-3">
                {StatusIcon && <StatusIcon className={cn('w-5 h-5 mt-0.5', config?.color)} />}
                <div>
                  <p className={cn('font-semibold text-sm', config?.color)}>{config?.label}</p>
                  <p className="text-xs text-slate-600 mt-1">{scanResult.message}</p>
                </div>
              </div>
            </div>

            {/* Bottom Scan prompt */}
            {needsBottomScan && (
              <div className="p-4 rounded-xl border-2 border-amber-400 bg-amber-50 space-y-3">
                <div className="flex items-center gap-2 text-amber-700 font-semibold">
                  <AlertTriangle className="w-5 h-5" />
                  <span>Pins not visible. Please upload bottom-view image.</span>
                </div>
                <div className="flex items-center gap-2">
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
                    disabled={bottomUploading}
                    onClick={() => bottomFileRef.current?.click()}
                    className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white font-semibold"
                  >
                    {bottomUploading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Uploading...
                      </>
                    ) : (
                      <>
                        <Upload className="w-4 h-4 mr-2" />
                        Upload Bottom View
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}

            {/* Manual Override */}
            <div className="p-4 rounded-xl border-2 border-blue-200 bg-blue-50 space-y-3">
              <div className="flex items-center gap-2 text-blue-800 font-semibold">
                <Edit3 className="w-5 h-5" />
                <span>Manual Part Number Override</span>
              </div>
              <div className="grid grid-cols-1 gap-3">
                <Input
                  placeholder="Enter correct part number"
                  value={overridePart}
                  onChange={(e) => setOverridePart(e.target.value)}
                  className="border-2 border-blue-200"
                />
                <Textarea
                  placeholder="Note (optional)"
                  value={overrideNote}
                  onChange={(e) => setOverrideNote(e.target.value)}
                  rows={2}
                  className="border-2 border-blue-200"
                />
                <Button
                  disabled={overrideLoading || !overridePart.trim()}
                  onClick={handleOverride}
                  className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white font-semibold"
                >
                  {overrideLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    'Save Override'
                  )}
                </Button>
              </div>
            </div>

            {localError && (
              <div className="p-3 rounded-lg border-2 border-red-300 bg-red-50 text-sm text-red-700">
                {localError}
              </div>
            )}

            {/* Parameters Grid */}
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2 p-4 rounded-lg bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-300 shadow-md">
                <div className="flex items-center gap-2 mb-2">
                  <Hash className="w-4 h-4 text-blue-600" />
                  <span className="text-xs font-medium text-blue-900">Part Number</span>
                </div>
                <p className="text-xl font-bold text-blue-900 font-mono break-all">
                  {scanResult.part_number_detected || scanResult.part_number || 'N/A'}
                </p>
              </div>

              {scanResult.manufacturer_detected && (
                <div className="col-span-2 p-4 rounded-lg bg-gradient-to-br from-purple-50 to-pink-50 border-2 border-purple-300 shadow-md">
                  <div className="flex items-center gap-2 mb-2">
                    <Building2 className="w-4 h-4 text-purple-600" />
                    <span className="text-xs font-medium text-purple-900">Manufacturer</span>
                  </div>
                  <p className="text-base font-semibold text-purple-900">{scanResult.manufacturer_detected}</p>
                </div>
              )}

              <div className="p-4 rounded-lg bg-gradient-to-br from-emerald-50 to-teal-50 border-2 border-emerald-300 shadow-md">
                <div className="flex items-center gap-2 mb-2">
                  <Cpu className="w-4 h-4 text-emerald-600" />
                  <span className="text-xs font-medium text-emerald-900">Pins</span>
                </div>
                <p className="text-2xl font-bold text-emerald-900 font-mono">{scanResult.detected_pins}</p>
              </div>

              <div className="p-4 rounded-lg bg-gradient-to-br from-amber-50 to-orange-50 border-2 border-amber-300 shadow-md">
                <div className="flex items-center gap-2 mb-2">
                  <Sparkles className="w-4 h-4 text-amber-600" />
                  <span className="text-xs font-medium text-amber-900">Confidence</span>
                </div>
                <p className="text-2xl font-bold text-amber-900 font-mono">{scanResult.confidence_score.toFixed(1)}%</p>
              </div>
            </div>

            {/* IC Specifications */}
            {scanResult.ic_specification && (
              <div className="space-y-3">
                <h4 className="text-xs font-semibold text-slate-900 uppercase">IC Specification</h4>
                
                {scanResult.ic_specification.package_type && (
                  <div className="p-3 rounded-lg bg-slate-50 border-2 border-slate-300 shadow-sm">
                    <div className="flex items-center gap-2 mb-1">
                      <Package className="w-3.5 h-3.5 text-slate-500" />
                      <span className="text-xs font-medium text-slate-600">Package Type</span>
                    </div>
                    <p className="text-sm font-semibold text-slate-900">{scanResult.ic_specification.package_type}</p>
                  </div>
                )}

                {scanResult.ic_specification.description && (
                  <div className="p-3 rounded-lg bg-slate-50 border-2 border-slate-300 shadow-sm">
                    <div className="flex items-center gap-2 mb-1">
                      <FileText className="w-3.5 h-3.5 text-slate-500" />
                      <span className="text-xs font-medium text-slate-600">Description</span>
                    </div>
                    <p className="text-sm text-slate-900">{scanResult.ic_specification.description}</p>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-lg bg-slate-50 border-2 border-slate-300 shadow-sm">
                    <div className="flex items-center gap-2 mb-1">
                      <Ruler className="w-3.5 h-3.5 text-slate-500" />
                      <span className="text-xs font-medium text-slate-600">Spec Pins</span>
                    </div>
                    <p className="text-sm font-semibold text-slate-900 font-mono">{scanResult.ic_specification.pin_count}</p>
                  </div>

                  {scanResult.ic_specification.voltage_min && scanResult.ic_specification.voltage_max && (
                    <div className="p-3 rounded-lg bg-slate-50 border-2 border-slate-300 shadow-sm">
                      <div className="flex items-center gap-2 mb-1">
                        <Zap className="w-3.5 h-3.5 text-slate-500" />
                        <span className="text-xs font-medium text-slate-600">Voltage</span>
                      </div>
                      <p className="text-sm font-semibold text-slate-900">{scanResult.ic_specification.voltage_min}V - {scanResult.ic_specification.voltage_max}V</p>
                    </div>
                  )}
                </div>

                {scanResult.ic_specification.operating_temp_min && scanResult.ic_specification.operating_temp_max && (
                  <div className="p-3 rounded-lg bg-slate-50 border-2 border-slate-300 shadow-sm">
                    <div className="flex items-center gap-2 mb-1">
                      <Thermometer className="w-3.5 h-3.5 text-slate-500" />
                      <span className="text-xs font-medium text-slate-600">Temperature Range</span>
                    </div>
                    <p className="text-sm font-semibold text-slate-900">{scanResult.ic_specification.operating_temp_min}°C to {scanResult.ic_specification.operating_temp_max}°C</p>
                  </div>
                )}

                {scanResult.ic_specification.datasheet_path && (
                  <a href={scanResult.ic_specification.datasheet_path} target="_blank" rel="noopener noreferrer">
                    <Button className="w-full bg-blue-600 hover:bg-blue-700 text-white shadow-lg" size="lg">
                      <FileText className="w-4 h-4 mr-2" />
                      View Datasheet
                      <ExternalLink className="w-4 h-4 ml-2" />
                    </Button>
                  </a>
                )}
              </div>
            )}

            {/* Metadata */}
            <div className="pt-3 border-t-2 border-slate-300">
              <div className="text-xs text-slate-500 space-y-1">
                <div className="flex justify-between">
                  <span>Scan ID:</span>
                  <span className="font-mono">{scanResult.scan_id.slice(0, 8)}...</span>
                </div>
                <div className="flex justify-between">
                  <span>Scanned At:</span>
                  <span>{new Date(scanResult.scanned_at).toLocaleString()}</span>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

