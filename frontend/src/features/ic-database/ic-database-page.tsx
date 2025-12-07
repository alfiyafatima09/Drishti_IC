import { useState, useCallback, useEffect, useRef } from 'react';
import { Search, Download, Cpu, Package, Zap, Thermometer, AlertCircle, CheckCircle, Database, Loader2 } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface ICSearchResultItem {
  part_number: string;
  manufacturer: string;
  manufacturer_name?: string;
  pin_count: number;
  package_type?: string;
  description?: string;
  has_datasheet?: boolean;
}

interface ICSearchResult {
  results: ICSearchResultItem[];
  total_count: number;
  limit: number;
  offset: number;
}

interface ICSpecification {
  part_number: string;
  manufacturer: string;
  manufacturer_name?: string;
  pin_count: number;
  package_type?: string;
  description?: string;
  datasheet_url?: string;
  datasheet_path?: string;
  has_datasheet?: boolean;
  voltage_min?: number;
  voltage_max?: number;
  operating_temp_min?: number;
  operating_temp_max?: number;
  electrical_specs?: Record<string, any>;
  source?: string;
  created_at?: string;
  updated_at?: string;
}

export default function ICDatabasePage() {
  const [searchResults, setSearchResults] = useState<ICSearchResult | null>(null);
  const [selectedIC, setSelectedIC] = useState<ICSpecification | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [hasResultsOnce, setHasResultsOnce] = useState(false);
  const inFlightController = useRef<AbortController | null>(null);

  const fetchSearch = useCallback(
    async (term: string) => {
      const trimmed = term.trim();
      if (!trimmed) {
        setSearchResults(null);
        setSelectedIC(null);
        setError(null);
        return;
      }

      setIsSearching(true);
      setError(null);

      // cancel any in-flight request
      if (inFlightController.current) {
        inFlightController.current.abort();
      }
      const controller = new AbortController();
      inFlightController.current = controller;

      try {
        const params = new URLSearchParams();
        params.append('q', trimmed);
        params.append('limit', '20');
        params.append('offset', '0');

        const response = await fetch(`${API_BASE}/api/v1/ic/search?${params.toString()}`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error('Search request failed');
        }

        const data: ICSearchResult = await response.json();
        setSearchResults(data);
        setHasResultsOnce(true);

        if (data.results.length === 0) {
          setError('No ICs found. Try a different part number.');
        }
      } catch (err: any) {
        if (err?.name === 'AbortError') {
          return;
        }
        setError('Failed to load IC list. Please try again.');
        console.error('List error:', err);
      } finally {
        if (inFlightController.current === controller) {
          inFlightController.current = null;
        }
        setIsSearching(false);
      }
    },
    []
  );

  // Debounced search on query input
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchSearch(query);
    }, 500);
    return () => {
      clearTimeout(timer);
      if (inFlightController.current) inFlightController.current.abort();
    };
  }, [query, fetchSearch]);

  const handleICClick = useCallback(async (partNumber: string) => {
    setIsLoadingDetails(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/api/v1/ic/details?part_number=${encodeURIComponent(partNumber)}`);
      
      if (!response.ok) {
        throw new Error('Failed to load IC details');
      }

      const data: ICSpecification = await response.json();
      setSelectedIC(data);
    } catch (err) {
      setError('Failed to load IC details. Please try again.');
      console.error('Details error:', err);
    } finally {
      setIsLoadingDetails(false);
    }
  }, []);

  const handleDownloadDatasheet = useCallback(async (partNumber: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/ic/datasheet?part_number=${encodeURIComponent(partNumber)}`);
      
      if (!response.ok) {
        throw new Error('Failed to download datasheet');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${partNumber}_datasheet.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError('Failed to download datasheet');
      console.error('Download error:', err);
    }
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-cyan-50 to-blue-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header Section */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">IC Database</h1>
          <p className="text-gray-600 text-lg">Search and explore integrated circuit specifications</p>
        </div>

        {/* Search Bar */}
        <div className="mb-6">
          <div className="relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  fetchSearch(query);
                }
              }}
              placeholder="Search by part number (e.g., LM555, STM32, NE555)..."
              className="w-full px-6 py-4 pl-14 text-lg border-3 border-blue-300 rounded-2xl 
                       focus:outline-none focus:ring-4 focus:ring-blue-400 focus:border-blue-500
                       bg-white shadow-lg transition-all"
              aria-label="Search part number"
            />
            <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-blue-500" size={24} />
            <button
              onClick={() => fetchSearch(query)}
              disabled={isSearching}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 
                       px-6 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 text-white 
                       rounded-xl hover:from-blue-700 hover:to-cyan-700 
                       disabled:opacity-50 disabled:cursor-not-allowed
                       font-semibold shadow-md transition-all"
            >
              {isSearching ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="animate-spin" size={18} />
                  Refreshing...
                </span>
              ) : (
                'Search'
              )}
            </button>
          </div>
        </div>


        {/* Error Message */}
        {error && !isSearching && (
          <div className="mb-6 p-4 bg-red-100 border-2 border-red-400 rounded-xl flex items-center gap-3">
            <AlertCircle className="text-red-600" size={24} />
            <p className="text-red-800 font-medium">{error}</p>
          </div>
        )}

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Panel: Search Results */}
          <div className="space-y-4">
            {isSearching && !hasResultsOnce && (
              <div className="bg-white rounded-2xl shadow-xl border-3 border-blue-200 p-10 flex flex-col items-center justify-center space-y-4 animate-pulse">
                <div className="h-16 w-16 rounded-full border-4 border-blue-300 border-t-transparent animate-spin" />
                <div className="text-center">
                  <p className="text-xl font-bold text-gray-700">Loading IC catalog…</p>
                  <p className="text-gray-500">Fetching data from server</p>
                </div>
              </div>
            )}

            {searchResults && (
              <div className="bg-white rounded-2xl shadow-xl border-3 border-blue-200 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-2xl font-bold text-gray-800">Search Results</h2>
                  <div className="flex items-center gap-3">
                    {isSearching && (
                      <div className="flex items-center gap-2 text-sm text-blue-600">
                        <Loader2 className="animate-spin" size={16} />
                        <span>Refreshing…</span>
                      </div>
                    )}
                    <span className="px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-full text-sm font-bold">
                      {searchResults.total_count} found
                    </span>
                  </div>
                </div>
                
                <div className="space-y-3 max-h-[calc(100vh-400px)] overflow-y-auto pr-2">
                  {searchResults.results.map((ic, index) => (
                    <div
                      key={`${ic.part_number}-${ic.manufacturer}-${index}`}
                      onClick={() => handleICClick(ic.part_number)}
                      className={`p-4 rounded-xl border-2 cursor-pointer transition-all hover:shadow-lg
                        ${selectedIC?.part_number === ic.part_number && selectedIC?.manufacturer === ic.manufacturer
                          ? 'border-green-500 bg-green-50 shadow-md'
                          : 'border-blue-200 bg-blue-50 hover:border-blue-400'
                        }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Cpu className="text-blue-600" size={20} />
                          <h3 className="text-xl font-bold text-gray-800">{ic.part_number}</h3>
                        </div>
                        {ic.has_datasheet && (
                          <CheckCircle className="text-green-600" size={20} />
                        )}
                      </div>
                      
                      <div className="space-y-1 text-sm">
                        <p className="text-gray-700">
                          <span className="font-semibold">Manufacturer:</span> {ic.manufacturer_name}
                        </p>
                        <p className="text-gray-700">
                          <span className="font-semibold">Package:</span> {ic.package_type} • 
                          <span className="font-semibold"> Pins:</span> {ic.pin_count}
                        </p>
                        <p className="text-gray-600 mt-2 line-clamp-2">{ic.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {!searchResults && !isSearching && (
              <div className="bg-white rounded-2xl shadow-xl border-3 border-blue-200 p-12 text-center">
                <Database className="mx-auto text-blue-400 mb-4" size={64} />
                <h3 className="text-xl font-bold text-gray-700 mb-2">Search IC Database</h3>
                <p className="text-gray-500">Enter an IC part number to get started</p>
              </div>
            )}
          </div>

          {/* Right Panel: IC Details */}
          <div className="space-y-4">
            {isLoadingDetails && (
              <div className="bg-white rounded-2xl shadow-xl border-3 border-blue-200 p-12 text-center">
                <Loader2 className="mx-auto text-blue-600 animate-spin mb-4" size={64} />
                <p className="text-gray-600 font-medium">Loading IC details...</p>
              </div>
            )}

            {selectedIC && !isLoadingDetails && (
              <div className="bg-white rounded-2xl shadow-xl border-3 border-green-400 p-6 space-y-6">
                {/* Header */}
                <div className="border-b-2 border-gray-200 pb-4">
                  <div className="flex items-center justify-between mb-2">
                    <h2 className="text-3xl font-bold text-gray-800">{selectedIC.part_number}</h2>
                    {selectedIC.has_datasheet && (
                      <button
                        onClick={() => handleDownloadDatasheet(selectedIC.part_number)}
                        className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-green-600 to-emerald-600 
                                 text-white rounded-xl hover:from-green-700 hover:to-emerald-700 
                                 font-semibold shadow-md transition-all"
                      >
                        <Download size={18} />
                        Datasheet
                      </button>
                    )}
                  </div>
                  <p className="text-lg text-gray-600 font-medium">{selectedIC.manufacturer_name}</p>
                </div>

                {/* Description */}
                <div className="bg-blue-50 border-2 border-blue-300 rounded-xl p-4">
                  <p className="text-gray-700 leading-relaxed">{selectedIC.description}</p>
                </div>

                {/* Basic Specifications */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gradient-to-br from-purple-100 to-pink-100 border-2 border-purple-300 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Package className="text-purple-600" size={20} />
                      <p className="text-sm font-semibold text-purple-900">Package Type</p>
                    </div>
                    <p className="text-2xl font-bold text-purple-800">{selectedIC.package_type}</p>
                  </div>

                  <div className="bg-gradient-to-br from-blue-100 to-cyan-100 border-2 border-blue-300 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Cpu className="text-blue-600" size={20} />
                      <p className="text-sm font-semibold text-blue-900">Pin Count</p>
                    </div>
                    <p className="text-2xl font-bold text-blue-800">{selectedIC.pin_count} pins</p>
                  </div>
                </div>

                {/* Voltage & Temperature */}
                {(selectedIC.voltage_min !== undefined || selectedIC.operating_temp_min !== undefined) && (
                  <div className="space-y-4">
                    <h3 className="text-xl font-bold text-gray-800 flex items-center gap-2">
                      <Zap className="text-yellow-600" size={24} />
                      Operating Conditions
                    </h3>

                    <div className="grid grid-cols-2 gap-4">
                      {selectedIC.voltage_min !== undefined && (
                        <div className="bg-gradient-to-br from-yellow-100 to-orange-100 border-2 border-yellow-400 rounded-xl p-4">
                          <p className="text-sm font-semibold text-yellow-900 mb-1">Voltage Range</p>
                          <p className="text-xl font-bold text-yellow-800">
                            {selectedIC.voltage_min}V - {selectedIC.voltage_max}V
                          </p>
                        </div>
                      )}

                      {selectedIC.operating_temp_min !== undefined && (
                        <div className="bg-gradient-to-br from-cyan-100 to-blue-100 border-2 border-cyan-400 rounded-xl p-4">
                          <div className="flex items-center gap-2 mb-1">
                            <Thermometer className="text-cyan-600" size={18} />
                            <p className="text-sm font-semibold text-cyan-900">Temperature Range</p>
                          </div>
                          <p className="text-xl font-bold text-cyan-800">
                            {selectedIC.operating_temp_min}°C - {selectedIC.operating_temp_max}°C
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Electrical Specifications */}
                {selectedIC.electrical_specs && Object.keys(selectedIC.electrical_specs).length > 0 && (
                  <div className="space-y-4">
                    <h3 className="text-xl font-bold text-gray-800">Electrical Specifications</h3>
                    <div className="bg-gradient-to-br from-indigo-50 to-purple-50 border-2 border-indigo-300 rounded-xl p-4 space-y-2">
                      {Object.entries(selectedIC.electrical_specs).map(([key, value]) => (
                        <div key={key} className="flex justify-between items-center py-2 border-b border-indigo-200 last:border-0">
                          <span className="text-gray-700 font-medium capitalize">
                            {key.replace(/_/g, ' ')}
                          </span>
                          <span className="text-gray-900 font-bold">{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Metadata */}
                <div className="grid grid-cols-2 gap-4 pt-4 border-t-2 border-gray-200">
                  <div>
                    <p className="text-sm text-gray-500 mb-1">Data Source</p>
                    <p className="text-sm font-semibold text-gray-800">
                      {selectedIC.source?.replace(/_/g, ' ') || 'N/A'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 mb-1">Last Updated</p>
                    <p className="text-sm font-semibold text-gray-800">
                      {selectedIC.updated_at 
                        ? new Date(selectedIC.updated_at).toLocaleDateString()
                        : 'N/A'
                      }
                    </p>
                  </div>
                </div>

                {/* Datasheet URL */}
                {selectedIC.datasheet_url && (
                  <div className="bg-gray-50 border-2 border-gray-300 rounded-xl p-4">
                    <p className="text-sm text-gray-600 mb-2">Original Datasheet URL</p>
                    <a
                      href={selectedIC.datasheet_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 font-medium text-sm break-all underline"
                    >
                      {selectedIC.datasheet_url}
                    </a>
                  </div>
                )}
              </div>
            )}

            {!selectedIC && !isLoadingDetails && searchResults && (
              <div className="bg-white rounded-2xl shadow-xl border-3 border-gray-300 p-12 text-center">
                <Cpu className="mx-auto text-gray-400 mb-4" size={64} />
                <h3 className="text-xl font-bold text-gray-700 mb-2">Select an IC</h3>
                <p className="text-gray-500">Click on an IC from the search results to view details</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

