/**
 * API Types - Generated from OpenAPI spec (contracts/openapi.yaml)
 * Keep these in sync with the backend contract
 */

// ============================================================
// ENUMS
// ============================================================

export type ScanStatus = 'PASS' | 'FAIL' | 'PARTIAL' | 'UNKNOWN' | 'COUNTERFEIT'

export type ActionRequired = 'NONE' | 'SCAN_BOTTOM'

export type CaptureType = 'TOP' | 'BOTTOM'

export type Manufacturer = 'STM' | 'TI'

export type SyncStatus = 'IDLE' | 'PROCESSING' | 'COMPLETED' | 'ERROR' | 'CANCELLED'

export type FakeSource = 'SYNC_NOT_FOUND' | 'MANUAL_REPORT'

export type DataSource =
  | 'MANUAL'
  | 'SCRAPED_STM'
  | 'SCRAPED_TI'
  | 'SCRAPED_MOUSER'
  | 'SCRAPED_DIGIKEY'
  | 'SCRAPED_ALLDATASHEET'

// ============================================================
// CORE SCAN SCHEMAS
// ============================================================

export interface MatchDetails {
  part_number_match: boolean
  pin_count_match?: boolean | null
  manufacturer_match?: boolean | null
}

export interface FakeRegistryInfo {
  added_at: string
  source: FakeSource
  reason: string
}

export interface ICSpecification {
  part_number: string
  manufacturer: Manufacturer
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
  electrical_specs?: Record<string, unknown>
  source?: DataSource
  created_at?: string
  updated_at?: string
}

export interface ScanResult {
  scan_id: string
  status: ScanStatus
  action_required: ActionRequired
  confidence_score: number
  ocr_text: string
  manufacturer_detected?: string | null
  detected_pins: number
  message: string
  match_details?: MatchDetails | null
  queued_for_sync: boolean
  ic_specification?: ICSpecification | null
  fake_registry_info?: FakeRegistryInfo | null
  scanned_at: string
  completed_at?: string | null
  part_number?: string;
  part_number_detected?: string;
}

// ============================================================
// CAMERA SCHEMAS
// ============================================================

export interface CaptureRequest {
  capture_type: CaptureType
  scan_id?: string
}

export interface CaptureResponse {
  success: boolean
  message: string
  scan_id: string
}

// ============================================================
// DASHBOARD SCHEMAS
// ============================================================

export interface RecentCounterfeit {
  part_number: string
  scanned_at: string
}

export interface DashboardStats {
  total_scans: number
  scans_today: number
  scans_this_week: number
  pass_count: number
  fail_count: number
  unknown_count: number
  counterfeit_count: number
  pass_rate_percentage: number
  queue_size: number
  fake_registry_size: number
  database_ic_count: number
  last_sync_at?: string | null
  last_sync_status?: SyncStatus | null
  recent_counterfeits?: RecentCounterfeit[]
}

// ============================================================
// SCAN HISTORY SCHEMAS
// ============================================================

export interface ScanListItem {
  scan_id: string
  part_number: string
  status: ScanStatus
  confidence_score: number
  detected_pins: number
  scanned_at: string
}

export interface ScanListResult {
  scans: ScanListItem[]
  total_count: number
  limit: number
  offset: number
}

export interface ScanDetails extends ScanResult {
  ocr_text_raw?: string
  part_number_detected?: string
  part_number_verified?: string
  expected_pins?: number | null
  has_bottom_scan?: boolean
  was_manual_override?: boolean
  failure_reasons?: string[] | null
}

// ============================================================
// IC DATABASE SCHEMAS
// ============================================================

export interface ICSearchResultItem {
  part_number: string
  manufacturer: Manufacturer
  manufacturer_name?: string
  pin_count: number
  package_type?: string
  description?: string
  has_datasheet?: boolean
}

export interface ICSearchResult {
  results: ICSearchResultItem[]
  total_count: number
  limit: number
  offset: number
}

// ============================================================
// COMMON SCHEMAS
// ============================================================

export interface SuccessResponse {
  success: boolean
  message: string
}

export interface ErrorResponse {
  error: string
  message: string
  suggestion?: string | null
  details?: Record<string, unknown> | null
}
