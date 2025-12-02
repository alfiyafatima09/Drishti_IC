-- ============================================================
-- BEL IC Verification System - Database Schema
-- Target: Supabase (PostgreSQL)
-- Run this script in Supabase SQL Editor to create all tables
-- ============================================================

-- Enable UUID extension (usually enabled by default in Supabase)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- TABLE 1: ic_specifications (Golden Record)
-- ============================================================
CREATE TABLE IF NOT EXISTS ic_specifications (
    id SERIAL PRIMARY KEY,
    part_number VARCHAR(100) UNIQUE NOT NULL,
    manufacturer VARCHAR(100),
    pin_count INTEGER NOT NULL,
    package_type VARCHAR(50),
    description TEXT,
    datasheet_url VARCHAR(500),
    datasheet_path VARCHAR(500),
    voltage_min FLOAT,
    voltage_max FLOAT,
    operating_temp_min FLOAT,
    operating_temp_max FLOAT,
    electrical_specs JSONB DEFAULT '{}',
    source VARCHAR(50) DEFAULT 'MANUAL',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for ic_specifications
CREATE INDEX IF NOT EXISTS idx_ic_specs_part_number ON ic_specifications(part_number);
CREATE INDEX IF NOT EXISTS idx_ic_specs_manufacturer ON ic_specifications(manufacturer);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_ic_specifications_updated_at
    BEFORE UPDATE ON ic_specifications
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- TABLE 2: scan_history (Audit Trail)
-- ============================================================
CREATE TABLE IF NOT EXISTS scan_history (
    id SERIAL PRIMARY KEY,
    scan_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    ocr_text_raw TEXT,
    part_number_detected VARCHAR(100),
    part_number_verified VARCHAR(100),
    status VARCHAR(20) NOT NULL CHECK (status IN ('PASS', 'FAIL', 'PARTIAL', 'UNKNOWN', 'COUNTERFEIT')),
    confidence_score FLOAT,
    detected_pins INTEGER,
    expected_pins INTEGER,
    manufacturer_detected VARCHAR(100),
    action_required VARCHAR(20) DEFAULT 'NONE' CHECK (action_required IN ('NONE', 'SCAN_BOTTOM')),
    has_bottom_scan BOOLEAN DEFAULT FALSE,
    match_details JSONB,
    failure_reasons JSONB,
    message TEXT,
    was_manual_override BOOLEAN DEFAULT FALSE,
    operator_note TEXT,
    scanned_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Indexes for scan_history
CREATE INDEX IF NOT EXISTS idx_scan_history_scan_id ON scan_history(scan_id);
CREATE INDEX IF NOT EXISTS idx_scan_history_status ON scan_history(status);
CREATE INDEX IF NOT EXISTS idx_scan_history_scanned_at ON scan_history(scanned_at);
CREATE INDEX IF NOT EXISTS idx_scan_history_part_number ON scan_history(part_number_verified);

-- ============================================================
-- TABLE 3: datasheet_queue (Pending Scrape Queue)
-- ============================================================
CREATE TABLE IF NOT EXISTS datasheet_queue (
    id SERIAL PRIMARY KEY,
    part_number VARCHAR(100) UNIQUE NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_scanned_at TIMESTAMPTZ DEFAULT NOW(),
    scan_count INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PROCESSING', 'FAILED')),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for datasheet_queue
CREATE INDEX IF NOT EXISTS idx_datasheet_queue_status ON datasheet_queue(status);

CREATE TRIGGER update_datasheet_queue_updated_at
    BEFORE UPDATE ON datasheet_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- TABLE 4: fake_registry (Known Fakes)
-- ============================================================
CREATE TABLE IF NOT EXISTS fake_registry (
    id SERIAL PRIMARY KEY,
    part_number VARCHAR(100) UNIQUE NOT NULL,
    source VARCHAR(20) NOT NULL CHECK (source IN ('SYNC_NOT_FOUND', 'MANUAL_REPORT')),
    reason TEXT,
    reported_by VARCHAR(100),
    scrape_attempts INTEGER DEFAULT 0,
    manufacturers_checked JSONB,
    added_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fake_registry
CREATE INDEX IF NOT EXISTS idx_fake_registry_part_number ON fake_registry(part_number);

-- ============================================================
-- TABLE 5: sync_jobs (Job Tracking)
-- ============================================================
CREATE TABLE IF NOT EXISTS sync_jobs (
    id SERIAL PRIMARY KEY,
    job_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    status VARCHAR(20) NOT NULL DEFAULT 'IDLE' CHECK (status IN ('IDLE', 'PROCESSING', 'COMPLETED', 'ERROR', 'CANCELLED')),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    total_items INTEGER DEFAULT 0,
    processed_items INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    fake_count INTEGER DEFAULT 0,
    current_item VARCHAR(100),
    error_message TEXT,
    log JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for sync_jobs
CREATE INDEX IF NOT EXISTS idx_sync_jobs_job_id ON sync_jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_sync_jobs_status ON sync_jobs(status);

-- ============================================================
-- TABLE 6: settings (System Configuration)
-- ============================================================
CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    value_type VARCHAR(20) DEFAULT 'STRING' CHECK (value_type IN ('STRING', 'INTEGER', 'FLOAT', 'BOOLEAN', 'JSON')),
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by VARCHAR(100)
);

CREATE TRIGGER update_settings_updated_at
    BEFORE UPDATE ON settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- INSERT DEFAULT SETTINGS
-- ============================================================
INSERT INTO settings (key, value, value_type, description) VALUES
    ('datasheet_folder_path', '/data/datasheets', 'STRING', 'Directory where PDF datasheets are stored'),
    ('auto_queue_unknown', 'true', 'BOOLEAN', 'Automatically add unknown ICs to sync queue'),
    ('ocr_confidence_threshold', '70.0', 'FLOAT', 'Minimum OCR confidence to accept (0-100)'),
    ('scan_history_retention_days', '365', 'INTEGER', 'Days to keep scan history before cleanup'),
    ('enable_auto_cleanup', 'true', 'BOOLEAN', 'Automatically delete old scan records'),
    ('pin_detection_model', 'yolov8', 'STRING', 'Vision model for pin counting'),
    ('ocr_model', 'paddleocr', 'STRING', 'OCR engine to use'),
    ('max_scrape_retries', '3', 'INTEGER', 'Max retries before marking IC as fake'),
    ('scrape_timeout_seconds', '30', 'INTEGER', 'Timeout for each scrape request')
ON CONFLICT (key) DO NOTHING;

-- ============================================================
-- INSERT SAMPLE IC DATA (for testing)
-- ============================================================
INSERT INTO ic_specifications (part_number, manufacturer, pin_count, package_type, description, voltage_min, voltage_max, operating_temp_min, operating_temp_max, electrical_specs, source) VALUES
    ('LM555', 'Texas Instruments', 8, 'DIP', 'Precision Timer IC capable of producing accurate time delays or oscillation', 4.5, 16.0, 0, 70, '{"timing_accuracy": "1%", "output_current": "200mA", "supply_current": "3mA"}', 'MANUAL'),
    ('NE555', 'Texas Instruments', 8, 'DIP', 'General Purpose Single Bipolar Timer', 4.5, 16.0, 0, 70, '{"timing_accuracy": "1%", "output_current": "200mA"}', 'MANUAL'),
    ('ATMEGA328P', 'Microchip', 32, 'QFN', '8-bit AVR Microcontroller with 32KB Flash', 1.8, 5.5, -40, 85, '{"flash_memory": "32KB", "sram": "2KB", "eeprom": "1KB", "max_frequency": "20MHz"}', 'MANUAL'),
    ('LM7805', 'Texas Instruments', 3, 'TO-220', 'Positive 5V Voltage Regulator', 7.0, 35.0, 0, 125, '{"output_voltage": "5V", "output_current": "1.5A", "dropout_voltage": "2V"}', 'MANUAL'),
    ('LM317', 'Texas Instruments', 3, 'TO-220', 'Adjustable Positive Voltage Regulator', 3.0, 40.0, 0, 125, '{"output_voltage_range": "1.25V-37V", "output_current": "1.5A"}', 'MANUAL'),
    ('74HC595', 'NXP', 16, 'DIP', '8-bit Serial-In Parallel-Out Shift Register', 2.0, 6.0, -40, 125, '{"max_frequency": "100MHz", "output_current": "35mA"}', 'MANUAL'),
    ('LM741', 'Texas Instruments', 8, 'DIP', 'General Purpose Operational Amplifier', 5.0, 18.0, 0, 70, '{"gain_bandwidth": "1MHz", "slew_rate": "0.5V/us", "input_offset_voltage": "1mV"}', 'MANUAL'),
    ('CD4017', 'Texas Instruments', 16, 'DIP', 'Decade Counter/Divider with 10 Decoded Outputs', 3.0, 15.0, -40, 85, '{"max_frequency": "5MHz", "propagation_delay": "250ns"}', 'MANUAL')
ON CONFLICT (part_number) DO NOTHING;

-- ============================================================
-- VIEWS (Optional - for dashboard queries)
-- ============================================================

-- View for dashboard statistics
CREATE OR REPLACE VIEW dashboard_stats AS
SELECT
    (SELECT COUNT(*) FROM scan_history) as total_scans,
    (SELECT COUNT(*) FROM scan_history WHERE scanned_at >= CURRENT_DATE) as scans_today,
    (SELECT COUNT(*) FROM scan_history WHERE scanned_at >= CURRENT_DATE - INTERVAL '7 days') as scans_this_week,
    (SELECT COUNT(*) FROM scan_history WHERE status = 'PASS') as pass_count,
    (SELECT COUNT(*) FROM scan_history WHERE status = 'FAIL') as fail_count,
    (SELECT COUNT(*) FROM scan_history WHERE status = 'UNKNOWN') as unknown_count,
    (SELECT COUNT(*) FROM scan_history WHERE status = 'COUNTERFEIT') as counterfeit_count,
    (SELECT COUNT(*) FROM datasheet_queue) as queue_size,
    (SELECT COUNT(*) FROM fake_registry) as fake_registry_size,
    (SELECT COUNT(*) FROM ic_specifications) as database_ic_count;

-- ============================================================
-- ROW LEVEL SECURITY (Optional - for Supabase)
-- ============================================================
-- Uncomment these if you want to enable RLS

-- ALTER TABLE ic_specifications ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE scan_history ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE datasheet_queue ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE fake_registry ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE sync_jobs ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE settings ENABLE ROW LEVEL SECURITY;

-- Create policies for authenticated users (adjust as needed)
-- CREATE POLICY "Allow all for authenticated users" ON ic_specifications FOR ALL USING (true);
-- CREATE POLICY "Allow all for authenticated users" ON scan_history FOR ALL USING (true);
-- CREATE POLICY "Allow all for authenticated users" ON datasheet_queue FOR ALL USING (true);
-- CREATE POLICY "Allow all for authenticated users" ON fake_registry FOR ALL USING (true);
-- CREATE POLICY "Allow all for authenticated users" ON sync_jobs FOR ALL USING (true);
-- CREATE POLICY "Allow all for authenticated users" ON settings FOR ALL USING (true);

-- ============================================================
-- DONE!
-- ============================================================
-- Run this script in Supabase SQL Editor
-- All tables, indexes, triggers, and sample data will be created

