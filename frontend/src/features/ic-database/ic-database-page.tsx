import { useState, useCallback, useEffect, useRef } from 'react'
import {
  Search,
  Cpu,
  Package,
  Zap,
  Thermometer,
  AlertCircle,
  Database,
  Loader2,
  Filter,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  X,
  Building2,
  FileText,
} from 'lucide-react'
import { API_BASE } from '@/lib/config'
import { Separator } from '@/components/ui/separator'

// Types
type ICSortBy =
  | 'part_number'
  | 'manufacturer'
  | 'pin_count'
  | 'package_type'
  | 'updated_at'
  | 'created_at'
type SortDirection = 'asc' | 'desc'

// Helper to format values for display
const formatValue = (value: unknown): string | null => {
  if (value === null || value === undefined) return null
  if (typeof value === 'object') {
    // Handle objects and arrays
    if (Array.isArray(value)) {
      return value.length > 0 ? value.join(', ') : null
    }
    // For objects, try to format nicely
    const entries = Object.entries(value as Record<string, unknown>).filter(
      ([, v]) => v !== null && v !== undefined,
    )
    if (entries.length === 0) return null
    return entries.map(([k, v]) => `${k}: ${v}`).join(', ')
  }
  const str = String(value)
  return str && str !== 'null' && str !== 'undefined' ? str : null
}

interface ICSearchResultItem {
  part_number: string
  manufacturer: string
  manufacturer_name?: string
  pin_count: number
  package_type?: string
  description?: string
  has_datasheet?: boolean
}

interface ICSearchResult {
  results: ICSearchResultItem[]
  total_count: number
  limit: number
  offset: number
}

interface ICSpecification {
  part_number: string
  manufacturer: string
  manufacturer_name?: string
  pin_count: number
  package_type?: string
  description?: string
  datasheet_url?: string
  datasheet_path?: string
  has_datasheet?: boolean
  voltage_min?: number
  voltage_max?: number
  operating_temp_min?: number
  operating_temp_max?: number
  electrical_specs?: Record<string, any>
  source?: string
  created_at?: string
  updated_at?: string
}

interface Filters {
  manufacturer: string
  package_type: string
  min_pins: string
  max_pins: string
  sort_by: ICSortBy
  sort_dir: SortDirection
}

const DEFAULT_FILTERS: Filters = {
  manufacturer: '',
  package_type: '',
  min_pins: '2', // Default to 2 to filter out invalid entries
  max_pins: '',
  sort_by: 'part_number',
  sort_dir: 'asc',
}

const ITEMS_PER_PAGE = 4

