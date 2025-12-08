import { useState, useCallback, useEffect, useRef } from 'react'
import {
  Search,
  ExternalLink,
  Cpu,
  Package,
  Zap,
  Thermometer,
  AlertCircle,
  CheckCircle,
  Database,
  Loader2,
  Filter,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  X,
} from 'lucide-react'
import { API_BASE } from '@/lib/config'

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

const ITEMS_PER_PAGE = 20

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
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-cyan-50 to-blue-100 p-6">
      <div className="mx-auto max-w-7xl">
        {/* Header Section */}
        <div className="mb-6">
          <h1 className="mb-2 text-4xl font-bold text-gray-800">IC Database</h1>
          <p className="text-lg text-gray-600">
            Scrape and manage integrated circuit specifications
          </p>
        </div>

        {/* Search Bar */}
        <div className="mb-4">
          <div className="relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by part number, description..."
              className="w-full rounded-xl border-2 border-blue-300 bg-white px-6 py-3 pl-12 text-base shadow-md transition-all focus:border-blue-500 focus:ring-3 focus:ring-blue-400 focus:outline-none"
              aria-label="Search ICs"
            />
            <Search
              className="absolute top-1/2 left-4 -translate-y-1/2 transform text-blue-500"
              size={20}
            />
            {query && (
              <button
                onClick={() => setQuery('')}
                className="absolute top-1/2 right-4 -translate-y-1/2 transform text-gray-400 hover:text-gray-600"
              >
                <X size={18} />
              </button>
            )}
          </div>
        </div>

        {/* Filter Toggle & Filters */}
        <div className="mb-6">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 font-medium transition-all ${
              showFilters || hasActiveFilters
                ? 'bg-blue-600 text-white'
                : 'border-2 border-blue-300 bg-white text-blue-700 hover:bg-blue-50'
            }`}
          >
            <Filter size={18} />
            Filters
            {hasActiveFilters && (
              <span className="ml-1 rounded-full bg-white px-2 py-0.5 text-xs font-bold text-blue-600">
                Active
              </span>
            )}
            {showFilters ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>

          {showFilters && (
            <div className="mt-3 rounded-xl border-2 border-blue-200 bg-white p-4 shadow-md">
              <div className="flex flex-wrap items-end gap-3">
                {/* Manufacturer */}
                <div className="min-w-[140px] flex-1">
                  <label className="mb-1 block text-xs font-semibold text-gray-600">
                    Manufacturer
                  </label>
                  <input
                    type="text"
                    value={filters.manufacturer}
                    onChange={(e) => updateFilter('manufacturer', e.target.value)}
                    placeholder="e.g. TI, STM"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-400 focus:outline-none"
                  />
                </div>

                {/* Package Type */}
                <div className="min-w-[120px] flex-1">
                  <label className="mb-1 block text-xs font-semibold text-gray-600">Package</label>
                  <input
                    type="text"
                    value={filters.package_type}
                    onChange={(e) => updateFilter('package_type', e.target.value)}
                    placeholder="e.g. DIP, SOIC"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-400 focus:outline-none"
                  />
                </div>

                {/* Min Pins */}
                <div className="w-[90px]">
                  <label className="mb-1 block text-xs font-semibold text-gray-600">Min Pins</label>
                  <input
                    type="number"
                    value={filters.min_pins}
                    onChange={(e) => updateFilter('min_pins', e.target.value)}
                    placeholder="1"
                    min="1"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-400 focus:outline-none"
                  />
                </div>

                {/* Max Pins */}
                <div className="w-[90px]">
                  <label className="mb-1 block text-xs font-semibold text-gray-600">Max Pins</label>
                  <input
                    type="number"
                    value={filters.max_pins}
                    onChange={(e) => updateFilter('max_pins', e.target.value)}
                    placeholder="256"
                    min="1"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-400 focus:outline-none"
                  />
                </div>

                {/* Sort By */}
                <div className="w-[140px]">
                  <label className="mb-1 block text-xs font-semibold text-gray-600">Sort By</label>
                  <select
                    value={filters.sort_by}
                    onChange={(e) => updateFilter('sort_by', e.target.value as ICSortBy)}
                    className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:ring-2 focus:ring-blue-400 focus:outline-none"
                  >
                    <option value="part_number">Part Number</option>
                    <option value="manufacturer">Manufacturer</option>
                    <option value="pin_count">Pin Count</option>
                    <option value="package_type">Package Type</option>
                    <option value="created_at">Newest First</option>
                    <option value="updated_at">Recently Updated</option>
                  </select>
                </div>

                {/* Sort Direction */}
                <div className="w-[100px]">
                  <label className="mb-1 block text-xs font-semibold text-gray-600">Order</label>
                  <select
                    value={filters.sort_dir}
                    onChange={(e) => updateFilter('sort_dir', e.target.value as SortDirection)}
                    className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:ring-2 focus:ring-blue-400 focus:outline-none"
                  >
                    <option value="asc">Asc ↑</option>
                    <option value="desc">Desc ↓</option>
                  </select>
                </div>

                {/* Clear Filters Button */}
                {hasActiveFilters && (
                  <button
                    onClick={clearFilters}
                    className="rounded-lg px-4 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-50 hover:text-red-700"
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
          <div className="mb-6 flex items-center gap-3 rounded-xl border-2 border-red-400 bg-red-100 p-4">
            <AlertCircle className="flex-shrink-0 text-red-600" size={24} />
            <p className="font-medium text-red-800">{error}</p>
          </div>
        )}

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Left Panel: Search Results */}
          <div className="space-y-4">
            {isLoading && !hasLoadedOnce && (
              <div className="flex animate-pulse flex-col items-center justify-center space-y-4 rounded-2xl border-2 border-blue-200 bg-white p-10 shadow-xl">
                <div className="h-16 w-16 animate-spin rounded-full border-4 border-blue-300 border-t-transparent" />
                <div className="text-center">
                  <p className="text-xl font-bold text-gray-700">Loading IC catalog…</p>
                  <p className="text-gray-500">Fetching data from server</p>
                </div>
              </div>
            )}

            {searchResults && (
              <div className="rounded-2xl border-2 border-blue-200 bg-white p-6 shadow-xl">
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-xl font-bold text-gray-800">
                    {query.trim() ? 'Search Results' : 'IC Catalog'}
                  </h2>
                  <div className="flex items-center gap-3">
                    {isLoading && (
                      <div className="flex items-center gap-2 text-sm text-blue-600">
                        <Loader2 className="animate-spin" size={16} />
                        <span>Loading…</span>
                      </div>
                    )}
                    <span className="rounded-full bg-gradient-to-r from-blue-600 to-cyan-600 px-3 py-1.5 text-sm font-bold text-white">
                      {searchResults.total_count} ICs
                    </span>
                  </div>
                </div>

                {/* Results List */}
                <div className="max-h-[calc(100vh-480px)] space-y-3 overflow-y-auto pr-2">
                  {searchResults.results.map((ic, index) => (
                    <div
                      key={`${ic.part_number}-${ic.manufacturer}-${index}`}
                      onClick={() => handleICClick(ic.part_number)}
                      className={`cursor-pointer rounded-xl border-2 p-4 transition-all hover:shadow-lg ${
                        selectedIC?.part_number === ic.part_number &&
                        selectedIC?.manufacturer === ic.manufacturer
                          ? 'border-green-500 bg-green-50 shadow-md'
                          : 'border-blue-200 bg-blue-50 hover:border-blue-400'
                      }`}
                    >
                      <div className="mb-2 flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <Cpu className="flex-shrink-0 text-blue-600" size={20} />
                          <h3 className="text-lg font-bold break-all text-gray-800">
                            {ic.part_number}
                          </h3>
                        </div>
                        {ic.has_datasheet && (
                          <span title="Datasheet available">
                            <CheckCircle className="flex-shrink-0 text-green-600" size={18} />
                          </span>
                        )}
                      </div>

                      <div className="space-y-1 text-sm">
                        <p className="text-gray-700">
                          <span className="font-semibold">Manufacturer:</span>{' '}
                          {ic.manufacturer_name || ic.manufacturer}
                        </p>
                        <div className="mt-2 flex flex-wrap gap-2 text-xs">
                          {ic.package_type && (
                            <span className="rounded-md bg-purple-100 px-2 py-1 font-medium text-purple-700">
                              {ic.package_type}
                            </span>
                          )}
                          <span className="rounded-md bg-blue-100 px-2 py-1 font-medium text-blue-700">
                            {ic.pin_count} pins
                          </span>
                        </div>
                        {ic.description && (
                          <p className="mt-2 line-clamp-2 text-gray-600">{ic.description}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="mt-4 flex items-center justify-between border-t border-gray-200 pt-4">
                    <button
                      onClick={() => handlePageChange(currentPage - 1)}
                      disabled={currentPage === 0 || isLoading}
                      className="flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium text-blue-600 transition-colors hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      <ChevronLeft size={18} />
                      Previous
                    </button>

                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-600">
                        Page <span className="font-bold">{currentPage + 1}</span> of{' '}
                        <span className="font-bold">{totalPages}</span>
                      </span>
                    </div>

                    <button
                      onClick={() => handlePageChange(currentPage + 1)}
                      disabled={currentPage >= totalPages - 1 || isLoading}
                      className="flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium text-blue-600 transition-colors hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      Next
                      <ChevronRight size={18} />
                    </button>
                  </div>
                )}
              </div>
            )}

            {!searchResults && !isLoading && (
              <div className="rounded-2xl border-2 border-blue-200 bg-white p-12 text-center shadow-xl">
                <Database className="mx-auto mb-4 text-blue-400" size={64} />
                <h3 className="mb-2 text-xl font-bold text-gray-700">Loading IC Database</h3>
                <p className="text-gray-500">Please wait while we fetch the catalog...</p>
              </div>
            )}
          </div>

          {/* Right Panel: IC Details */}
          <div className="space-y-4">
            {isLoadingDetails && (
              <div className="rounded-2xl border-2 border-blue-200 bg-white p-12 text-center shadow-xl">
                <Loader2 className="mx-auto mb-4 animate-spin text-blue-600" size={64} />
                <p className="font-medium text-gray-600">Loading IC details...</p>
              </div>
            )}

            {selectedIC && !isLoadingDetails && (
              <div className="space-y-6 rounded-2xl border-2 border-green-400 bg-white p-6 shadow-xl">
                {/* Header */}
                <div className="border-b-2 border-gray-200 pb-4">
                  <div className="mb-2 flex items-center justify-between">
                    <h2 className="text-2xl font-bold break-all text-gray-800">
                      {selectedIC.part_number}
                    </h2>
                    {selectedIC.has_datasheet && (
                      <button
                        onClick={() => handleViewDatasheet(selectedIC.part_number)}
                        className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-green-600 to-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-md transition-all hover:from-green-700 hover:to-emerald-700"
                      >
                        <ExternalLink size={16} />
                        View Datasheet
                      </button>
                    )}
                  </div>
                  <p className="text-lg font-medium text-gray-600">
                    {selectedIC.manufacturer_name || selectedIC.manufacturer}
                  </p>
                </div>

                {/* Description */}
                {selectedIC.description && (
                  <div className="rounded-xl border-2 border-blue-300 bg-blue-50 p-4">
                    <p className="leading-relaxed text-gray-700">{selectedIC.description}</p>
                  </div>
                )}

                {/* Basic Specifications */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-xl border-2 border-purple-300 bg-gradient-to-br from-purple-100 to-pink-100 p-4">
                    <div className="mb-2 flex items-center gap-2">
                      <Package className="text-purple-600" size={18} />
                      <p className="text-xs font-semibold text-purple-900">Package Type</p>
                    </div>
                    <p className="text-xl font-bold text-purple-800">
                      {selectedIC.package_type || 'N/A'}
                    </p>
                  </div>

                  <div className="rounded-xl border-2 border-blue-300 bg-gradient-to-br from-blue-100 to-cyan-100 p-4">
                    <div className="mb-2 flex items-center gap-2">
                      <Cpu className="text-blue-600" size={18} />
                      <p className="text-xs font-semibold text-blue-900">Pin Count</p>
                    </div>
                    <p className="text-xl font-bold text-blue-800">{selectedIC.pin_count} pins</p>
                  </div>
                </div>

                {/* Voltage & Temperature - Only show if we have actual values */}
                {((selectedIC.voltage_min !== null && selectedIC.voltage_min !== undefined) ||
                  (selectedIC.operating_temp_min !== null &&
                    selectedIC.operating_temp_min !== undefined)) && (
                  <div className="space-y-3">
                    <h3 className="flex items-center gap-2 text-lg font-bold text-gray-800">
                      <Zap className="text-yellow-600" size={20} />
                      Operating Conditions
                    </h3>

                    <div className="grid grid-cols-2 gap-4">
                      {selectedIC.voltage_min !== null &&
                        selectedIC.voltage_min !== undefined &&
                        selectedIC.voltage_max !== null &&
                        selectedIC.voltage_max !== undefined && (
                          <div className="rounded-xl border-2 border-yellow-400 bg-gradient-to-br from-yellow-100 to-orange-100 p-4">
                            <p className="mb-1 text-xs font-semibold text-yellow-900">
                              Voltage Range
                            </p>
                            <p className="text-lg font-bold text-yellow-800">
                              {selectedIC.voltage_min}V - {selectedIC.voltage_max}V
                            </p>
                          </div>
                        )}

                      {selectedIC.operating_temp_min !== null &&
                        selectedIC.operating_temp_min !== undefined &&
                        selectedIC.operating_temp_max !== null &&
                        selectedIC.operating_temp_max !== undefined && (
                          <div className="rounded-xl border-2 border-cyan-400 bg-gradient-to-br from-cyan-100 to-blue-100 p-4">
                            <div className="mb-1 flex items-center gap-2">
                              <Thermometer className="text-cyan-600" size={16} />
                              <p className="text-xs font-semibold text-cyan-900">Temp Range</p>
                            </div>
                            <p className="text-lg font-bold text-cyan-800">
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
                    <div className="space-y-3">
                      <h3 className="text-lg font-bold text-gray-800">Electrical Specifications</h3>
                      <div className="space-y-2 rounded-xl border-2 border-indigo-300 bg-gradient-to-br from-indigo-50 to-purple-50 p-4">
                        {Object.entries(selectedIC.electrical_specs)
                          .map(([key, value]) => ({ key, formattedValue: formatValue(value) }))
                          .filter(({ formattedValue }) => formattedValue !== null)
                          .map(({ key, formattedValue }) => (
                            <div
                              key={key}
                              className="flex items-center justify-between border-b border-indigo-200 py-2 last:border-0"
                            >
                              <span className="text-sm font-medium text-gray-700 capitalize">
                                {key.replace(/_/g, ' ')}
                              </span>
                              <span className="max-w-[60%] text-right text-sm font-bold break-words text-gray-900">
                                {formattedValue}
                              </span>
                            </div>
                          ))}
                      </div>
                    </div>
                  )}

                {/* Metadata */}
                <div className="grid grid-cols-2 gap-4 border-t-2 border-gray-200 pt-4">
                  <div>
                    <p className="mb-1 text-xs text-gray-500">Data Source</p>
                    <p className="text-sm font-semibold text-gray-800">
                      {selectedIC.source?.replace(/_/g, ' ') || 'N/A'}
                    </p>
                  </div>
                  <div>
                    <p className="mb-1 text-xs text-gray-500">Last Updated</p>
                    <p className="text-sm font-semibold text-gray-800">
                      {selectedIC.updated_at
                        ? new Date(selectedIC.updated_at).toLocaleDateString()
                        : 'N/A'}
                    </p>
                  </div>
                </div>

                {/* Datasheet URL */}
                {selectedIC.datasheet_url && (
                  <div className="rounded-xl border-2 border-gray-300 bg-gray-50 p-4">
                    <p className="mb-2 text-xs text-gray-600">Original Datasheet URL</p>
                    <a
                      href={selectedIC.datasheet_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-medium break-all text-blue-600 underline hover:text-blue-800"
                    >
                      {selectedIC.datasheet_url}
                    </a>
                  </div>
                )}
              </div>
            )}

            {!selectedIC && !isLoadingDetails && (
              <div className="rounded-2xl border-2 border-gray-300 bg-white p-12 text-center shadow-xl">
                <Cpu className="mx-auto mb-4 text-gray-400" size={64} />
                <h3 className="mb-2 text-xl font-bold text-gray-700">Select an IC</h3>
                <p className="text-gray-500">Click on an IC from the list to view details</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
