import { useState } from 'react';
import { 
  Globe, 
  Download, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  ArrowRight,
  Trash2,
  AlertCircle,
  Database,
  FileText,
  Plus,
  Shield
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';

// Mock data - replace with actual API calls
const mockQueueData = [
  { part_number: 'STM32F103', added_at: '2025-12-04T10:30:00Z', status: 'pending' },
  { part_number: 'ATMEGA328P', added_at: '2025-12-04T09:15:00Z', status: 'pending' },
  { part_number: 'LM358', added_at: '2025-12-03T14:20:00Z', status: 'pending' },
];

type SyncStage = 'idle' | 'connecting' | 'scraping' | 'downloading' | 'updating' | 'completed' | 'error';

export default function ScrapingPage() {
  const [queueItems, setQueueItems] = useState(mockQueueData);
  const [syncStage, setSyncStage] = useState<SyncStage>('idle');
  const [currentIC, setCurrentIC] = useState('');
  const [progress, setProgress] = useState(0);
  
  // Form states
  const [fakeIC, setFakeIC] = useState({ part_number: '', reason: '', reported_by: '' });
  const [manualIC, setManualIC] = useState({
    part_number: '',
    manufacturer: '',
    pin_count: '',
    package_type: '',
    description: '',
    voltage_min: '',
    voltage_max: '',
    temp_min: '',
    temp_max: ''
  });

  const handleStartSync = () => {
    // Simulate sync process
    setSyncStage('connecting');
    setProgress(0);
    
    setTimeout(() => {
      setSyncStage('scraping');
      setCurrentIC(queueItems[0]?.part_number || '');
      setProgress(25);
    }, 1500);
    
    setTimeout(() => {
      setSyncStage('downloading');
      setProgress(50);
    }, 3000);
    
    setTimeout(() => {
      setSyncStage('updating');
      setProgress(75);
    }, 4500);
    
    setTimeout(() => {
      setSyncStage('completed');
      setProgress(100);
    }, 6000);
    
    setTimeout(() => {
      setSyncStage('idle');
      setProgress(0);
      setCurrentIC('');
    }, 8000);
  };

  const handleRemoveFromQueue = (partNumber: string) => {
    setQueueItems(items => items.filter(item => item.part_number !== partNumber));
  };

  const handleMarkAsFake = () => {
    console.log('Marking as fake:', fakeIC);
    setFakeIC({ part_number: '', reason: '', reported_by: '' });
  };

  const handleAddManualIC = () => {
    console.log('Adding manual IC:', manualIC);
    setManualIC({
      part_number: '', manufacturer: '', pin_count: '', package_type: '',
      description: '', voltage_min: '', voltage_max: '', temp_min: '', temp_max: ''
    });
  };

  const stageConfig: Record<SyncStage, { label: string; color: string; icon: typeof Globe }> = {
    idle: { label: 'Ready to Sync', color: 'border-slate-300 bg-slate-50', icon: Globe },
    connecting: { label: 'Connecting to Internet', color: 'border-blue-400 bg-blue-50 animate-pulse', icon: Globe },
    scraping: { label: 'Scraping IC Data', color: 'border-cyan-400 bg-cyan-50 animate-pulse', icon: Download },
    downloading: { label: 'Downloading Datasheet', color: 'border-purple-400 bg-purple-50 animate-pulse', icon: FileText },
    updating: { label: 'Updating Database', color: 'border-amber-400 bg-amber-50 animate-pulse', icon: Database },
    completed: { label: 'Sync Completed', color: 'border-emerald-400 bg-emerald-50', icon: CheckCircle2 },
    error: { label: 'Sync Failed', color: 'border-red-400 bg-red-50', icon: XCircle },
  };

  return (
    <div className="flex flex-col h-full gap-6 p-6 overflow-hidden bg-gradient-to-br from-blue-50 via-cyan-50 to-blue-100">
      {/* Header */}
      <div className="shrink-0">
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 shadow-lg border-2 border-blue-200">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-black bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent mb-2">
                IC Data Management
              </h1>
              <p className="text-base font-semibold text-slate-700">
                Scrape datasheets, manage queue, and add IC specifications
              </p>
            </div>
            <Globe className="w-12 h-12 text-cyan-600" />
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Queue Table & Sync */}
          <div className="lg:col-span-2 space-y-6">
            {/* Sync Control */}
            <div className="bg-white rounded-2xl shadow-xl border-2 border-blue-300 p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-slate-900">Internet Sync & Scraping</h2>
                <Badge className="bg-blue-500 text-white font-bold">
                  {queueItems.length} in Queue
                </Badge>
              </div>

              <div className="space-y-4">
                <p className="text-sm text-slate-600 font-medium">
                  Connect to the internet to scrape IC datasheets and update the database automatically
                </p>

                <Button
                  onClick={handleStartSync}
                  disabled={syncStage !== 'idle' || queueItems.length === 0}
                  className="w-full h-14 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white font-bold text-base shadow-xl"
                >
                  <Globe className="w-5 h-5 mr-2" />
                  Start Sync & Scrape Queue
                </Button>

                {/* Sync Progress */}
                {syncStage !== 'idle' && (
                  <div className="space-y-3">
                    {/* Progress Bar */}
                    <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-blue-600 to-cyan-600 transition-all duration-500"
                        style={{ width: `${progress}%` }}
                      />
                    </div>

                    {/* Stage Flow */}
                    <div className="grid grid-cols-5 gap-2">
                      {(['connecting', 'scraping', 'downloading', 'updating', 'completed'] as SyncStage[]).map((stage, idx) => {
                        const config = stageConfig[stage];
                        const Icon = config.icon;
                        const isActive = syncStage === stage;
                        const isPast = ['connecting', 'scraping', 'downloading', 'updating', 'completed'].indexOf(syncStage) > idx;
                        
                        return (
                          <div key={stage} className="flex flex-col items-center">
                            <div className={cn(
                              'w-12 h-12 rounded-xl border-2 flex items-center justify-center mb-2 transition-all',
                              isActive ? config.color : isPast ? 'border-emerald-400 bg-emerald-50' : 'border-slate-300 bg-slate-50'
                            )}>
                              <Icon className={cn('w-6 h-6', isActive ? 'text-blue-600' : isPast ? 'text-emerald-600' : 'text-slate-400')} />
                            </div>
                            {idx < 4 && (
                              <ArrowRight className="w-4 h-4 text-slate-400 absolute mt-5" style={{ marginLeft: '40px' }} />
                            )}
                          </div>
                        );
                      })}
                    </div>

                    {/* Current Status */}
                    <div className={cn('p-4 rounded-xl border-2', stageConfig[syncStage].color)}>
                      <p className="font-bold text-slate-900">{stageConfig[syncStage].label}</p>
                      {currentIC && <p className="text-sm text-slate-600 mt-1">Processing: {currentIC}</p>}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Queue Table */}
            <div className="bg-white rounded-2xl shadow-xl border-2 border-blue-300 p-6">
              <h2 className="text-xl font-bold text-slate-900 mb-4">Scraping Queue</h2>
              
              {queueItems.length === 0 ? (
                <div className="text-center py-12">
                  <Clock className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                  <p className="text-slate-500 font-medium">Queue is empty</p>
                  <p className="text-sm text-slate-400 mt-1">ICs will be added here when scanned but not found in database</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b-2 border-blue-200">
                        <th className="text-left py-3 px-4 font-bold text-slate-700">Part Number</th>
                        <th className="text-left py-3 px-4 font-bold text-slate-700">Added Date</th>
                        <th className="text-left py-3 px-4 font-bold text-slate-700">Status</th>
                        <th className="text-right py-3 px-4 font-bold text-slate-700">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {queueItems.map((item) => (
                        <tr key={item.part_number} className="border-b border-slate-200 hover:bg-blue-50 transition-colors">
                          <td className="py-3 px-4 font-mono font-bold text-blue-600">{item.part_number}</td>
                          <td className="py-3 px-4 text-slate-600 text-sm">
                            {new Date(item.added_at).toLocaleString()}
                          </td>
                          <td className="py-3 px-4">
                            <Badge className="bg-amber-100 text-amber-700 border border-amber-300 font-semibold">
                              <Clock className="w-3 h-3 mr-1" />
                              Pending
                            </Badge>
                          </td>
                          <td className="py-3 px-4 text-right">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleRemoveFromQueue(item.part_number)}
                              className="border-red-300 text-red-600 hover:bg-red-50"
                            >
                              <Trash2 className="w-4 h-4 mr-1" />
                              Remove
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* Right Column - Forms */}
          <div className="space-y-6">
            {/* Mark as Fake Form */}
            <div className="bg-white rounded-2xl shadow-xl border-2 border-red-300 p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-red-500 flex items-center justify-center">
                  <Shield className="w-5 h-5 text-white" />
                </div>
                <h2 className="text-lg font-bold text-slate-900">Mark IC as Fake</h2>
              </div>

              <div className="space-y-4">
                <div>
                  <Label className="text-sm font-bold text-slate-700 mb-2">Part Number</Label>
                  <Input
                    value={fakeIC.part_number}
                    onChange={(e) => setFakeIC({...fakeIC, part_number: e.target.value})}
                    placeholder="e.g., FAKE123"
                    className="h-11 border-2 border-red-200 focus:border-red-400"
                  />
                </div>

                <div>
                  <Label className="text-sm font-bold text-slate-700 mb-2">Reason</Label>
                  <Textarea
                    value={fakeIC.reason}
                    onChange={(e) => setFakeIC({...fakeIC, reason: e.target.value})}
                    placeholder="Why is this IC fake?"
                    rows={3}
                    className="border-2 border-red-200 focus:border-red-400"
                  />
                </div>

                <div>
                  <Label className="text-sm font-bold text-slate-700 mb-2">Reported By (Optional)</Label>
                  <Input
                    value={fakeIC.reported_by}
                    onChange={(e) => setFakeIC({...fakeIC, reported_by: e.target.value})}
                    placeholder="Your name"
                    className="h-11 border-2 border-red-200 focus:border-red-400"
                  />
                </div>

                <Button
                  onClick={handleMarkAsFake}
                  className="w-full h-12 bg-red-600 hover:bg-red-700 text-white font-bold shadow-lg"
                  disabled={!fakeIC.part_number || !fakeIC.reason}
                >
                  <AlertCircle className="w-5 h-5 mr-2" />
                  Mark as Counterfeit
                </Button>
              </div>
            </div>

            {/* Manual IC Entry Form */}
            <div className="bg-white rounded-2xl shadow-xl border-2 border-emerald-300 p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-emerald-500 flex items-center justify-center">
                  <Plus className="w-5 h-5 text-white" />
                </div>
                <h2 className="text-lg font-bold text-slate-900">Add IC Manually</h2>
              </div>

              <p className="text-xs text-slate-500 mb-4 font-medium">
                If scraping fails, enter IC specifications manually
              </p>

              <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
                <div>
                  <Label className="text-sm font-bold text-slate-700 mb-1">Part Number *</Label>
                  <Input
                    value={manualIC.part_number}
                    onChange={(e) => setManualIC({...manualIC, part_number: e.target.value})}
                    placeholder="e.g., LM555"
                    className="h-10 border-2 border-emerald-200 focus:border-emerald-400"
                  />
                </div>

                <div>
                  <Label className="text-sm font-bold text-slate-700 mb-1">Manufacturer *</Label>
                  <Input
                    value={manualIC.manufacturer}
                    onChange={(e) => setManualIC({...manualIC, manufacturer: e.target.value})}
                    placeholder="e.g., Texas Instruments"
                    className="h-10 border-2 border-emerald-200 focus:border-emerald-400"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-sm font-bold text-slate-700 mb-1">Pin Count *</Label>
                    <Input
                      type="number"
                      value={manualIC.pin_count}
                      onChange={(e) => setManualIC({...manualIC, pin_count: e.target.value})}
                      placeholder="8"
                      className="h-10 border-2 border-emerald-200 focus:border-emerald-400"
                    />
                  </div>

                  <div>
                    <Label className="text-sm font-bold text-slate-700 mb-1">Package</Label>
                    <Input
                      value={manualIC.package_type}
                      onChange={(e) => setManualIC({...manualIC, package_type: e.target.value})}
                      placeholder="DIP"
                      className="h-10 border-2 border-emerald-200 focus:border-emerald-400"
                    />
                  </div>
                </div>

                <div>
                  <Label className="text-sm font-bold text-slate-700 mb-1">Description</Label>
                  <Textarea
                    value={manualIC.description}
                    onChange={(e) => setManualIC({...manualIC, description: e.target.value})}
                    placeholder="IC functionality"
                    rows={2}
                    className="border-2 border-emerald-200 focus:border-emerald-400"
                  />
                </div>

                <div>
                  <Label className="text-sm font-bold text-slate-700 mb-1">Voltage Range (V)</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      type="number"
                      step="0.1"
                      value={manualIC.voltage_min}
                      onChange={(e) => setManualIC({...manualIC, voltage_min: e.target.value})}
                      placeholder="Min"
                      className="h-10 border-2 border-emerald-200 focus:border-emerald-400"
                    />
                    <Input
                      type="number"
                      step="0.1"
                      value={manualIC.voltage_max}
                      onChange={(e) => setManualIC({...manualIC, voltage_max: e.target.value})}
                      placeholder="Max"
                      className="h-10 border-2 border-emerald-200 focus:border-emerald-400"
                    />
                  </div>
                </div>

                <div>
                  <Label className="text-sm font-bold text-slate-700 mb-1">Temperature Range (°C)</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      type="number"
                      value={manualIC.temp_min}
                      onChange={(e) => setManualIC({...manualIC, temp_min: e.target.value})}
                      placeholder="Min"
                      className="h-10 border-2 border-emerald-200 focus:border-emerald-400"
                    />
                    <Input
                      type="number"
                      value={manualIC.temp_max}
                      onChange={(e) => setManualIC({...manualIC, temp_max: e.target.value})}
                      placeholder="Max"
                      className="h-10 border-2 border-emerald-200 focus:border-emerald-400"
                    />
                  </div>
                </div>

                <Button
                  onClick={handleAddManualIC}
                  className="w-full h-12 bg-emerald-600 hover:bg-emerald-700 text-white font-bold shadow-lg"
                  disabled={!manualIC.part_number || !manualIC.manufacturer || !manualIC.pin_count}
                >
                  <Database className="w-5 h-5 mr-2" />
                  Add to Database
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