export default function ICDatabasePage() {
  const [searchResults, setSearchResults] = useState<ICSearchResult | null>(null)
  const [selectedIC, setSelectedIC] = useState<ICSpecification | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingDetails, setIsLoadingDetails] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS)
  const [showFilters, setShowFilters] = useState(false)
  const [currentPage, setCurrentPage] = useState(0)
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false)
  const inFlightController = useRef<AbortController | null>(null)

  // Build query params from filters
  const buildParams = useCallback(
    (offset: number, searchQuery?: string): URLSearchParams => {
      const params = new URLSearchParams()

      if (searchQuery) {
        params.append('q', searchQuery)
      }

      if (filters.manufacturer.trim()) {
        params.append('manufacturer', filters.manufacturer.trim())
      }
      if (filters.package_type.trim()) {
        params.append('package_type', filters.package_type.trim())
      }
      if (filters.min_pins.trim()) {
        params.append('min_pins', filters.min_pins.trim())
      }
      if (filters.max_pins.trim()) {
        params.append('max_pins', filters.max_pins.trim())
      }

      params.append('sort_by', filters.sort_by)
      params.append('sort_dir', filters.sort_dir)
      params.append('limit', ITEMS_PER_PAGE.toString())
      params.append('offset', offset.toString())

      return params
    },
    [filters],
  )

  // Fetch ICs - uses /list when no query, /search when query provided
  const fetchICs = useCallback(
    async (searchQuery: string, page: number = 0) => {
      setIsLoading(true)
      setError(null)

      // Cancel any in-flight request
      if (inFlightController.current) {
        inFlightController.current.abort()
      }
      const controller = new AbortController()
      inFlightController.current = controller

      const offset = page * ITEMS_PER_PAGE
      const trimmedQuery = searchQuery.trim()

      // Use /search if query is provided, otherwise use /list
      const endpoint = trimmedQuery ? `${API_BASE}/ic/search` : `${API_BASE}/ic/list`

      const params = buildParams(offset, trimmedQuery || undefined)

      try {
        const response = await fetch(`${endpoint}?${params.toString()}`, {
          signal: controller.signal,
        })

        if (!response.ok) {
          throw new Error('Request failed')
        }

        const data: ICSearchResult = await response.json()
        setSearchResults(data)
        setHasLoadedOnce(true)

        if (data.results.length === 0) {
          setError(
            trimmedQuery
              ? `No ICs found for "${trimmedQuery}". Try different search terms or filters.`
              : 'No ICs found. Try adjusting your filters.',
          )
        }
      } catch (err: any) {
        if (err?.name === 'AbortError') {
          return
        }
        setError('Failed to load IC catalog. Please try again.')
        console.error('Fetch error:', err)
      } finally {
        if (inFlightController.current === controller) {
          inFlightController.current = null
        }
        setIsLoading(false)
      }
    },
    [buildParams],
  )

  // Initial load - fetch all ICs
  useEffect(() => {
    fetchICs('', 0)
  }, [])

  // Debounced search when query or filters change
  useEffect(() => {
    const timer = setTimeout(() => {
      setCurrentPage(0)
      fetchICs(query, 0)
    }, 400)

    return () => {
      clearTimeout(timer)
      if (inFlightController.current) inFlightController.current.abort()
    }
  }, [query, filters])

  // Handle page changes
  const handlePageChange = useCallback(
    (newPage: number) => {
      setCurrentPage(newPage)
      fetchICs(query, newPage)
    },
    [fetchICs, query],
  )

  // Handle IC click to load details
  const handleICClick = useCallback(async (partNumber: string) => {
    setIsLoadingDetails(true)
    setError(null)

    try {
      const response = await fetch(
        `${API_BASE}/ic/details?part_number=${encodeURIComponent(partNumber)}`,
      )

      if (!response.ok) {
        throw new Error('Failed to load IC details')
      }

      const data: ICSpecification = await response.json()
      setSelectedIC(data)
    } catch (err) {
      setError('Failed to load IC details. Please try again.')
      console.error('Details error:', err)
    } finally {
      setIsLoadingDetails(false)
    }
  }, [])

  // Handle datasheet view - open in new tab
  const handleViewDatasheet = useCallback((partNumber: string) => {
    const url = `${API_BASE}/ic/datasheet?part_number=${encodeURIComponent(partNumber)}`
    window.open(url, '_blank')
  }, [])

  // Update a single filter
  const updateFilter = useCallback(<K extends keyof Filters>(key: K, value: Filters[K]) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }, [])

  // Clear all filters
  const clearFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS)
    setQuery('')
  }, [])

  // Check if any filters are active
  const hasActiveFilters =
    filters.manufacturer ||
    filters.package_type ||
    filters.min_pins ||
    filters.max_pins ||
    filters.sort_by !== 'part_number' ||
    filters.sort_dir !== 'asc'

  // Calculate pagination
  const totalPages = searchResults ? Math.ceil(searchResults.total_count / ITEMS_PER_PAGE) : 0

  return (
    <div className="flex h-full w-full flex-col overflow-hidden bg-slate-50/50 p-4 animate-in fade-in duration-500">
      <div className="mx-auto w-full max-w-7xl flex-1 flex flex-col min-h-0">
        {/* Header Section */}
        <div className="flex shrink-0 items-end justify-between mb-4">
          <div className="space-y-1">
            <h1 className="text-3xl font-black tracking-tight text-slate-900">IC Database</h1>
            <p className="text-slate-500 font-medium">
              Browse and manage integrated circuit specifications
            </p>
          </div>

          {/* Filter Toggle Button moved to header area for better layout */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 rounded-full px-5 py-2.5 font-bold text-sm transition-all shadow-sm ${showFilters || hasActiveFilters
              ? 'bg-blue-600 text-white shadow-blue-200'
              : 'bg-white text-slate-600 border border-slate-200 hover:border-blue-300 hover:text-blue-600'
              }`}
          >
            <Filter size={16} />
            Filters
            {hasActiveFilters && (
              <span className="ml-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-white text-[10px] font-bold text-blue-600">
                !
              </span>
            )}
            {showFilters ? <ChevronUp size={16} className="ml-1" /> : <ChevronDown size={16} className="ml-1" />}
          </button>
        </div>

        {/* Search & Filters Container */}
        <div className="shrink-0 space-y-4 mb-4 relative z-20">
          {/* Search Bar */}
          <div className="relative group max-w-2xl">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by part number, description..."
              className="w-full rounded-2xl border border-slate-200 bg-white px-6 py-4 pl-14 text-base shadow-sm hover:border-blue-300 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 focus:outline-none transition-all placeholder:text-slate-400"
              aria-label="Search ICs"
            />
            <Search
              className="absolute top-1/2 left-5 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-500 transition-colors"
              size={22}
            />
            {query && (
              <button
                onClick={() => setQuery('')}
                className="absolute top-1/2 right-5 -translate-y-1/2 p-1 rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-all"
              >
                <X size={18} />
              </button>
            )}
          </div>

          {/* Filters Panel */}
          {showFilters && (
            <div className="absolute top-full left-0 right-0 mt-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/50 animate-in slide-in-from-top-2 duration-200 z-50">
              <div className="flex flex-wrap items-end gap-4">
                {/* Manufacturer */}
                <div className="min-w-[140px] flex-1">
                  <label className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-500">
                    Manufacturer
                  </label>
                  <input
                    type="text"
                    value={filters.manufacturer}
                    onChange={(e) => updateFilter('manufacturer', e.target.value)}
                    placeholder="e.g. TI, STM"
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none transition-all placeholder:text-slate-400"
                  />
                </div>

                {/* Package Type */}
                <div className="min-w-[120px] flex-1">
                  <label className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-500">Package</label>
                  <input
                    type="text"
                    value={filters.package_type}
                    onChange={(e) => updateFilter('package_type', e.target.value)}
                    placeholder="e.g. DIP, SOIC"
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none transition-all placeholder:text-slate-400"
                  />
                </div>

                {/* Min Pins */}
                <div className="w-[90px]">
                  <label className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-500">Min Pins</label>
                  <input
                    type="number"
                    value={filters.min_pins}
                    onChange={(e) => updateFilter('min_pins', e.target.value)}
                    placeholder="1"
                    min="1"
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none transition-all placeholder:text-slate-400"
                  />
                </div>

                {/* Max Pins */}
                <div className="w-[90px]">
                  <label className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-500">Max Pins</label>
                  <input
                    type="number"
                    value={filters.max_pins}
                    onChange={(e) => updateFilter('max_pins', e.target.value)}
                    placeholder="256"
                    min="1"
                    className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none transition-all placeholder:text-slate-400"
                  />
                </div>

                {/* Sort By */}
                <div className="w-[150px]">
                  <label className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-500">Sort By</label>
                  <div className="relative">
                    <select
                      value={filters.sort_by}
                      onChange={(e) => updateFilter('sort_by', e.target.value as ICSortBy)}
                      className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm appearance-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none transition-all cursor-pointer"
                    >
                      <option value="part_number">Part Number</option>
                      <option value="manufacturer">Manufacturer</option>
                      <option value="pin_count">Pin Count</option>
                      <option value="package_type">Package Type</option>
                      <option value="created_at">Newest First</option>
                      <option value="updated_at">Recently Updated</option>
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" size={14} />
                  </div>
                </div>

                {/* Sort Direction */}
                <div className="w-[110px]">
                  <label className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-500">Order</label>
                  <div className="relative">
                    <select
                      value={filters.sort_dir}
                      onChange={(e) => updateFilter('sort_dir', e.target.value as SortDirection)}
                      className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm appearance-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none transition-all cursor-pointer"
                    >
                      <option value="asc">Asc ↑</option>
                      <option value="desc">Desc ↓</option>
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" size={14} />
                  </div>
                </div>

                {/* Clear Filters Button */}
                {hasActiveFilters && (
                  <button
                    onClick={clearFilters}
                    className="rounded-xl px-4 py-2 text-sm font-semibold text-red-600 transition-colors hover:bg-red-50 hover:text-red-700 active:scale-95 duration-200"
                  >
                    Clear All
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Error Message */}
        {error && !isLoading && (
          <div className="mb-6 flex shrink-0 items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-4 shadow-sm">
            <AlertCircle className="flex-shrink-0 text-red-600" size={24} />
            <p className="font-medium text-red-800">{error}</p>
          </div>
        )}

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 min-h-0 flex-1">
          {/* Left Panel: Search Results */}
          <div className="flex flex-col min-h-0">
            {isLoading && !hasLoadedOnce && (
              <div className="flex flex-col items-center justify-center space-y-4 rounded-2xl border border-slate-200 bg-white p-16 shadow-lg shadow-slate-200/50">
                <Loader2 className="h-10 w-10 animate-spin text-blue-600" />
                <div className="text-center">
                  <p className="text-lg font-bold text-slate-900">Loading IC catalog...</p>
                  <p className="text-slate-500">Fetching data from server</p>
                </div>
              </div>
            )}

            {searchResults && (
              <div className="flex flex-1 flex-col rounded-2xl border border-slate-200 bg-white shadow-lg shadow-slate-200/50 overflow-hidden">
                <div className="flex shrink-0 items-center justify-between border-b border-slate-100 bg-white px-6 py-4">
                  <h2 className="text-lg font-bold text-slate-900">
                    {query.trim() ? 'Search Results' : 'IC Catalog'}
                  </h2>
                  <div className="flex items-center gap-3">
                    {isLoading && (
                      <div className="flex items-center gap-2 text-xs font-medium text-blue-600">
                        <Loader2 className="animate-spin" size={14} />
                      </div>
                    )}
                    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">
                      {searchResults.total_count} ICs
                    </span>
                  </div>
                </div>

                {/* Results List */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
                  {searchResults.results.map((ic, index) => (
                    <div
                      key={`${ic.part_number}-${ic.manufacturer}-${index}`}
                      onClick={() => handleICClick(ic.part_number)}
                      className={`group cursor-pointer rounded-xl border p-4 transition-all duration-200 ${selectedIC?.part_number === ic.part_number &&
                        selectedIC?.manufacturer === ic.manufacturer
                        ? 'border-blue-400 bg-blue-50/50 shadow-sm ring-1 ring-blue-400/20'
                        : 'border-slate-100 bg-white hover:border-slate-300 hover:shadow-md hover:-translate-y-0.5'
                        }`}
                    >
                      <div className="mb-2 flex items-start justify-between">
                        <div className="flex items-center gap-2.5">
                          <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${selectedIC?.part_number === ic.part_number ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-500 group-hover:text-slate-700'
                            }`}>
                            <Cpu size={18} />
                          </div>
                          <h3 className="text-base font-bold text-slate-900 break-all">
                            {ic.part_number}
                          </h3>
                        </div>
                        {ic.has_datasheet && (
                          <span title="Datasheet available">
                            <FileText className="text-slate-300 group-hover:text-blue-500" size={16} />
                          </span>
                        )}
                      </div>

                      <div className="space-y-2 pl-[42px]">
                        <p className="text-sm font-medium text-slate-600 break-words">
                          {ic.manufacturer_name || ic.manufacturer}
                        </p>
                        <div className="flex flex-wrap gap-2 text-xs">
                          {ic.package_type && (
                            <span className="inline-flex items-center rounded-md border border-slate-200 bg-slate-50 px-2 py-1 font-medium text-slate-600">
                              {ic.package_type}
                            </span>
                          )}
                          <span className="inline-flex items-center rounded-md border border-slate-200 bg-slate-50 px-2 py-1 font-medium text-slate-600">
                            {ic.pin_count} pins
                          </span>
                        </div>
                        {ic.description && (
                          <p className="line-clamp-2 text-xs text-slate-500 leading-relaxed">{ic.description}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex shrink-0 items-center justify-between border-t border-slate-100 bg-slate-50/50 px-6 py-3">
                    <button
                      onClick={() => handlePageChange(currentPage - 1)}
                      disabled={currentPage === 0 || isLoading}
                      className="flex items-center gap-1 rounded-full px-4 py-2 text-sm font-bold text-slate-600 transition-colors hover:bg-white hover:shadow-sm hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      <ChevronLeft size={16} />
                      Prev
                    </button>

                    <span className="text-xs font-bold text-slate-500">
                      Page {currentPage + 1} of {totalPages}
                    </span>

                    <button
                      onClick={() => handlePageChange(currentPage + 1)}
                      disabled={currentPage >= totalPages - 1 || isLoading}
                      className="flex items-center gap-1 rounded-full px-4 py-2 text-sm font-bold text-slate-600 transition-colors hover:bg-white hover:shadow-sm hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Next
                      <ChevronRight size={16} />
                    </button>
                  </div>
                )}
              </div>
            )}

            {!searchResults && !isLoading && (
              <div className="flex flex-col items-center justify-center space-y-4 rounded-2xl border border-slate-200 bg-white p-16 text-center shadow-lg shadow-slate-200/50">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-50">
                  <Database className="text-slate-300" size={32} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-900">Loading IC Database</h3>
                  <p className="text-slate-500">Please wait, initializing connection...</p>
                </div>
              </div>
            )}
          </div>

          {/* Right Panel: IC Details */}
          <div className="flex flex-col min-h-0">
            {isLoadingDetails && (
              <div className="flex flex-col items-center justify-center space-y-4 rounded-2xl border border-slate-200 bg-white p-16 shadow-lg shadow-slate-200/50 min-h-[200px]">
                <Loader2 className="h-10 w-10 animate-spin text-blue-600" />
                <p className="font-medium text-slate-500">Loading IC details...</p>
              </div>
            )}

            {selectedIC && !isLoadingDetails && (
              <div className="flex flex-1 flex-col rounded-2xl border border-slate-200 bg-white shadow-lg shadow-slate-200/50 overflow-hidden">
                {/* Header */}
                <div className="shrink-0 border-b border-slate-100 bg-white px-6 py-5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h2 className="text-2xl font-black tracking-tight text-slate-900 break-all leading-tight">
                        {selectedIC.part_number}
                      </h2>
                      <p className="text-sm font-semibold text-slate-500 mt-1 flex items-center gap-1.5 break-words">
                        <Building2 size={14} className="shrink-0" />
                        {selectedIC.manufacturer_name || selectedIC.manufacturer}
                      </p>
                    </div>
                    {selectedIC.has_datasheet && (
                      <button
                        onClick={() => handleViewDatasheet(selectedIC.part_number)}
                        className="flex shrink-0 items-center gap-2 rounded-full bg-blue-600 px-4 py-2 text-xs font-bold text-white shadow-md shadow-blue-600/20 hover:bg-blue-700 transition-all active:scale-95"
                      >
                        <FileText size={14} />
                        Datasheet
                      </button>
                    )}
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">

                  {/* Compact Grid for Core Specs */}
                  <div className="grid grid-cols-2 gap-3">
                    {/* Package */}
                    <div className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-slate-50 p-3 shadow-sm hover:border-slate-300 transition-all">
                      <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500">Package Type</span>
                      <div className="flex items-center gap-1.5 font-bold text-slate-900 truncate">
                        <Package className="h-3.5 w-3.5 text-slate-400" />
                        <span className="truncate">{selectedIC.package_type || 'N/A'}</span>
                      </div>
                    </div>

                    {/* Pins */}
                    <div className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-slate-50 p-3 shadow-sm hover:border-slate-300 transition-all">
                      <span className="text-[10px] uppercase tracking-wider font-bold text-slate-500">Pin Count</span>
                      <div className="flex items-center gap-1.5 font-bold text-slate-900">
                        <Cpu className="h-3.5 w-3.5 text-slate-400" />
                        <span>{selectedIC.pin_count} pins</span>
                      </div>
                    </div>
                  </div>

                  {/* Description */}
                  {selectedIC.description && (
                    <div className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
                      <p className="text-sm leading-relaxed text-slate-600 font-medium">{selectedIC.description}</p>
                    </div>
                  )}

                  <Separator className="bg-slate-100" />

                  {/* Voltage & Temperature */}
                  {((selectedIC.voltage_min !== null && selectedIC.voltage_min !== undefined) ||
                    (selectedIC.operating_temp_min !== null &&
                      selectedIC.operating_temp_min !== undefined)) && (
                      <div className="space-y-4">
                        <h3 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-900">
                          <Zap className="text-blue-500" size={14} />
                          Operating Conditions
                        </h3>

                        <div className="grid grid-cols-2 gap-3">
                          {selectedIC.voltage_min !== null &&
                            selectedIC.voltage_min !== undefined &&
                            selectedIC.voltage_max !== null &&
                            selectedIC.voltage_max !== undefined && (
                              <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm hover:border-slate-300 transition-all">
                                <p className="mb-1 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                                  Voltage
                                </p>
                                <p className="text-sm font-bold text-slate-900">
                                  {selectedIC.voltage_min}V - {selectedIC.voltage_max}V
                                </p>
                              </div>
                            )}

                          {selectedIC.operating_temp_min !== null &&
                            selectedIC.operating_temp_min !== undefined &&
                            selectedIC.operating_temp_max !== null &&
                            selectedIC.operating_temp_max !== undefined && (
                              <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm hover:border-slate-300 transition-all">
                                <div className="mb-1 flex items-center justify-between">
                                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Temp</p>
                                  <Thermometer className="text-slate-300" size={12} />
                                </div>
                                <p className="text-sm font-bold text-slate-900">
                                  {selectedIC.operating_temp_min}°C to {selectedIC.operating_temp_max}°C
                                </p>
                              </div>
                            )}
                        </div>
                      </div>
                    )}

                  {/* Electrical Specifications */}
                  {selectedIC.electrical_specs &&
                    Object.keys(selectedIC.electrical_specs).length > 0 && (
                      <div className="space-y-4">
                        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900">Specs</h3>
                        <div className="grid grid-cols-2 gap-3">
                          {Object.entries(selectedIC.electrical_specs)
                            .map(([key, value]) => ({ key, formattedValue: formatValue(value) }))
                            .filter(({ formattedValue }) => formattedValue !== null)
                            .map(({ key, formattedValue }) => (
                              <div
                                key={key}
                                className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-slate-50 p-3 shadow-sm hover:border-slate-300 transition-all"
                              >
                                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 break-words" title={key.replace(/_/g, ' ')}>
                                  {key.replace(/_/g, ' ')}
                                </span>
                                <span className="text-sm font-bold text-slate-900 break-words">
                                  {formattedValue}
                                </span>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}

                  {/* Metadata */}
                  <div className="grid grid-cols-2 gap-3 pt-2">
                    <div className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
                      <p className="text-[10px] uppercase font-bold text-slate-400">Data Source</p>
                      <div className="flex items-center gap-1.5">
                        <div className="h-1.5 w-1.5 rounded-full bg-emerald-400"></div>
                        <p className="text-xs font-bold text-slate-700">
                          {selectedIC.source?.replace(/_/g, ' ') || 'N/A'}
                        </p>
                      </div>
                    </div>
                    <div className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
                      <p className="text-[10px] uppercase font-bold text-slate-400">Last Updated</p>
                      <p className="text-xs font-bold text-slate-700">
                        {selectedIC.updated_at
                          ? new Date(selectedIC.updated_at).toLocaleDateString()
                          : 'N/A'}
                      </p>
                    </div>
                  </div>

                </div>
              </div>
            )}

            {!selectedIC && !isLoadingDetails && (
              <div className="flex flex-col items-center justify-center space-y-4 rounded-2xl border border-slate-200 bg-white p-16 text-center shadow-lg shadow-slate-200/50 min-h-[200px]">
                <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-slate-50 text-slate-300">
                  <Cpu size={40} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-900">Select an IC</h3>
                  <p className="text-slate-500 max-w-[200px] mx-auto">Click on a component from the list to view its full specifications</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
