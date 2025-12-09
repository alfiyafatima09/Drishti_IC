/**
 * API Types - Generated from OpenAPI spec (contracts/openapi.yaml)
 * Keep these in sync with the backend contract
 */

// ============================================================
// ENUMS
// ============================================================

export type ScanStatus =
  | 'PASS'
  | 'FAIL'
  | 'PARTIAL'
  | 'UNKNOWN'
  | 'COUNTERFEIT'
  | 'EXTRACTED'
  | 'NEED_BOTTOM_SCAN'
  | 'MATCH_FOUND'
  | 'PIN_MISMATCH'
  | 'MANUFACTURER_MISMATCH'
  | 'NOT_IN_DATABASE'

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
  part_number?: string | null
  part_number_detected?: string | null
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
  part_number: string | null
  part_number_detected: string | null
  part_number_candidates?: string[] | null
  part_number_verified: string | null
  status: ScanStatus
  action_required: ActionRequired
  confidence_score: number | null
  detected_pins: number | null
  expected_pins?: number | null
  has_bottom_scan: boolean
  was_manual_override: boolean
  manufacturer_detected: string | null
  message: string | null
  scanned_at: string
  completed_at: string | null
  batch_id: string | null
  batch_vender: string | null
}

export interface ScanListResult {
  scans: ScanListItem[]
  total_count: number
  limit: number
  offset: number
}

export interface ScanDetails extends ScanResult {
  ocr_text_raw?: string | null
  part_number_detected?: string | null
  part_number_candidates?: string[] | null
  part_number_verified?: string | null
  expected_pins?: number | null
  batch_id?: string | null
  batch_vender?: string | null
  has_bottom_scan?: boolean
  was_manual_override?: boolean
  operator_note?: string | null
  verification_checks?: Record<string, any> | null
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
// SYNC HISTORY SCHEMAS
// ============================================================

export interface SyncHistoryItem {
  job_id: string
  status: 'COMPLETED' | 'ERROR' | 'CANCELLED'
  started_at: string
  completed_at: string
  total_items: number
  success_count: number
  failed_count: number
  fake_count: number
}

export interface SyncHistoryResult {
  sync_jobs: SyncHistoryItem[]
  total_count: number
}

// ============================================================
// COMMON SCHEMAS
// ============================================================

export interface BatchScanResult {
  job_id: string
  status: string
  total_images: number
  message: string
}

export interface BatchProgress {
  job_id: string
  status: 'processing' | 'completed' | 'failed'
  progress_percentage: number
  processed_images: number
  total_images: number
  results?: BatchImageResult[]
  estimated_time_remaining?: number
}

export interface BatchImageResult {
  image_path: string
  classification: {
    model_type: string
    confidence: number
    features: Record<string, any>
    estimated_time: number
  }
  result: {
    method: string
    specs?: {
      part_number?: string
      manufacturer?: string
      pin_count?: string
    }
    confidence: number
    validation_status: string
    is_counterfeit?: boolean
  }
  processing_time: number
}

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
